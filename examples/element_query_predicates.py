"""Evaluate a complete query with compatible supplied values, without Archicad.

For real project data, validate the query against its property catalogue first.
This example demonstrates recursion, not candidate listing or API execution.
"""

from unittest.mock import MagicMock
from uuid import UUID

from multiconn_archicad.models.tapir.types import ElementId, ElementIdArrayItem, ElementType
from multiconn_archicad.utilities import BatchGrid, BatchRow, BatchSlot, PropertyUndefinedError
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    ContextBuilder,
    ElementTypePredicate,
    EvaluationContext,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
    TextOperator,
    TextTest,
)

HEIGHT = UUID("22222222-2222-4222-8222-222222222222")
DESCRIPTION = UUID("11111111-1111-4111-8111-111111111111")
TALL, SLAB, UNDEFINED, INVALID = (UUID(int=index) for index in range(1, 5))


def make_example_query() -> Query:
    """Match walls that are tall or have an External description."""
    return Query(
        where=AllOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                AnyOf(
                    items=(
                        PropertyPredicate(
                            property_id=HEIGHT, test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3)
                        ),
                        PropertyPredicate(
                            property_id=DESCRIPTION, test=TextTest(operator=TextOperator.STARTS_WITH, value="External")
                        ),
                    )
                ),
            )
        )
    )


def make_context(query: Query) -> EvaluationContext:
    """Supply one shared batch of reads for four elements, without live calls."""
    grid = BatchGrid(
        rows=(
            BatchRow((BatchSlot.success("3.5"), BatchSlot.success("Internal"))),
            BatchRow((BatchSlot.success("3.5"), BatchSlot.success("External"))),
            BatchRow(
                (
                    BatchSlot.failure(PropertyUndefinedError.from_message("Height is undefined")),
                    BatchSlot.success("External wall"),
                )
            ),
            BatchRow((BatchSlot.success("not a number"), BatchSlot.success("External"))),
        ),
        width=2,
    )
    candidates = [ElementIdArrayItem(elementId=ElementId(guid=guid)) for guid in (TALL, SLAB, UNDEFINED, INVALID)]
    api = MagicMock()
    api.utilities.property.get_property_values_per_element_result.return_value = grid
    api.tapir.element.filter_elements.return_value = [item for item in candidates if item.elementId.guid != SLAB]
    builder = ContextBuilder()
    query.where.prepare(builder)
    return builder.build(api, candidates)


if __name__ == "__main__":
    query = make_example_query()
    context = make_context(query)
    elements = (
        ("Tall wall", TALL),
        ("Slab", SLAB),
        ("Undefined height, External description", UNDEFINED),
        ("Invalid height", INVALID),
    )
    for label, element_id in elements:
        result = query.where.evaluate(context, element_id)
        print(f"{label}: {result.error if result.is_error else result.value}")
