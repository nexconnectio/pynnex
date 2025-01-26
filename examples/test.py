import asyncio
import threading
import time
from pynnex import with_emitters, emitter, listener, with_worker


@with_worker
class DataWorker:
    def __init__(self):
        self._running = False
        self._update_task = None
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)

    @emitter
    def data_processed(self):
        pass

    @listener
    async def on_started(self, *args, **kwargs):
        print(f"[DataWorker][on_started] thread: {threading.current_thread().name}")
        self._running = True
        self._update_task = self.queue_task(self.process_data())

    @listener
    async def on_stopped(self):
        self._running = False
        print(f"[DataWorker][on_stopped] thread: {threading.current_thread().name}")

        # try:
        #     await self._update_task
        # except asyncio.CancelledError:
        #     pass

    async def process_data(self):
        count = 0
        while self._running:
            print(
                f"[DataWorker][process_data] data {count} thread: {threading.current_thread().name}"
            )
            self.data_processed.emit(count)
            count += 1
            await asyncio.sleep(1)
        print(
            f"[DataWorker][process_data] END thread: {threading.current_thread().name}"
        )


@with_emitters
class DataDisplay:
    def __init__(self):
        self.last_value = None

    @listener
    def on_data_processed(self, value):
        current_thread = threading.current_thread()
        print(
            f"[DataDisplay][on_data_processed] START in thread: {current_thread.name}"
        )
        self.last_value = value
        time.sleep(0.1)  # simulate heavy processing
        print(f"[DataDisplay][on_data_processed] END value {value}")


async def main():
    worker = DataWorker()
    display = DataDisplay()

    worker.data_processed.connect(display, display.on_data_processed)
    worker.start()

    try:
        await asyncio.sleep(3)
    finally:
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
