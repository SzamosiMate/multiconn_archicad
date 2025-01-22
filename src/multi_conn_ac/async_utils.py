import asyncio
import functools
from asyncio import Task
from typing import Callable, Coroutine, Any
import threading

_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()

_thr: threading.Thread = threading.Thread(target=_loop.run_forever, name="Async Runner",
                        daemon=True)

# This will block the calling thread until the coroutine is finished.
# Any exception that occurs in the coroutine is raised in the caller
def run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    if not _thr.is_alive():
        _thr.start()
    future = asyncio.run_coroutine_threadsafe(coroutine, _loop)
    return future.result()

def callable_from_sync_or_async_context[T, **P](function: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P,  T | Task[T]]:
    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Task[T]:
        try:
            asyncio.get_running_loop().is_running()
            return asyncio.create_task(function(*args, **kwargs))
        except RuntimeError:
            return asyncio.run(function(*args, **kwargs))
    return wrapper

def run_in_sync_or_async_context[T, **P](function: Callable[P, Coroutine[Any, Any, T]], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        asyncio.get_running_loop().is_running()
        return run_async(function(*args, **kwargs))
    except RuntimeError as e:
        return asyncio.run(function(*args, **kwargs))
