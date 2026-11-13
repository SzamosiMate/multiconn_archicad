"""Check source batching, typed storage, and shared predicate execution data."""

from collections.abc import Sequence
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    PROPERTY_VALUES,
    TYPE_MEMBERSHIP,
    AllOf,
    AnyOf,
    ContextBuilder,
    ContextSource,
    ElementTypePredicate,
    ElementTypeTest,
    EvaluationContext,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
)
from multiconn_archicad.utilities.results.batch_results import BatchError, BatchGrid, BatchRow, BatchSlot

pytestmark = pytest.mark.unit
FIRST, SECOND = UUID(int=1), UUID(int=2)
HEIGHT, WIDTH = UUID(int=3), UUID(int=4)


def elements():
    return [tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=guid)) for guid in (FIRST, SECOND)]


class LengthSource(ContextSource[str, int]):
    def __init__(self):
        self.calls = []

    def load(self, api, elements, keys: Sequence[str]):
        self.calls.append((elements, tuple(keys)))
        return {key: len(key) for key in keys}


class LabelSource(ContextSource[int, str]):
    def load(self, api, elements, keys: Sequence[int]):
        return {key: f"Label {key}" for key in keys}


def test_unrelated_sources_share_a_context_and_deduplicate_keys_in_request_order():
    lengths, labels = LengthSource(), LabelSource()
    builder = ContextBuilder()
    builder.require(lengths, "wall")
    builder.require(labels, 5)
    builder.require(lengths, "window")
    builder.require(lengths, "wall")
    candidates = elements()

    assert builder.requested_keys(lengths) == ("wall", "window")
    assert builder.requested_keys(labels) == (5,)
    assert builder.requested_keys(LengthSource()) == ()

    context = builder.build(MagicMock(), candidates)

    assert context.data(lengths) == {"wall": 4, "window": 6}
    assert context.data(labels) == {5: "Label 5"}
    assert lengths.calls == [(candidates, ("wall", "window"))]


def test_source_instances_have_independent_request_and_payload_storage():
    first, second = LengthSource(), LengthSource()
    builder = ContextBuilder()
    builder.require(first, "wall")
    builder.require(second, "slab")

    context = builder.build(MagicMock(), elements())

    assert context.data(first) == {"wall": 4}
    assert context.data(second) == {"slab": 4}
    with pytest.raises(KeyError):
        context.data(LengthSource())


def test_provided_values_skip_reads_and_only_missing_keys_are_loaded():
    source = LengthSource()
    builder = ContextBuilder()
    builder.provide(source, "wall", 99)
    builder.require(source, "wall")
    builder.require(source, "window")

    context = builder.build(MagicMock(), elements())

    assert source.calls[0][1] == ("window",)
    assert context.data(source) == {"wall": 99, "window": 6}


def test_fully_provided_source_does_not_load():
    source = LengthSource()
    builder = ContextBuilder()
    builder.provide(source, "wall", 99)
    builder.require(source, "wall")

    assert builder.build(MagicMock(), elements()).data(source) == {"wall": 99}
    assert source.calls == []


def test_empty_population_does_not_load_sources():
    source = LengthSource()
    builder = ContextBuilder()
    builder.require(source, "wall")

    assert builder.build(MagicMock(), []).data(source) == {}
    assert source.calls == []


def test_builds_are_independent_and_builder_changes_do_not_modify_a_completed_context():
    source = LengthSource()
    builder = ContextBuilder()
    builder.require(source, "wall")
    first = builder.build(MagicMock(), elements())
    builder.provide(source, "wall", 99)
    builder.require(source, "window")
    second = builder.build(MagicMock(), elements())

    assert first.data(source) == {"wall": 4}
    assert second.data(source) == {"wall": 99, "window": 6}
    assert len(source.calls) == 2


def test_loader_failures_propagate_without_becoming_nonmatches():
    error = RuntimeError("Cannot load source")

    class BrokenSource(LengthSource):
        def load(self, api, elements, keys):
            raise error

    builder = ContextBuilder()
    builder.require(BrokenSource(), "wall")

    with pytest.raises(RuntimeError) as caught:
        builder.build(MagicMock(), elements())
    assert caught.value is error


def test_nested_prepare_batches_properties_and_reuses_the_original_grid_and_slots():
    error = BatchError.from_message("Width unreadable")
    grid = BatchGrid(
        rows=(
            BatchRow((BatchSlot.success("4"), BatchSlot.failure(error))),
            BatchRow((BatchSlot.success("2"), BatchSlot.success("1"))),
        ),
        width=2,
    )
    api = MagicMock()
    api.utilities.property.get_property_values_per_element_result.return_value = grid

    def prop(guid):
        return PropertyPredicate(field_id=guid, test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3))

    node = AllOf(items=(prop(HEIGHT), AnyOf(items=(prop(WIDTH), prop(HEIGHT)))))
    builder = ContextBuilder()
    node.prepare(builder)
    candidates = elements()
    context = builder.build(api, candidates)
    data = context.data(PROPERTY_VALUES)

    api.utilities.property.get_property_values_per_element_result.assert_called_once_with(candidates, (HEIGHT, WIDTH))
    assert data[HEIGHT].grid is grid
    assert data[WIDTH].grid is grid
    assert data[HEIGHT].row_indices is data[WIDTH].row_indices
    assert data[WIDTH].value(FIRST) is grid.rows[0].slots[1]
    assert data[WIDTH].value(FIRST).error is error
    assert node.evaluate(context, FIRST).is_error
    assert node.evaluate(context, SECOND).value is False


def test_type_source_reads_distinct_sets_once_and_one_context_serves_multiple_elements():
    wall = ElementTypePredicate(test=ElementTypeTest(types=(tapir.ElementType.WALL,)))
    slab = ElementTypePredicate(test=ElementTypeTest(types=(tapir.ElementType.SLAB,)))
    node = AnyOf(items=(wall, AllOf(items=(wall, slab))))
    builder = ContextBuilder()
    node.prepare(builder)
    api = MagicMock()
    candidates = elements()
    api.tapir.element.filter_elements.side_effect = [candidates[:1], candidates[1:]]

    context = builder.build(api, candidates)

    assert api.tapir.element.filter_elements.call_count == 2
    assert context.data(TYPE_MEMBERSHIP)[wall.candidate_types()] == frozenset({FIRST})
    assert wall.evaluate(context, FIRST).value is True
    assert wall.evaluate(context, SECOND).value is False
    assert slab.evaluate(context, SECOND).value is True


def test_new_predicate_can_prepare_a_new_source_without_changing_the_builder_or_context():
    source = LengthSource()

    class CustomPredicate(ElementTypePredicate):
        def prepare(self, builder: ContextBuilder) -> None:
            builder.require(source, "wall")

        def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
            return BatchSlot.success(context.data(source)["wall"] == 4)

    node = AllOf(items=(CustomPredicate(test=ElementTypeTest(types=(tapir.ElementType.WALL,))),))
    builder = ContextBuilder()
    node.prepare(builder)
    context = builder.build(MagicMock(), elements())

    assert node.evaluate(context, FIRST).value is True
    assert source.calls[0][1] == ("wall",)
    assert not builder.requires(TYPE_MEMBERSHIP)
