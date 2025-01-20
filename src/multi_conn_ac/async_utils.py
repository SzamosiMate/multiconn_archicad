import asyncio
import functools
from asyncio import Task
from typing import Callable, Coroutine, Any
from asgiref.sync import async_to_sync

def callable_from_sync_or_async_context[T, **P](function: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P,  T | Task[T]]:
    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Task[T]:
        try:
            if asyncio.get_running_loop().is_running():
                return asyncio.create_task(function(*args, **kwargs))
        except RuntimeError:
            pass
        return asyncio.run(function(*args, **kwargs))
    return wrapper

def run_in_sync_or_async_context[T, **P](function: Callable[P, Coroutine[Any, Any, T]], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        if asyncio.get_running_loop().is_running():
            return async_to_sync(function)(*args, **kwargs)
    except RuntimeError:
        pass
    return asyncio.run(function(*args, **kwargs))
