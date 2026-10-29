"""Preserve property conditions and failures while projecting display strings."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError, RequestError, TapirCommandError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import PropertyUnavailableError, PropertyUndefinedError
from multiconn_archicad.utilities.namespaces.properties import PropertyUtilities
from multiconn_archicad.utilities.results.batch_results import BatchError, SlotState

pytestmark = pytest.mark.unit


def _value(value: str, available: bool | None = None) -> tapir.PropertyValueArrayItem:
    return tapir.PropertyValueArrayItem(propertyValue=tapir.PropertyValue(value=value), isAvailable=available)


def _error(message: str, available: bool | None = None) -> tapir.PropertyValueErrorItem:
    return tapir.PropertyValueErrorItem(error=tapir.Error(code=7, message=message), isAvailable=available)


@pytest.fixture
def api():
    api = MagicMock()
    api.tapir.application.get_add_on_version.return_value = "1.7.3"
    return api


@pytest.mark.parametrize(
    ("version", "expected_kwargs"),
    [
        ("1.7.2", {}),
        ("1.7.3", {"include_availability": True}),
        ("1.7.10", {"include_availability": True}),
        ("1.8.0", {"include_availability": True}),
    ],
)
def test_read_requests_availability_only_on_supported_versions(api, version, expected_kwargs):
    api.tapir.application.get_add_on_version.return_value = version
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=[_value("value")])
    ]
    element, property_id = uuid4(), uuid4()

    result = PropertyUtilities(api).get_flat_property_values_result([element], property_id)

    assert result.successes == ["value"]
    api.tapir.application.get_add_on_version.assert_called_once_with()
    args, kwargs = api.tapir.property.get_property_values_of_elements.call_args
    assert args[0][0].elementId.guid == element
    assert args[1][0].propertyId.guid == property_id
    assert kwargs == expected_kwargs


@pytest.mark.parametrize("version", ["1.7.2", "1.7.3"])
def test_flat_read_recognizes_only_the_exact_undefined_sentinel(api, version):
    api.tapir.application.get_add_on_version.return_value = version
    values = ["first", "<Undefined>", "<undefined>", " <Undefined>", "", "last"]
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=[_value(value)]) for value in values
    ]

    result = PropertyUtilities(api).get_flat_property_values_result([uuid4() for _ in values], uuid4())

    assert result.indices(SlotState.ERROR) == (1,)
    assert isinstance(result.slots[1].error, PropertyUndefinedError)
    assert result.slots[1].error.message == "Property value is undefined"
    assert result.successes == ["first", "<undefined>", " <Undefined>", "", "last"]


def test_grid_distinguishes_unavailability_from_other_failures_and_preserves_rows(api):
    unavailable = _error("Not available or not evaluated property", False)
    not_evaluated = _error("Not available or not evaluated property", True)
    ambiguous = _error("Not available or not evaluated property")
    invalid_guid = _error("Property not found or invalid", False)
    conversion = _error("Failed to get property value as string", False)
    row_error = tapir.ErrorItem(error=tapir.Error(code=9, message="Failed to get property values for element"))
    cells = [_value("ok"), _value("<Undefined>"), unavailable, not_evaluated, ambiguous, invalid_guid, conversion]
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=cells),
        row_error,
    ]

    result = PropertyUtilities(api).get_property_values_per_element_result([uuid4(), uuid4()], [uuid4() for _ in cells])

    assert result.width == len(cells)
    assert result.row_lengths == (len(cells), len(cells))
    assert result.rows[0][0].value == "ok"
    assert isinstance(result.rows[0][1].error, PropertyUndefinedError)
    assert isinstance(result.rows[0][2].error, PropertyUnavailableError)
    assert result.rows[0][2].error.error is unavailable.error
    for index, original in enumerate([not_evaluated, ambiguous, invalid_guid, conversion], start=3):
        assert type(result.rows[0][index].error) is BatchError
        assert result.rows[0][index].error.error is original.error
    assert result.rows[1].error.error is row_error.error
    assert all(slot.error is result.rows[1].error for slot in result.rows[1])


def test_available_value_and_undefined_remain_distinct(api):
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=[_value("value", True)]),
        tapir.PropertyValuesArrayItem(propertyValues=[_value("<Undefined>", True)]),
    ]

    result = PropertyUtilities(api).get_flat_property_values_result([uuid4(), uuid4()], uuid4())

    assert result.slots[0].value == "value"
    assert isinstance(result.slots[1].error, PropertyUndefinedError)


def test_flat_read_preserves_row_failures_and_classifies_cell_failures(api):
    row_error = tapir.ErrorItem(error=tapir.Error(code=9, message="Failed to get property values for element"))
    unavailable = _error("Not available or not evaluated property", False)
    api.tapir.property.get_property_values_of_elements.return_value = [
        row_error,
        tapir.PropertyValuesArrayItem(propertyValues=[unavailable]),
    ]

    result = PropertyUtilities(api).get_flat_property_values_result([uuid4(), uuid4()], uuid4())

    assert type(result.slots[0].error) is BatchError
    assert result.slots[0].error.error is row_error.error
    assert isinstance(result.slots[1].error, PropertyUnavailableError)


def test_dictionary_aggregation_and_mapping_preserve_specialized_causes(api):
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(
            propertyValues=[_value("<Undefined>"), _error("Not available or not evaluated property", False)]
        )
    ]
    utilities = PropertyUtilities(api)
    elements, properties = [uuid4()], [uuid4(), uuid4()]

    grid = utilities.get_property_values_per_element_result(elements, properties).map(str.upper)
    assert isinstance(grid.rows[0][0].error, PropertyUndefinedError)
    assert isinstance(grid.rows[0][1].error, PropertyUnavailableError)
    result = utilities.get_property_values_dict_per_element_result(elements, properties)
    assert isinstance(result.errors[0].causes[0], PropertyUndefinedError)
    assert isinstance(result.errors[0].causes[1], PropertyUnavailableError)


@pytest.mark.parametrize("condition", ["undefined", "unavailable"])
@pytest.mark.parametrize("shape", ["flat", "grid", "dictionary"])
def test_plain_read_methods_raise_for_property_conditions(api, condition, shape):
    cell = (
        _value("<Undefined>") if condition == "undefined" else _error("Not available or not evaluated property", False)
    )
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=[cell])
    ]
    utilities = PropertyUtilities(api)
    elements, property_id = [uuid4()], uuid4()

    with pytest.raises(BatchOperationError) as caught:
        if shape == "flat":
            utilities.get_flat_property_values(elements, property_id)
        elif shape == "grid":
            utilities.get_property_values_per_element(elements, [property_id])
        else:
            utilities.get_property_values_dict_per_element(elements, [property_id])

    error = caught.value.result.errors[0]
    if shape == "dictionary":
        error = error.causes[0]
    expected_type = PropertyUndefinedError if condition == "undefined" else PropertyUnavailableError
    assert isinstance(error, expected_type)


@pytest.mark.parametrize("stage", ["version", "read"])
def test_whole_command_failures_propagate(api, stage):
    error = RequestError("Disconnected") if stage == "version" else TapirCommandError("Command failed")
    if stage == "version":
        api.tapir.application.get_add_on_version.side_effect = error
    else:
        api.tapir.property.get_property_values_of_elements.side_effect = error

    with pytest.raises(type(error)) as caught:
        PropertyUtilities(api).get_flat_property_values_result([uuid4()], uuid4())

    assert caught.value is error
    if stage == "version":
        api.tapir.property.get_property_values_of_elements.assert_not_called()
