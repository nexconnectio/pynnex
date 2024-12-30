

This document provides an overview and explanation of the included examples. Each example demonstrates various aspects of using Pynnex, from basic signal-slot handling to more complex threaded worker patterns and UI integrations.

# Table of Contents
  
- [Table of Contents](#table-of-contents)
    - [signal\_basic.py (source)](#signal_basicpy-source)
  - [signal\_async.py (source)](#signal_asyncpy-source)
  - [signal\_function\_slots.py (source)](#signal_function_slotspy-source)
  - [signal\_lambda\_slots.py (source)](#signal_lambda_slotspy-source)
  - [thread\_basic.py (source)](#thread_basicpy-source)
  - [thread\_worker.py (source)](#thread_workerpy-source)
  - [stock\_monitor\_simple.py (source)](#stock_monitor_simplepy-source)
  - [stock\_monitor\_console.py (source)](#stock_monitor_consolepy-source)
  - [stock\_monitor\_ui.py (source)](#stock_monitor_uipy-source)
  - [stock\_core.py (source)](#stock_corepy-source)

---

### signal_basic.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/signal_basic.py)
**Purpose**: Introduces the most basic usage of Pynnex:
- Defining signals on a class (`@nx_signal`)
- Defining synchronous slots
- Connecting signals to slots and emitting signals

**What it demonstrates**:
- Simple increment of a counter
- Immediate synchronous slot response

**Scenario:**
- User interacts with Counter through a simple console input prompt
- Counter emits a signal when its value changes, triggering the on_count_changed method in Display class
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

Use this as a starting point if you’re new to Pynnex. There’s no threading or async complexity—just a straightforward signal-slot mechanism.

---

## signal_async.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/signal_async.py)
**Purpose**: Showcases how to handle asynchronous slots:
- Async slots using `@nx_slot` with `async def`
- Emitting signals that trigger async processing
- Demonstrates asynchronous delays (`await asyncio.sleep`)

**What it demonstrates**:
- Signal connection with asynchronous slots
- Combination of @nx_slot decorator with async functions
- Non-blocking operation handling

**Scenario:**
- User interacts with Counter through a simple console input prompt
- Counter emits a signal when its value changes, triggering the async on_count_changed method in AsyncDisplay class
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
        note right of C: Signal emission triggers async slot in AsyncDisplay
        C->>D: on_count_changed(value)
        note right of D: Async slot execution starts
        D->>D: print("Display processing count: value")
        D->>D: await asyncio.sleep(1)
        D->>D: self.last_value = value
        D->>D: print("Display finished processing: value")
        note right of D: Async slot completes
        D->>M: Control returns to main
        M->>M: await asyncio.sleep(0.1) for processing
        M->>M: Loop continues until user presses 'q'
    end
```

This example is ideal for learning how to integrate async operations into your event-driven code.

---

## signal_function_slots.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/signal_function_slots.py)
**Purpose**: Showcases how to use standalone functions as slots:
- Using standalone functions as slots without classes
- Demonstrates how to connect signals to standalone functions
- Shows how to use functions as slots without decorators

**What it demonstrates**:
- Flexibility of callable objects as slots
- Simple way to use functions as slots without classes
- Basic pattern for signal-slot connections

**Scenario:**
- The user interacts with a console CLI (`Counter`) to increment the counter.
- The counter emits a signal when the count changes, which triggers the `print_value` function.
- The function prints the current count value.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main
    participant C as Counter
    participant F as Function Slot (print_value)
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
            F->>F: Print "Function Slot received value: {count}"
        else input == 'q'
            M->>M: Break loop
        end
    end

    Note over M: Program ends
```

This example is a good starting point for learning how Pynnex can be used in a functional programming style, especially for developers who prefer non-class-based approaches.

---

## signal_lambda_slots.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/signal_lambda_slots.py)
**Purpose**: showcases how to use lambda functions as slots:
- Demonstrates how to connect signals to lambda functions
- Shows how to use lambda functions as slots without classes

**What it demonstrates**:
- Flexibility of lambda functions as slots
- Quick implementation of simple inline tasks
- Signal-slot system's flexibility

**Scenario:**
- The user interacts with a console CLI (`Counter`) to increment the counter.
- The counter emits a signal when the count changes, which triggers the lambda function.
- The lambda function prints the current count value.

**Sequence:**
```mermaid
sequenceDiagram
    autonumber
    participant M as Main
    participant C as Counter
    participant L as Lambda Slot
    participant U as User Input

    Note over M: Program starts
    M->>C: Create Counter instance
    M->>C: Connect count_changed to lambda v: print(f"Lambda Slot received: {v}")

    loop Until 'q' entered
        U->>M: Enter input
        alt input != 'q'
            M->>C: counter.increment()
            C->>C: self.count += 1
            C->>C: Print "Counter incremented to: {count}"
            C->>C: count_changed.emit(count)
            C->>L: lambda(count)
            L->>L: Print "Lambda Slot received: {count}"
        else input == 'q'
            M->>M: Break loop
        end
    end

    Note over M: Program ends
```

This example showcases Pynnex's flexibility, particularly useful for quick slot implementations for simple tasks. Lambda functions allow for simple processing of signals without the need for separate function or method definitions.

---

## thread_basic.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/thread_basic.py)
**Purpose**: Demonstrates thread-safe communication between main and worker threads using signals:
- Main thread hosts a user interface object (`UserView`)
- Worker thread hosts data model and mediator (`UserModel`, `UserMediator`)
- Signals and slots handle thread-safe calls between threads

**What it demonstrates**:
- How signals and slots automatically handle thread boundary crossings
- Running a worker thread with its own event loop
- Ensuring UI updates occur in the main thread, even though data processing happens elsewhere

**Scenario:**
- The user interacts with a console CLI (`UserView`) to log in.
- The `UserView` emits a signal when the user logs in, which triggers the `on_login_requested` slot in `UserModel`.
- The `UserModel` authenticates the user and emits a signal when the authentication is successful, which triggers the `on_user_logged_in` slot in `UserView`.
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
        W->>W: No signal emitted
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
**Purpose**: Introduces the `@nx_with_worker` pattern:
- A `ImageProcessor` class running in a worker thread
- Task queuing with `queue_task`
- Signal emission from a worker thread to the main thread

**What it demonstrates**:
- Creating a dedicated worker event loop using `@nx_with_worker`
- Scheduling asynchronous tasks on the worker thread (`queue_task`)
- Emitting signals from the worker to the main thread (`processing_complete`, `batch_complete`)
- Graceful start/stop of the worker

**Scenario:**
- The user interacts with a console CLI (`ImageViewer`) to start processing images.
- The `ImageViewer` emits a signal when the user starts processing images, which triggers the `on_started` slot in `ImageProcessor`.
- The `ImageProcessor` processes the images asynchronously and emits a signal when the processing is complete, which triggers the `on_image_processed` slot in `ImageViewer`.
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
- Uses a worker to emit periodic “data processed” signals
- A display object receiving those signals and updating a value

**What it demonstrates**:
- A basic worker pattern with `@nx_with_worker`
- Connecting worker signals to a display slot
- Observing data changes over time

**Scenario:**
- The user interacts with a console CLI (`DataDisplay`) to view the data changes.
- The `DataDisplay` receives the `data_processed` signal from the `DataWorker` and updates the display.
- The `DataWorker` emits the `data_processed` signal periodically, simulating data changes.

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
        note right of W: Signal emitted from worker thread

        alt Different threads
            W->>D: on_data_processed(value)
            note right of D: Called in main thread via queued connection
            D->>D: Update last_value, print logs
            D->>D: time.sleep(0.1)
            D->>M: Control returns after slot executes
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
- Multi-threaded architecture with signals crossing between threads
- How async/await is integrated with user input via an event loop
- Complex signal/slot connections for a real-world scenario (stock updates and alerts)

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
    CLI->>V: If command sets or removes alerts, call set_alert or remove_alert signals

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

This example is great for seeing how Pynnex can be scaled up to more realistic, production-like use cases.

---

## stock_monitor_ui.py [(source)](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_ui.py)
**Purpose**: Shows how Pynnex integrates with a GUI framework (Kivy):
- Similar functionality to the console version, but with a graphical UI
- `StockView` as a Kivy widget updates UI elements when signals fire
- `set_alert` and `remove_alert` signals triggered from UI and handled by `StockProcessor`

**Screenshot:**
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/main/docs/images/stock_monitor_ui.png" alt="Stock Monitor UI" width="800"/>
  <p><em>Stock Monitor UI: Real-time price updates, alert configuration, and notification history in action</em></p>
</div>

**What it demonstrates**:
- Integrating Pynnex with Kivy’s main loop and UI elements
- Thread-safe updates to UI from background workers
- Handling user input, setting alerts, and reflecting changes on the UI

**Scenario:**
- The user interacts with a Kivy GUI (`StockView`) to start processing stocks.
- The `StockView` emits a signal when the user starts processing stocks, which triggers the `on_started` slot in `StockService`.
- The `StockService` processes the stocks asynchronously and emits a signal when the processing is complete, which triggers the `on_stock_processed` slot in `StockViewModel`.
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

    %% Start/Stop signals -> Service/Processor
    UC_Start --> S
    UC_Start --> P
    UC_Stop --> S
    UC_Stop --> P

    %% Service → Processor: stock price update signal
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
- Each component uses signals/slots to communicate without direct dependencies

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
        +price_updated() Signal
        +on_started() async
        +on_stopped() async
        +update_prices() async
    }

    class StockViewModel {
        +Dict[str, StockPrice] current_prices
        +List[Tuple[str, str, float]] alerts
        +Dict[str, Tuple[Optional[float], Optional[float]]] alert_settings
        +prices_updated() Signal
        +alert_added() Signal
        +set_alert() Signal
        +remove_alert() Signal
        +on_price_processed(price_data:StockPrice)
        +on_alert_triggered(code:str, alert_type:str, price:float)
        +on_alert_settings_changed(code:str, lower:float?, upper:float?)
    }

    class StockProcessor {
        +Dict[str, Tuple[Optional[float], Optional[float]]] price_alerts
        +price_processed() Signal
        +alert_triggered() Signal
        +alert_settings_changed() Signal
        +on_set_price_alert(code:str, lower:float?, upper:float?) async
        +on_remove_price_alert(code:str) async
        +on_price_updated(price_data:StockPrice) async
        +process_price(price_data:StockPrice) async
        +on_started() async
        +on_stopped() async
    }

    StockService --> StockPrice
    StockProcessor --> StockPrice

    %% Signals and Slots relationships (not standard UML, just for clarity)
    %% Representing the fact that signals can connect to slots:
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

    Note over VM: UI updates accordingly after signals
```
This example provides a strong architectural foundation for a real-time monitoring app.

---

**In Summary:**
- **signal_basic.py** and **signal_async.py**: Start here to understand basic signal/slot mechanics.
- **signal_function_slots.py** and **signal_lambda_slots.py**: Next steps showing flexible ways to use functions and lambdas as slots.
- **thread_basic.py** and **thread_worker.py**: Learn about threading, event loops, and task queues.
- **stock_monitor_simple.py**: A minimal stock example using a worker.
- **stock_monitor_console.py** and **stock_monitor_ui.py**: Realistic, more complex examples that integrate multiple components, async processing, alerts, and UI/CLI interfaces.
- **stock_core.py**: Core domain logic extracted for reuse in different UIs, demonstrating best practices in modular design.

Use these examples in sequence to progressively gain expertise in Pynnex's capabilities.
