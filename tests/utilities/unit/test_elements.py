from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir.commands import ChangeSelectionOfElementsResult
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.elements import TYPES_3D, ElementUtilities
from multiconn_archicad.utilities.results import BatchResult, SlotState


def _element(guid: UUID | None = None) -> tapir.ElementIdArrayItem:
    return tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=guid or uuid4()))


def _error(message: str = "bad") -> tapir.ErrorItem:
    return tapir.ErrorItem(error=tapir.Error(code=7, message=message))


def _elements_response(*elements: tapir.ElementIdArrayItem, **kwargs: object) -> tapir.ElementsWithExecutionResults:
    return tapir.ElementsWithExecutionResults(elements=list(elements), **kwargs)


def test_set_selected_elements_changes_only_the_difference_and_reports_add_failures():
    api = MagicMock()
    previous, retained = _element(), _element()
    added, rejected = _element(), _element()
    api.tapir.element.get_selected_elements.return_value = [previous, retained]
    response = ChangeSelectionOfElementsResult(
        executionResultsOfRemoveFromSelection=[tapir.SuccessfulExecutionResult()],
        executionResultsOfAddToSelection=[
            tapir.SuccessfulExecutionResult(),
            tapir.FailedExecutionResult(error=tapir.Error(code=7, message="locked")),
        ],
    )
    api.tapir.element.change_selection_of_elements.return_value = response

    result = ElementUtilities(api).set_selected_elements_result([retained, added, rejected])

    api.tapir.element.change_selection_of_elements.assert_called_once_with(
        add_elements_to_selection=[added, rejected],
        remove_elements_from_selection=[previous],
    )
    assert result.count(SlotState.SUCCESS) == 2
    assert [slot.value for slot in result.slots[:2]] == [retained, added]
    assert result.errors[0].message == "locked"

    with pytest.raises(BatchOperationError, match="locked"):
        ElementUtilities(api).set_selected_elements([retained, added, rejected])


def test_set_selected_elements_skips_change_when_selection_matches():
    api = MagicMock()
    first, second = _element(), _element()
    api.tapir.element.get_selected_elements.return_value = [first, second]

    result = ElementUtilities(api).set_selected_elements_result([second, first])

    assert result.successes == [second, first]
    api.tapir.element.change_selection_of_elements.assert_not_called()


def test_set_selected_elements_raises_if_clearing_fails():
    api = MagicMock()
    api.tapir.element.get_selected_elements.return_value = [_element()]
    api.tapir.element.change_selection_of_elements.return_value = ChangeSelectionOfElementsResult(
        executionResultsOfRemoveFromSelection=[
            tapir.FailedExecutionResult(error=tapir.Error(code=7, message="cannot clear"))
        ],
        executionResultsOfAddToSelection=[tapir.SuccessfulExecutionResult()],
    )

    with pytest.raises(BatchOperationError, match="cannot clear"):
        ElementUtilities(api).set_selected_elements([uuid4()])

    api.tapir.element.change_selection_of_elements.assert_called_once()


def test_get_3d_elements_returns_list_in_type_order():
    api = MagicMock()
    responses = {element_type: _elements_response(_element()) for element_type in TYPES_3D}
    api.tapir.element.get_elements_by_type.side_effect = lambda element_type, **_: responses[element_type]

    result = ElementUtilities(api).get_3d_elements()

    calls = api.tapir.element.get_elements_by_type.call_args_list
    assert tuple(call.args[0] for call in calls) == TYPES_3D
    assert all(call.kwargs == {"filters": [tapir.ElementFilter.IS_INDEPENDENT]} for call in calls)
    assert result == [element for response in responses.values() for element in response.elements]


def test_filter_elements_by_property_values_preserves_alignment_and_skips_empty_searches():
    api = MagicMock()
    utilities = ElementUtilities(api)
    prop = uuid4()
    ids = [uuid4(), uuid4(), uuid4()]
    api.utilities.property.get_flat_property_values_result.return_value = BatchResult.from_items(
        ["Layer A", _error("property unavailable"), "layer a"]
    )

    result = utilities.filter_elements_by_property_values_result(ids, prop, ["Layer A"])

    assert result.slots[0].is_success
    assert result.slots[0].value == _element(ids[0])
    assert result.slots[1].is_error
    assert result.slots[1].error.message == "property unavailable"
    assert result.slots[2].is_filtered
    assert api.utilities.property.get_flat_property_values_result.call_count == 1
    passed_elements, passed_property = api.utilities.property.get_flat_property_values_result.call_args.args
    assert [item.elementId.guid for item in passed_elements] == ids
    assert passed_property.propertyId.guid == prop

    api.utilities.property.get_flat_property_values_result.reset_mock()
    no_values = utilities.filter_elements_by_property_values_result(ids, prop, [])
    assert no_values.indices(SlotState.FILTERED) == (0, 1, 2)
    api.utilities.property.get_flat_property_values_result.assert_not_called()

    with pytest.raises(BatchOperationError):
        utilities.filter_elements_by_property_values(ids, prop, ["Layer A"])


def test_grouping_keeps_duplicates_and_empty_keys():
    api = MagicMock()
    utilities = ElementUtilities(api)
    ids = [uuid4(), uuid4(), uuid4(), uuid4()]
    ids[2] = ids[0]
    api.utilities.property.get_flat_property_values.return_value = ["", "first", "", "first"]
    grouped = utilities.group_elements_by_property_value(ids, uuid4())
    assert list(grouped) == ["", "first"]
    assert [item.elementId.guid for item in grouped[""]] == [ids[0], ids[2]]
    assert [item.elementId.guid for item in grouped["first"]] == [ids[1], ids[3]]


def _configure_3d_population(api: MagicMock, elements: list[tapir.ElementIdArrayItem]) -> None:
    api.tapir.element.get_elements_by_type.side_effect = lambda element_type, **_: (
        _elements_response(*elements) if element_type is tapir.ElementType.WALL else _elements_response()
    )


def test_layer_combination_composes_attribute_population_and_property_queries():
    api = MagicMock()
    elements = [_element(), _element(), _element()]
    _configure_3d_population(api, elements)
    api.utilities.attribute.get_layer_names_of_combination.return_value = ["Layer A", "Layer B"]
    prop = _element().elementId.guid
    api.utilities.property.resolve_property_id.return_value = tapir.PropertyIdArrayItem(
        propertyId=tapir.PropertyId(guid=prop)
    )
    api.utilities.property.get_flat_property_values_result.return_value = BatchResult.from_items(
        ["Layer A", "Hidden", "Layer B"]
    )

    result = ElementUtilities(api).get_elements_in_layer_combination_result("Combination")

    assert [element.elementId.guid for element in result.successes] == [
        elements[0].elementId.guid,
        elements[2].elementId.guid,
    ]
    api.utilities.attribute.get_layer_names_of_combination.assert_called_once_with("Combination")
    api.utilities.property.resolve_property_id.assert_called_once_with(
        official.BuiltInPropertyUserId(nonLocalizedName="ModelView_LayerName")
    )
    api.utilities.property.get_flat_property_values_result.assert_called_once()
