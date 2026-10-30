"""Compare supplied property values without an API or predicate-tree executor."""

import pytest

from multiconn_archicad.utilities.queries import NumberTest, TextTest, evaluate_property
from multiconn_archicad.utilities.results.batch_results import BatchError, BatchRow, BatchSlot
from multiconn_archicad.utilities.results.property_errors import PropertyUnavailableError, PropertyUndefinedError

pytestmark = pytest.mark.unit

NUMBER_EXPECTATIONS = {
    "is": (False, True, False),
    "is not": (True, False, True),
    "is greater than": (False, False, True),
    "is greater than or equal to": (False, True, True),
    "is less than": (True, False, False),
    "is less than or equal to": (True, True, False),
}

TEXT_CASES = [
    ("is", "EXTERNAL", "external", True),
    ("is", "internal", "external", False),
    ("is not", "EXTERNAL", "external", False),
    ("is not", "internal", "external", True),
    ("contains", "External WALL", "wall", True),
    ("contains", "External wall", "door", False),
    ("does not contain", "External WALL", "wall", False),
    ("does not contain", "External wall", "door", True),
    ("starts with", "EXTERNAL wall", "external", True),
    ("starts with", "Internal external", "external", False),
    ("ends with", "External WALL", "wall", True),
    ("ends with", "External wall panel", "wall", False),
]


def test_examples_cover_every_advertised_operator():
    assert set(NUMBER_EXPECTATIONS) == set(NumberTest.operators())
    assert {operator for operator, *_ in TEXT_CASES} == set(TextTest.operators())


@pytest.mark.parametrize("operator", NUMBER_EXPECTATIONS)
@pytest.mark.parametrize(("raw_value", "index"), [("2", 0), ("3", 1), ("4", 2)])
def test_numeric_comparison_below_equal_and_above_operand(operator, raw_value, index):
    result = NumberTest(operator=operator, value=3).evaluate(raw_value)

    assert result.is_success
    assert result.value is NUMBER_EXPECTATIONS[operator][index]


@pytest.mark.parametrize("raw_value", ["3.5", " 3.5 ", "3.5e0", "+3.5"])
def test_numeric_values_use_float_conversion_directly(raw_value):
    assert NumberTest(operator="is", value=3.5).evaluate(raw_value).value is True


def test_numeric_comparisons_apply_no_rounding_or_tolerance():
    raw_value = "0.30000000000000004"

    assert NumberTest(operator="is", value=0.3).evaluate(raw_value).value is False
    assert NumberTest(operator="is greater than", value=0.3).evaluate(raw_value).value is True


@pytest.mark.parametrize("raw_value", ["", "abc", "3 m", "3,5"])
def test_numeric_conversion_failures_are_error_slots(raw_value):
    result = NumberTest(operator="is", value=3).evaluate(raw_value)

    assert result.is_error
    assert raw_value.__repr__() in result.error.message
    assert "number" in result.error.message


@pytest.mark.parametrize(("operator", "raw_value", "operand", "expected"), TEXT_CASES)
def test_text_operations_compare_without_case_sensitivity(operator, raw_value, operand, expected):
    result = TextTest(operator=operator, value=operand).evaluate(raw_value)

    assert result.is_success
    assert result.value is expected


@pytest.mark.parametrize(
    ("operator", "raw_value", "operand", "expected"),
    [
        ("is", " External ", "External", False),
        ("is not", " External ", "External", True),
        ("contains", "External  wall", "external wall", False),
        ("does not contain", "External  wall", "external wall", True),
        ("starts with", " External", "External", False),
        ("ends with", "External ", "External", False),
        ("is", "", "", True),
        ("contains", "External", "", True),
        ("is", "Straße", "STRASSE", True),
    ],
)
def test_text_keeps_whitespace_and_uses_casefold(operator, raw_value, operand, expected):
    result = TextTest(operator=operator, value=operand).evaluate(raw_value)

    assert result.is_success
    assert result.value is expected


@pytest.mark.parametrize(
    ("test", "raw_value", "expected"),
    [
        (NumberTest(operator="is greater than", value=3), "3.5", True),
        (NumberTest(operator="is greater than", value=3), "2.5", False),
        (TextTest(operator="contains", value="external"), "EXTERNAL wall", True),
        (TextTest(operator="does not contain", value="temporary"), "TEMPORARY wall", False),
    ],
)
def test_successful_property_reads_delegate_to_the_family(test, raw_value, expected):
    result = evaluate_property(test, BatchSlot.success(raw_value))

    assert result.is_success
    assert result.value is expected


@pytest.mark.parametrize("family", [TextTest, NumberTest])
@pytest.mark.parametrize("condition", [PropertyUnavailableError, PropertyUndefinedError])
def test_every_operator_returns_false_for_unavailable_or_undefined_properties(family, condition):
    error = condition.from_message("No comparable property value")
    for operator in family.operators():
        test = family(operator=operator, value="example" if family is TextTest else 3)

        result = evaluate_property(test, BatchSlot.failure(error))

        assert result.is_success
        assert result.value is False


@pytest.mark.parametrize("condition", [PropertyUnavailableError, PropertyUndefinedError])
@pytest.mark.parametrize("sibling", [True, False])
def test_undefined_and_unavailable_values_participate_in_groups_as_false(condition, sibling):
    test = TextTest(operator="is not", value="Temporary")
    decision = evaluate_property(test, BatchSlot.failure(condition.from_message("No value")))
    combined = BatchRow((decision, BatchSlot.success(sibling))).aggregate()

    assert combined.map(any).value is sibling
    assert combined.map(all).value is False


@pytest.mark.parametrize(
    "error",
    [
        BatchError.from_message("Not available or not evaluated property", code=7),
        BatchError.from_message("Property not found or invalid", code=7),
        BatchError.from_message("Failed to get property values for element", code=9),
    ],
)
def test_other_property_failures_retain_identity_without_calling_the_family(error):
    class ExplodingTest(NumberTest):
        def evaluate(self, raw_value: str) -> BatchSlot[bool]:
            raise AssertionError("A failed read must not reach the family")

    test = ExplodingTest(operator="is not", value=3)

    result = evaluate_property(test, BatchSlot.failure(error))

    assert result.is_error
    assert result.error is error


@pytest.mark.parametrize("error", [ValueError("Family bug"), RuntimeError("Family bug")])
def test_unexpected_family_exceptions_propagate(error):
    class BrokenTest(NumberTest):
        def evaluate(self, raw_value: str) -> BatchSlot[bool]:
            raise error

    with pytest.raises(type(error)) as caught:
        evaluate_property(BrokenTest(operator="is", value=3), BatchSlot.success("3"))

    assert caught.value is error


@pytest.mark.parametrize("slot", [BatchSlot.filtered(), BatchSlot.upstream_failed()])
def test_skipped_slots_are_not_interpreted_as_completed_reads(slot):
    with pytest.raises(ValueError, match="no successful value"):
        evaluate_property(NumberTest(operator="is not", value=3), slot)


def test_evaluation_preserves_serialized_test_state():
    test = TextTest(operator="starts with", value=" EXTERNAL ")
    original = test.model_dump_json()

    assert test.evaluate(" external wall").value is True
    assert test.model_dump_json() == original
