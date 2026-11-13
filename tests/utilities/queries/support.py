"""Synthetic project data and a fake project API; expected behavior lives in tests."""

from unittest.mock import MagicMock
from uuid import UUID

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.utilities.api import Utilities
from multiconn_archicad.utilities.queries import (
    AllOf,
    ElementTypePredicate,
    ElementTypeTest,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
)

HEIGHT = UUID("22222222-2222-4222-8222-222222222222")
DESCRIPTION = UUID("11111111-1111-4111-8111-111111111111")
FLAG = UUID("33333333-3333-4333-8333-333333333333")
TALL, SLAB, SHORT, BAD, UNDEFINED, UNAVAILABLE = [UUID(int=index) for index in range(1, 7)]


def element(guid):
    return tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=guid))


def floor_plan_database():
    return tapir.DatabaseIdArrayItem(databaseId=tapir.DatabaseId(guid=UUID("d5d16dd4-093f-4674-895d-410d634d8c7e")))


def default_listing_filters():
    return [tapir.ElementFilter.INCLUDE_SUB_ELEM_OBJECTS, tapir.ElementFilter.IS_INDEPENDENT]


def cell_error(message, available=None):
    return tapir.PropertyValueErrorItem(error=tapir.Error(code=7, message=message), isAvailable=available)


def height_node():
    return PropertyPredicate(field_id=HEIGHT, test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3))


def type_node(*types):
    return ElementTypePredicate(test=ElementTypeTest(types=types))


def wall_query():
    return Query(where=AllOf(items=(type_node(tapir.ElementType.WALL), height_node())))


class FakeProject:
    def __init__(self):
        self.api = MagicMock()
        self.api.utilities = Utilities(self.api)
        self.types = {
            TALL: tapir.ElementType.WALL,
            SLAB: tapir.ElementType.SLAB,
            SHORT: tapir.ElementType.WALL,
            BAD: tapir.ElementType.WALL,
            UNDEFINED: tapir.ElementType.WALL,
            UNAVAILABLE: tapir.ElementType.WALL,
        }
        self.values = {
            TALL: {HEIGHT: "4", DESCRIPTION: "External"},
            SLAB: {HEIGHT: "5", DESCRIPTION: "External slab"},
            SHORT: {HEIGHT: "2", DESCRIPTION: "Internal"},
            BAD: {HEIGHT: "not a number", DESCRIPTION: "External"},
            UNDEFINED: {HEIGHT: "<Undefined>", DESCRIPTION: "External"},
            UNAVAILABLE: {
                HEIGHT: cell_error("Not available or not evaluated property", False),
                DESCRIPTION: "External",
            },
        }
        self.row_errors = {}
        for guid, row in self.values.items():
            row[FLAG] = {
                TALL: "True",
                BAD: "unexpected",
                UNDEFINED: "<Undefined>",
                UNAVAILABLE: cell_error("Not available or not evaluated property", False),
            }.get(guid, "False")
        self.api.read_header_metadata.return_value = None
        self.api.tapir.application.get_add_on_version.return_value = "2.0.0"
        common = {
            "propertyType": "Custom",
            "propertyGroupName": "Example",
            "propertyCollectionType": "Single",
            "propertyIsEditable": True,
            "isExpressionBased": False,
        }
        self.api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult.model_validate(
            {
                "properties": [
                    {
                        **common,
                        "propertyId": {"guid": FLAG},
                        "propertyName": "Flag",
                        "propertyValueType": "Boolean",
                        "propertyMeasureType": "Default",
                    },
                    {
                        **common,
                        "propertyId": {"guid": HEIGHT},
                        "propertyName": "Height",
                        "propertyValueType": "Real",
                        "propertyMeasureType": "Length",
                    },
                    {
                        **common,
                        "propertyId": {"guid": DESCRIPTION},
                        "propertyName": "Description",
                        "propertyValueType": "String",
                        "propertyMeasureType": "Default",
                    },
                ]
            }
        )
        self.api.tapir.element.get_all_elements.side_effect = self.list_all
        self.api.tapir.element.get_elements_by_type.side_effect = self.list_type
        self.api.tapir.element.filter_elements.side_effect = self.filter_types
        self.api.tapir.property.get_property_values_of_elements.side_effect = self.read_values

    def listing(self, ids, databases):
        return tapir.ElementsWithExecutionResults(
            elements=[element(guid) for guid in ids],
            executionResultForDatabases=[tapir.SuccessfulExecutionResult() for _ in databases] if databases else None,
        )

    def list_all(self, *, databases=None, filters=None):
        return self.listing(self.types, databases)

    def list_type(self, kind, *, databases=None, filters=None):
        return self.listing([guid for guid, actual in self.types.items() if actual == kind], databases)

    def read_values(self, elements, properties, **kwargs):
        rows = []
        for item in elements:
            guid = item.elementId.guid
            if guid in self.row_errors:
                rows.append(self.row_errors[guid])
                continue
            cells = []
            for property_id in properties:
                value = self.values[guid][property_id.propertyId.guid]
                cells.append(
                    value
                    if isinstance(value, tapir.PropertyValueErrorItem)
                    else tapir.PropertyValueArrayItem(propertyValue=tapir.PropertyValue(value=value), isAvailable=True)
                )
            rows.append(tapir.PropertyValuesArrayItem(propertyValues=cells))
        return rows

    def filter_types(self, elements, *, element_types):
        return [item for item in elements if self.types.get(item.elementId.guid) in element_types]


def invoke(project, entry, query, ids=None):
    utility = project.api.utilities.element
    if entry in ("find_elements", "find_elements_result"):
        return getattr(utility, entry)(query)
    return getattr(utility, entry)([TALL] if ids is None else ids, query)


def guids(elements):
    return [item.elementId.guid for item in elements]


def property_details(**changes) -> tapir.PropertyDetails:
    """Build synthetic metadata independently of any open Archicad project."""
    data = {
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
    data.update(changes)
    return tapir.PropertyDetails.model_validate(data)
