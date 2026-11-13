"""Results and per-element failures. See element_query_reference.md."""

from uuid import UUID, uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.types import ElementId, ElementIdArrayItem
from multiconn_archicad.utilities import BatchResult, BatchSlot, FindElementsResult
from multiconn_archicad.utilities.queries import (
    AnyOf,
    BooleanTest,
    PropertyPredicate,
    Query,
    TextOperator,
    TextTest,
)
from multiconn_archicad.utilities.queries import FindElementsResult as QueryFindElementsResult
from multiconn_archicad.utilities.results.batch_results import SlotState

from .support import (
    BAD,
    DESCRIPTION,
    FLAG,
    HEIGHT,
    SHORT,
    SLAB,
    TALL,
    UNAVAILABLE,
    UNDEFINED,
    cell_error,
    element,
    guids,
    height_node,
    invoke,
    wall_query,
)

pytestmark = pytest.mark.unit


def test_filter_retains_alignment_duplicates_and_errors_and_plain_filter_raises(project):
    ids = [SHORT, TALL, BAD, TALL]
    result = project.api.utilities.element.filter_elements_by_query_result(ids, wall_query())
    assert [slot.state for slot in result.slots] == [
        SlotState.FILTERED,
        SlotState.SUCCESS,
        SlotState.ERROR,
        SlotState.SUCCESS,
    ]
    assert guids(result.successes) == [TALL, TALL]
    assert "where.items[1].test" in result.errors[0].message
    read_ids = project.api.tapir.property.get_property_values_of_elements.call_args.args[0]
    assert guids(read_ids) == [SHORT, TALL, BAD]
    assert guids(project.api.tapir.element.filter_elements.call_args.args[0]) == [SHORT, TALL, BAD]
    project.api.tapir.element.get_details_of_elements.assert_not_called()
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    with pytest.raises(BatchOperationError):
        project.api.utilities.element.filter_elements_by_query(ids, wall_query())


def test_strict_filter_returns_ordered_duplicate_matches_when_reads_succeed(project):
    result = project.api.utilities.element.filter_elements_by_query([SHORT, TALL, TALL, SLAB], wall_query())

    assert guids(result) == [TALL, TALL]
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_elements_by_type.assert_not_called()


def test_read_failure_after_fresh_metadata_validation_uses_normal_filter_policy(project):
    original = cell_error("Property not found or invalid", False)
    project.values[TALL][HEIGHT] = original
    result = project.api.utilities.element.filter_elements_by_query_result([TALL], wall_query())
    assert result.slots[0].is_error
    assert "Property not found or invalid" in result.errors[0].message
    assert project.api.utilities.element.find_elements(wall_query()) == []
    with pytest.raises(BatchOperationError):
        project.api.utilities.element.filter_elements_by_query([TALL], wall_query())


@pytest.mark.parametrize(
    ("predicate", "matches", "states"),
    [
        pytest.param(
            height_node(),
            [TALL, SLAB],
            [
                SlotState.SUCCESS,
                SlotState.SUCCESS,
                SlotState.FILTERED,
                SlotState.ERROR,
                SlotState.FILTERED,
                SlotState.FILTERED,
            ],
            id="number",
        ),
        pytest.param(
            PropertyPredicate(field_id=FLAG, test=BooleanTest(operator="is", value=True)),
            [TALL],
            [
                SlotState.SUCCESS,
                SlotState.FILTERED,
                SlotState.FILTERED,
                SlotState.ERROR,
                SlotState.FILTERED,
                SlotState.FILTERED,
            ],
            id="boolean",
        ),
    ],
)
def test_diagnostic_search_aligns_matches_nonmatches_conditions_and_parse_errors(project, predicate, matches, states):
    result = project.api.utilities.element.find_elements_result(Query(where=predicate))

    assert isinstance(result, FindElementsResult)
    assert guids(result.candidates) == [TALL, SLAB, SHORT, BAD, UNDEFINED, UNAVAILABLE]
    assert [slot.state for slot in result.outcomes.slots] == states
    assert guids(result.outcomes.successes) == matches
    assert result.outcomes.slots[0].value is result.candidates[0]
    error = result.outcomes.slots[3].error
    assert "where.test" in error.message
    assert str(predicate.field_id) in error.message
    assert guids(project.api.utilities.element.find_elements(Query(where=predicate))) == matches


@pytest.mark.parametrize("failure", ["row", "cell"])
def test_diagnostic_search_preserves_original_read_errors_and_candidate_identity(project, failure):
    if failure == "row":
        original = tapir.ErrorItem(error=tapir.Error(code=9, message="Element read failed"))
        project.row_errors[TALL] = original
    else:
        original = cell_error("Cell read failed", True)
        project.values[TALL][HEIGHT] = original

    result = project.api.utilities.element.find_elements_result(Query(where=height_node()))

    assert result.candidates[0].elementId.guid == TALL
    error = result.outcomes.slots[0].error
    assert error.causes[0].error is original.error
    assert str(HEIGHT) in error.message
    assert "where.test" in error.message


def test_diagnostic_search_conditions_are_false_leaves_and_real_errors_survive_a_decisive_or(project):
    query = Query(
        where=AnyOf(
            items=(
                height_node(),
                PropertyPredicate(
                    field_id=DESCRIPTION, test=TextTest(operator=TextOperator.STARTS_WITH, value="External")
                ),
            )
        )
    )

    result = project.api.utilities.element.find_elements_result(query)

    assert guids(result.outcomes.successes) == [TALL, SLAB, UNDEFINED, UNAVAILABLE]
    assert result.outcomes.slots[3].is_error
    assert "where.items[0].test" in result.outcomes.slots[3].error.message


def test_diagnostic_search_keeps_first_listing_occurrence_and_evaluates_each_guid_once(project):
    first_tall, repeated_tall = element(TALL), element(TALL)
    project.api.tapir.element.get_all_elements.side_effect = None
    project.api.tapir.element.get_all_elements.return_value = tapir.ElementsWithExecutionResults(
        elements=[element(BAD), first_tall, element(SHORT), repeated_tall, element(BAD)],
    )

    result = project.api.utilities.element.find_elements_result(Query(where=height_node()))

    assert guids(result.candidates) == [BAD, TALL, SHORT]
    assert result.candidates[1] is first_tall
    assert result.outcomes.slots[1].value is first_tall
    read_ids = project.api.tapir.property.get_property_values_of_elements.call_args.args[0]
    assert guids(read_ids) == [BAD, TALL, SHORT]
    project.api.tapir.property.get_property_values_of_elements.assert_called_once()


def test_diagnostic_search_captures_candidates_before_narrowing_and_forwards_scope(project):
    project.api.tapir.element.get_elements_by_type.side_effect = None
    project.api.tapir.element.get_elements_by_type.return_value = project.listing([SLAB, TALL, SHORT, TALL], None)
    project.row_errors[SLAB] = tapir.ErrorItem(error=tapir.Error(code=9, message="Excluded element must not be read"))
    database = tapir.DatabaseIdArrayItem(databaseId=tapir.DatabaseId(guid=uuid4()))
    filters = (tapir.ElementFilter.IS_VISIBLE_BY_LAYER,)

    result = project.api.utilities.element.find_elements_result(wall_query(), databases=(database,), filters=filters)

    assert guids(result.candidates) == [SLAB, TALL, SHORT]
    assert [slot.state for slot in result.outcomes.slots] == [SlotState.FILTERED, SlotState.SUCCESS, SlotState.FILTERED]
    project.api.tapir.element.get_elements_by_type.assert_called_once_with(
        tapir.ElementType.WALL, databases=[database], filters=list(filters)
    )
    assert guids(project.api.tapir.property.get_property_values_of_elements.call_args.args[0]) == [TALL, SHORT]


def test_diagnostic_search_retains_all_candidates_when_narrowing_excludes_everyone(project):
    project.api.tapir.element.get_elements_by_type.side_effect = None
    project.api.tapir.element.get_elements_by_type.return_value = project.listing([SLAB, SLAB], None)

    result = project.api.utilities.element.find_elements_result(wall_query())

    assert guids(result.candidates) == [SLAB]
    assert result.outcomes.slots[0].is_filtered
    project.api.tapir.property.get_all_properties.assert_called_once()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


def test_diagnostic_search_distinguishes_empty_population_from_all_failed_candidates(project):
    project.types = {BAD: tapir.ElementType.WALL}
    query = Query(where=height_node())
    failed = project.api.utilities.element.find_elements_result(query)

    assert guids(failed.candidates) == [BAD]
    assert failed.outcomes.successes == []
    assert len(failed.outcomes.errors) == 1
    assert project.api.utilities.element.find_elements(query) == []

    project.types.clear()
    empty = project.api.utilities.element.find_elements_result(query)
    assert empty.candidates == ()
    assert empty.outcomes.slots == ()


@pytest.mark.parametrize(("candidate_count", "outcome_count"), [(1, 0), (0, 1), (2, 1)])
def test_search_result_rejects_misaligned_candidates_and_outcomes(candidate_count, outcome_count):
    candidates = tuple(
        ElementIdArrayItem(elementId=ElementId(guid=UUID(int=index + 1))) for index in range(candidate_count)
    )
    outcomes = BatchResult(tuple(BatchSlot.filtered() for _ in range(outcome_count)))

    with pytest.raises(ValueError, match="Candidate count must match"):
        FindElementsResult(candidates, outcomes)


def test_search_result_copies_candidate_sequence_to_a_tuple():
    candidates = [ElementIdArrayItem(elementId=ElementId(guid=UUID(int=1)))]
    result = FindElementsResult(candidates, BatchResult((BatchSlot.filtered(),)))
    candidates.clear()

    assert isinstance(result.candidates, tuple)
    assert len(result.candidates) == 1
    assert QueryFindElementsResult is FindElementsResult


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query", "filter_elements_by_query_result"]
)
def test_localized_numeric_strings_follow_each_entrypoints_error_policy(project, entry):
    project.types = {TALL: tapir.ElementType.WALL}
    project.values[TALL][HEIGHT] = "3,00"
    query = Query(where=height_node())

    if entry == "filter_elements_by_query":
        with pytest.raises(BatchOperationError, match="3,00"):
            invoke(project, entry, query)
        return

    result = invoke(project, entry, query)
    if entry == "find_elements":
        assert result == []
        return
    outcomes = result.outcomes if entry == "find_elements_result" else result
    assert outcomes.slots[0].is_error
    assert "3,00" in outcomes.errors[0].message
