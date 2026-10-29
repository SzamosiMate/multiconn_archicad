"""Build and round-trip a query without connecting to Archicad.

The property GUIDs are illustrative; replace them with actual catalogue GUIDs
before context validation. Evaluation is not implemented yet. Text comparisons
will ignore case and preserve whitespace; numeric operands use SI without added
tolerance.
"""

from uuid import UUID

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    AllOf,
    ElementTypePredicate,
    NumberTest,
    PropertyPredicate,
    Query,
    TextTest,
)


def make_example_query() -> Query:
    """Describe walls taller than three metres with an External description."""
    return Query(
        where=AllOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                PropertyPredicate(
                    property_id=UUID("22222222-2222-4222-8222-222222222222"),
                    test=NumberTest(operator="is greater than", value=3),
                ),
                PropertyPredicate(
                    property_id=UUID("11111111-1111-4111-8111-111111111111"),
                    test=TextTest(operator="starts with", value="External"),
                ),
            )
        )
    )


if __name__ == "__main__":
    query = make_example_query()
    serialized = query.model_dump_json(indent=2)
    print(serialized)
    restored = Query.model_validate_json(serialized)
    print(f"Round-trip valid: {restored == query}")
