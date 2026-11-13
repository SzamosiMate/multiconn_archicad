"""Evaluate individual tests; see element_query_predicates.py for a full tree."""

from multiconn_archicad.utilities import BatchSlot, PropertyUnavailableError, PropertyUndefinedError
from multiconn_archicad.utilities.queries import (
    BooleanOperator,
    BooleanTest,
    IntegerTest,
    NumberOperator,
    RealTest,
    PropertyTestModel,
    TextOperator,
    TextTest,
    evaluate_property,
)


def make_examples() -> tuple[tuple[str, PropertyTestModel, BatchSlot[str]], ...]:
    """Use the same read-slot contract as the existing property utilities."""
    return (
        ("Boolean match", BooleanTest(operator=BooleanOperator.IS, value=True), BatchSlot.success("True")),
        ("Boolean non-match", BooleanTest(operator=BooleanOperator.IS_NOT, value=False), BatchSlot.success("False")),
        ("Boolean conversion failure", BooleanTest(operator=BooleanOperator.IS, value=True), BatchSlot.success("yes")),
        ("Numeric match", RealTest(operator=NumberOperator.GREATER_THAN, value=3), BatchSlot.success("3.5")),
        ("Numeric non-match", RealTest(operator=NumberOperator.GREATER_THAN, value=3), BatchSlot.success("2.5")),
        ("Real roundoff match", RealTest(operator=NumberOperator.IS, value=30), BatchSlot.success("29.999999999999996")),
        ("Exact integer match", IntegerTest(operator=NumberOperator.IS, value=3), BatchSlot.success("3")),
        ("Conversion failure", RealTest(operator=NumberOperator.IS, value=3), BatchSlot.success("not a number")),
        (
            "Case-insensitive text",
            TextTest(operator=TextOperator.CONTAINS, value="external"),
            BatchSlot.success("EXTERNAL wall"),
        ),
        (
            "Unavailable negative comparison",
            TextTest(operator=TextOperator.IS_NOT, value="Temporary"),
            BatchSlot.failure(PropertyUnavailableError.from_message("Property is unavailable")),
        ),
        (
            "Undefined value",
            RealTest(operator=NumberOperator.GREATER_THAN, value=3),
            BatchSlot.failure(PropertyUndefinedError.from_message("Property is undefined")),
        ),
    )


if __name__ == "__main__":
    for label, test, read in make_examples():
        result = evaluate_property(test, read)
        if result.is_error:
            print(f"{label}: error ({type(result.error).__name__}: {result.error.message})")
        else:
            print(f"{label}: success ({result.value})")
