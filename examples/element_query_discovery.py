"""Adapt a small offline property batch into searchable query fields."""

import json

from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    AnyOf,
    ElementTypePredicate,
    PropertyCatalogue,
    PropertyPredicate,
    PropertyTest,
    Query,
    TestRegistry,
    validate_query,
)


def make_example_catalogue() -> PropertyCatalogue:
    """Use synthetic metadata; live discovery is Utilities.property.discover_query_fields()."""
    common = {
        "propertyType": "Custom",
        "propertyGroupName": "Example",
        "propertyIsEditable": True,
        "isExpressionBased": False,
    }
    response = GetAllPropertiesResult.model_validate(
        {
            "properties": [
                {
                    **common,
                    "propertyId": {"guid": "22222222-2222-4222-8222-222222222222"},
                    "propertyName": "Height",
                    "propertyCollectionType": "Single",
                    "propertyValueType": "Real",
                    "propertyMeasureType": "Length",
                },
                {
                    **common,
                    "propertyId": {"guid": "11111111-1111-4111-8111-111111111111"},
                    "propertyName": "Fire rating",
                    "propertyCollectionType": "SingleChoiceEnumeration",
                    "propertyValueType": "String",
                    "propertyMeasureType": "Default",
                },
            ]
        }
    )
    return PropertyCatalogue(response.properties, TestRegistry.from_union(PropertyTest))


if __name__ == "__main__":
    catalogue = make_example_catalogue()
    for field in catalogue:
        print(field.qualified_name, "supported:", field.supported)
    height = catalogue.search("height", supported_only=True)[0]
    test = height.create_test(operator="is greater than", value=3)
    query = Query(where=PropertyPredicate.model_validate({**height.reference, "test": test}))
    result = validate_query(query, catalogue)
    result.raise_for_errors()
    print(json.dumps(result.describe(), indent=2))

    # A valid sibling does not skip validation of this unsupported property.
    fire_rating = catalogue.unsupported[0]
    invalid_query = Query(
        where=AnyOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                PropertyPredicate.model_validate(
                    {**fire_rating.reference, "test": {"kind": "text", "operator": "is", "value": "REI 60"}}
                ),
            )
        )
    )
    print(json.dumps(validate_query(invalid_query, catalogue).describe(), indent=2))
    print(json.dumps(catalogue.describe(), indent=2))
