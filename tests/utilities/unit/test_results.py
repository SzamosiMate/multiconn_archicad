from __future__ import annotations

import pytest
from multiconn_archicad.utilities.results import BatchResult, extract_error
from multiconn_archicad.models.official import types as official_types
from multiconn_archicad.models.tapir import types as tapir_types


class TestExtractError:
    def test_extracts_from_tapir_failed_execution_result(self):
        err = tapir_types.Error(code=404, message="Element not found")
        item = tapir_types.FailedExecutionResult(error=err)
        assert extract_error(item) == err

    def test_extracts_from_tapir_error_item(self):
        err = tapir_types.Error(code=500, message="Internal error")
        item = tapir_types.ErrorItem(error=err)
        assert extract_error(item) == err

    def test_extracts_from_official_failed_execution_result(self):
        err = official_types.Error(code=400, message="Official execution failure")
        item = official_types.FailedExecutionResult(error=err)
        assert extract_error(item) == err

    def test_returns_none_for_successful_models(self):
        assert extract_error(tapir_types.SuccessfulExecutionResult()) is None
        assert extract_error(official_types.SuccessfulExecutionResult()) is None

    def test_does_not_duck_type_arbitrary_dicts_or_objects(self):
        assert extract_error({"success": False, "error": {"code": 1, "message": "msg"}}) is None
        assert extract_error("non_error_string") is None
        assert extract_error(None) is None


class TestBatchResultFromItems:
    def test_all_successful_without_accessor(self):
        raw = ["elem_1", "elem_2"]
        result = BatchResult.from_items(raw)

        assert result.is_all_success is True
        assert result.items == ["elem_1", "elem_2"]
        assert result.successes == ["elem_1", "elem_2"]
        assert result.errors == {}

    def test_all_successful_with_accessor(self):
        class MockProp:
            def __init__(self, val: str):
                self.val = val

        raw = [MockProp("100.0"), MockProp("200.0")]
        result = BatchResult.from_items(raw, accessor=lambda x: x.val)

        assert result.is_all_success is True
        assert result.items == ["100.0", "200.0"]
        assert result.successes == ["100.0", "200.0"]

    def test_partial_failure_with_accessor(self):
        err = tapir_types.Error(code=99, message="Unavailable")
        raw = [
            tapir_types.PropertyValue(value="A"),
            tapir_types.ErrorItem(error=err),
            tapir_types.PropertyValue(value="B"),
        ]
        result = BatchResult.from_items(raw, accessor=lambda pv: pv.value)

        assert result.is_all_success is False
        assert result.items == ["A", None, "B"]
        assert result.successes == ["A", "B"]
        assert result.errors[1] == err


class TestBatchResultFromMasked:
    def test_all_successful(self):
        payload = ["Item_1", "Item_2"]
        mask = [
            tapir_types.SuccessfulExecutionResult(),
            tapir_types.SuccessfulExecutionResult(),
        ]
        result = BatchResult.from_masked(payload, mask)

        assert result.is_all_success is True
        assert result.items == ["Item_1", "Item_2"]
        assert result.successes == ["Item_1", "Item_2"]

    def test_partial_failure_with_accessor(self):
        class MockCommand:
            def __init__(self, name: str):
                self.name = name

        items = [MockCommand("cmd_1"), MockCommand("cmd_2")]
        err = tapir_types.Error(code=500, message="Locked")
        mask = [
            tapir_types.SuccessfulExecutionResult(),
            tapir_types.FailedExecutionResult(error=err),
        ]
        result = BatchResult.from_masked(items, mask, accessor=lambda cmd: cmd.name)

        assert result.is_all_success is False
        assert result.items == ["cmd_1", None]
        assert result.successes == ["cmd_1"]
        assert result.errors[1] == err

    def test_length_mismatch_raises(self):
        items = ["A", "B"]
        mask = [tapir_types.SuccessfulExecutionResult()]
        with pytest.raises(ValueError, match="Items length.*must match mask length"):
            BatchResult.from_masked(items, mask)


class TestBatchResultDisplayAndShape:
    def test_repr_and_str_1d(self):
        pv1 = tapir_types.PropertyValue(value="alpha")
        pv2 = tapir_types.PropertyValue(value="beta")
        result = BatchResult.from_items([pv1, pv2])

        assert repr(result) == "BatchResult[PropertyValue](total=2, successes=2, errors=0)"
        assert str(result) == "BatchResult[PropertyValue]: All 2 succeeded"

    def test_repr_and_str_with_errors(self):
        err = tapir_types.Error(code=404, message="Not Found")
        pv = tapir_types.PropertyValue(value="ok")
        result = BatchResult.from_items([pv, tapir_types.ErrorItem(error=err)])

        assert repr(result) == "BatchResult[PropertyValue](total=2, successes=1, errors=1)"
        assert str(result) == "BatchResult[PropertyValue]: 1/2 succeeded (1 failed)"

    def test_repr_and_str_empty(self):
        result = BatchResult.from_items([])
        assert repr(result) == "BatchResult[empty](total=0, successes=0, errors=0)"
        assert str(result) == "BatchResult[empty]: empty"

    def test_debug_dump(self):
        err = tapir_types.Error(code=500, message="Fail")
        result = BatchResult.from_items(["item_1", tapir_types.ErrorItem(error=err)])

        dump = result.debug_dump()
        assert dump == {"items": ["item_1", None], "errors": {1: err}}