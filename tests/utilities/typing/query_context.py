"""Check source-specific keys/payloads with mypy --warn-unused-ignores."""

from collections.abc import Mapping
from typing import assert_type
from uuid import UUID

from multiconn_archicad.models.tapir.types import AttributeType, ElementType
from multiconn_archicad.utilities.queries import (
    ClassificationInfo,
    ContextBuilder,
    EvaluationContext,
    LayerAttribute,
)
from multiconn_archicad.utilities.queries.layer_data import LayerCombinationData
from multiconn_archicad.utilities.results.batch_results import BatchSlot
from multiconn_archicad.utilities.queries.sources import (
    PROPERTY_VALUES,
    CLASSIFICATION_FIELDS,
    CLASSIFICATION_VALUES,
    TYPE_MEMBERSHIP,
    ATTRIBUTE_CHOICES,
    ELEMENT_LAYER_INDICES,
    LAYER_COMBINATIONS,
    ColumnData,
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
assert_type(context.data(PROPERTY_VALUES), Mapping[UUID, ColumnData[str]])
assert_type(context.data(CLASSIFICATION_VALUES), Mapping[UUID, ColumnData[UUID | None]])
assert_type(context.data(CLASSIFICATION_FIELDS), Mapping[UUID, ClassificationInfo])
assert_type(context.data(TYPE_MEMBERSHIP), Mapping[frozenset[ElementType], frozenset[UUID]])
assert_type(context.data(ATTRIBUTE_CHOICES), Mapping[AttributeType, Mapping[int, LayerAttribute]])
assert_type(context.data(ELEMENT_LAYER_INDICES), Mapping[None, Mapping[UUID, BatchSlot[int]]])
assert_type(context.data(LAYER_COMBINATIONS), Mapping[None, Mapping[UUID, LayerCombinationData]])
