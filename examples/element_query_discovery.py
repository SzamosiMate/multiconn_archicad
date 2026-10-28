"""Adapt a small offline property batch into searchable query fields."""

import json

from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.utilities.queries import PropertyCatalogue, PropertyTest, TestRegistry


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
    print(height.create_test(operator="is greater than", value=3).model_dump_json())
    print(json.dumps(catalogue.describe(), indent=2))
