import asyncio
import functools
from typing import Callable, Coroutine, Any

    @functools.wraps(function)
        return run_or_add_to_loop(function, *args, **kwargs)
    return wrapper

    try:
        if asyncio.get_running_loop().is_running():
            return asyncio.create_task(function(*args, **kwargs))
    except RuntimeError:
        return asyncio.run(function(*args, **kwargs))
