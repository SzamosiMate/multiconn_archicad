import logging
import functools
import traceback
import types
from typing import Callable, Type, Protocol


class FunctionLike[**P, T](Protocol):
    __module__: str
    __code__: types.CodeType
    __name__: str

    def __call__(*args: P.args, **kwargs: P.kwargs) -> T: ...


def log_exceptions[**P, T](func: FunctionLike[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        logger = logging.getLogger(func.__module__)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            if tb and tb[-1].name == func.__name__ and tb[-1].filename == func.__code__.co_filename:
                logger.exception(str(e))
            raise

    return wrapper


def auto_decorate_methods[T](decorator: Callable[[Callable], Callable]) -> Callable[[Type[T]], Type[T]]:
    def class_decorator(cls: Type[T]) -> Type[T]:
        for attr_name, attr_value in cls.__dict__.items():
            if isinstance(attr_value, (types.FunctionType, types.MethodType)):
                # Skip special methods like __init__, __str__, etc.
                if not attr_name.startswith("__"):
                    setattr(cls, attr_name, decorator(attr_value))
        return cls

    return class_decorator
