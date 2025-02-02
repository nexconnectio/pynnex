# src/pynnex/examples/fastapi_socketio_stock_monitor.py

"""
stock_monitor_ui_fastapi.py (Bootstrap table version)

Usage:
  1) Put this file and stock_core.py in the same directory.
  2) pip install fastapi uvicorn python-socketio pynnex
  3) python stock_monitor_ui_fastapi.py
  4) Open http://127.0.0.1:8000 in your browser.
"""

import asyncio
from dataclasses import dataclass
import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from typing import Dict, Optional

# Import classes from stock_core.py
from stock_core import (
    StockService,
    StockProcessor,
    StockViewModel,
    StockPrice,
)

from pynnex import with_signals, signal,slot

# Create Socket.IO server
sio = socketio.AsyncServer(async_mode="asgi")

@dataclass
class CandleState:
    """
    State for a single symbol's candle data.
    """
    
    tick_count: int = 0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = float("inf")
    close_price: float = 0.0

    def reset(self):
        self.tick_count = 0
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = float("inf")
        self.close_price = 0.0

@with_signals
class CandleAggregator:
    """
    Aggregates 1-second StockPrice data into 5-second candles (OHLC) for multiple symbols.

    - We accumulate 5 ticks per symbol -> form one candle: (open, close, low, high).
    - Then emit 'candle_5s' signal to the UI Bridge.

    Example usage:
      1) Listen to `processor.price_processed.connect(aggregator, aggregator.on_price_updated)`.
      2) aggregator emits `candle_5s` whenever a symbol completes 5 ticks.
    """

    def __init__(self):
      self.symbol_states = {}

    def _get_state(self, symbol: str) -> CandleState:
        """
        Internal helper: Get or create a CandleState object for a given symbol.
        """

        if symbol not in self.symbol_states:
            self.symbol_states[symbol] = CandleState()

        return self.symbol_states[symbol]

    @slot
    def on_price_updated(self, data: StockPrice):
        """
        Called whenever 'price_updated' is emitted from the ViewModel,
        
        We'll accumulate 5 ticks for the symbol, then emit 'candle_5s' when that
        symbol completes 5 ticks.
        """
        
        current_price = data.price

        state = self._get_state(data.symbol)

        if state.tick_count == 0:
            # If first tick, initialize open/high/low/close to current price
            state.open_price = current_price
            state.high_price = current_price
            state.low_price = current_price
        else:
            if current_price > state.high_price:
                state.high_price = current_price
            if current_price < state.low_price:
                state.low_price = current_price

        state.close_price = current_price
        state.tick_count += 1

        # If 5 ticks (5 seconds) accumulated, form one candle
        if state.tick_count >= 5:
            o = state.open_price
            h = state.high_price
            l = state.low_price
            c = state.close_price

            state.reset()

            # Emit 'candle_5s' signal
            self.candle_5s.emit({
                "symbol": data.symbol,
                "open": o,
                "close": c,
                "low": l,
                "high": h
            })

    def reset_aggregator(self, symbol: str = None):
        """
        Optional method to reset data for a specific symbol or for all symbols.
        """

        if symbol:
            if symbol in self.symbol_states:
                self.symbol_states[symbol].reset()
        else:
            for st in self.symbol_states.values():
                st.reset()

    @signal
    def candle_5s(self, candle_data: dict):
        """
        Emitted after every 5 ticks for each symbol to form one candle.
        Payload example:
          {
            "symbol": "AAPL",
            "open": 180.0,
            "high": 183.5,
            "low": 179.8,
            "close": 182.1
          }
        """
        pass

# A UI Bridge for pushing data to Socket.IO
@with_signals
class StockUIBridge:
    def __init__(self, viewmodel: StockViewModel, aggregator: CandleAggregator):
        viewmodel.price_updated.connect(self, self.on_price_updated)
        viewmodel.price_updated.connect(aggregator, aggregator.on_price_updated)
        viewmodel.alert_added.connect(self, self.on_alert_added)
        aggregator.candle_5s.connect(self, self.on_candle_5s)

    @slot
    async def on_price_updated(self, price_data: StockPrice):
        """
        Called whenever 'price_updated' is emitted from the ViewModel,
        we'll emit 'prices_update' to the UI Bridge.
        """

        # Convert data to a simpler dict for JSON
        payload = {
            "symbol": price_data.symbol,
            "price": round(price_data.price, 2),
            "change": round(price_data.change, 2),
            "timestamp": price_data.timestamp,
        }
        asyncio.create_task(sio.emit("prices_update", payload))

    @slot
    def on_alert_added(self, symbol: str, alert_type: str, price: float):
        """
        Called whenever 'alert_added' is emitted from the ViewModel,
        we'll emit 'alert_update' to the UI Bridge.
        """

        alert_data = {
            "symbol": symbol,
            "alert_type": alert_type,
            "price": round(price, 2),
        }
        asyncio.create_task(sio.emit("alert_update", alert_data))

    @slot
    def on_candle_5s(self, candle_data: Dict[str, float]):
        """
        Called whenever 'candle_5s' is emitted from the CandleAggregator,
        we'll emit 'candle_update' to the UI Bridge.
        """

        asyncio.create_task(sio.emit("candle_update", candle_data))

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    """

    print("=== FastAPI: lifespan startup ===")

    service = StockService()
    processor = StockProcessor()
    viewmodel = StockViewModel()
    aggregator = CandleAggregator()

    service.price_updated.connect(processor, processor.on_price_updated)
    processor.price_processed.connect(viewmodel, viewmodel.on_price_processed)
    processor.alert_triggered.connect(viewmodel, viewmodel.on_alert_triggered)
    processor.alert_settings_changed.connect(viewmodel, viewmodel.on_alert_settings_changed)
    viewmodel.set_alert.connect(
        processor, processor.on_set_price_alert
    )
    viewmodel.remove_alert.connect(
        processor, processor.on_remove_price_alert
    )

    app.state.stock_service = service
    app.state.stock_processor = processor
    app.state.stock_viewmodel = viewmodel
    app.state.aggregator = aggregator

    # Start workers
    service.start()
    processor.start()

    # Bridge for pushing updates to browser
    ui_bridge = StockUIBridge(viewmodel, aggregator)
    app.state.ui_bridge = ui_bridge

    yield

    print("=== FastAPI: lifespan shutdown ===")
    processor.stop()
    service.stop()

app = FastAPI(lifespan=lifespan)

# Wrap with socketio
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """
    Called whenever a client connects to the Socket.IO server.
    """

    print(f"[Socket.IO] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    """
    Called whenever a client disconnects from the Socket.IO server.
    """

    print(f"[Socket.IO] Client disconnected: {sid}")

@sio.event
async def start_service(sid, data):
    """
    Called whenever a client sends a 'start_service' event.
    """

    app.state.stock_service.start()
    app.state.stock_processor.start()
    await sio.emit("service_status", {"status": "started"}, to=sid)
    print("[Socket.IO] Received start_service")

@sio.event
async def stop_service(sid, data):
    """
    Called whenever a client sends a 'stop_service' event.
    """

    app.state.stock_service.stop()
    app.state.stock_processor.stop()
    await sio.emit("service_status", {"status": "stopped"}, to=sid)
    print("[Socket.IO] Received stop_service")

@sio.event
async def set_alert(sid, data):
    """
    Called whenever a client sends a 'set_alert' event.
    """

    symbol = data.get("symbol")
    lower = data.get("lower")
    upper = data.get("upper")

    vm = app.state.stock_viewmodel
    vm.set_alert.emit(symbol, lower, upper)

    await sio.emit("alert_ack", {"msg": f"Set alert for {symbol} (lower={lower}, upper={upper})"}, to=sid)

@sio.event
async def remove_alert(sid, data):
    """
    Called whenever a client sends a 'remove_alert' event.
    """

    symbol = data.get("symbol")
    vm = app.state.stock_viewmodel
    vm.remove_alert.emit(symbol)

    await sio.emit("alert_ack", {"msg": f"Removed alert for {symbol}"}, to=sid)

@sio.event
def reset_aggregator(sid, data):
    """
    Called whenever a client sends a 'reset_aggregator' event.
    """

    symbol = data.get("symbol")

    if symbol:
        aggregator = app.state.aggregator
        aggregator.reset_aggregator(symbol)
        print(f"Aggregator reset for {symbol}")

# HTML endpoint with Bootstrap-based table
@app.get("/")
async def index():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
  <title>Stock Monitor (FastAPI + Socket.IO + Bootstrap)</title>
  <!-- Bootstrap CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="https://unpkg.com/ag-grid-community/dist/styles/ag-grid.css">
  <link rel="stylesheet" href="https://unpkg.com/ag-grid-community/dist/styles/ag-theme-alpine.css">
  <script src="https://unpkg.com/ag-grid-community/dist/ag-grid-community.min.noStyle.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>

  <style>
    body {
      padding: 20px;
    }
    .ag-theme-alpine .ag-row:hover {
      background-color: #f5f5f5 !important;
    }
    .ag-theme-alpine .ag-row.ag-row-selected {
      background-color: #d1e7dd !important;
    }
  </style>
</head>
<body>
  <div class="container">

    <h1 class="mb-3">Stock Monitor Demo</h1>

    <h3>Prices</h3>
    <div id="pricesGrid" style="width: 100%; height: 300px;" class="ag-theme-alpine"></div>

    <div class="mt-3">
      <h3>Candle Chart (5s)</h3>
      <div id="candleChart" style="width: 100%; height: 400px;"></div>
    </div>

    <div class="mt-3">
      <h3>Alerts</h3>      
    </div>

    <!-- Alert settings -->
    <div class="row mb-4">
      <div class="col-md-3">
        <label for="lowerThresh" class="form-label fw-bold">Lower</label>
        <input type="number" class="form-control" id="lowerThresh" placeholder="e.g. 170">
      </div>
      <div class="col-md-3">
        <label for="upperThresh" class="form-label fw-bold">Upper</label>
        <input type="number" class="form-control" id="upperThresh" placeholder="e.g. 190">
      </div>
    </div>

    <div class="mb-3">
      <button class="btn btn-success me-2" onclick="setAlert()">Set Alert</button>
      <button class="btn btn-danger" onclick="removeAlert()">Remove Alert</button>
    </div>

    <div id="alertsArea" class="mt-2"></div>
  </div> <!-- /container -->

  <!-- Socket.IO script -->
  <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
  <!-- Bootstrap JS (optional for certain components) -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/js/bootstrap.bundle.min.js"></script>

  <script>
    const socket = io();
    let gridOptions = null;
    let candleChart = null;
    let candleOption = null;
    let currentSymbol = "AAPL";
    let stockDataMap = {};

    function initPricesTable() {
      const gridDiv = document.querySelector('#pricesGrid');

      const columnDefs = [
        { field: 'symbol', headerName: 'Symbol', sortable: true },
        { 
          field: 'price', 
          headerName: 'Price', 
          sortable: true, 
          valueFormatter: params => params.value ? params.value.toFixed(2) : '' 
        },
        { 
          field: 'change', 
          headerName: 'Change (%)', 
          sortable: true, 
          cellClass: params => params.value >= 0 ? 'text-success' : 'text-danger',
          valueFormatter: params => params.value ? params.value.toFixed(2) : '' 
        }
      ];
      
      function updateSymbolAndChart(symbol) {
          currentSymbol = symbol;
          initCandleChart();
          socket.emit("reset_aggregator", { symbol: currentSymbol });
      }
      
      gridOptions = {
        columnDefs: columnDefs,
        rowData: [],
        rowSelection: 'single',
        getRowId: (params) => {
          return params.data.symbol;
        },
        onRowClicked: onRowClicked,
        onGridReady: function (params) {
          gridOptions.api = params.api;
          gridOptions.columnApi = params.columnApi;
                        
          // Wait for the first data to arrive
          const waitForFirstData = setInterval(() => {
            const firstNode = params.api.getDisplayedRowAtIndex(0);
            if (firstNode) {
              clearInterval(waitForFirstData);
              firstNode.setSelected(true);
              params.api.redrawRows();
              currentSymbol = firstNode.data.symbol;
              initCandleChart();
              updateSymbolAndChart(currentSymbol);
            }
          }, 100);
          
          setTimeout(() => clearInterval(waitForFirstData), 10000);
        }
      }

      agGrid.createGrid(gridDiv, gridOptions);

      // Change the chart target when a row is clicked
      function onRowClicked(event) {
        updateSymbolAndChart(event.data.symbol);
      }
    }

    function initCandleChart() {
      if (!candleChart) {
        let chartDom = document.getElementById("candleChart");
        candleChart = echarts.init(chartDom);
      }
      
      candleOption = {
        backgroundColor: '#f8f9fa',
        xAxis: [{
          type: 'category',
          data: []
        }],
        yAxis: [{ 
          scale: true
        }],
        series: [{
          type: 'candlestick',
          name: currentSymbol,
          data: []
        }],
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        }
      };
      candleChart.setOption(candleOption, { notMerge: true });
    }

    socket.on('connect', () => {
      console.log("Socket connected");
    });

    socket.on('service_status', (data) => {
      console.log("Service status:", data);
    });

    // Real-time prices update (data = StockPrice)
    socket.on('prices_update', (data) => {
      if (!gridOptions || !gridOptions.api) {
        console.log("Grid not ready yet. Skipping update.");
        return;
      }

      // data: { symbol, price, change, timestamp, ... }
      const symbol = data.symbol;
      const price = data.price;
      const change = data.change;
      const row = { symbol, price, change };

      if (stockDataMap[symbol]) {
        gridOptions.api.applyTransaction({ 
          update: [
            row
          ] 
        });
      } else {
        gridOptions.api.applyTransaction({ add: [row] });
      }

      stockDataMap[symbol] = row;
    });

    socket.on("candle_update", (candle) => {
      if (candle.symbol !== currentSymbol) {
        return;
      }

      let now = new Date();
      let hh = String(now.getHours()).padStart(2, '0');
      let mm = String(now.getMinutes()).padStart(2, '0');
      let ss = String(now.getSeconds()).padStart(2, '0');
      let label = `${hh}:${mm}:${ss}`;
      candleOption.xAxis[0].data.push(label);

      const candleData = [candle.open, candle.close, candle.low, candle.high];
      candleOption.series[0].data.push(candleData);
      candleChart.setOption(candleOption);
    });

    // Alerts
    socket.on('alert_update', (data) => {
      // data: { symbol, alert_type, price }
      let alertHTML = `
        <div class="alert alert-warning alert-dismissible fade show" role="alert">
          <strong></strong> ${data.symbol} ${data.alert_type} @ ${data.price}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
      
      const alertsDiv = document.getElementById('alertsArea');
      alertsDiv.insertAdjacentHTML('afterbegin', alertHTML);
      const alerts = alertsDiv.getElementsByClassName('alert');

      if (alerts.length > 5) {
        alertsDiv.removeChild(alerts[alerts.length - 1]);
      }
    });

    // Acknowledge for set/remove alert
    socket.on('alert_ack', (data) => {
      console.log("alert_ack:", data);
    });

    function startService() {
      socket.emit("start_service", {});
    }

    function stopService() {
      socket.emit("stop_service", {});
    }

    function setAlert() {
      let lower = document.getElementById("lowerThresh").value;
      let upper = document.getElementById("upperThresh").value;
      let lowerVal = lower ? parseFloat(lower) : null;
      let upperVal = upper ? parseFloat(upper) : null;

      socket.emit("set_alert", { symbol: currentSymbol, lower: lowerVal, upper: upperVal });
    }

    function removeAlert() {
      socket.emit("remove_alert", { symbol: currentSymbol });
    }

    document.addEventListener('DOMContentLoaded', function() {
      initPricesTable();
      initCandleChart();
    });
  </script>
</body>
</html>
""")

if __name__ == "__main__":
    uvicorn.run(
        socketio.ASGIApp(sio, other_asgi_app=app),
        host="127.0.0.1",
        port=8000
    )
