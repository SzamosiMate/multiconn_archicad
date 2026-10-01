"""Connection notifications, independent of connection discovery and HTTP work."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
import logging
from threading import RLock
from typing import Callable, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from multiconn_archicad.orchestration.basic_types import Port
    from multiconn_archicad.orchestration.conn_header import ConnHeader

log = logging.getLogger(__name__)

type Dispatcher = Callable[[Callable[[], None]], object]
type MetadataCallback = Callable[["ConnHeader"], None]
type PrimaryCallback = Callable[["ConnHeader | None", "ConnHeader | None"], None]


def _direct(task: Callable[[], None]) -> None:
    task()


class _Subscription:
    def __init__(self, owner: ConnectionEvents, callback: Callable[..., None]) -> None:
        self.owner = owner
        self.callback = callback
        self.queue: deque[tuple[str, tuple[object, ...]]] = deque()
        self.scheduled = False
        self.active = True
        self.queued_tokens: dict[Port, object] = {}

    def enqueue(self, kind: str, *args: object) -> bool:
        self.queue.append((kind, args))
        if self.scheduled:
            return False
        self.scheduled = True
        return True

    def enqueue_metadata(self, header: ConnHeader, token: object) -> bool:
        """Accept each fetch once, including while its callback is still queued."""
        port = header.port
        if port is None or self.queued_tokens.get(port) is token:
            return False
        self.queued_tokens[port] = token
        return self.enqueue("metadata", port, header, token)

    def schedule(self) -> None:
        try:
            self.owner._dispatcher(self.drain)
        except Exception:
            log.exception("Connection event dispatcher failed")
            with self.owner._lock:
                self.queue.clear()
                self.queued_tokens.clear()
                self.scheduled = False

    def drain(self) -> None:
        while True:
            with self.owner._lock:
                if not self.active or not self.queue:
                    self.scheduled = False
                    return
                kind, args = self.queue.popleft()
                if kind == "metadata":
                    _, header, token = args
                    if not self.owner._is_current_completion(cast("ConnHeader", header), token):
                        continue
            try:
                self.callback(cast("ConnHeader", args[1])) if kind == "metadata" else self.callback(*args)
            except Exception:
                log.exception("Connection event callback failed")

    def unsubscribe(self) -> None:
        with self.owner._lock:
            self.active = False
            self.queue.clear()
            self.queued_tokens.clear()
            if self in self.owner._metadata_subscribers:
                self.owner._metadata_subscribers.remove(self)
            if self in self.owner._primary_subscribers:
                self.owner._primary_subscribers.remove(self)
            self.callback = lambda *args: None


class ConnectionEvents:
    """Deliver connection changes through the supplied zero-argument dispatcher.

    The default dispatcher runs callbacks synchronously on the publishing thread.
    Applications serialize registration with connection management. Metadata
    publication may run concurrently. State providers return snapshots without
    triggering discovery.
    """

    def __init__(
        self,
        dispatcher: Dispatcher | None = None,
        *,
        get_primary: Callable[[], ConnHeader | None],
        get_headers: Callable[[], Mapping[Port, ConnHeader]],
    ) -> None:
        self._dispatcher = dispatcher or _direct
        self._lock = RLock()
        self._get_primary = get_primary
        self._get_headers = get_headers
        self._metadata_subscribers: list[_Subscription] = []
        self._primary_subscribers: list[_Subscription] = []

    def subscribe_metadata_resolved(self, callback: MetadataCallback) -> Callable[[], None]:
        """Subscribe to current fetch completions and replay managed completed headers.

        Registration does not discover ports. The header is live; inspect its current
        status before rendering. The returned unsubscribe function is idempotent and
        suppresses queued callbacks that have not started.
        """
        subscriber = _Subscription(self, callback)
        with self._lock:
            self._metadata_subscribers.append(subscriber)
            should_schedule = False
            for header in self._get_headers().values():
                token = header._resolved_fetch_token()
                if token is not None:
                    should_schedule = subscriber.enqueue_metadata(header, token) or should_schedule
        if should_schedule:
            subscriber.schedule()
        return subscriber.unsubscribe

    def subscribe_primary_changed(self, callback: PrimaryCallback) -> Callable[[], None]:
        """Subscribe to selection changes, starting with (None, current selection).

        Registration does not discover ports. A dispatcher may defer delivery; the
        header arguments are live objects. Unsubscribe suppresses queued callbacks.
        """
        subscriber = _Subscription(self, callback)
        with self._lock:
            self._primary_subscribers.append(subscriber)
            should_schedule = subscriber.enqueue("primary", None, self._get_primary())
        if should_schedule:
            subscriber.schedule()
        return subscriber.unsubscribe

    def _is_current_completion(self, header: ConnHeader, token: object) -> bool:
        port = header.port
        return (
            port is not None
            and self._get_headers().get(port) is header
            and header._resolved_fetch_token() is token
        )

    def _resolved(self, header: ConnHeader, token: object) -> None:
        to_schedule: list[_Subscription] = []
        with self._lock:
            if not self._is_current_completion(header, token):
                return
            for subscriber in self._metadata_subscribers:
                if subscriber.active and subscriber.enqueue_metadata(header, token):
                    to_schedule.append(subscriber)
        for subscriber in to_schedule:
            subscriber.schedule()

    def _primary_changed(self, previous: ConnHeader | None, current: ConnHeader | None) -> None:
        to_schedule: list[_Subscription] = []
        with self._lock:
            if previous is current:
                return
            for subscriber in self._primary_subscribers:
                if subscriber.active and subscriber.enqueue("primary", previous, current):
                    to_schedule.append(subscriber)
        for subscriber in to_schedule:
            subscriber.schedule()
