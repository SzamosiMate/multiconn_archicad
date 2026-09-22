from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError, BatchWriteError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import PopulationResults
from multiconn_archicad.utilities.properties import (
    PropertyUtilities,
    create_element_property_values,
    create_element_property_values_flat,
    create_element_property_values_sparse,
    get_possible_enum_values,
)
from multiconn_archicad.utilities.results import (
    BatchGrid,
    BatchResult,
    BatchRow,
    BatchSlot,
    SlotState,
)


def _value(value: str) -> tapir.PropertyValueArrayItem:
    return tapir.PropertyValueArrayItem(propertyValue=tapir.PropertyValue(value=value))


def _error() -> tapir.ErrorItem:
    return tapir.ErrorItem(error=tapir.Error(code=7, message="bad"))


def test_payload_builders_and_sparse_matrix_omit_failed_cells():
    elements, properties = [uuid4(), uuid4()], [uuid4(), uuid4()]
    assert len(create_element_property_values(elements, properties, [["a", None], [0, False]])) == 4
    assert len(create_element_property_values_flat(elements, properties[0], ["a", "b"])) == 2
    sparse = create_element_property_values_sparse(elements, properties, [[_error(), "x"], ["y", _error()]])
    assert len(sparse) == 2
    assert sparse[0].elementId.guid == elements[0]
    assert sparse[1].elementId.guid == elements[1]

    matrix = BatchGrid.from_rows([["a", _error()], _error()], width=2)
    sparse_from_result = create_element_property_values_sparse(elements, properties, matrix)
    assert len(sparse_from_result) == 1
    assert sparse_from_result[0].elementId.guid == elements[0]


def test_matrix_read_preserves_cell_error_and_dictionary_aggregates_failed_rows():
    api = MagicMock()
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=[_error(), _error()]),
        tapir.PropertyValuesArrayItem(propertyValues=[_value("b"), _value("c")]),
    ]
    utilities = PropertyUtilities(api)
    elements, properties = [uuid4(), uuid4()], [uuid4(), uuid4()]
    result = utilities.get_property_values_per_element_result(elements, properties)
    assert list(result.iter_errors())[0][0] == (0, 0)

    dictionary_result = utilities.get_property_values_dict_per_element_result(elements, properties, ["a", "b"])
    assert dictionary_result.successes == [{"a": "b", "b": "c"}]
    assert len(dictionary_result.errors[0].causes) == 2
    assert "contains 2 error(s)" in dictionary_result.errors[0].message
    with pytest.raises(BatchOperationError):
        utilities.get_property_values_dict_per_element(elements, properties, ["a", "b"])
    with pytest.raises(ValueError):
        utilities.get_property_values_dict_per_element(elements, properties, ["a"])


def test_row_error_and_partial_copy_pipeline_keep_other_cells_writable():
    api = MagicMock()
    elements, properties = [uuid4(), uuid4()], [uuid4(), uuid4()]
    api.tapir.property.get_property_values_of_elements.return_value = [
        tapir.PropertyValuesArrayItem(propertyValues=[_value("a"), _error()]),
        _error(),
    ]
    read = PropertyUtilities(api).get_property_values_per_element_result(elements, properties)
    assert read.indices(SlotState.ERROR) == ((0, 1), (1, 0), (1, 1))
    results = PopulationResults(elements)
    results.record("read", read)
    coordinates = read.indices(SlotState.SUCCESS)
    payload = create_element_property_values_sparse(elements, properties, read)
    assert len(payload) == 1
    api.tapir.property.set_property_values_of_elements.return_value = [tapir.SuccessfulExecutionResult(success=True)]
    write = BatchResult.from_items(api.tapir.property.set_property_values_of_elements(payload))
    results.record("copy", write, item_indices=[row for row, _ in coordinates])
    report = results.snapshot(completed=True)
    assert report.outcomes[0].failed
    assert report.outcomes[1].failed
    assert api.tapir.property.set_property_values_of_elements.call_count == 1


def test_matrix_write_rejects_zero_properties_and_supports_zero_elements():
    api = MagicMock()
    api.tapir.property.set_property_values_of_elements.return_value = []
    utilities = PropertyUtilities(api)

    # 1. Zero properties (width = 0) is rejected
    with pytest.raises(ValueError, match="At least one property must be specified."):
        utilities.set_property_values_per_element_result([uuid4()], [], [[]])

    # 2. Zero elements with valid properties (0 x M) is supported
    prop = uuid4()
    result = utilities.set_property_values_per_element_result([], [prop], [])
    assert result.rows == ()
    assert result.row_lengths == ()


def test_sparse_flat_write_omits_unsuccessful_values_and_projects_api_results():
    api = MagicMock()
    utilities = PropertyUtilities(api)
    elements = [uuid4(), uuid4(), uuid4(), uuid4()]
    property_id = uuid4()
    values = BatchResult(
        (
            BatchSlot.success("first"),
            BatchSlot.failure("invalid"),
            BatchSlot.filtered(),
            BatchSlot.success("last"),
        )
    )
    api.tapir.property.set_property_values_of_elements.return_value = [
        tapir.SuccessfulExecutionResult(success=True),
        _error(),
    ]

    result = utilities.set_flat_property_values_sparse_result(elements, property_id, values)

    payload = api.tapir.property.set_property_values_of_elements.call_args.args[0]
    assert [item.elementId.guid for item in payload] == [elements[0], elements[3]]
    assert [item.propertyValue.value for item in payload] == ["first", "last"]
    assert result.slots[0].is_success
    assert result.slots[1].is_upstream_failed
    assert result.slots[2].is_filtered
    assert result.slots[3].is_error


def test_sparse_flat_write_validates_element_count():
    utilities = PropertyUtilities(MagicMock())

    with pytest.raises(ValueError, match="Expected 1 rows in values_matrix, got 0"):
        utilities.set_flat_property_values_sparse_result([uuid4()], uuid4(), BatchResult(()))


def test_scripting_write_returns_none_and_partial_failure_raises_informative_error():
    api = MagicMock()
    utilities = PropertyUtilities(api)
    elements = [uuid4(), uuid4()]
    property_id = uuid4()

    api.tapir.property.set_property_values_of_elements.return_value = [
        tapir.SuccessfulExecutionResult(success=True),
        _error(),
    ]
    with pytest.raises(BatchWriteError) as raised:
        utilities.set_flat_property_values(elements, property_id, ["first", "second"])

    error = raised.value
    assert error.succeeded_count == 1
    assert error.failed_count == 1
    assert error.upstream_failed_count == 0
    assert error.filtered_count == 0
    assert error.partial_success is True
    assert error.result.slots[1].is_error
    assert "Single property write partially failed." in str(error)
    assert "Successful writes were applied and were not rolled back." in str(error)
    assert "  - [1]: [7] bad" in str(error)

    api.tapir.property.set_property_values_of_elements.return_value = [
        tapir.SuccessfulExecutionResult(success=True),
        tapir.SuccessfulExecutionResult(success=True),
    ]
    assert utilities.set_flat_property_values(elements, property_id, ["first", "second"]) is None


def test_sparse_scripting_write_reports_write_errors_and_omitted_input_counts():
    api = MagicMock()
    utilities = PropertyUtilities(api)
    values = BatchResult(
        (
            BatchSlot.success("first"),
            BatchSlot.failure("unavailable"),
            BatchSlot.filtered(),
            BatchSlot.success("last"),
        )
    )
    api.tapir.property.set_property_values_of_elements.return_value = [
        tapir.SuccessfulExecutionResult(success=True),
        _error(),
    ]

    with pytest.raises(BatchWriteError) as raised:
        utilities.set_flat_property_values_sparse(
            [uuid4(), uuid4(), uuid4(), uuid4()], uuid4(), values
        )

    error = raised.value
    assert error.succeeded_count == 1
    assert error.failed_count == 1
    assert error.upstream_failed_count == 1
    assert error.filtered_count == 1
    assert "1 value was skipped because an upstream operation failed." in str(error)
    assert "1 value was filtered intentionally." in str(error)


def test_dense_matrix_write_rejects_skipped_input_before_calling_api():
    api = MagicMock()
    utilities = PropertyUtilities(api)
    values = BatchGrid(((BatchRow((BatchSlot.filtered(),)),)), width=1)

    with pytest.raises(BatchOperationError, match="requires every item to succeed"):
        utilities.set_property_values_per_element_result([uuid4()], [uuid4()], values)

    api.tapir.property.set_property_values_of_elements.assert_not_called()


def test_resolution_metadata_and_enum_helpers():
    api = MagicMock()
    guid = uuid4()
    api.official.property.get_property_ids.return_value = [
        official.PropertyIdArrayItem(propertyId=official.PropertyId(guid=guid))
    ]
    utilities = PropertyUtilities(api)
    user_id = official.UserDefinedPropertyUserId(localizedName=["Group", "Name"])
    assert utilities.resolve_property_id(user_id).propertyId.guid == guid
    definition = official.PropertyDefinition(
        group=official.PropertyGroup(propertyGroupId=official.PropertyGroupId(guid=uuid4()), name="G"),
        name="N",
        description="",
        isEditable=True,
        type="string",
        possibleEnumValues=None,
    )
    api.official.property.get_details_of_properties.return_value = [
        official.PropertyDefinitionWrapperItem(propertyDefinition=definition)
    ]
    assert utilities.get_property_types([guid]) == ["string"]
    assert get_possible_enum_values(definition) == []
