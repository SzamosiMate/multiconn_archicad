import asyncio
import functools
from asyncio import Task
from typing import Callable, Coroutine, Any

def sync_or_async[T, **P](function: Callable[P, Coroutine[Any, Any, T]]):
    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Task[Any]:
        return run_or_add_to_loop(function, *args, **kwargs)
    return wrapper

def run_or_add_to_loop[T, **P](function: Callable[P, Coroutine[Any, Any, T]], *args: P.args, **kwargs: P.kwargs) -> T | Task[Any]:
    try:
        if asyncio.get_running_loop().is_running():
            return asyncio.create_task(function(*args, **kwargs))
    except RuntimeError:
        pass
    return asyncio.run(function(*args, **kwargs))
