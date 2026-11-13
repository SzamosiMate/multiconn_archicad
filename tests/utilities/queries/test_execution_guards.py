"""Validation before I/O and query-wide failures. See element_query_reference.md."""

from uuid import uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError, MulticonnArchicadError, RequestError, TapirCommandError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AllOf,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
    QueryValidationError,
    TextOperator,
    TextTest,
)

from .support import HEIGHT, TALL, element, height_node, invoke, type_node, wall_query

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query_result", "filter_elements_by_query"]
)
def test_invalid_query_is_fatal_even_for_empty_or_impossible_candidates(project, entry):
    query = Query(
        where=AllOf(
            items=(
                type_node(tapir.ElementType.WALL),
                type_node(tapir.ElementType.SLAB),
                PropertyPredicate(field_id=HEIGHT, test=TextTest(operator=TextOperator.IS, value="3")),
            )
        )
    )
    with pytest.raises(QueryValidationError) as caught:
        invoke(project, entry, query, [])
    assert caught.value.result.issues[0].code == "invalid_test"
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_unknown_property_is_rejected_before_candidate_listing(project, entry):
    query = Query(where=PropertyPredicate(field_id=uuid4(), test=NumberTest(operator=NumberOperator.IS, value=3)))
    with pytest.raises(QueryValidationError) as caught:
        invoke(project, entry, query)
    assert caught.value.result.issues[0].code == "unknown_field"
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.official.property.get_details_of_properties.assert_not_called()


@pytest.mark.parametrize("typed", [True, False])
@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_whole_listing_error_is_fatal(project, typed, entry):
    method = project.api.tapir.element.get_elements_by_type if typed else project.api.tapir.element.get_all_elements
    method.side_effect = TapirCommandError("Listing failed", code=9)
    query = Query(where=type_node(tapir.ElementType.WALL) if typed else height_node())
    with pytest.raises(TapirCommandError, match="Listing failed"):
        invoke(project, entry, query)
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_partial_database_listing_failure_is_fatal(project, entry):
    project.api.tapir.element.get_elements_by_type.side_effect = None
    project.api.tapir.element.get_elements_by_type.return_value = tapir.ElementsWithExecutionResults(
        elements=[element(TALL)],
        executionResultForDatabases=[
            tapir.SuccessfulExecutionResult(),
            tapir.FailedExecutionResult(error=tapir.Error(code=9, message="Database failed")),
        ],
    )
    database = tapir.DatabaseIdArrayItem(databaseId=tapir.DatabaseId(guid=uuid4()))
    with pytest.raises(BatchOperationError, match="Database failed"):
        getattr(project.api.utilities.element, entry)(wall_query(), databases=[database, database])
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query", "filter_elements_by_query_result"]
)
def test_query_json_must_be_parsed_before_calling_the_utility(project, entry):
    with pytest.raises(TypeError, match="Expected a Query instance"):
        invoke(project, entry, {"where": {"kind": "unsupported"}})
    project.api.tapir.property.get_all_properties.assert_not_called()


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query", "filter_elements_by_query_result"]
)
@pytest.mark.parametrize("installed", ["1.8.0", "2.0.0rc1"])
def test_execution_requires_tapir_2_before_discovery_even_for_empty_input(project, entry, installed):
    project.api.tapir.application.get_add_on_version.return_value = installed
    with pytest.raises(MulticonnArchicadError, match="require Tapir 2.0.0 or newer"):
        invoke(project, entry, wall_query(), [])
    project.api.tapir.property.get_all_properties.assert_not_called()


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_search_does_not_swallow_unexpected_evaluator_exceptions(project, entry):
    class BrokenNumberTest(NumberTest):
        def evaluate(self, raw_value):
            raise RuntimeError("Evaluator bug")

    query = Query(where=PropertyPredicate(field_id=HEIGHT, test=BrokenNumberTest(operator=NumberOperator.IS, value=3)))

    with pytest.raises(RuntimeError, match="Evaluator bug"):
        invoke(project, entry, query)


@pytest.mark.parametrize(
    ("entry", "stage"),
    [
        (entry, stage)
        for entry in (
            "find_elements",
            "find_elements_result",
            "filter_elements_by_query",
            "filter_elements_by_query_result",
        )
        for stage in ("metadata", "listing", "types", "properties")
        if stage != "listing" or entry.startswith("find")
    ],
    ids=lambda value: value,
)
@pytest.mark.parametrize("error_type", [RequestError, TapirCommandError], ids=["transport", "whole-command"])
def test_query_wide_failures_raise_from_every_applicable_entrypoint(project, entry, stage, error_type):
    error = error_type("Command failed")
    commands = {
        "metadata": project.api.tapir.property.get_all_properties,
        "listing": project.api.tapir.element.get_elements_by_type,
        "types": project.api.tapir.element.filter_elements,
        "properties": project.api.tapir.property.get_property_values_of_elements,
    }
    commands[stage].side_effect = error

    with pytest.raises(error_type) as caught:
        invoke(project, entry, wall_query())
    assert caught.value is error


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query_result", "filter_elements_by_query"]
)
@pytest.mark.parametrize("version", ["1.1", "2.0", "0.9", "invalid"])
def test_version_rejection_precedes_io_even_for_empty_or_impossible_populations(project, entry, version):
    query = Query(
        schema_version=version,
        where=AllOf(
            items=(
                type_node(tapir.ElementType.WALL),
                type_node(tapir.ElementType.SLAB),
                height_node(),
            )
        ),
    )

    with pytest.raises(ValueError, match="query schema version"):
        invoke(project, entry, query, [])

    assert project.api.tapir.mock_calls == []
