<!-- docs/examples.md -->

# Examples

This document provides an overview and explanation of the included examples. Each example demonstrates various aspects of using PynneX, from basic emitter-listener handling to more complex threaded worker patterns and UI integrations.

## Requirements

PynneX requires **Python 3.10** or higher, plus a running `asyncio` event loop for any async usage.

## Table of Contents
  
- [Examples](#examples)
  - [Requirements](#requirements)
  - [Table of Contents](#table-of-contents)
    - [emitter\_basic.py (source)](#emitter_basicpy-source)
  - [emitter\_async.py (source)](#emitter_asyncpy-source)
  - [emitter\_function\_listeners.py (source)](#emitter_function_listenerspy-source)
  - [emitter\_lambda\_listeners.py (source)](#emitter_lambda_listenerspy-source)
  - [thread\_basic.py (source)](#thread_basicpy-source)
  - [thread\_worker.py (source)](#thread_workerpy-source)
  - [stock\_monitor\_simple.py (source)](#stock_monitor_simplepy-source)
  - [stock\_monitor\_console.py (source)](#stock_monitor_consolepy-source)
  - [stock\_monitor\_ui.py (source)](#stock_monitor_uipy-source)
  - [stock\_core.py (source)](#stock_corepy-source)
  - [fastapi\_socketio\_simple.py (source)](#fastapi_socketio_simplepy-source)
  - [fastapi\_socketio\_qr.py (source)](#fastapi_socketio_qrpy-source)
  - [fastapi\_socketio\_stock\_monitor.py (source)](#fastapi_socketio_stock_monitorpy-source)

---

### emitter_basic.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_basic.py)
**Purpose**: Introduces the most basic usage of PynneX:
- Defining emitters on a class (`@nx_emitter`, aliases: `@emitter`, `@signal`, `@publisher`)
- Defining synchronous listeners
- Connecting emitters to listeners and emitting emitters

**What it demonstrates**:
- Simple increment of a counter
- Immediate synchronous listener response

**Scenario:**
- User interacts with Counter through a simple console input prompt
- Counter emits an emitter when its value changes, triggering the on_count_changed method in Display class
- Display processes the new value synchronously (with a 1-second simulated delay), blocking the main thread

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main (asyncio main)
    participant C as Counter
    participant D as Display

    M->>M: Prompt user input ("> ")
    alt line == "q"
        M->>M: User quits the loop
        M->>M: End program
    else line != "q"
        M->>C: counter.increment()
        C->>C: self.count += 1
        C->>C: Print "Counter incremented to: {count}"
        C->>C: count_changed.emit(count)
        C->>D: on_count_changed(value)
        D->>D: Print "Display processing count: {value}"
        D->>D: time.sleep(1)
        D->>D: self.last_value = value
        D->>D: Print "Display finished processing: {value}"
        note right of D: Synchronous processing blocks main thread
        D->>M: Control returns after synchronous processing
        M->>M: Loop continues until user presses 'q'
    end
```

Use this as a starting point if you’re new to PynneX. There’s no threading or async complexity—just a straightforward emitter-listener mechanism.

---

## emitter_async.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_async.py)
**Purpose**: Showcases how to handle asynchronous listeners:
- Async listeners using `@nx_listener`(Qt alias: `@slot`, Pub/Sub alias: `@subscriber`) with `async def`
- Emitting emitters that trigger async processing
- Demonstrates asynchronous delays (`await asyncio.sleep`)

**What it demonstrates**:
- Emitter connection with asynchronous listeners
- Combination of @nx_listener decorator with async functions
- Non-blocking operation handling

**Scenario:**
- User interacts with Counter through a simple console input prompt
- Counter emits an emitter when its value changes, triggering the async on_count_changed method in AsyncDisplay class
- AsyncDisplay processes the new value asynchronously (with a 1-second simulated delay), without blocking the main thread

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main (asyncio main)
    participant C as Counter
    participant D as AsyncDisplay

    M->>M: Prompt user input ("> ")
    alt line == "q"
        M->>M: User quits the loop
        M->>M: End program
    else line != "q"
        M->>C: counter.increment()
        C->>C: self.count += 1
        C->>C: count_changed.emit(self.count)
        note right of C: Emitter emission triggers async listener in AsyncDisplay
        C->>D: on_count_changed(value)
        note right of D: Async listener execution starts
        D->>D: print("Display processing count: value")
        D->>D: await asyncio.sleep(1)
        D->>D: self.last_value = value
        D->>D: print("Display finished processing: value")
        note right of D: Async listener completes
        D->>M: Control returns to main
        M->>M: await asyncio.sleep(0.1) for processing
        M->>M: Loop continues until user presses 'q'
    end
```

This example is ideal for learning how to integrate async operations into your event-driven code.

---

## emitter_function_listeners.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_function_listeners.py)
**Purpose**: Showcases how to use standalone functions as listeners:
- Using standalone functions as listeners without classes
- Demonstrates how to connect emitters to standalone functions
- Shows how to use functions as listeners without decorators

**What it demonstrates**:
- Flexibility of callable objects as listeners
- Simple way to use functions as listeners without classes
- Basic pattern for emitter-listener connections

**Scenario:**
- The user interacts with a console CLI (`Counter`) to increment the counter.
- The counter emits an emitter when the count changes, which triggers the `print_value` function.
- The function prints the current count value.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main
    participant C as Counter
    participant F as Function Listener (print_value)
    participant U as User Input

    Note over M: Program starts
    M->>C: Create Counter instance
    M->>C: Connect count_changed to print_value function

    loop Until 'q' entered
        U->>M: Enter input
        alt input != 'q'
            M->>C: counter.increment()
            C->>C: self.count += 1
            C->>C: Print "Counter incremented to: {count}"
            C->>C: count_changed.emit(count)
            C->>F: print_value(count)
            F->>F: Print "Function Listener received value: {count}"
        else input == 'q'
            M->>M: Break loop
        end
    end

    Note over M: Program ends
```

This example is a good starting point for learning how PynneX can be used in a functional programming style, especially for developers who prefer non-class-based approaches.

---

## emitter_lambda_listeners.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_lambda_listeners.py)
**Purpose**: showcases how to use lambda functions as listeners:
- Demonstrates how to connect emitters to lambda functions
- Shows how to use lambda functions as listeners without classes

**What it demonstrates**:
- Flexibility of lambda functions as listeners
- Quick implementation of simple inline tasks
- Emitter-listener system's flexibility

**Scenario:**
- The user interacts with a console CLI (`Counter`) to increment the counter.
- The counter emits an emitter when the count changes, which triggers the lambda function.
- The lambda function prints the current count value.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main
    participant C as Counter
    participant L as Lambda Listener
    participant U as User Input

    Note over M: Program starts
    M->>C: Create Counter instance
    M->>C: Connect count_changed to lambda v: print(f"Lambda Listener received: {v}")

    loop Until 'q' entered
        U->>M: Enter input
        alt input != 'q'
            M->>C: counter.increment()
            C->>C: self.count += 1
            C->>C: Print "Counter incremented to: {count}"
            C->>C: count_changed.emit(count)
            C->>L: lambda(count)
            L->>L: Print "Lambda Listener received: {count}"
        else input == 'q'
            M->>M: Break loop
        end
    end

    Note over M: Program ends
```

This example showcases PynneX's flexibility, particularly useful for quick listener implementations for simple tasks. Lambda functions allow for simple processing of emitters without the need for separate function or method definitions.

---

## thread_basic.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/thread_basic.py)
**Purpose**: Demonstrates thread-safe communication between main and worker threads using emitters:
- Main thread hosts a user interface object (`UserView`)
- Worker thread hosts data model and mediator (`UserModel`, `UserMediator`)
- Emitters and listeners handle thread-safe calls between threads

**What it demonstrates**:
- How emitters and listeners automatically handle thread boundary crossings
- Running a worker thread with its own event loop
- Ensuring UI updates occur in the main thread, even though data processing happens elsewhere

**Scenario:**
- The user interacts with a console CLI (`UserView`) to log in.
- The `UserView` emits an emitter when the user logs in, which triggers the `on_login_requested` listener in `UserModel`.
- The `UserModel` authenticates the user and emits an emitter when the authentication is successful, which triggers the `on_user_logged_in` listener in `UserView`.
- The `UserView` updates the UI to reflect the logged-in state.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main Thread (UserView)
    participant W as Worker Thread (UserModel & UserMediator)

    Note over M: UserView is created in main thread
    M->>M: request_login("admin", "admin123")
    M->>M: login_requested.emit("admin", "admin123")

    Note over W: Worker Thread running event loop
    M->>W: on_login_requested("admin", "admin123") via Mediator
    W->>W: UserMediator calls UserModel.authenticate_user("admin", "admin123")
    W->>W: Simulate DB lookup (sleep)
    alt Credentials correct
        W->>W: user_authenticated.emit(user_data)
        W->>M: on_user_logged_in(user_data)
        M->>M: current_user = user_data
        M->>M: print("Logged in as Administrator")
    else Credentials incorrect
        W->>W: No emitter emitted
    end

    Note over M: After login, user requests logout
    M->>M: request_logout()
    M->>M: logout_requested.emit()

    M->>W: on_logout_requested() via Mediator
    W->>W: UserModel.logout_user()
    W->>W: Simulate cleanup (sleep)
    W->>W: user_logged_out.emit()

    W->>M: on_user_logged_out()
    M->>M: current_user = None
    M->>M: print("Logged out")

    Note over M: Interaction complete
```

This is useful for scenarios where you have a separate thread doing background work and need to update the main thread’s UI or state safely.

---

## thread_worker.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/thread_worker.py)
**Purpose**: Introduces the `@nx_with_worker`(aliases: `@with_worker`) pattern:
- A `ImageProcessor` class running in a worker thread
- Task queuing with `queue_task`
- Emitter emission from a worker thread to the main thread

**What it demonstrates**:
- Creating a dedicated worker event loop using `@nx_with_worker`
- Scheduling asynchronous tasks on the worker thread (`queue_task`)
- Emitting emitters from the worker to the main thread (`processing_complete`, `batch_complete`)
- Graceful start/stop of the worker

**Scenario:**
- The user interacts with a console CLI (`ImageViewer`) to start processing images.
- The `ImageViewer` emits an emitter when the user starts processing images, which triggers the `on_started` listener in `ImageProcessor`.
- The `ImageProcessor` processes the images asynchronously and emits an emitter when the processing is complete, which triggers the `on_image_processed` listener in `ImageViewer`.
- The `ImageViewer` updates the UI to reflect the processed images.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main Thread (ImageViewer)
    participant W as Worker Thread (ImageProcessor)

    Note over M: Viewer created in main thread
    M->>W: processor.start(cache_size=5)

    Note over M: Queue single image processing tasks
    loop For each image
        M->>W: queue_task(process_image(img_id, img_data))
        W->>W: process_image() async execution in worker
        W->>W: Simulate processing (sleep)
        W->>W: processing_complete.emit(img_id, result)
        W->>M: on_image_processed(img_id, result)
        M->>M: processed_images[img_id] = result
    end

    Note over M: Queue batch processing
    M->>W: queue_task(process_batch(batch))
    W->>W: For each image in batch, call process_image()
    W->>W: processing_complete.emit(img_id, result) per image
    W->>M: on_image_processed(img_id, result) per image
    M->>M: processed_images[img_id] = result

    W->>W: After batch done, batch_complete.emit(results)
    W->>M: on_batch_complete(results)
    M->>M: print("Batch complete")

    Note over M: Stop worker
    M->>W: processor.stop()
    W->>W: on_stopped() async, clears cache

    Note over M: Interaction complete
```

Ideal for learning how to perform background computations without blocking the main thread.

---

## stock_monitor_simple.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_simple.py)
**Purpose**: A simple stock monitor example:
- Uses a worker to emit periodic “data processed” emitters
- A display object receiving those emitters and updating a value

**What it demonstrates**:
- A basic worker pattern with `@nx_with_worker`
- Connecting worker emitters to a display listener
- Observing data changes over time

**Scenario:**
- The user interacts with a console CLI (`DataDisplay`) to view the data changes.
- The `DataDisplay` receives the `data_processed` emitter from the `DataWorker` and updates the display.
- The `DataWorker` emits the `data_processed` emitter periodically, simulating data changes.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main Thread (main)
    participant W as DataWorker (Worker Thread)
    participant D as DataDisplay (Main Thread UI)

    Note over M: Main starts in main thread, creates Worker and Display
    M->>M: worker = DataWorker()
    M->>M: display = DataDisplay()

    M->>M: worker.data_processed.connect(display, display.on_data_processed)

    M->>W: worker.start()
    Note over W: Worker thread & event loop start<br>run() invoked in worker thread
    W->>W: run(): _running = True
    W->>W: create update_loop task

    loop until stopped
        W->>W: update_loop(): count++
        W->>W: data_processed.emit(count)
        note right of W: Emitter emitted from worker thread

        alt Different threads
            W->>D: on_data_processed(value)
            note right of D: Called in main thread via queued connection
            D->>D: Update last_value, print logs
            D->>D: time.sleep(0.1)
            D->>M: Control returns after listener executes
        end

        W->>W: await asyncio.sleep(1)
    end

    Note over M: After ~3 seconds main stops worker
    M->>W: worker.stop()
    W->>W: on stop: _running = False, cancel update_loop task

    Note over M: Program ends
```

This is a stepping stone to more complex stock monitoring examples.

---

## stock_monitor_console.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_console.py)
**Purpose**: A more advanced console-based stock monitor:
- Integrates `StockService`, `StockProcessor`, and `StockViewModel` from `stock_core.py`
- Provides a CLI for setting alerts, listing stocks, and monitoring price changes
- Demonstrates a three-component architecture:
  - `StockService`: Generates stock price updates in a worker thread
  - `StockProcessor`: Processes updates, applies alerts, and emits results
  - `StockViewModel`: Maintains state for the UI (in this case, a console UI)
  
**Screenshot:**
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/main/docs/images/stock_monitor_console.png" alt="Stock Monitor Console" width="800"/>
  <p><em>Stock Monitor Console: Real-time price updates, alert configuration, and notification history in action</em></p>
</div>

**What it demonstrates**:
- Multi-threaded architecture with emitters crossing between threads
- How async/await is integrated with user input via an event loop
- Complex emitter/listener connections for a real-world scenario (stock updates and alerts)

**Scenario**: 
- The user interacts with a console CLI (`StockMonitorCLI`) to view and set alerts on stocks.
- `StockService` and `StockProcessor` run in worker threads, generating and processing stock prices.
- `StockViewModel` manages the UI state (prices, alerts) and communicates changes to the CLI.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant CLI as StockMonitorCLI (Main Thread)
    participant V as StockViewModel (Main Thread)
    participant S as StockService (Worker)
    participant P as StockProcessor (Worker)
    participant U as User (Console Input)

    Note over CLI: CLI run loop in main thread
    U->>CLI: Enter command (e.g., "stocks" or "alert AAPL 150 200")
    CLI->>V: If command sets or removes alerts, call set_alert or remove_alert emitters

    V->>P: on_set_price_alert(code, lower, upper)
    P->>P: price_alerts[code] = (lower, upper)
    P->>V: alert_settings_changed.emit(code, lower, upper)
    V->>V: on_alert_settings_changed(...)

    V->>P: on_remove_price_alert(code)
    P->>P: remove price_alerts[code]
    P->>V: alert_settings_changed.emit(code, None, None)
    V->>V: on_alert_settings_changed(...)

    Note over S: StockService running and emitting price_updated periodically
    S->>P: on_price_updated(price_data)
    P->>P: queue_task(process_price(price_data))
    P->>P: process_price checks alerts
    alt Alert triggered
        P->>V: alert_triggered.emit(code, type, price)
        V->>V: on_alert_triggered(code, type, price)
        V->>V: alert_added.emit(...)
    end
    P->>V: price_processed.emit(price_data)
    V->>V: on_price_processed(price_data)
    V->>V: current_prices updated
    V->>V: prices_updated.emit(current_prices)

    CLI->>CLI: on_prices_updated(...) if showing_prices = True, display updated info

    Note over CLI: User can quit (enter "quit")
    U->>CLI: "quit"
    CLI->>S: service.stop()
    CLI->>P: processor.stop()
    CLI->>CLI: Exit loop and end program
```

This example is great for seeing how PynneX can be scaled up to more realistic, production-like use cases.

---

## stock_monitor_ui.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_ui.py)
**Purpose**: Shows how PynneX integrates with a GUI framework (Kivy):
- Similar functionality to the console version, but with a graphical UI
- `StockView` as a Kivy widget updates UI elements when emitters fire
- `set_alert` and `remove_alert` emitters triggered from UI and handled by `StockProcessor`

**Screenshot:**
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/main/docs/images/stock_monitor_ui.png" alt="Stock Monitor UI" width="800"/>
  <p><em>Stock Monitor UI: Real-time price updates, alert configuration, and notification history in action</em></p>
</div>

**What it demonstrates**:
- Integrating PynneX with Kivy’s main loop and UI elements
- Thread-safe updates to UI from background workers
- Handling user input, setting alerts, and reflecting changes on the UI

**Scenario:**
- The user interacts with a Kivy GUI (`StockView`) to start processing stocks.
- The `StockView` emits an emitter when the user starts processing stocks, which triggers the `on_started` listener in `StockService`.
- The `StockService` processes the stocks asynchronously and emits an emitter when the processing is complete, which triggers the `on_stock_processed` listener in `StockViewModel`.
- The `StockViewModel` updates the UI to reflect the processed stocks.

**Usecase:**
```mermaid
flowchart LR
    %% classDef actor fill:#FF99FF,stroke:#333,stroke-width:1px;
    %% classDef system fill:#EFEFEF,stroke:#333,stroke-width:1px,font-style:italic;

    %% Actor (User)
    User([User]):::actor

    %% Usecase-like nodes: () shape for oval feel
    UC_Start((Start_Monitoring))
    UC_Stop((Stop_Monitoring))
    UC_SetAlert((Set_Alert))
    UC_RemoveAlert((Remove_Alert))

    %% System boundary: StockMonitoringSystem as a subgraph
    subgraph StockMonitoringSystem[Stock Monitoring System]
        UI[[StockView_Kivy_UI]]:::system
        VM[[StockViewModel]]:::system
        S[[StockService_Worker]]:::system
        P[[StockProcessor_Worker]]:::system
    end

    %% User and usecase relationships
    User --> UC_Start
    User --> UC_Stop
    User --> UC_SetAlert
    User --> UC_RemoveAlert

    %% Usecase and UI relationships: user performs actions through UI
    UC_Start --> UI
    UC_Stop --> UI
    UC_SetAlert --> UI
    UC_RemoveAlert --> UI

    %% UI and ViewModel relationship
    UI --> VM

    %% Start/Stop emitters -> Service/Processor
    UC_Start --> S
    UC_Start --> P
    UC_Stop --> S
    UC_Stop --> P

    %% Service → Processor: stock price update emitter
    S --> P

    %% Processor → ViewModel: processing results/alerts
    P --> VM

    %% ViewModel → UI: UI updates
    VM --> UI

    %% Alert setting/removal flow
    UC_SetAlert --> VM
    UC_RemoveAlert --> VM
    VM --> P
```

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant UI as StockView (Kivy UI in Main Thread)
    participant V as StockViewModel (Main Thread)
    participant S as StockService (Worker)
    participant P as StockProcessor (Worker)
    participant U as User (UI Interaction)

    Note over UI: User sees UI with Start button, stock spinner, alert fields
    U->>UI: Click "Start"
    UI->>S: service.start()
    UI->>P: processor.start()
    UI->>UI: status_label = "Service started"

    Note over S: StockService emits price_updated periodically
    S->>P: on_price_updated(price_data)
    P->>P: queue_task(process_price(price_data))
    P->>P: process_price checks alerts
    alt Alert triggered
        P->>V: alert_triggered.emit(code, type, price)
        V->>V: on_alert_triggered(...)
        V->>UI: alert_added.emit(code, type, price)
        UI->>UI: on_alert_added(...) display alert in UI
    end

    P->>V: price_processed.emit(price_data)
    V->>V: on_price_processed(price_data)
    V->>V: current_prices updated
    V->>UI: prices_updated.emit(current_prices)
    UI->>UI: update_prices(...) refresh UI labels

    U->>UI: Enter alert bounds in text inputs and press "Set Alert"
    UI->>V: set_alert.emit(code, lower, upper)
    V->>P: on_set_price_alert(code, lower, upper)
    P->>P: price_alerts[code] = (lower, upper)
    P->>P: alert_settings_changed.emit(code, lower, upper)
    V->>V: on_alert_settings_changed(...)
    UI->>UI: alert_label updated

    U->>UI: Press "Remove Alert"
    UI->>V: remove_alert.emit(code)
    V->>P: on_remove_price_alert(code)
    P->>P: remove price_alerts[code]
    P->>P: alert_settings_changed.emit(code, None, None)
    V->>V: on_alert_settings_changed(...)
    UI->>UI: alert_label updated

    U->>UI: Press "Stop"
    UI->>S: service.stop()
    UI->>P: processor.stop()
    UI->>UI: status_label = "Service stopped"
```
This is useful if you’re building a GUI application and want to keep UI responsive while performing background tasks.

---

## stock_core.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_core.py)
**Purpose**: Core classes for stock monitoring logic:
- `StockService`: Generates random stock price updates in a worker thread
- `StockProcessor`: Processes these prices, triggers alerts based on user settings
- `StockViewModel`: Manages the current state of stock prices and alerts

**What it demonstrates**:
- Separation of concerns: generation of data (`StockService`), processing/alert logic (`StockProcessor`), and state management (`StockViewModel`)
- Each component uses emitters/listeners to communicate without direct dependencies

**Classes**:
```mermaid
classDiagram
    class StockPrice {
        +str code
        +float price
        +float change
        +float timestamp
    }

    class StockService {
        +Dict[str, float] prices
        +Dict[str, str] descriptions
        +Dict[str, float] last_prices
        +bool _running
        +_update_task
        +price_updated() Emitter
        +on_started() async
        +on_stopped() async
        +update_prices() async
    }

    class StockViewModel {
        +Dict[str, StockPrice] current_prices
        +List[Tuple[str, str, float]] alerts
        +Dict[str, Tuple[Optional[float], Optional[float]]] alert_settings
        +prices_updated() Emitter
        +alert_added() Emitter
        +set_alert() Emitter
        +remove_alert() Emitter
        +on_price_processed(price_data:StockPrice)
        +on_alert_triggered(code:str, alert_type:str, price:float)
        +on_alert_settings_changed(code:str, lower:float?, upper:float?)
    }

    class StockProcessor {
        +Dict[str, Tuple[Optional[float], Optional[float]]] price_alerts
        +price_processed() Emitter
        +alert_triggered() Emitter
        +alert_settings_changed() Emitter
        +on_set_price_alert(code:str, lower:float?, upper:float?) async
        +on_remove_price_alert(code:str) async
        +on_price_updated(price_data:StockPrice) async
        +process_price(price_data:StockPrice) async
        +on_started() async
        +on_stopped() async
    }

    StockService --> StockPrice
    StockProcessor --> StockPrice

    %% Emitters and Listeners relationships (not standard UML, just for clarity)
    %% Representing the fact that emitters can connect to listeners:
    %% StockService.price_updated --> StockProcessor.on_price_updated
    %% StockProcessor.price_processed --> StockViewModel.on_price_processed
    %% StockProcessor.alert_triggered --> StockViewModel.on_alert_triggered
    %% StockProcessor.alert_settings_changed --> StockViewModel.on_alert_settings_changed
    %% StockViewModel.set_alert --> StockProcessor.on_set_price_alert
    %% StockViewModel.remove_alert --> StockProcessor.on_remove_price_alert

    %% For clarity, these are conceptual links rather than class-level associations.
```
**Sequence:**
``` mermaid
sequenceDiagram
    participant S as StockService (Worker)
    participant P as StockProcessor (Worker)
    participant VM as StockViewModel (Main/UI Thread)
    participant U as User/External Input

    Note over S: StockService runs in background<br>and periodically updates prices
    S->>S: update_prices() loop
    S->>S: price_updated.emit(price_data)

    Note over P: Processor receives updated price
    S->>P: on_price_updated(price_data)
    P->>P: queue_task(process_price(price_data))
    P->>P: process_price checks alerts
    alt Alert conditions met
        P->>P: alert_triggered.emit(code, type, price)
        P->>VM: on_alert_triggered(code, type, price)
        VM->>VM: alerts.append((code, type, price))
        VM->>VM: alert_added.emit(code, type, price)
    end

    P->>P: price_processed.emit(price_data)
    P->>VM: on_price_processed(price_data)
    VM->>VM: current_prices[code] = price_data
    VM->>VM: prices_updated.emit(current_prices)

    Note over U: User can set or remove alerts
    U->>VM: set_alert.emit(code, lower, upper)
    VM->>P: on_set_price_alert(code, lower, upper)
    P->>P: price_alerts[code] = (lower, upper)
    P->>P: alert_settings_changed.emit(code, lower, upper)
    VM->>VM: on_alert_settings_changed(code, lower, upper)

    U->>VM: remove_alert.emit(code)
    VM->>P: on_remove_price_alert(code)
    P->>P: remove price_alerts[code]
    P->>P: alert_settings_changed.emit(code, None, None)
    VM->>VM: on_alert_settings_changed(code, None, None)

    Note over VM: UI updates accordingly after emitters
```
This example provides a strong architectural foundation for a real-time monitoring app.

---

## fastapi_socketio_simple.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/fastapi_socketio_simple.py)
**Purpose**: Demonstrates a minimal FastAPI & SocketIO integration with PynneX worker:
- Uses `@with_worker` to handle asynchronous berry checking tasks
- Shows how to integrate FastAPI, SocketIO, and PynneX worker
- Provides a simple web interface for task submission

**Screenshot:**
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/main/docs/images/fastapi_socketio_simple.png" alt="FastAPI with Worker Simple" width="800"/>
  <p><em>FastAPI with Worker Simple: Real-time WebSocket communication with worker</em></p>
</div>

**What it demonstrates**:
- Setting up a FastAPI application with SocketIO
- Using PynneX worker for background task processing
- Real-time updates via WebSocket
- Basic HTML/JavaScript frontend integration

**Scenario:**
- User clicks a button to request berry checking
- Request is processed asynchronously in a worker thread
- Results are sent back to the browser in real-time

**Sequence:**
```mermaid
sequenceDiagram
    participant B as Browser
    participant F as FastAPI (Main Thread)
    participant W as Worker Thread
    
    Note over B: User clicks "Check Berry"
    B->>F: socket.emit("message", {command, index})
    F->>F: message handler receives data
    F->>W: queue_task(check_berry())
    W->>W: Process berry check
    W->>F: emit "task_done" event
    F->>B: Send result via WebSocket
    B->>B: Update UI with result
```

This example is perfect for learning how to:
1. Set up a minimal web application with FastAPI & SocketIO
2. Use PynneX worker for background processing
3. Handle real-time communication between server and client
4. Integrate with a simple web frontend

Required packages:
```bash
pip install fastapi python-socketio uvicorn
```

---

## fastapi_socketio_qr.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/fastapi_socketio_qr.py)
**Purpose**: Demonstrates QR code generation with FastAPI & SocketIO integration:
- Uses `@with_worker` to handle asynchronous QR code generation
- Shows real-time QR code updates via WebSocket
- Provides a simple web interface for QR code generation

**Screenshot:**
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/main/docs/images/fastapi_socketio_qr.png" alt="FastAPI QR Code Generator" width="800"/>
  <p><em>FastAPI QR Code Generator: Real-time QR code generation with WebSocket communication</em></p>
</div>

**What it demonstrates**:
- Setting up a FastAPI application with SocketIO
- Using PynneX worker for QR code generation
- Real-time image updates via WebSocket
- Base64 image encoding/decoding
- Basic HTML/JavaScript frontend integration

**Scenario:**
- User clicks a button to request QR code generation
- Request is processed asynchronously in a worker thread
- Generated QR code is sent back to the browser in real-time as Base64 image

**Sequence:**
```mermaid
sequenceDiagram
    participant B as Browser
    participant F as FastAPI (Main Thread)
    participant W as QRWorker Thread
    
    Note over B: User clicks "Generate QR"
    B->>F: socket.emit("request_qr", payload)
    F->>F: QRController emits qrRequested
    F->>W: on_qr_requested(sid, payload)
    W->>W: Generate QR code
    W->>W: Convert to Base64
    W->>F: emit "qr_response" event
    F->>B: Send QR image via WebSocket
    B->>B: Display QR code image
```

This example is perfect for learning how to:
1. Set up a web application with FastAPI & SocketIO
2. Use PynneX worker for image generation
3. Handle real-time image data communication
4. Integrate with a web frontend using Base64 images

Required packages:
```bash
pip install fastapi python-socketio uvicorn qrcode
```

---

## fastapi_socketio_stock_monitor.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/fastapi_socketio_stock_monitor.py)
**Purpose**: Demonstrates a full-featured stock monitoring web application:
- Uses FastAPI & SocketIO for real-time web interface
- Integrates with stock_core.py for core business logic
- Shows real-time price updates, candlestick charts, and price alerts
- Uses ag-Grid for interactive data grid and eCharts for candlestick visualization

**Screenshot:**
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/main/docs/images/fastapi_socketio_stock_monitor.png" alt="FastAPI Stock Monitor" width="800"/>
  <p><em>FastAPI Stock Monitor: Real-time stock monitoring with interactive grid, candlestick chart, and price alerts</em></p>
</div>

**What it demonstrates**:
- Setting up a FastAPI application with SocketIO
- Using pynnex worker for stock data processing
- Real-time data updates via WebSocket
- Integration with third-party libraries (ag-Grid, eCharts)
- Complex UI interactions and state management
- Price alert system with real-time notifications

**Scenario:**
- User views real-time stock prices in an interactive grid
- Selecting a stock displays its candlestick chart
- User can set price alerts for selected stocks
- Real-time notifications when price alerts are triggered

**Sequence:**
```mermaid
sequenceDiagram
    participant B as Browser
    participant F as FastAPI (Main Thread)
    participant S as StockService (Worker)
    participant P as StockProcessor (Worker)
    
    Note over B: User opens application
    B->>F: Connect via WebSocket
    F->>S: Start stock service
    F->>P: Start stock processor

    loop Price Updates
        S->>S: Generate price updates
        S->>P: Process price data
        P->>F: Emit processed prices
        F->>B: Send price updates
        B->>B: Update grid & chart
    end

    Note over B: User sets price alert
    B->>F: socket.emit("set_alert", data)
    F->>P: Register price alert
    
    alt Price Alert Triggered
        P->>F: Alert condition met
        F->>B: Send alert notification
        B->>B: Display alert
    end
```

This example showcases:
1. Complex real-time web application architecture
2. Integration of multiple UI components
3. Real-time data processing and visualization
4. Interactive user experience with immediate feedback
5. Alert system with real-time notifications

Required packages:
```bash
pip install fastapi python-socketio uvicorn
```

Frontend dependencies (included via CDN):
- ag-Grid Community Edition
- eCharts
- Bootstrap 5

---

**In Summary:**
- **emitter_basic.py** and **emitter_async.py**: Start here to understand basic emitter/listener mechanics.
- **emitter_function_listeners.py** and **emitter_lambda_listeners.py**: Next steps showing flexible ways to use functions and lambdas as listeners.
- **thread_basic.py** and **thread_worker.py**: Learn about threading, event loops, and task queues.
- **stock_monitor_simple.py**: A minimal stock example using a worker.
- **stock_monitor_console.py** and **stock_monitor_ui.py**: Realistic, more complex examples that integrate multiple components, async processing, alerts, and UI/CLI interfaces.
- **stock_core.py**: Core domain logic extracted for reuse in different UIs, demonstrating best practices in modular design.

Use these examples in sequence to progressively gain expertise in PynneX's capabilities.
