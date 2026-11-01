"""Run the search/filter APIs through a fake transport; no Archicad is contacted."""

from unittest.mock import MagicMock
from uuid import UUID

from multiconn_archicad.clients.unified_api.api import UnifiedApi
from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    AllOf,
    ElementTypePredicate,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
)

HEIGHT = str(UUID("22222222-2222-4222-8222-222222222222"))
ELEMENTS = [str(UUID(int=index)) for index in range(1, 4)]
VALUES = dict(zip(ELEMENTS, ("3.5", "2.5", "not a number"), strict=True))


def fake_command(command: str, parameters: dict | None = None) -> dict:
    """Return representative JSON through the normal generated client parsers."""
    parameters = parameters or {}
    if command == "GetAddOnVersion":
        return {"version": "1.7.3"}
    if command == "GetAllProperties":
        return {
            "properties": [
                {
                    "propertyId": {"guid": HEIGHT},
                    "propertyType": "Custom",
                    "propertyGroupName": "Example",
                    "propertyName": "Height",
                    "propertyCollectionType": "Single",
                    "propertyValueType": "Real",
                    "propertyMeasureType": "Length",
                    "propertyIsEditable": True,
                    "isExpressionBased": False,
                }
            ]
        }
    if command == "GetElementsByType":
        return {"elements": [{"elementId": {"guid": guid}} for guid in ELEMENTS]}
    if command == "GetPropertyValuesOfElements":
        return {
            "propertyValuesForElements": [
                {
                    "propertyValues": [
                        {"propertyValue": {"value": VALUES[item["elementId"]["guid"]]}, "isAvailable": True}
                    ]
                }
                for item in parameters["elements"]
            ]
        }
    if command == "FilterElements":
        return {"elements": parameters["elements"]}  # Every example element is a wall.
    raise AssertionError(f"Unexpected command: {command}")


def make_example_api() -> UnifiedApi:
    core = MagicMock()
    core.post_tapir_command.side_effect = fake_command
    return UnifiedApi(core)


def make_example_query() -> Query:
    return Query(
        where=AllOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                PropertyPredicate(
                    property_id=UUID(HEIGHT), test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3)
                ),
            )
        )
    )


if __name__ == "__main__":
    api = make_example_api()
    query = make_example_query()
    print("Search matches:", [str(item.elementId.guid) for item in api.utilities.element.find_elements(query)])
    diagnostic = api.utilities.element.find_elements_result(query)
    print("Search candidates:", [str(item.elementId.guid) for item in diagnostic.candidates])
    print("Search outcomes:", [slot.state.value for slot in diagnostic.outcomes.slots])
    for index, slot in enumerate(diagnostic.outcomes.slots):
        if slot.is_error:
            print("Search error:", diagnostic.candidates[index].elementId.guid, slot.error.message)
    supplied = [ELEMENTS[1], ELEMENTS[0], ELEMENTS[2], ELEMENTS[0]]
    result = api.utilities.element.filter_elements_by_query_result(supplied, query)
    print("Filter states:", [slot.state.value for slot in result.slots])
    print("Filter matches:", [str(item.elementId.guid) for item in result.successes])
    try:
        api.utilities.element.filter_elements_by_query(supplied, query)
    except BatchOperationError as error:
        print("Strict filter raises:", type(error).__name__)
