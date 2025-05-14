import asyncio
import functools
from typing import Callable, Coroutine, Any
import threading
import logging

log = logging.getLogger(__name__)

_BACKGROUND_LOOP: asyncio.AbstractEventLoop | None = None
_BACKGROUND_THREAD: threading.Thread | None = None
_THREAD_LOCK = threading.Lock()  # To protect access to global loop/thread vars


def _ensure_background_loop_running():
    """Starts the background event loop if not already running. Thread-safe."""
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
            log.debug(f"Starting background asyncio thread: {_BACKGROUND_THREAD.name}")
            _BACKGROUND_THREAD.start()


def run_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Runs an awaitable coroutine from a synchronous context
    using a background event loop.
    """
    _ensure_background_loop_running()

    if threading.current_thread() is _BACKGROUND_THREAD:
        log.error("run_sync cannot be called from the background asyncio thread itself.")
        raise RuntimeError("run_sync cannot be called from the background asyncio thread itself.")
    else:
        assert _BACKGROUND_LOOP
        future = asyncio.run_coroutine_threadsafe(coro, _BACKGROUND_LOOP)
    try:
        # Block the calling thread until the coroutine finishes and return/raise result.
        result = future.result()
        return result
    except Exception as e:
        log.debug(f"Exception propagated from background coroutine via run_sync: {e}")
        raise


def callable_from_sync_or_async_context[T, **P](
    async_func: Callable[P, Coroutine[Any, Any, T]],
) -> Callable[P, T | Coroutine[Any, Any, T]]:
    """
    Decorator for public async methods.
    - If called from an async context, it behaves like a normal async function (returns awaitable).
    - If called from a sync context, it runs the async function to completion
      using the shared background event loop (via run_sync) and returns the result.
    """

    @functools.wraps(async_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Coroutine[Any, Any, T]:
        try:
            asyncio.get_running_loop().is_running()
            return async_func(*args, **kwargs)
        except RuntimeError:
            return run_sync(async_func(*args, **kwargs))

    return wrapper
