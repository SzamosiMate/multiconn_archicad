"""Construct validated union variants while retaining a common model type."""

from inspect import getdoc
from typing import Annotated, Any, ClassVar, get_args

from pydantic import Field, TypeAdapter

from .base import APIModel


class _UnionMeta(type(APIModel)):
    def __call__(cls, **values: Any) -> Any:
        # Concrete subclasses inherit the attribute, but must never dispatch again.
        adapter = cls.__dict__.get("_variant_adapter")
        if adapter is not None:
            return adapter.validate_python(values)
        return super().__call__(**values)


class UnionModel(APIModel, metaclass=_UnionMeta):
    """A common model type whose constructor selects a validated variant."""

    _variant_adapter: ClassVar[TypeAdapter[Any] | None] = None

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> Any:
        adapter = cls.__dict__.get("_variant_adapter")
        return adapter.core_schema if adapter is not None else handler(source)


def bind_variants(model: type[UnionModel], variants: Any) -> None:
    """Bind generated subclasses before defining models that consume the parent."""
    members = get_args(variants)
    if len(members) < 2 or not all(isinstance(member, type) and issubclass(member, model) for member in members):
        raise TypeError("Every union variant must inherit from the factory model")
    if model.__dict__.get("_variant_adapter") is not None:
        raise TypeError("Variants must be bound once, before defining consumers")
    model._variant_adapter = TypeAdapter(Annotated[variants, Field(title=model.__name__, description=getdoc(model))])
    model.model_rebuild(force=True)
