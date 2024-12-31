# examples/thread_basic.py

"""
Thread Communication Example

This example demonstrates thread-safe communication between UI (main thread) and 
backend (worker thread) components using PynneX:

1. Main Thread:
   - UserView: UI component that displays data and handles user input
2. Worker Thread:
   - UserModel: Data model that manages user data
   - UserMediator: Mediates between View and Model

Architecture:
- View runs in main thread for UI operations
- Model and Mediator run in worker thread for data processing
- Signal/Slot connections automatically handle thread-safe communication
"""

import asyncio
import threading
import time
from pynnex import with_signals, signal, slot
from utils import logger_setup
logger_setup("pynnex")
logger = logger_setup(__name__)

@with_signals
class UserView:
    """UI component in main thread"""

    def __init__(self):
        self.current_user = None
        print("UserView created in main thread")

    @signal
    def login_requested(self):
        """Signal emitted when user requests login"""

    @signal
    def logout_requested(self):
        """Signal emitted when user requests logout"""

    @slot
    def on_user_logged_in(self, user_data):
        """Slot called when login succeeds (automatically runs in main thread)"""

        self.current_user = user_data
        print(f"[Main Thread] UI Updated: Logged in as {user_data['name']}")

    @slot
    def on_user_logged_out(self):
        """Slot called when logout completes"""
        self.current_user = None
        print("[Main Thread] UI Updated: Logged out")

    def request_login(self, username, password):
        """UI action to request login"""

        print(f"[Main Thread] Login requested for user: {username}")
        self.login_requested.emit(username, password)

    def request_logout(self):
        """UI action to request logout"""

        if self.current_user:
            print(f"[Main Thread] Logout requested for {self.current_user['name']}")
            self.logout_requested.emit()


@with_signals
class UserModel:
    """Data model in worker thread"""

    def __init__(self):
        self.users = {
            "admin": {"password": "admin123", "name": "Administrator", "role": "admin"}
        }
        print("[Worker Thread] UserModel created")

    @signal
    def user_authenticated(self):
        """Signal emitted when user authentication succeeds"""

    @signal
    def user_logged_out(self):
        """Signal emitted when user logout completes"""

    def authenticate_user(self, username, password):
        """Authenticate user credentials (runs in worker thread)"""
        print(f"[Worker Thread] Authenticating user: {username}")
        # Simulate database lookup
        time.sleep(1)

        user = self.users.get(username)
        if user and user["password"] == password:
            print(f"[Worker Thread] Authentication successful for {username}")
            self.user_authenticated.emit(user)
            return True
        return False

    def logout_user(self):
        """Process user logout (runs in worker thread)"""

        print("[Worker Thread] Processing logout")
        # Simulate cleanup
        time.sleep(0.5)
        self.user_logged_out.emit()


@with_signals
class UserMediator:
    """Mediator between View and Model in worker thread"""

    def __init__(self, view: UserView, model: UserModel):
        self.view = view
        self.model = model

        # Connect View signals to Mediator slots
        view.login_requested.connect(self, self.on_login_requested)
        view.logout_requested.connect(self, self.on_logout_requested)

        # Connect Model signals to View slots
        model.user_authenticated.connect(view, view.on_user_logged_in)
        model.user_logged_out.connect(view, view.on_user_logged_out)

        print("UserMediator created in worker thread")

    @slot
    def on_login_requested(self, username, password):
        """Handle login request from View (automatically runs in worker thread)"""

        print(f"[Worker Thread] Mediator handling login request for {username}")
        self.model.authenticate_user(username, password)

    @slot
    def on_logout_requested(self):
        """Handle logout request from View"""

        print("[Worker Thread] Mediator handling logout request")
        self.model.logout_user()


def run_worker_thread(view):
    """Worker thread function"""

    print(f"[Worker Thread] Started: {threading.current_thread().name}")

    # Create Model and Mediator in worker thread
    async def create_model_and_mediator():
        _model = UserModel()
        _mediator = UserMediator(view, _model)

    # Create and run event loop for worker thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Keep worker thread running
    try:
        loop.create_task(create_model_and_mediator())
        loop.run_forever()
    finally:
        loop.close()


async def main():
    """Main function"""

    # Create View in main thread
    view = UserView()

    # Start worker thread
    worker = threading.Thread(target=run_worker_thread, args=(view,))
    worker.daemon = True
    worker.start()

    # Wait for worker thread to initialize
    await asyncio.sleep(0.1)

    print("\n=== Starting user interaction simulation ===\n")

    # Simulate user interactions
    view.request_login("admin", "admin123")
    await asyncio.sleep(1.5)  # Wait for login process

    view.request_logout()
    await asyncio.sleep(1)  # Wait for logout process

    print("\n=== Simulation completed ===")


if __name__ == "__main__":

    asyncio.run(main())
