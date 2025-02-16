import threading
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class BackgroundTaskRunner:
    """Runs a function in a background thread and allows stopping it if necessary."""

    def __init__(self, target):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.stop_event = threading.Event()
        self.future = None
        self.target = target

    def start(self, **kwargs) -> None:
        """Starts the background task once, if it's not already running."""
        if not self.future or self.future.done():
            self.stop_event.clear()
            self.future = self.executor.submit(self._safe_target, **kwargs)

    def _safe_target(self, **kwargs) -> None:
        """Runs the target function and logs errors."""
        try:
            self.target(self.stop_event, **kwargs)
        except Exception as e:
            logging.error(f"Background task error: {e}", exc_info=True)

    def stop(self) -> None:
        """Stops the task by setting the stop event and waits for it to exit."""
        self.stop_event.set()
        if self.future:
            try:
                self.future.result()  # Wait for the task to finish and catch exceptions
            except Exception as e:
                logging.error(f"Error in background thread: {e}", exc_info=True)
        self.executor.shutdown(wait=True)