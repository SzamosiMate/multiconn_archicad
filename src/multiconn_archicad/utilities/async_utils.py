import asyncio
import threading
import concurrent.futures
from typing import Awaitable, TypeVar, Union, Coroutine, Any
import logging

log = logging.getLogger(__name__)

_BACKGROUND_LOOP: asyncio.AbstractEventLoop | None = None
_BACKGROUND_THREAD: threading.Thread | None = None
_THREAD_LOCK = threading.Lock()

T = TypeVar("T")
AsyncHandle = Union[asyncio.Task[T], concurrent.futures.Future[T]]


def _ensure_background_loop_running():
    """Starts the background event loop if not already running."""
    global _BACKGROUND_LOOP, _BACKGROUND_THREAD

    if (
        _BACKGROUND_THREAD is not None
        and _BACKGROUND_THREAD.is_alive()
        and _BACKGROUND_LOOP is not None
        and _BACKGROUND_LOOP.is_running()
    ):
        return

    with _THREAD_LOCK:
        if _BACKGROUND_THREAD is None or not _BACKGROUND_THREAD.is_alive():
            _BACKGROUND_LOOP = asyncio.new_event_loop()
            _BACKGROUND_THREAD = threading.Thread(
                target=_BACKGROUND_LOOP.run_forever,
                name="MultiConnArchicadAsyncRunner",
                daemon=True,
            )
            _BACKGROUND_THREAD.start()


def run_sync(awaitable: Awaitable[T]) -> T:
    """ Runs an Awaitable (Coroutine or Task) from a synchronous context."""
    _ensure_background_loop_running()

    if threading.current_thread() is _BACKGROUND_THREAD:
        raise RuntimeError("run_sync cannot be called from the background thread.")

    async def wrapper():
        return await awaitable

    # Submit to background loop and wait for result
    assert _BACKGROUND_LOOP
    future = asyncio.run_coroutine_threadsafe(wrapper(), _BACKGROUND_LOOP)
    return future.result()


def start_background_task(coro: Coroutine[Any, Any, T]) -> AsyncHandle[T]:
    """
    Schedules a coroutine to run on the background loop.

    Context-Aware:
    - If called from the background thread (e.g. inside scan_ports), returns an asyncio.Task.
    - If called from the main thread (e.g. user script), returns a concurrent.futures.Future.
    """
    _ensure_background_loop_running()
    assert _BACKGROUND_LOOP

    try:
        current_loop = asyncio.get_running_loop()
        if current_loop is _BACKGROUND_LOOP:
            return current_loop.create_task(coro)
    except RuntimeError:
        pass

    return asyncio.run_coroutine_threadsafe(coro, _BACKGROUND_LOOP)


def wait_for_handle(handle: AsyncHandle[T] | None) -> T | None:
    """
    Blocks the calling thread until the handle finishes.
    """
    if handle is None:
        return None

    if threading.current_thread() is _BACKGROUND_THREAD:
        if handle.done():
            return handle.result()
        else:
            return None

    if isinstance(handle, concurrent.futures.Future):
        return handle.result()

    if isinstance(handle, asyncio.Task):
        return run_sync(handle)

    return None
