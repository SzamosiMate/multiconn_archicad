"""Exercise search and filtering through real utilities and a fake project API."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError, RequestError, TapirCommandError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.utilities.api import Utilities
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    BooleanOperator,
    BooleanTest,
    ElementTypePredicate,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
    QueryValidationError,
    TextOperator,
    TextTest,
)
from multiconn_archicad.utilities.results.batch_results import SlotState
from multiconn_archicad.utilities import FindElementsResult

pytestmark = pytest.mark.unit
HEIGHT = UUID("22222222-2222-4222-8222-222222222222")
DESCRIPTION = UUID("11111111-1111-4111-8111-111111111111")
FLAG = UUID("33333333-3333-4333-8333-333333333333")
TALL, SLAB, SHORT, BAD, UNDEFINED, UNAVAILABLE = [UUID(int=index) for index in range(1, 7)]


def element(guid):
    return tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=guid))


def cell_error(message, available=None):
    return tapir.PropertyValueErrorItem(error=tapir.Error(code=7, message=message), isAvailable=available)


def height_node():
    return PropertyPredicate(property_id=HEIGHT, test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3))


def type_node(*types):
    return ElementTypePredicate(types=types)


def wall_query():
    return Query(where=AllOf(items=(type_node(tapir.ElementType.WALL), height_node())))


class FakeProject:
    def __init__(self):
        self.api = MagicMock()
        self.api.utilities = Utilities(self.api)
        self.types = {
            TALL: tapir.ElementType.WALL,
            SLAB: tapir.ElementType.SLAB,
            SHORT: tapir.ElementType.WALL,
            BAD: tapir.ElementType.WALL,
            UNDEFINED: tapir.ElementType.WALL,
            UNAVAILABLE: tapir.ElementType.WALL,
        }
        self.values = {
            TALL: {HEIGHT: "4", DESCRIPTION: "External"},
            SLAB: {HEIGHT: "5", DESCRIPTION: "External slab"},
            SHORT: {HEIGHT: "2", DESCRIPTION: "Internal"},
            BAD: {HEIGHT: "not a number", DESCRIPTION: "External"},
            UNDEFINED: {HEIGHT: "<Undefined>", DESCRIPTION: "External"},
            UNAVAILABLE: {
                HEIGHT: cell_error("Not available or not evaluated property", False),
                DESCRIPTION: "External",
            },
        }
        self.row_errors = {}
        for guid, row in self.values.items():
            row[FLAG] = {
                TALL: "True",
                BAD: "unexpected",
                UNDEFINED: "<Undefined>",
                UNAVAILABLE: cell_error("Not available or not evaluated property", False),
            }.get(guid, "False")
        self.api.tapir.application.get_add_on_version.return_value = "1.7.3"
        common = {
            "propertyType": "Custom",
            "propertyGroupName": "Example",
            "propertyCollectionType": "Single",
            "propertyIsEditable": True,
            "isExpressionBased": False,
        }
        self.api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult.model_validate(
            {
                "properties": [
                    {
                        **common,
                        "propertyId": {"guid": FLAG},
                        "propertyName": "Flag",
                        "propertyValueType": "Boolean",
                        "propertyMeasureType": "Default",
                    },
                    {
                        **common,
                        "propertyId": {"guid": HEIGHT},
                        "propertyName": "Height",
                        "propertyValueType": "Real",
                        "propertyMeasureType": "Length",
                    },
                    {
                        **common,
                        "propertyId": {"guid": DESCRIPTION},
                        "propertyName": "Description",
                        "propertyValueType": "String",
                        "propertyMeasureType": "Default",
                    },
                ]
            }
        )
        self.api.tapir.element.get_all_elements.side_effect = self.list_all
        self.api.tapir.element.get_elements_by_type.side_effect = self.list_type
        self.api.tapir.element.filter_elements.side_effect = self.filter_types
        self.api.tapir.property.get_property_values_of_elements.side_effect = self.read_values

    def listing(self, ids, databases):
        return tapir.ElementsWithExecutionResults(
            elements=[element(guid) for guid in ids],
            executionResultForDatabases=[tapir.SuccessfulExecutionResult() for _ in databases] if databases else None,
        )

    def list_all(self, *, databases=None, filters=None):
        return self.listing(self.types, databases)

    def list_type(self, kind, *, databases=None, filters=None):
        return self.listing([guid for guid, actual in self.types.items() if actual == kind], databases)

    def read_values(self, elements, properties, **kwargs):
        rows = []
        for item in elements:
            guid = item.elementId.guid
            if guid in self.row_errors:
                rows.append(self.row_errors[guid])
                continue
            cells = []
            for property_id in properties:
                value = self.values[guid][property_id.propertyId.guid]
                cells.append(
                    value
                    if isinstance(value, tapir.PropertyValueErrorItem)
                    else tapir.PropertyValueArrayItem(propertyValue=tapir.PropertyValue(value=value), isAvailable=True)
                )
            rows.append(tapir.PropertyValuesArrayItem(propertyValues=cells))
        return rows

    def filter_types(self, elements, *, element_types):
        return [item for item in elements if self.types.get(item.elementId.guid) in element_types]


@pytest.fixture
def project():
    return FakeProject()


def invoke(project, entry, query, ids=None):
    utility = project.api.utilities.element
    if entry in ("find_elements", "find_elements_result"):
        return getattr(utility, entry)(query)
    return getattr(utility, entry)([TALL] if ids is None else ids, query)


def guids(elements):
    return [item.elementId.guid for item in elements]


@pytest.mark.parametrize(
    ("operator", "expected"), [(BooleanOperator.IS, [TALL]), (BooleanOperator.IS_NOT, [SLAB, SHORT])]
)
def test_boolean_queries_share_discovery_batch_reads_and_diagnostic_execution(project, operator, expected):
    query = Query.model_validate_json(
        Query(
            where=PropertyPredicate(
                property_id=FLAG,
                test=BooleanTest(operator=operator, value=True),
            )
        ).model_dump_json()
    )
    result = project.api.utilities.element.find_elements_result(query)

    assert guids(result.candidates) == list(project.types)
    assert guids(result.outcomes.successes) == expected
    assert result.outcomes.slots[3].is_error
    assert "boolean" in result.outcomes.slots[3].error.message
    assert f"property {FLAG}" in result.outcomes.slots[3].error.message
    assert all(result.outcomes.slots[i].is_filtered for i in [4, 5])
    project.api.tapir.property.get_property_values_of_elements.assert_called_once()
    assert guids(project.api.utilities.element.find_elements(query)) == expected
    filtered = project.api.utilities.element.filter_elements_by_query_result([BAD, TALL, TALL, UNAVAILABLE], query)
    assert filtered.slots[0].is_error
    assert guids(filtered.successes) == ([TALL, TALL] if operator is BooleanOperator.IS else [])
    assert filtered.slots[3].is_filtered


def test_boolean_conversion_error_survives_a_decisive_or_sibling(project):
    query = Query(
        where=AnyOf(
            items=(
                type_node(tapir.ElementType.WALL),
                PropertyPredicate(property_id=FLAG, test=BooleanTest(operator=BooleanOperator.IS, value=True)),
            )
        )
    )
    result = project.api.utilities.element.filter_elements_by_query_result([BAD], query)
    assert result.slots[0].is_error
    assert "where.items[1].test" in result.slots[0].error.message


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (height_node(), None),
        (type_node(tapir.ElementType.WALL, tapir.ElementType.WALL), frozenset({tapir.ElementType.WALL})),
        (AllOf(items=(height_node(), height_node())), None),
        (
            AllOf(items=(type_node(tapir.ElementType.WALL, tapir.ElementType.SLAB), type_node(tapir.ElementType.SLAB))),
            frozenset({tapir.ElementType.SLAB}),
        ),
        (AllOf(items=(type_node(tapir.ElementType.WALL), type_node(tapir.ElementType.SLAB))), frozenset()),
        (AnyOf(items=(type_node(tapir.ElementType.WALL), height_node())), None),
        (
            AnyOf(items=(type_node(tapir.ElementType.SLAB), type_node(tapir.ElementType.WALL))),
            frozenset({tapir.ElementType.WALL, tapir.ElementType.SLAB}),
        ),
    ],
)
def test_candidate_type_bounds_are_safe_intersections_and_unions(node, expected):
    assert node.candidate_types() == expected


def test_typed_search_uses_filter_elements_and_omits_per_element_failures(project):
    result = project.api.utilities.element.find_elements(wall_query())
    assert guids(result) == [TALL]
    project.api.tapir.element.get_elements_by_type.assert_called_once_with(
        tapir.ElementType.WALL, databases=None, filters=None
    )
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_details_of_elements.assert_not_called()
    project.api.tapir.element.filter_elements.assert_called_once()
    project.api.tapir.property.get_property_values_of_elements.assert_called_once()
    project.api.tapir.property.get_all_properties.assert_called_once()
    project.api.tapir.element.change_selection_of_elements.assert_not_called()


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


def test_unrestricted_property_search_uses_one_all_listing_and_no_type_read(project):
    result = project.api.utilities.element.find_elements(Query(where=height_node()))
    assert guids(result) == [TALL, SLAB]
    project.api.tapir.element.get_all_elements.assert_called_once_with(databases=None, filters=None)
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.element.get_details_of_elements.assert_not_called()
    project.api.tapir.element.filter_elements.assert_not_called()


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


def test_unrestricted_or_branch_uses_membership_results_and_keeps_real_failures(project):
    query = Query(where=AnyOf(items=(type_node(tapir.ElementType.WALL), height_node())))
    result = project.api.utilities.element.find_elements(query)
    assert guids(result) == [TALL, SLAB, SHORT, UNDEFINED, UNAVAILABLE]
    project.api.tapir.element.get_all_elements.assert_called_once()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.element.filter_elements.assert_called_once()
    project.api.tapir.element.get_details_of_elements.assert_not_called()


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


def test_typed_branches_keep_their_type_predicates_and_use_consistent_scope(project):
    project.values[TALL][DESCRIPTION] = "W-01"
    project.values[SLAB][DESCRIPTION] = "W-02"

    def branch(kind, prefix):
        return AllOf(
            items=(
                type_node(kind),
                PropertyPredicate(
                    property_id=DESCRIPTION, test=TextTest(operator=TextOperator.STARTS_WITH, value=prefix)
                ),
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
    type_checks = project.api.tapir.element.filter_elements.call_args_list
    assert [call.kwargs["element_types"] for call in type_checks] == [
        [tapir.ElementType.WALL, tapir.ElementType.SLAB],
        [tapir.ElementType.SLAB],
        [tapir.ElementType.WALL],
    ]
    project.api.tapir.element.get_details_of_elements.assert_not_called()


def test_repeated_properties_are_read_once_and_search_duplicates_are_removed(project):
    query = Query(where=AllOf(items=(height_node(), height_node())))
    project.api.tapir.element.get_all_elements.side_effect = None
    project.api.tapir.element.get_all_elements.return_value = project.listing([TALL, TALL, SLAB, TALL], None)
    assert guids(project.api.utilities.element.find_elements(query)) == [TALL, SLAB]
    call = project.api.tapir.property.get_property_values_of_elements.call_args
    assert guids(call.args[0]) == [TALL, SLAB]
    assert [item.propertyId.guid for item in call.args[1]] == [HEIGHT]


def test_one_execution_context_is_shared_across_candidate_evaluations(project, monkeypatch):
    contexts = []
    original = PropertyPredicate.evaluate

    def record_context(self, context, element_id, *, path="where"):
        contexts.append(context)
        return original(self, context, element_id, path=path)

    monkeypatch.setattr(PropertyPredicate, "evaluate", record_context)

    result = project.api.utilities.element.filter_elements_by_query_result(
        [TALL, SLAB, TALL], Query(where=height_node())
    )

    assert guids(result.successes) == [TALL, SLAB, TALL]
    assert len(contexts) == 2
    assert contexts[0] is contexts[1]


def test_contradictory_types_do_not_list_or_read_elements(project):
    query = Query(where=AllOf(items=(type_node(tapir.ElementType.WALL), type_node(tapir.ElementType.SLAB))))
    assert project.api.utilities.element.find_elements(query) == []
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.property.get_all_properties.assert_not_called()


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query_result", "filter_elements_by_query"]
)
def test_invalid_query_is_fatal_even_for_empty_or_impossible_candidates(project, entry):
    query = Query(
        where=AllOf(
            items=(
                type_node(tapir.ElementType.WALL),
                type_node(tapir.ElementType.SLAB),
                PropertyPredicate(property_id=HEIGHT, test=TextTest(operator=TextOperator.IS, value="3")),
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
    query = Query(where=PropertyPredicate(property_id=uuid4(), test=NumberTest(operator=NumberOperator.IS, value=3)))
    with pytest.raises(QueryValidationError) as caught:
        invoke(project, entry, query)
    assert caught.value.result.issues[0].code == "unknown_field"
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.official.property.get_details_of_properties.assert_not_called()


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


def test_read_failure_after_fresh_metadata_validation_uses_normal_filter_policy(project):
    original = cell_error("Property not found or invalid", False)
    project.values[TALL][HEIGHT] = original
    result = project.api.utilities.element.filter_elements_by_query_result([TALL], wall_query())
    assert result.slots[0].is_error
    assert "Property not found or invalid" in result.errors[0].message
    assert project.api.utilities.element.find_elements(wall_query()) == []
    with pytest.raises(BatchOperationError):
        project.api.utilities.element.filter_elements_by_query([TALL], wall_query())


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
        executionResultForDatabases=[tapir.FailedExecutionResult(error=tapir.Error(code=9, message="Database failed"))],
    )
    database = tapir.DatabaseIdArrayItem(databaseId=tapir.DatabaseId(guid=uuid4()))
    with pytest.raises(BatchOperationError, match="Database failed"):
        getattr(project.api.utilities.element, entry)(wall_query(), databases=[database])
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


@pytest.mark.parametrize("stage", ["metadata", "properties", "types", "listing"])
def test_command_and_transport_failures_propagate(project, stage):
    error = RequestError("Disconnected")
    commands = {
        "metadata": project.api.tapir.property.get_all_properties,
        "properties": project.api.tapir.property.get_property_values_of_elements,
        "types": project.api.tapir.element.filter_elements,
        "listing": project.api.tapir.element.get_elements_by_type,
    }
    commands[stage].side_effect = error
    with pytest.raises(RequestError) as caught:
        invoke(project, "find_elements" if stage == "listing" else "filter_elements_by_query_result", wall_query())
    assert caught.value is error


def test_per_element_row_error_is_retained_by_filter_and_omitted_by_search(project):
    original = tapir.ErrorItem(error=tapir.Error(code=9, message="Element read failed"))
    project.row_errors[TALL] = original
    query = Query(where=height_node())
    result = project.api.utilities.element.filter_elements_by_query_result([TALL, SLAB], query)
    assert result.slots[0].is_error
    assert result.slots[0].error.causes[0].error is original.error
    assert guids(result.successes) == [SLAB]
    assert guids(project.api.utilities.element.find_elements(query)) == [SLAB]


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_query_json_must_be_parsed_before_calling_the_utility(project, entry):
    with pytest.raises(TypeError, match="Expected a Query instance"):
        invoke(project, entry, {"where": {"kind": "unsupported"}})
    project.api.tapir.property.get_all_properties.assert_not_called()


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
def test_search_does_not_swallow_unexpected_evaluator_exceptions(project, entry):
    class BrokenNumberTest(NumberTest):
        def evaluate(self, raw_value):
            raise RuntimeError("Evaluator bug")

    query = Query(
        where=PropertyPredicate(property_id=HEIGHT, test=BrokenNumberTest(operator=NumberOperator.IS, value=3))
    )

    with pytest.raises(RuntimeError, match="Evaluator bug"):
        invoke(project, entry, query)


def test_diagnostic_search_aligns_matches_nonmatches_and_errors(project):
    result = project.api.utilities.element.find_elements_result(Query(where=height_node()))

    assert isinstance(result, FindElementsResult)
    assert guids(result.candidates) == [TALL, SLAB, SHORT, BAD, UNDEFINED, UNAVAILABLE]
    assert [slot.state for slot in result.outcomes.slots] == [
        SlotState.SUCCESS,
        SlotState.SUCCESS,
        SlotState.FILTERED,
        SlotState.ERROR,
        SlotState.FILTERED,
        SlotState.FILTERED,
    ]
    assert guids(result.outcomes.successes) == [TALL, SLAB]
    assert result.outcomes.slots[0].value is result.candidates[0]
    error = result.outcomes.slots[3].error
    assert "where.test" in error.message
    assert str(HEIGHT) in error.message
    assert "not a number" in error.causes[0].message
    assert guids(project.api.utilities.element.find_elements(Query(where=height_node()))) == [TALL, SLAB]


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
                    property_id=DESCRIPTION, test=TextTest(operator=TextOperator.STARTS_WITH, value="External")
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


def test_contradictory_types_produce_an_empty_diagnostic_search_without_listing(project):
    query = Query(where=AllOf(items=(type_node(tapir.ElementType.WALL), type_node(tapir.ElementType.SLAB))))

    result = project.api.utilities.element.find_elements_result(query)

    assert result.candidates == ()
    assert result.outcomes.slots == ()
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


@pytest.mark.parametrize("entry", ["find_elements", "find_elements_result"])
@pytest.mark.parametrize("stage", ["metadata", "listing", "types", "properties"])
def test_both_search_methods_propagate_command_and_transport_errors(project, entry, stage):
    error = RequestError("Disconnected")
    commands = {
        "metadata": project.api.tapir.property.get_all_properties,
        "listing": project.api.tapir.element.get_elements_by_type,
        "types": project.api.tapir.element.filter_elements,
        "properties": project.api.tapir.property.get_property_values_of_elements,
    }
    commands[stage].side_effect = error

    with pytest.raises(RequestError) as caught:
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
