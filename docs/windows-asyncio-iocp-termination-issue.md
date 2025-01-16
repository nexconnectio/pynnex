<!-- docs/windows-asyncio-iocp-termination-issue.md -->

# Windows IOCP and asyncio Event Loop Termination Issue

## Problem Overview
A chronic issue that occurs when terminating asyncio event loops in Windows environments. This primarily occurs with `ProactorEventLoop`, which is based on Windows' IOCP (Input/Output Completion Port).

## Key Symptoms
- Event loop fails to terminate completely even when all tasks are completed and no pending work exists
- Event loop continues to show as running even after calling `loop.stop()`
- Process remains in background without full termination

## Root Cause
- Windows IOCP kernel objects not being properly cleaned up
- Incomplete integration between Python asyncio and Windows IOCP
- Multiple reports in Python bug tracker ([bpo-23057](https://bugs.python.org/issue23057), [bpo-45097](https://bugs.python.org/issue45097))

## Code Example
Here's a typical scenario where this issue occurs:

```python
import asyncio
import threading

class WorkerClass:
    def start_worker(self):
        self.worker_thread = threading.Thread(
            target=run_worker,
            name="WorkerThread",
            daemon=True # Set as daemon thread to work around the issue
        )
        self.worker_thread.start()

    def stop_worker(self):
        if self.worker_loop:
            self.worker_loop.call_soon_threadsafe(self._worker_loop.stop)
        if self.worker_thread:
            self.worker_thread.join()
```

## Solution
The most common workaround is to set the worker thread as a daemon thread:

### Benefits of Daemon Thread Approach
- Allows forced thread termination on program exit
- Bypasses event loop hanging issues
- Enables clean process termination

### Important Notes
- This issue is less prevalent on Linux and macOS
- Not a perfect solution as forced termination might lead to resource cleanup issues
- Remains an ongoing issue in the Python community

## Alternative Solutions
While daemon threads are the most practical solution, other approaches include:

1. Implementing careful cleanup logic:
```python
async def cleanup():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
            task.cancel()
    await asyncio.gather(tasks, return_exceptions=True)
    loop.stop()
```

2. Using emitter handlers for graceful shutdown
3. Implementing timeout-based forced termination

## Platform Specifics
- Windows: Most affected due to IOCP implementation
- Linux/macOS: Less problematic due to different event loop implementations
- The issue is specific to asyncio's integration with Windows' IOCP


