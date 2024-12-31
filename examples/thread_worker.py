# examples/thread_worker.py

"""
Thread Worker Pattern Example

This example demonstrates the worker thread pattern using PynneX's nx_with_worker decorator:

1. Worker Thread:
   - ImageProcessor: A worker class that processes images in background
   - Supports async initialization and cleanup
   - Uses task queue for processing requests
   - Communicates results via signals

2. Main Thread:
   - Controls worker lifecycle
   - Submits processing requests
   - Receives processing results

Architecture:
- Worker runs in separate thread with its own event loop
- Task queue ensures sequential processing
- Signal/Slot connections handle thread-safe communication
"""

# pylint: disable=no-member
# pylint: disable=unused-argument

import asyncio
from pynnex import with_signals, signal, slot, with_worker
from utils import logger_setup

logger_setup("pynnex")
logger = logger_setup(__name__)

@with_worker
class ImageProcessor:
    """Worker that processes images in background thread"""

    def __init__(self, cache_size=100):
        self.cache_size = cache_size
        self.cache = {}
        super().__init__()
        self.stopped.connect(self, self.on_stopped)

    async def on_stopped(self):
        """Cleanup worker (runs in worker thread)"""

        print("[Worker Thread] Cleaning up image processor")
        self.cache.clear()

    @signal
    def processing_complete(self):
        """Signal emitted when image processing completes"""

    @signal
    def batch_complete(self):
        """Signal emitted when batch processing completes"""

    async def process_image(self, image_id: str, image_data: bytes):
        """Process single image (runs in worker thread)"""

        print(f"[Worker Thread] Processing image {image_id}")

        # Simulate image processing
        await asyncio.sleep(0.5)
        result = f"Processed_{image_id}"

        # Cache result
        if len(self.cache) >= self.cache_size:
            self.cache.pop(next(iter(self.cache)))
        self.cache[image_id] = result

        # Emit result
        self.processing_complete.emit(image_id, result)
        return result

    async def process_batch(self, images: list):
        """Process batch of images (runs in worker thread)"""

        results = []

        for img_id, img_data in images:
            result = await self.process_image(img_id, img_data)
            results.append(result)

        self.batch_complete.emit(results)

        return results


@with_signals
class ImageViewer:
    """UI component that displays processed images"""

    def __init__(self):
        print("[Main Thread] Creating image viewer")
        self.processed_images = {}

    @slot
    def on_image_processed(self, image_id: str, result: str):
        """Handle processed image (runs in main thread)"""
        print(f"[Main Thread] Received processed image {image_id}")
        self.processed_images[image_id] = result

    @slot
    def on_batch_complete(self, results: list):
        """Handle completed batch (runs in main thread)"""
        print(f"[Main Thread] Batch processing complete: {len(results)} images")


async def main():
    """Main function to run the example"""

    # Create components
    processor = ImageProcessor()
    viewer = ImageViewer()

    # Connect signals
    processor.processing_complete.connect(viewer, viewer.on_image_processed)
    processor.batch_complete.connect(viewer, viewer.on_batch_complete)

    # Start worker
    print("\n=== Starting worker ===\n")
    processor.start(cache_size=5)

    # Simulate image processing requests
    print("\n=== Processing single images ===\n")
    for i in range(3):
        image_id = f"img_{i}"
        image_data = b"fake_image_data"
        processor.queue_task(processor.process_image(image_id, image_data))

    # Simulate batch processing
    print("\n=== Processing batch ===\n")
    batch = [(f"batch_img_{i}", b"fake_batch_data") for i in range(3)]
    processor.queue_task(processor.process_batch(batch))

    # Wait for processing to complete
    await asyncio.sleep(3)

    # Stop worker
    print("\n=== Stopping worker ===\n")
    processor.stop()


if __name__ == "__main__":
    asyncio.run(main())
