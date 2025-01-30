# src/examples/fastapi_socketio_worker_simple.py

"""FastAPI and SocketIO example with pynnex worker.

This example demonstrates how to use pynnex worker with FastAPI and python-socketio
to handle asynchronous berry checking tasks.

Required packages:
    - fastapi
    - python-socketio
    - uvicorn

Install dependencies:
    pip install fastapi python-socketio uvicorn

Run example:
    python fastapi_socketio_worker.py
    
Then open http://localhost:8000 in your browser.
"""

# Python standard library
import asyncio
import random
from contextlib import asynccontextmanager

# Third party packages
import socketio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Local packages
from pynnex import with_worker

# For debugging
# from pynnex._internal.log_config import setup_logging
# setup_logging()

# Create socketio server
sio = socketio.AsyncServer(async_mode='asgi')

@with_worker
class Worker:
    """Worker class that handles asynchronous berry checking tasks"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)

    def on_started(self):
        """Callback for worker started"""

        print("=== Worker started ===")

    def on_stopped(self):
        """Callback for worker stopped"""

        print("=== Worker stopped ===")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for FastAPI"""

    # startup
    print("Startup: loop=", asyncio.get_running_loop())
    worker = Worker(app)
    app.state.worker = worker
    worker.start()
    yield
    
    # shutdown
    print("Shutdown: cleaning up...")
    worker.stop()
    print("Shutdown: done")

@sio.event
async def connect(sid, environ):
    """Callback for client connected"""

    print("[Server] Client connected:", sid)

@sio.event
async def message(sid, data):
    """Handle incoming messages and queue berry checking tasks
    
    Expected data format:
    {
        'command': 'check_berry',
        'index': <integer>
    }    
    """

    print("[Server] Received message:", data)

    async def check_berry():
        """Task to check berry"""
        
        results = ["🍓 ripe!", "😖 too sour...", "📈 almost there.", "💩overripe..."]
        chosen = random.choice(results)
        msg = f"Berry #{data['index']} => {chosen}"
        print(msg)

        await sio.emit("task_done", msg, to=sid)

    if data['command'] == "check_berry":
        app.state.worker.queue_task(check_berry)

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def index():
    """Handler for root path"""

    return HTMLResponse("""
    <!doctype html>
    <html>
    <head><title>FastAPI-SocketIO Minimal Example</title></head>
    <body>
    <h1>Minimal Example: pynnex Worker with FastAPI & SocketIO</h1>
    <button onclick="sendMessage()">Check Berry</button>
    <div id="berry-results"></div>
    <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
    <script>
        let berryIndex = 1;
        var socket = io();

        socket.on('connect', function() {
            console.log('Socket connected!');
        });

        socket.on('message', function(msg) {
            console.log('Received from server:', msg);
            document.body.innerHTML += "<p>" + msg + "</p>";
        });

        socket.on('task_done', function(msg) {
            console.log('Received from server:', msg);
            const resultsDiv = document.getElementById('berry-results');
            const p = document.createElement('p');
            p.textContent = msg;
            resultsDiv.appendChild(p);
        });

        function sendMessage() {
            const msg = {
                command: "check_berry",
                index: berryIndex++
            };
            socket.emit("message", msg);
            console.log("sendMessage: ", msg);
        }          
    </script>
    </body>
</html>
""")

if __name__ == "__main__":
    uvicorn.run(
        socketio.ASGIApp(sio, other_asgi_app=app),
        host="127.0.0.1",
        port=8000)
