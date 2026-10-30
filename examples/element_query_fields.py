"""Inspect a field and construct a query using offline example metadata."""

import json

from multiconn_archicad.models.tapir.types import PropertyDetails
from multiconn_archicad.utilities.queries import (
    NumberOperator,
    PropertyInfo,
    PropertyPredicate,
    PropertyTest,
    Query,
    TestRegistry,
)


def make_example_field() -> PropertyInfo:
    """Use a placeholder GUID; no project or Archicad connection is required."""
    details = PropertyDetails.model_validate(
        {
            "propertyId": {"guid": "22222222-2222-4222-8222-222222222222"},
            "propertyType": "Custom",
            "propertyGroupName": "Example",
            "propertyName": "Height",
            "propertyCollectionType": "Single",
            "propertyValueType": "Real",
            "propertyMeasureType": "Length",
            "propertyIsEditable": True,
            "isExpressionBased": False,
        }
    )
    return PropertyInfo(details, TestRegistry.from_union(PropertyTest))


if __name__ == "__main__":
    height = make_example_field()
    print(height.qualified_name)
    print(height.operators())

    test = height.create_test(operator=NumberOperator.GREATER_THAN, value=3)
    height.validate(test)
    predicate = PropertyPredicate.model_validate({**height.reference, "test": test})
    query = Query(where=predicate)

    print(json.dumps(height.describe(), indent=2))
    serialized = query.model_dump_json(indent=2)
    print(serialized)
    print(f"Round-trip valid: {Query.model_validate_json(serialized) == query}")
