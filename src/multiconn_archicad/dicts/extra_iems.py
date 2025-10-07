from typing import Type, Any


def extra_items[_T](value_type: Type[_T]):
    """
    Shim for future typing_extensions.extra_items.
    In 3.12+, it returns a decorator that creates a union type:
    TypedDict | dict[str, value_type]
    """
    def decorator(cls: Type[Any]) -> Any:
        return cls | dict[str, value_type]  # type: ignore
    return decorator