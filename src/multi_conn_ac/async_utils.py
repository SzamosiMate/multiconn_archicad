import asyncio
import functools
from typing import Callable, Coroutine, Any

def sync_or_async[T, **P](function: Callable[[P], Coroutine[Any, P, T]]):
    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return run_or_add_to_loop(function, *args, **kwargs)
    return wrapper

def run_or_add_to_loop[T, **P](function: Callable[[P], Coroutine[Any, P, T]], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        if asyncio.get_running_loop().is_running():
            return asyncio.create_task(function(*args, **kwargs))
    except RuntimeError:
        return asyncio.run(function(*args, **kwargs))
