# src/pynnex/examples/fastapi_socketio_qr.py

"""FastAPI and SocketIO example with PynneX worker for QR code generation.

This example demonstrates how to use PynneX worker with FastAPI and python-socketio
to handle asynchronous QR code generation tasks.

Required packages:
    - fastapi
    - python-socketio
    - uvicorn
    - qrcode

Install dependencies:
    pip install fastapi python-socketio uvicorn qrcode

Run example:
    python fastapi_socketio_worker_qr.py
    
Then open http://localhost:8000 in your browser.

(NOTE) 'checkberry.io' is a fictitious domain for demonstration.
"""

import base64
from io import BytesIO
from contextlib import asynccontextmanager
import uuid

import qrcode
import socketio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from pynnex import with_emitters, with_worker, emitter, listener

# Socket.IO and FastAPI setup
sio = socketio.AsyncServer(async_mode="asgi")
app = FastAPI()

# Controller with a Signal
@with_emitters
class QRController:
    """
    Controller with a Signal
    """

    @emitter
    def qrRequested(self, sid, data):
        """
        Signal emitted when the client asks to generate a QR code.
        """


# Worker that listens to the Signal
@with_worker
class QRWorker:
    """
    Worker that listens to the Signal
    """

    def __init__(self, controller: QRController):
        # Connect the signal to our slot
        controller.qrRequested.connect(self.on_qr_requested)

        # PynneX Worker lifecycle signals
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)

    def on_started(self):
        """
        Slot that is automatically called when the worker thread starts.
        """

        print("=== QRWorker started ===")

    def on_stopped(self):
        """
        Slot that is automatically called when the worker thread stops.
        """

        print("=== QRWorker stopped ===")

    @listener
    async def on_qr_requested(self, sid, payload):
        """
        Slot that is automatically called when 
        'controller.qrRequested' signal is emitted.
        Runs in the worker's thread+event loop.
        """

        unique_id = str(uuid.uuid4())

        # Create the QR code for a fictitious URL
        qr_data = f"https://checkberry.io/berry?id={unique_id}"
        
        print(f"[QRWorker] Generating QR code for: {qr_data}")
        qr_img = qrcode.make(qr_data)

        # 2) Convert image to Base64
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        b64_data = base64.b64encode(buffer.read()).decode("utf-8")

        # Emit back to the client
        #   key='qr_image' holds the Base64 data, 
        #   we also add a message about what it does
        await sio.emit("qr_response", {
            "qr_image": b64_data,
            "msg": f"Scan in Berry app to process ID: {unique_id}",
            "to": sid
        })

        print("[QRWorker] Sent QR code to client.")


# Lifespan context: initialize Worker
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context: initialize Worker
    """

    print("=== FastAPI startup ===")

    # Create controller and worker
    controller = QRController()
    worker = QRWorker(controller)
    worker.start()

    # Store references in app.state
    app.state.qr_controller = controller
    app.state.qr_worker = worker

    yield

    print("=== FastAPI shutdown ===")
    worker.stop()


app = FastAPI(lifespan=lifespan)

# Socket.IO events
@sio.event
async def connect(sid, environ):
    """
    Called whenever a client connects to the Socket.IO server.
    """

    print("[Server] Client connected:", sid)


@sio.event
async def request_qr(sid, data):
    """
    Client triggers "request_qr" event -> emit the signal 
    so that QRWorker on_qr_requested slot is called.
    """
    print("[Server] request_qr event received:", data)

    # We can pass additional info in 'data' if needed
    # e.g. if data has 'berry_id' or something
    app.state.qr_controller.qrRequested.emit(sid, data)


# Simple HTML endpoint
@app.get("/")
async def index():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
  <title>QR Code Demo (Signal-Slot Only)</title>
</head>
<body>
  <h1>QR Code Demo with PynneX Worker</h1>
  <button onclick="sendQRRequest()">Generate QR</button>
  <p id="info">Click the button to request a QR code.</p>
  <div id="qr-container"></div>

  <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
  <script>
    const socket = io();
    const infoP = document.getElementById("info");
    const qrDiv = document.getElementById("qr-container");

    socket.on("connect", () => {
      console.log("Socket connected.");
      infoP.innerText = "Connected. Click 'Generate QR' to get your code.";
    });

    // Listen for the server to respond with 'qr_response'
    socket.on("qr_response", (data) => {
      console.log("Received qr_response:", data);

      // Show message
      infoP.innerText = data.msg;

      // Show the QR code image
      const img = document.createElement("img");
      img.src = "data:image/png;base64," + data.qr_image;

      // Clear previous image if any
      qrDiv.innerHTML = "";
      qrDiv.appendChild(img);
    });

    function sendQRRequest() {
      const payload = { note: "Any extra info if needed" };
      socket.emit("request_qr", payload);
      infoP.innerText = "Generating QR code...";
    }
  </script>
</body>
</html>
""")


# Uvicorn + SocketIO ASGI
if __name__ == "__main__":
    uvicorn.run(
        socketio.ASGIApp(sio, other_asgi_app=app),
        host="127.0.0.1",
        port=8000
    )
