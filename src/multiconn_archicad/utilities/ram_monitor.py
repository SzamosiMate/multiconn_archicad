from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Callable, Iterator
import psutil

from multiconn_archicad.utilities.process_utils import find_pid_by_port, get_process_rss_bytes

log = logging.getLogger(__name__)


class AtomicPeak:
    """Thread-safe container for tracking maximum recorded integer values."""

    def __init__(self, initial_value: int | None = None) -> None:
        self._value: int | None = initial_value
        self._lock = threading.Lock()

    def update_if_greater(self, new_value: int) -> None:
        with self._lock:
            if self._value is None or new_value > self._value:
                self._value = new_value

    def get(self) -> int | None:
        with self._lock:
            return self._value

    def set(self, value: int | None) -> None:
        with self._lock:
            self._value = value


class RamMonitor:
    """Encapsulates process memory tracking, live RSS queries, and background peak RAM polling."""

    def __init__(
        self,
        port_getter: Callable[[], int | None] | None = None,
        initial_peak_bytes: int | None = None,
    ) -> None:
        self._port_getter = port_getter
        self._peak = AtomicPeak(initial_peak_bytes)
        self._cached_pid: int | None = None

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def peak_bytes(self) -> int | None:
        """The highest observed RSS memory usage in bytes."""
        return self._peak.get()

    @peak_bytes.setter
    def peak_bytes(self, value: int | None) -> None:
        self._peak.set(value)

    @property
    def current_bytes(self) -> int | None:
        """Queries live RSS memory and automatically updates peak RAM if exceeded."""
        return self.get_current_rss()

    @property
    def pid(self) -> int | None:
        """Returns the PID of the Archicad process associated with the port."""
        return self.get_pid()

    @property
    def is_polling(self) -> bool:
        """Indicates whether background polling is actively running."""
        return self._thread is not None and self._thread.is_alive()

    def get_pid(self) -> int | None:
        """Resolves the PID using the cached PID or port lookup."""
        if self._cached_pid is not None:
            if psutil.pid_exists(self._cached_pid):
                return self._cached_pid
            self._cached_pid = None

        if self._port_getter is None:
            return None

        port = self._port_getter()
        if port is None:
            return None

        pid = find_pid_by_port(port)
        self._cached_pid = pid
        return pid

    def get_current_rss(self) -> int | None:
        """Queries live process RSS and atomically updates peak RAM if exceeded."""
        pid = self.get_pid()
        if pid is None:
            return None

        current_rss = get_process_rss_bytes(pid)
        if current_rss is not None:
            self._peak.update_if_greater(current_rss)

        return current_rss

    def start(self, interval_s: float = 1.0) -> None:
        """Starts a background daemon thread polling memory at the given interval."""
        if self.is_polling:
            log.debug("RAM polling is already active.")
            return

        self._stop_event.clear()
        port_label = self._port_getter() if self._port_getter else "unassigned"
        self._thread = threading.Thread(
            target=self._polling_worker,
            args=(interval_s,),
            name=f"RamMonitorWorker-port-{port_label}",
            daemon=True,
        )
        self._thread.start()
        log.debug(f"Started background RAM polling (interval={interval_s}s).")

    def stop(self) -> int | None:
        """Stops the background polling thread cleanly and returns the peak bytes."""
        self._stop_event.set()
        if self._thread is not None and threading.current_thread() != self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
            log.debug("Stopped background RAM polling.")
        return self.peak_bytes

    def reset_process(self) -> None:
        """Stops active polling and clears the cached PID while retaining peak RAM metrics."""
        self.stop()
        self._cached_pid = None

    @contextmanager
    def track_peak_ram(self, interval_s: float = 1.0) -> Iterator[None]:
        """Context manager to track peak RAM during an enclosed block of work."""
        self.start(interval_s=interval_s)
        try:
            yield
        finally:
            self.stop()

    def _polling_worker(self, interval_s: float) -> None:
        """Background thread worker loop. Immediately takes a sample, then polls on interval."""
        self.get_current_rss()
        while not self._stop_event.wait(timeout=interval_s):
            self.get_current_rss()