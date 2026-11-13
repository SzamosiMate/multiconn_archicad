"""Evaluate recursive predicate commands against shared execution data."""

from uuid import UUID

import pytest

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    PROPERTY_VALUES,
    TYPE_MEMBERSHIP,
    AllOf,
    AnyOf,
    ColumnData,
    ElementTypePredicate,
    ElementTypeTest,
    EvaluationContext,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
    TextOperator,
    TextTest,
)
from multiconn_archicad.utilities.results.batch_results import BatchError, BatchGrid, BatchRow, BatchSlot
from multiconn_archicad.utilities.results.property_errors import PropertyUnavailableError, PropertyUndefinedError

from .support import height_node, type_node

pytestmark = pytest.mark.unit

HEIGHT = UUID("22222222-2222-4222-8222-222222222222")
DESCRIPTION = UUID("11111111-1111-4111-8111-111111111111")
ELEMENT = UUID(int=1)


def make_context(*, property_values=None, type_matches=None):
    data = {}
    if property_values is not None:
        grid = BatchGrid(rows=(BatchRow(tuple(property_values.values())),), width=len(property_values))
        data[PROPERTY_VALUES] = {
            key: ColumnData(grid, {ELEMENT: 0}, column) for column, key in enumerate(property_values)
        }
    if type_matches is not None:
        data[TYPE_MEMBERSHIP] = {
            types: frozenset({ELEMENT}) if matches else frozenset() for types, matches in type_matches.items()
        }
    return EvaluationContext(data)


def height_predicate() -> PropertyPredicate:
    return PropertyPredicate(field_id=HEIGHT, test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3))


def description_predicate(operator: TextOperator, value: str) -> PropertyPredicate:
    return PropertyPredicate(field_id=DESCRIPTION, test=TextTest(operator=operator, value=value))


def nested_query() -> Query:
    return Query(
        where=AllOf(
            items=(
                ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))),
                AnyOf(items=(height_predicate(), description_predicate(TextOperator.STARTS_WITH, "External"))),
                description_predicate(TextOperator.DOES_NOT_CONTAIN, "Temporary"),
            )
        )
    )


class TestBooleanExpressions:
    @pytest.mark.parametrize(
        ("element_type", "height", "description", "expected"),
        [
            (ElementType.WALL, "3.5", "Internal", True),
            (ElementType.WALL, "2.5", "EXTERNAL", True),
            (ElementType.WALL, "2.5", "Internal", False),
            (ElementType.SLAB, "3.5", "External", False),
            (ElementType.WALL, "3.5", "External Temporary", False),
        ],
    )
    def test_nested_query_evaluates_without_changing_query_or_context(
        self, element_type, height, description, expected
    ):
        query = nested_query()
        reads = {HEIGHT: BatchSlot.success(height), DESCRIPTION: BatchSlot.success(description)}
        context = make_context(
            property_values=reads, type_matches={frozenset({ElementType.WALL}): element_type is ElementType.WALL}
        )
        original_query = query.model_dump_json()
        original_reads = reads.copy()

        result = query.where.evaluate(context, ELEMENT)

        assert result.is_success
        assert result.value is expected
        assert query.model_dump_json() == original_query
        assert reads == original_reads

    @pytest.mark.parametrize("group", [AllOf, AnyOf])
    @pytest.mark.parametrize(("first", "second"), [(True, True), (True, False), (False, True), (False, False)])
    def test_groups_apply_boolean_truth_tables_to_successful_results(self, group, first, second):
        node = group(items=(height_predicate(), description_predicate(TextOperator.IS, "yes")))
        context = make_context(
            property_values={
                HEIGHT: BatchSlot.success("4" if first else "2"),
                DESCRIPTION: BatchSlot.success("yes" if second else "no"),
            }
        )

        result = node.evaluate(context, ELEMENT)

        assert result.is_success
        assert result.value is (all((first, second)) if group is AllOf else any((first, second)))

    @pytest.mark.parametrize("condition", [PropertyUnavailableError, PropertyUndefinedError])
    @pytest.mark.parametrize("group", [AllOf, AnyOf])
    @pytest.mark.parametrize("sibling", [True, False])
    def test_condition_markers_are_false_leaves_in_real_groups(self, condition, group, sibling):
        node = group(
            items=(
                description_predicate(TextOperator.IS_NOT, "Temporary"),
                ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))),
            )
        )
        context = make_context(
            property_values={DESCRIPTION: BatchSlot.failure(condition.from_message("No value"))},
            type_matches={frozenset({ElementType.WALL}): sibling},
        )

        result = node.evaluate(context, ELEMENT)

        assert result.is_success
        assert result.value is (sibling if group is AnyOf else False)

    @pytest.mark.parametrize("group", [AllOf, AnyOf])
    def test_decisive_sibling_does_not_hide_conversion_failure(self, group):
        node = group(items=(ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))), height_predicate()))
        context = make_context(
            property_values={HEIGHT: BatchSlot.success("not a number")},
            type_matches={frozenset({ElementType.WALL}): group is AnyOf},
        )

        result = node.evaluate(context, ELEMENT)

        assert result.is_error
        assert "where.items[1].test" in result.error.message
        assert str(HEIGHT) in result.error.message
        assert "not a number" in result.error.message

    def test_nested_failures_retain_all_paths_property_ids_and_original_causes(self):
        height_error = BatchError.from_message("Numeric property read failed", code=7)
        description_error = BatchError.from_message("Text property read failed", code=9)
        query = nested_query()
        context = make_context(
            property_values={
                HEIGHT: BatchSlot.failure(height_error),
                DESCRIPTION: BatchSlot.failure(description_error),
            },
            type_matches={frozenset({ElementType.WALL}): True},
        )

        result = query.where.evaluate(context, ELEMENT)

        assert result.is_error
        assert "where.items[1].items[0].test" in result.error.message
        assert "where.items[1].items[1].test" in result.error.message
        assert "where.items[2].test" in result.error.message
        assert str(HEIGHT) in result.error.message
        assert str(DESCRIPTION) in result.error.message
        inner_group, repeated_description = result.error.causes
        assert inner_group.causes[0].causes[0] is height_error
        assert inner_group.causes[1].causes[0] is description_error
        assert repeated_description.causes[0] is description_error

    def test_multiple_type_predicates_use_their_own_membership_results(self):
        wall = ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,)))
        slab = ElementTypePredicate(test=ElementTypeTest(types=(ElementType.SLAB,)))
        context = make_context(type_matches={wall.candidate_types(): False, slab.candidate_types(): True})

        assert wall.evaluate(context, ELEMENT).value is False
        assert slab.evaluate(context, ELEMENT).value is True
        assert AnyOf(items=(wall, slab)).evaluate(context, ELEMENT).value is True

    def test_unexpected_family_exception_propagates_through_a_group(self):
        class BrokenTextTest(TextTest):
            def evaluate(self, raw_value: str) -> BatchSlot[bool]:
                raise ValueError("Broken family implementation")

        node = AnyOf(
            items=(
                ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))),
                PropertyPredicate(
                    field_id=DESCRIPTION, test=BrokenTextTest(operator=TextOperator.IS, value="External")
                ),
            )
        )
        context = make_context(
            property_values={DESCRIPTION: BatchSlot.success("External")},
            type_matches={frozenset({ElementType.WALL}): True},
        )

        with pytest.raises(ValueError, match="Broken family implementation"):
            node.evaluate(context, ELEMENT)


class TestPreparedInputs:
    def test_property_only_query_needs_no_type_read(self):
        result = height_predicate().evaluate(make_context(property_values={HEIGHT: BatchSlot.success("3.5")}), ELEMENT)

        assert result.is_success
        assert result.value is True

    @pytest.mark.parametrize(("actual", "expected"), [(ElementType.WALL, True), (ElementType.SLAB, False)])
    def test_type_only_query_needs_no_property_reads(self, actual, expected):
        node = ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL, ElementType.DOOR)))

        result = node.evaluate(make_context(type_matches={node.candidate_types(): actual in node.test.types}), ELEMENT)

        assert result.is_success
        assert result.value is expected

    def test_missing_property_context_is_not_treated_as_an_unavailable_value(self):
        with pytest.raises(KeyError) as caught:
            height_predicate().evaluate(EvaluationContext({PROPERTY_VALUES: {}}), ELEMENT)

        assert caught.value.args == (HEIGHT,)

    def test_missing_type_context_raises_an_execution_input_error(self):
        with pytest.raises(KeyError):
            ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))).evaluate(EvaluationContext(), ELEMENT)


class TestCandidateTypeBounds:
    @pytest.mark.parametrize(
        ("node", "expected"),
        [
            (height_node(), None),
            (type_node(ElementType.WALL, ElementType.WALL), frozenset({ElementType.WALL})),
            (AllOf(items=(height_node(), height_node())), None),
            (
                AllOf(items=(type_node(ElementType.WALL, ElementType.SLAB), type_node(ElementType.SLAB))),
                frozenset({ElementType.SLAB}),
            ),
            (AllOf(items=(type_node(ElementType.WALL), type_node(ElementType.SLAB))), frozenset()),
            (AnyOf(items=(type_node(ElementType.WALL), height_node())), None),
            (
                AnyOf(items=(type_node(ElementType.SLAB), type_node(ElementType.WALL))),
                frozenset({ElementType.WALL, ElementType.SLAB}),
            ),
        ],
    )
    def test_candidate_type_bounds_are_safe_intersections_and_unions(self, node, expected):
        assert node.candidate_types() == expected
