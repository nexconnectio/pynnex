# examples/stock_monitor_console.py

"""
Stock monitor console example.

This module demonstrates a command-line interface (CLI) for interacting
with the stock monitoring system. It ties together `StockService`,
`StockProcessor`, and `StockViewModel`, showing how signals/slots
flow between them to provide user commands and real-time price updates.

Usage:
  1. Instantiate the main `StockMonitorCLI` class with references
     to the service, processor, and view model.
  2. Run `cli.run()` in an async context to start the CLI loop.
  3. The user can type commands like "stocks", "alert", or "remove"
     to manage alerts and display prices.
"""

import asyncio
from typing import Dict
from utils import logger_setup
from stock_core import StockPrice, StockService, StockProcessor, StockViewModel
from pynnex import with_signals, slot

logger_setup("pynnex")
logger_setup("stock_core")
logger = logger_setup(__name__)


@with_signals
class StockMonitorCLI:
    """
    Stock monitoring CLI interface.

    This class provides a text-based interactive prompt where users can:
      - View stock prices
      - Set or remove price alerts
      - Start/stop showing price updates
      - Quit the application

    Attributes
    ----------
    service : StockService
        The worker responsible for generating stock prices.
    processor : StockProcessor
        The worker responsible for processing prices and handling alerts.
    view_model : StockViewModel
        A view-model that stores the latest prices and user alert settings.
    showing_prices : bool
        Whether the CLI is currently in "showprices" mode, continuously updating prices.
    running : bool
        Whether the CLI loop is active.
    """

    def __init__(
        self,
        service: StockService,
        processor: StockProcessor,
        view_model: StockViewModel,
    ):
        logger.debug("[StockMonitorCLI][__init__] started")
        self.service = service
        self.processor = processor
        self.view_model = view_model
        self.current_input = ""
        self.running = True
        self.showing_prices = False

    def print_menu(self):
        """Print the menu"""

        print("\n===== MENU =====")
        print("stocks            - List available stocks and prices")
        print("alert <code> <l> <u> - Set price alert")
        print("remove <code>     - Remove price alert")
        print("list              - List alert settings")
        print("showprices        - Start showing price updates (press Enter to stop)")
        print("quit              - Exit")
        print("================\n")

    async def get_line_input(self, prompt="Command> "):
        """
        Get a line of user input asynchronously.

        Parameters
        ----------
        prompt : str
            The prompt to display before reading user input.

        Returns
        -------
        str
            The user-inputted line.
        """

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: input(prompt)
        )

    @slot
    def on_prices_updated(self, prices: Dict[str, StockPrice]):
        """
        Respond to updated prices in the view model.

        If `showing_prices` is True, prints the current prices and any triggered alerts
        to the console without re-displaying the main menu.
        """

        # If we are in showprices mode, display current prices:
        if self.showing_prices:
            print("Showing price updates (Press Enter to return to menu):")
            print("\nCurrent Prices:")

            for code, data in sorted(self.view_model.current_prices.items()):
                print(f"{code} ${data.price:.2f} ({data.change:+.2f}%)")

            print("\n(Press Enter to return to menu)")

            alerts = []

            for code, data in prices.items():
                if code in self.view_model.alert_settings:
                    lower, upper = self.view_model.alert_settings[code]

                    if lower and data.price <= lower:
                        alerts.append(
                            f"{code} price (${data.price:.2f}) below ${lower:.2f}"
                        )

                    if upper and data.price >= upper:
                        alerts.append(
                            f"{code} price (${data.price:.2f}) above ${upper:.2f}"
                        )

            if alerts:
                print("\nAlerts:")

                for alert in alerts:
                    print(alert)

    async def process_command(self, command: str):
        """
        Process a single user command from the CLI.

        Supported commands:
          - stocks
          - alert <code> <lower> <upper>
          - remove <code>
          - list
          - showprices
          - quit
        """

        parts = command.strip().split()

        if not parts:
            return

        if parts[0] == "stocks":
            print("\nAvailable Stocks:")
            print(f"{'Code':<6} {'Price':>10} {'Change':>8}  {'Company Name':<30}")
            print("-" * 60)

            desc = self.service.descriptions

            for code in desc:
                if code in self.view_model.current_prices:
                    price_data = self.view_model.current_prices[code]
                    print(
                        f"{code:<6} ${price_data.price:>9.2f} {price_data.change:>+7.2f}%  {desc[code]:<30}"
                    )

        elif parts[0] == "alert" and len(parts) == 4:
            try:
                code = parts[1].upper()
                lower = float(parts[2])
                upper = float(parts[3])

                if code not in self.view_model.current_prices:
                    print(f"Unknown stock code: {code}")
                    return

                self.view_model.set_alert.emit(code, lower, upper)
                print(f"Alert set for {code}: lower={lower} upper={upper}")
            except ValueError:
                print("Invalid price values")

        elif parts[0] == "remove" and len(parts) == 2:
            code = parts[1].upper()

            if code in self.view_model.alert_settings:
                self.view_model.remove_alert.emit(code)
                print(f"Alert removed for {code}")

        elif parts[0] == "list":
            if not self.view_model.alert_settings:
                print("\nNo alerts currently set.")
            else:
                print("\nCurrent alerts:")
                print(f"{'Code':^6} {'Lower':>10} {'Upper':>10}")
                print("-" * 30)
                for code, (lower, upper) in sorted(
                    self.view_model.alert_settings.items()
                ):
                    print(f"{code:<6} ${lower:>9.2f} ${upper:>9.2f}")

        elif parts[0] == "showprices":
            self.showing_prices = True
            print("Now showing price updates. Press Enter to return to menu.")

        elif parts[0] == "quit":
            self.running = False
            print("Exiting...")

        else:
            print(f"Unknown command: {command}")

    async def run(self):
        """
        Main execution loop for the CLI.

        Connects signals between `service`, `processor`, and `view_model`,
        then continuously reads user input until the user exits.
        """

        logger.debug(
            "[StockMonitorCLI][run] started current loop: %s %s",
            id(asyncio.get_running_loop()),
            asyncio.get_running_loop(),
        )

        # Future for receiving started signal
        main_loop = asyncio.get_running_loop()
        processor_started = asyncio.Future()

        # Connect service.start to processor's started signal
        def on_processor_started():
            """Processor started"""

            logger.debug("[StockMonitorCLI][run] processor started, starting service")
            self.service.start()

            # Set processor_started future to True in the main loop
            def set_processor_started_true():
                """Set processor started"""

                logger.debug(
                    "[StockMonitorCLI][run] set_processor_started_true current loop: %s %s",
                    id(asyncio.get_running_loop()),
                    asyncio.get_running_loop(),
                )
                processor_started.set_result(True)

            main_loop.call_soon_threadsafe(set_processor_started_true)

        self.service.price_updated.connect(
            self.processor, self.processor.on_price_updated
        )
        self.processor.price_processed.connect(
            self.view_model, self.view_model.on_price_processed
        )
        self.view_model.prices_updated.connect(self, self.on_prices_updated)
        self.view_model.set_alert.connect(
            self.processor, self.processor.on_set_price_alert
        )
        self.view_model.remove_alert.connect(
            self.processor, self.processor.on_remove_price_alert
        )
        self.processor.alert_triggered.connect(
            self.view_model, self.view_model.on_alert_triggered
        )
        self.processor.alert_settings_changed.connect(
            self.view_model, self.view_model.on_alert_settings_changed
        )

        self.processor.started.connect(on_processor_started)
        self.processor.start()

        # Wait until processor is started and service is started
        await processor_started

        while self.running:
            if not self.showing_prices:
                self.print_menu()
                command = await self.get_line_input()
                await self.process_command(command)
            else:
                await self.get_line_input("")
                self.showing_prices = False

        self.service.stop()
        self.processor.stop()


async def main():
    """Main function"""
    service = StockService()
    view_model = StockViewModel()
    processor = StockProcessor()

    cli = StockMonitorCLI(service, processor, view_model)

    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
