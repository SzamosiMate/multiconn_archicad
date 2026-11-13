"""Batched reads and supplied-population execution. See element_query_reference.md."""

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AllOf,
    Query,
)
from multiconn_archicad.utilities.results.batch_results import SlotState

from .support import BAD, HEIGHT, SHORT, SLAB, TALL, UNAVAILABLE, UNDEFINED, guids, height_node, type_node, wall_query

pytestmark = pytest.mark.unit


def test_type_bound_excludes_nonmatching_inputs_before_property_reads(project):
    project.row_errors[SLAB] = tapir.ErrorItem(error=tapir.Error(code=7, message="Must not be read"))

    result = project.api.utilities.element.filter_elements_by_query_result([SLAB, TALL], wall_query())

    assert result.slots[0].is_filtered
    assert guids(result.successes) == [TALL]
    assert guids(project.api.tapir.property.get_property_values_of_elements.call_args.args[0]) == [TALL]


def test_equivalent_type_predicates_share_one_filter_request(project):
    query = Query(
        where=AllOf(
            items=(
                type_node(tapir.ElementType.WALL, tapir.ElementType.SLAB),
                type_node(tapir.ElementType.SLAB, tapir.ElementType.WALL, tapir.ElementType.WALL),
                height_node(),
            )
        )
    )

    assert guids(project.api.utilities.element.find_elements(query)) == [TALL, SLAB]
    project.api.tapir.element.filter_elements.assert_called_once()


def test_type_only_search_has_no_property_or_details_requests(project):
    query = Query(where=type_node(tapir.ElementType.WALL))
    assert guids(project.api.utilities.element.find_elements(query)) == [TALL, SHORT, BAD, UNDEFINED, UNAVAILABLE]
    project.api.tapir.property.get_all_properties.assert_not_called()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()
    project.api.tapir.element.get_details_of_elements.assert_not_called()


def test_type_only_filter_checks_membership_once_and_preserves_duplicate_positions(project):
    query = Query(where=type_node(tapir.ElementType.WALL))
    result = project.api.utilities.element.filter_elements_by_query_result([SLAB, TALL, TALL], query)

    assert [slot.state for slot in result.slots] == [SlotState.FILTERED, SlotState.SUCCESS, SlotState.SUCCESS]
    assert guids(result.successes) == [TALL, TALL]
    assert guids(project.api.tapir.element.filter_elements.call_args.args[0]) == [SLAB, TALL]
    project.api.tapir.element.filter_elements.assert_called_once()
    project.api.tapir.property.get_all_properties.assert_not_called()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


def test_repeated_property_predicates_share_one_batched_column(project):
    query = Query(where=AllOf(items=(height_node(), height_node())))
    project.api.tapir.element.get_all_elements.side_effect = None
    project.api.tapir.element.get_all_elements.return_value = project.listing([TALL, SLAB], None)
    assert guids(project.api.utilities.element.find_elements(query)) == [TALL, SLAB]
    call = project.api.tapir.property.get_property_values_of_elements.call_args
    assert guids(call.args[0]) == [TALL, SLAB]
    assert [item.propertyId.guid for item in call.args[1]] == [HEIGHT]
    project.api.tapir.property.get_property_values_of_elements.assert_called_once()


def test_empty_filter_validates_but_performs_no_element_reads(project):
    result = project.api.utilities.element.filter_elements_by_query_result([], wall_query())
    assert result.slots == ()
    project.api.tapir.property.get_all_properties.assert_called_once()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()
    project.api.tapir.element.get_details_of_elements.assert_not_called()


def test_empty_search_validates_and_lists_but_does_not_read_values(project):
    project.types.clear()

    assert project.api.utilities.element.find_elements(Query(where=height_node())) == []
    project.api.tapir.property.get_all_properties.assert_called_once()
    project.api.tapir.element.get_all_elements.assert_called_once()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


def test_execution_requests_exact_property_ids_without_browse_filters(project):
    query = Query(where=AllOf(items=(height_node(), height_node())))
    project.api.utilities.element.find_elements(query)
    project.api.tapir.property.get_all_properties.assert_called_once_with(
        properties=[tapir.PropertyIdArrayItem(propertyId=tapir.PropertyId(guid=HEIGHT))],
    )
    project.api.tapir.property.get_properties_of_tool_defaults.assert_not_called()
    project.api.official.basic.get_product_info.assert_not_called()
