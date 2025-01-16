# examples/stock_monitor_ui.py

# pylint: disable=too-many-instance-attributes
# pylint: disable=no-member
# pylint: disable=unused-argument

"""
Stock monitor UI example.

Demonstrates integrating PynneX-based emitters/listeners into a Kivy GUI application.
It showcases a real-time price update loop (`StockService`), an alert/processing
component (`StockProcessor`), and a Kivy-based front-end (`StockView`) for
visualizing and setting stock alerts, all running asynchronously.
"""

import asyncio
from typing import Dict

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.clock import Clock
import logging

from utils import logger_setup
from stock_core import StockPrice, StockService, StockProcessor, StockViewModel
from pynnex import with_signals, slot

logger = logger_setup(__name__)
logger_setup("pynnex")
logger_setup("stock_core")


@with_signals
class StockView(BoxLayout):
    """
    Stock monitor UI view (Kivy layout).

    Displays:
      - A status label
      - A Start/Stop button
      - A dropdown to select stock codes
      - Current price and change
      - Alert setting/removal inputs
      - A display label for triggered alerts
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 10
        self.padding = 10

        # Area to display status
        self.status_label = Label(
            text="Press Start to begin", size_hint_y=None, height=40
        )
        self.add_widget(self.status_label)

        # Start/Stop button
        self.control_button = Button(text="Start", size_hint_y=None, height=40)
        self.add_widget(self.control_button)

        # Stock selection (using only AAPL for now, expand as needed)
        self.stock_spinner = Spinner(
            text="AAPL",
            values=("AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"),
            size_hint_y=None,
            height=40,
        )
        self.add_widget(self.stock_spinner)

        # Display price
        self.price_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40
        )
        self.price_label = Label(text="Price: --")
        self.change_label = Label(text="Change: --")
        self.price_layout.add_widget(self.price_label)
        self.price_layout.add_widget(self.change_label)
        self.add_widget(self.price_layout)

        # Alert setting layout
        self.alert_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40, spacing=5
        )

        self.lower_input = TextInput(
            text="", hint_text="Lower", multiline=False, size_hint=(0.3, 1)
        )
        self.upper_input = TextInput(
            text="", hint_text="Upper", multiline=False, size_hint=(0.3, 1)
        )
        self.set_alert_button = Button(text="Set Alert", size_hint=(0.2, 1))
        self.remove_alert_button = Button(text="Remove Alert", size_hint=(0.2, 1))

        self.alert_layout.add_widget(self.lower_input)
        self.alert_layout.add_widget(self.upper_input)
        self.alert_layout.add_widget(self.set_alert_button)
        self.alert_layout.add_widget(self.remove_alert_button)

        self.add_widget(self.alert_layout)

        # Alert display label
        self.alert_label = Label(text="", size_hint_y=None, height=40)
        self.add_widget(self.alert_label)

        self.add_widget(Widget(size_hint_y=1))

    def update_prices(self, prices: Dict[str, StockPrice]):
        """
        Update the displayed price information based on the currently selected stock.

        If the spinner's text matches a code in `prices`, update the price label
        and change label. Also shows a status message indicating successful update.
        """

        if self.stock_spinner.text in prices:
            price_data = prices[self.stock_spinner.text]
            self.price_label.text = f"Price: {price_data.price:.2f}"
            self.change_label.text = f"Change: {price_data.change:+.2f}%"
            self.status_label.text = "Prices updated"

    @slot
    def on_alert_added(self, code: str, alert_type: str, price: float):
        """
        Listener for handling newly triggered alerts.

        Updates the `alert_label` in the UI to inform the user about the alert.
        """

        self.alert_label.text = f"ALERT: {code} {alert_type} {price:.2f}"


class AsyncKivyApp(App):
    """
    A Kivy application that integrates with asyncio for background tasks.

    This class sets up the UI (`StockView`), the stock service, processor,
    and view model, and wires them together with emitters/listeners. It also provides
    a background task that keeps the UI responsive and handles graceful shutdown.
    """

    def __init__(self):
        super().__init__()
        self.title = "Stock Monitor"
        self.background_task_running = True
        self.tasks = []
        self.view = None
        self.service = None
        self.processor = None
        self.viewmodel = None
        self.async_lib = None

    def build(self):
        """
        Build the UI layout, connect emitters, and initialize the main components.
        """

        self.view = StockView()

        self.service = StockService()
        self.processor = StockProcessor()
        self.viewmodel = StockViewModel()

        # Connect emitters
        self.service.price_updated.connect(
            self.processor, self.processor.on_price_updated
        )
        self.processor.price_processed.connect(
            self.viewmodel, self.viewmodel.on_price_processed
        )
        self.viewmodel.prices_updated.connect(self.view, self.view.update_prices)

        # Alert related emitters
        self.processor.alert_triggered.connect(
            self.viewmodel, self.viewmodel.on_alert_triggered
        )
        self.processor.alert_settings_changed.connect(
            self.viewmodel, self.viewmodel.on_alert_settings_changed
        )
        self.viewmodel.alert_added.connect(self.view, self.view.on_alert_added)

        # Alert setting/removal emitters
        self.viewmodel.set_alert.connect(
            self.processor, self.processor.on_set_price_alert
        )
        self.viewmodel.remove_alert.connect(
            self.processor, self.processor.on_remove_price_alert
        )

        # Button event connections
        self.view.control_button.bind(on_press=self._toggle_service)
        self.view.set_alert_button.bind(on_press=self._set_alert)
        self.view.remove_alert_button.bind(on_press=self._remove_alert)

        Window.bind(on_request_close=self.on_request_close)

        return self.view

    def _toggle_service(self, instance):
        """
        Start or stop the StockService and StockProcessor based on the current button state.
        """

        if instance.text == "Start":
            self.service.start()
            self.processor.start()
            instance.text = "Stop"
            self.view.status_label.text = "Service started"
        else:
            self.service.stop()
            self.processor.stop()
            instance.text = "Start"
            self.view.status_label.text = "Service stopped"

    def _set_alert(self, instance):
        """
        Handle the "Set Alert" button press.

        Reads the lower/upper thresholds from the text fields and emits `set_alert`.
        """

        code = self.view.stock_spinner.text
        lower_str = self.view.lower_input.text.strip()
        upper_str = self.view.upper_input.text.strip()

        lower = float(lower_str) if lower_str else None
        upper = float(upper_str) if upper_str else None

        if not code:
            self.view.alert_label.text = "No stock selected"
            return

        self.viewmodel.set_alert.emit(code, lower, upper)
        self.view.alert_label.text = f"Alert set for {code}: lower={lower if lower else 'None'} upper={upper if upper else 'None'}"

    def _remove_alert(self, instance):
        """
        Handle the "Remove Alert" button press.

        Emits `remove_alert` for the currently selected stock code.
        """

        code = self.view.stock_spinner.text

        if not code:
            self.view.alert_label.text = "No stock selected"
            return

        self.viewmodel.remove_alert.emit(code)
        self.view.alert_label.text = f"Alert removed for {code}"

    async def background_task(self):
        """
        Background task that can be used for periodic checks or housekeeping.

        Runs concurrently with the Kivy event loop in async mode.
        """

        try:
            while self.background_task_running:
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    def on_request_close(self, *args):
        """
        Intercept the Kivy window close event to properly shut down.

        Returns True to indicate we handle the closing ourselves.
        """

        asyncio.create_task(self.cleanup())
        return True

    async def cleanup(self):
        """
        Perform a graceful shutdown by stopping background tasks and stopping the app.
        """

        self.background_task_running = False

        for task in self.tasks:
            if not task.done():
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.stop()

    async def async_run(self, async_lib=None):
        """
        Launch the Kivy app in an async context.

        Parameters
        ----------
        async_lib : module or None
            The async library to use (defaults to `asyncio`).
        """

        self._async_lib = async_lib or asyncio

        return await self._async_lib.gather(
            self._async_lib.create_task(super().async_run(async_lib=async_lib))
        )


async def main():
    """
    Main entry point for running the Kivy app in an async-friendly manner.
    """

    Clock.init_async_lib("asyncio")

    app = AsyncKivyApp()
    background_task = asyncio.create_task(app.background_task())
    app.tasks.append(background_task)

    try:
        await app.async_run()
    except Exception as e:
        print(f"Error during app execution: {e}")
    finally:
        for task in app.tasks:
            if not task.done():
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
