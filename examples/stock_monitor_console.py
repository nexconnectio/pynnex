# examples/stock_monitor_console.py

"""
Stock monitor console example.

This module demonstrates a command-line interface (CLI) for interacting
with the stock monitoring system. It ties together `StockService`,
`StockProcessor`, and `StockViewModel`, showing how emitters/listeners
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
from pynnex import with_emitters, listener

logger_setup("pynnex")
logger_setup("stock_core")
logger = logger_setup(__name__)


@with_emitters
class StockMonitorCLI:
    """
    Stock monitoring CLI interface.

    This class provides a text-based interactive prompt where users can:
      - View stock prices
      - Set or remove price alerts
      - Start/stop showing price updates
      - Quit the application
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
        """Print the menu."""
        print("\n===== MENU =====")
        print("stocks                 - List available stocks and prices")
        print("alert <code> <l> <u>   - Set price alert")
        print("remove <code>          - Remove price alert")
        print("list                   - List alert settings")
        print("showprices             - Start showing price updates (press Enter to stop)")
        print("quit                   - Exit")
        print("================\n")

    async def get_line_input(self, prompt="Command> "):
        """
        Get a line of user input asynchronously.
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: input(prompt)
        )

    @listener
    def on_price_updated(self, price_data: StockPrice):
        """
        Listener that responds to a single updated stock price.

        If `showing_prices` is True, prints the current prices and any triggered
        alerts to the console without re-displaying the main menu.
        """
        if self.showing_prices:
            print("Showing price updates (Press Enter to return to menu):")
            print("\nCurrent Prices:")

            # Print all stock prices
            for code, data in sorted(self.view_model.current_prices.items()):
                print(f"{code} ${data.price:.2f} ({data.change:+.2f}%)")

            print("\n(Press Enter to return to menu)")

            # Check for alerts in real-time
            alerts = []
            for code, data in self.view_model.current_prices.items():
                if code in self.view_model.alert_settings:
                    lower, upper = self.view_model.alert_settings[code]

                    if lower is not None and data.price <= lower:
                        alerts.append(
                            f"{code} price (${data.price:.2f}) below ${lower:.2f}"
                        )
                    if upper is not None and data.price >= upper:
                        alerts.append(
                            f"{code} price (${data.price:.2f}) above ${upper:.2f}"
                        )

            if alerts:
                print("\nAlerts:")
                for alert_msg in alerts:
                    print(alert_msg)

    async def process_command(self, command: str):
        """
        Process a single user command from the CLI.
        """
        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "stocks":
            print("\nAvailable Stocks:")
            print(f"{'Code':<6} {'Price':>10} {'Change':>8}  {'Company Name':<30}")
            print("-" * 60)

            desc = self.service.descriptions
            for code in desc:
                if code in self.view_model.current_prices:
                    price_data = self.view_model.current_prices[code]
                    print(
                        f"{code:<6} ${price_data.price:>9.2f} "
                        f"{price_data.change:>+7.2f}%  {desc[code]:<30}"
                    )

        elif cmd == "alert" and len(parts) == 4:
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

        elif cmd == "remove" and len(parts) == 2:
            code = parts[1].upper()

            if code in self.view_model.alert_settings:
                self.view_model.remove_alert.emit(code)
                print(f"Alert removed for {code}")
            else:
                print(f"No alert found for {code}")

        elif cmd == "list":
            if not self.view_model.alert_settings:
                print("\nNo alerts currently set.")
            else:
                print("\nCurrent alerts:")
                print(f"{'Code':^6} {'Lower':>10} {'Upper':>10}")
                print("-" * 30)
                for code, (lower, upper) in sorted(
                    self.view_model.alert_settings.items()
                ):
                    l_str = f"${lower:.2f}" if lower is not None else "None"
                    u_str = f"${upper:.2f}" if upper is not None else "None"
                    print(f"{code:<6} {l_str:>10} {u_str:>10}")

        elif cmd == "showprices":
            self.showing_prices = True
            print("Now showing price updates. Press Enter to return to menu.")

        elif cmd == "quit":
            self.running = False
            print("Exiting...")

        else:
            print(f"Unknown command: {command}")

    async def run(self):
        """
        Main execution loop for the CLI.
        """
        logger.debug(
            "[StockMonitorCLI][run] started current loop: %s %s",
            id(asyncio.get_running_loop()),
            asyncio.get_running_loop(),
        )

        main_loop = asyncio.get_running_loop()
        processor_started = asyncio.Future()

        # Connect service.start to processor's started emitter
        def on_processor_started():
            """
            Slot that is automatically called when the processor starts.
            """
            logger.debug("[StockMonitorCLI][run] processor started, starting service")
            self.service.start()

            def set_processor_started_true():
                """
                # Set processor_started future to True in the main loop
                """
                processor_started.set_result(True)

            main_loop.call_soon_threadsafe(set_processor_started_true)

        self.service.price_updated.connect(
            self.processor, self.processor.on_price_updated
        )
        self.processor.price_processed.connect(
            self.view_model, self.view_model.on_price_processed
        )
        self.view_model.price_updated.connect(self, self.on_price_updated)

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
    except (KeyboardInterrupt, SystemExit):
        pass
