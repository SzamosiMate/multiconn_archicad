"""Check source-specific keys/payloads with mypy --warn-unused-ignores."""

from collections.abc import Mapping
from typing import assert_type
from uuid import UUID

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    PROPERTY_VALUES,
    TYPE_MEMBERSHIP,
    ContextBuilder,
    EvaluationContext,
    PropertyValuesData,
)

builder = ContextBuilder()
property_id = UUID(int=1)
types = frozenset({ElementType.WALL})
builder.require(PROPERTY_VALUES, property_id)
builder.require(TYPE_MEMBERSHIP, types)
builder.provide(TYPE_MEMBERSHIP, types, frozenset({UUID(int=2)}))

builder.require(PROPERTY_VALUES, "wrong key")  # type: ignore[misc]
builder.require(TYPE_MEMBERSHIP, property_id)  # type: ignore[misc]
builder.provide(TYPE_MEMBERSHIP, types, "wrong value")  # type: ignore[misc]

context = EvaluationContext()
assert_type(context.data(PROPERTY_VALUES), Mapping[UUID, PropertyValuesData])
assert_type(context.data(TYPE_MEMBERSHIP), Mapping[frozenset[ElementType], frozenset[UUID]])
