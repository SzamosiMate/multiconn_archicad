"""Search scope and candidate collection. See element_query_reference.md."""

from uuid import uuid4

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    PropertyPredicate,
    Query,
    TextOperator,
    TextTest,
)

from .support import (
    DESCRIPTION,
    SHORT,
    SLAB,
    TALL,
    UNAVAILABLE,
    UNDEFINED,
    default_listing_filters,
    floor_plan_database,
    guids,
    height_node,
    invoke,
    type_node,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
@pytest.mark.parametrize("typed", [True, False])
def test_default_search_uses_floor_plan_instead_of_the_active_database(project, entry, typed):
    def list_in_database(*args, databases=None, filters=None):
        ids = [TALL] if databases == [floor_plan_database()] else [SLAB]
        return project.listing(ids, databases)

    project.api.tapir.element.get_all_elements.side_effect = list_in_database
    project.api.tapir.element.get_elements_by_type.side_effect = list_in_database
    query = Query(where=type_node(tapir.ElementType.WALL) if typed else height_node())

    result = getattr(project.api.utilities.element, entry)(query)
    matches = result.outcomes.successes if entry == "find_elements_result" else result

    assert guids(matches) == [TALL]
    listing = project.api.tapir.element.get_elements_by_type if typed else project.api.tapir.element.get_all_elements
    assert listing.call_args.kwargs == {
        "databases": [floor_plan_database()],
        "filters": default_listing_filters(),
    }
    project.api.tapir.application.get_current_window_type.assert_not_called()


@pytest.mark.parametrize("typed", [True, False])
@pytest.mark.parametrize("override", ["databases", "filters", "both"])
@pytest.mark.parametrize("empty", [False, True], ids=["nonempty-override", "empty-override"])
def test_explicit_listing_options_replace_defaults_even_when_empty(project, typed, override, empty):
    database = tapir.DatabaseIdArrayItem(databaseId=tapir.DatabaseId(guid=uuid4()))
    filters = (tapir.ElementFilter.INCLUDE_SUB_ELEM_OBJECTS,)
    options = {}
    if override in ("databases", "both"):
        options["databases"] = () if empty else (database,)
    if override in ("filters", "both"):
        options["filters"] = () if empty else filters
    query = Query(where=type_node(tapir.ElementType.WALL) if typed else height_node())

    project.api.utilities.element.find_elements_result(query, **options)

    listing = project.api.tapir.element.get_elements_by_type if typed else project.api.tapir.element.get_all_elements
    assert listing.call_args.kwargs == {
        "databases": list(options.get("databases", [floor_plan_database()])),
        "filters": list(options.get("filters", default_listing_filters())),
    }


def test_listing_defaults_are_fresh_for_each_search(project):
    query = Query(where=height_node())
    project.api.utilities.element.find_elements(query)
    first = project.api.tapir.element.get_all_elements.call_args.kwargs
    first["databases"][0].databaseId.guid = uuid4()
    first["databases"].clear()
    first["filters"].clear()

    project.api.utilities.element.find_elements(query)

    assert project.api.tapir.element.get_all_elements.call_args.kwargs == {
        "databases": [floor_plan_database()],
        "filters": default_listing_filters(),
    }


def test_unrestricted_property_search_uses_one_all_listing_and_no_type_read(project):
    result = project.api.utilities.element.find_elements(Query(where=height_node()))
    assert guids(result) == [TALL, SLAB]
    project.api.tapir.element.get_all_elements.assert_called_once_with(
        databases=[floor_plan_database()], filters=default_listing_filters()
    )
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.element.get_details_of_elements.assert_not_called()
    project.api.tapir.element.filter_elements.assert_not_called()


def test_unrestricted_or_branch_uses_membership_results_and_keeps_real_failures(project):
    query = Query(where=AnyOf(items=(type_node(tapir.ElementType.WALL), height_node())))
    result = project.api.utilities.element.find_elements(query)
    assert guids(result) == [TALL, SLAB, SHORT, UNDEFINED, UNAVAILABLE]
    project.api.tapir.element.get_all_elements.assert_called_once()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.element.filter_elements.assert_called_once()
    project.api.tapir.element.get_details_of_elements.assert_not_called()


def test_typed_branches_keep_their_type_predicates_and_use_consistent_scope(project):
    # Candidate bounds must preserve (slab AND S...) OR (wall AND W...),
    # rather than allowing every type to match either text test.
    project.values[TALL][DESCRIPTION] = "W-01"
    project.values[SLAB][DESCRIPTION] = "W-02"

    def branch(kind, prefix):
        return AllOf(
            items=(
                type_node(kind),
                PropertyPredicate(field_id=DESCRIPTION, test=TextTest(operator=TextOperator.STARTS_WITH, value=prefix)),
            )
        )

    query = Query(where=AnyOf(items=(branch(tapir.ElementType.SLAB, "S"), branch(tapir.ElementType.WALL, "W"))))
    database = tapir.DatabaseIdArrayItem(databaseId=tapir.DatabaseId(guid=uuid4()))
    filters = (tapir.ElementFilter.IS_VISIBLE_BY_LAYER,)
    result = project.api.utilities.element.find_elements(query, databases=(database,), filters=filters)
    assert guids(result) == [TALL]
    calls = project.api.tapir.element.get_elements_by_type.call_args_list
    assert [call.args[0] for call in calls] == [tapir.ElementType.WALL, tapir.ElementType.SLAB]
    assert all(call.kwargs == {"databases": [database], "filters": list(filters)} for call in calls)


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_impossible_type_intersection_returns_empty_without_listing(project, entry):
    query = Query(where=AllOf(items=(type_node(tapir.ElementType.WALL), type_node(tapir.ElementType.SLAB))))
    result = invoke(project, entry, query)
    if entry == "find_elements_result":
        assert result.candidates == ()
        assert result.outcomes.slots == ()
    else:
        assert result == []
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.property.get_all_properties.assert_not_called()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


def test_explicit_none_selects_the_documented_defaults(project):
    project.api.utilities.element.find_elements(Query(where=height_node()), databases=None, filters=None)

    project.api.tapir.element.get_all_elements.assert_called_once_with(
        databases=[floor_plan_database()], filters=default_listing_filters()
    )


def test_explicit_component_types_remain_candidates_under_default_filters(project):
    project.types[TALL] = tapir.ElementType.BEAM_SEGMENT
    query = Query(where=type_node(tapir.ElementType.BEAM_SEGMENT))

    assert guids(project.api.utilities.element.find_elements(query)) == [TALL]
    project.api.tapir.element.get_elements_by_type.assert_called_once_with(
        tapir.ElementType.BEAM_SEGMENT, databases=[floor_plan_database()], filters=default_listing_filters()
    )
