"""Discover disconnected field snapshots and resolve identities; see query editing guide."""

import json
from pathlib import Path
from unittest.mock import MagicMock, call
from uuid import UUID, uuid4

import pytest

from multiconn_archicad.errors import MulticonnArchicadError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.models.tapir.types import PropertyDetails, PropertyType
from multiconn_archicad.orchestration.basic_types import PendingResponse, ProductInfo, TapirInfo
from multiconn_archicad.orchestration.header_state import HeaderMetadata
from multiconn_archicad.utilities.api import Utilities
from multiconn_archicad.utilities.namespaces.properties import PropertyUtilities
from multiconn_archicad.utilities.queries import (
    AmbiguousPropertyTypeError,
    NumberTest,
    PropertyCatalogue,
    PropertyInfo,
    PropertyTest,
    TextTest,
    UnsupportedPropertyInfo,
    UnsupportedPropertyTypeError,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry
from multiconn_archicad.utilities.queries.editing import QueryRow

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "query_property_discovery_19723.json"
ELEMENT_ID = UUID("7E221F33-829B-4FBC-A670-E74DABCE6289")
SDK_ELEMENT_ID = UUID("8BACB089-BBFE-41C2-B5A4-D1CEBC2F4FB3")
HEIGHT = UUID("02DB7087-5E1D-4AF3-AF62-4D08C1B70C3E")
POSITION = UUID("53402BE5-29D9-44A5-B6D6-4FA90938DDC9")
MISSING = UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def metadata() -> list[PropertyDetails]:
    return GetAllPropertiesResult.model_validate_json(FIXTURE.read_text(encoding="utf-8")).properties


def test_catalogue_preserves_order_names_and_distinct_builtin_identities(metadata):
    catalogue = PropertyCatalogue(metadata, Registry.from_union(PropertyTest))

    assert len(catalogue) == len(metadata) == 8
    assert tuple(catalogue) == catalogue.fields
    assert [field.property_id for field in catalogue] == [row.propertyId.guid for row in metadata]
    assert catalogue[ELEMENT_ID].qualified_name == "General Parameters / Element ID"
    assert catalogue[SDK_ELEMENT_ID].qualified_name == "GeneralElemProperties / ElementID"
    assert catalogue[ELEMENT_ID].reference != catalogue[SDK_ELEMENT_ID].reference
    assert len(catalogue.supported) == 5
    assert len(catalogue.unsupported) == 3
    assert all(isinstance(field, PropertyInfo) for field in catalogue.supported)
    assert all(isinstance(field, UnsupportedPropertyInfo) for field in catalogue.unsupported)


@pytest.mark.parametrize("archicad_major", [26, 27])
def test_browse_scope_hides_fundamental_fields_but_resolves_exact_references(metadata, archicad_major):
    custom = metadata[0].model_copy(
        update={
            "propertyId": tapir.PropertyId(guid=uuid4()),
            "propertyType": PropertyType.CUSTOM,
            "propertyName": "Custom element tag",
        }
    )
    api = MagicMock()
    api.utilities = Utilities(api)
    api.read_header_metadata.return_value = None
    api.tapir.application.get_add_on_version.return_value = "2.0.0"
    api.official.basic.get_product_info.return_value.version = archicad_major
    api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult(properties=[*metadata, custom])
    api.official.property.get_all_property_ids.return_value = [
        tapir.PropertyIdArrayItem(propertyId=custom.propertyId),
    ]
    api.tapir.property.get_properties_of_tool_defaults.return_value = [
        tapir.ToolDefaultProperties(
            properties=[
                tapir.ToolDefaultProperty(
                    propertyId=tapir.PropertyId(guid=ELEMENT_ID),
                    propertyName="Element ID",
                    propertyGroupId=tapir.PropertyGroupId(guid=uuid4()),
                )
            ]
        ),
        tapir.ErrorItem(error=tapir.Error(code=1, message="No tool default")),
    ]
    api.official.classification.get_all_classification_systems.return_value = []

    catalogue = api.utilities.element.discover_query_fields()
    entries = {entry.field.qualified_name: entry.group_path for entry in catalogue.browse_fields()}
    assert entries["General Parameters / Element ID"] == ("Built-in Properties", "General Parameters")
    assert "GeneralElemProperties / ElementID" not in entries
    assert ("User-defined Properties", custom.propertyGroupName) in entries.values()
    reference = {"kind": "property", "field_id": str(SDK_ELEMENT_ID)}
    assert catalogue.resolve(reference).property_id == SDK_ELEMENT_ID
    assert catalogue.resolve({"kind": "property", "field_id": str(MISSING)}) is None

    api.tapir.property.get_all_properties.reset_mock()
    api.official.property.get_all_property_ids.reset_mock()
    api.tapir.property.get_properties_of_tool_defaults.reset_mock()
    api.official.basic.get_product_info.reset_mock()
    scoped = api.utilities.element.discover_query_fields([QueryRow(predicate=reference)])
    api.tapir.property.get_all_properties.assert_called_once_with(
        properties=[tapir.PropertyIdArrayItem(propertyId=tapir.PropertyId(guid=SDK_ELEMENT_ID))],
    )
    assert scoped.resolve(reference).property_id == SDK_ELEMENT_ID
    api.official.basic.get_product_info.assert_not_called()
    api.official.property.get_all_property_ids.assert_not_called()
    api.tapir.property.get_properties_of_tool_defaults.assert_not_called()


@pytest.mark.parametrize("archicad_major", [28, 29])
def test_browse_scope_uses_all_properties_directly_from_archicad_28(metadata, archicad_major):
    api = MagicMock()
    api.utilities = Utilities(api)
    api.read_header_metadata.return_value = HeaderMetadata(
        product_info=ProductInfo(version=archicad_major, buildNumber=3001, languageCode="INT"),
        tapir_info=TapirInfo(version="2.0.0"),
        archicad_id=PendingResponse(),
        archicad_location=PendingResponse(),
    )
    api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult(properties=[metadata[0]])
    api.official.classification.get_all_classification_systems.return_value = []

    catalogue = api.utilities.element.discover_query_fields()

    assert any(entry.field.qualified_name == "General Parameters / Element ID" for entry in catalogue.browse_fields())
    api.tapir.property.get_all_properties.assert_called_once_with()
    api.read_header_metadata.assert_called_once_with()
    api.tapir.application.get_add_on_version.assert_not_called()
    api.official.basic.get_product_info.assert_not_called()
    api.official.property.get_all_property_ids.assert_not_called()
    api.tapir.property.get_properties_of_tool_defaults.assert_not_called()


def test_unsupported_metadata_keeps_identity_choices_and_an_explicit_reason(metadata):
    catalogue = PropertyCatalogue(metadata, Registry.from_union(PropertyTest))
    field = catalogue[POSITION]

    assert not field.supported
    assert field.qualified_name == "CategoryPropertyDefinitionGroup / Position"
    assert field.unsupported_reason and "SingleChoiceEnumeration" in field.unsupported_reason
    assert field.details.possibleEnumValues
    assert field.operators() == ()
    assert field.test_schema() is None
    with pytest.raises(UnsupportedPropertyTypeError, match="Position"):
        field.create_test(operator="is", value="Interior")
    with pytest.raises(UnsupportedPropertyTypeError, match="Position"):
        field.validate(TextTest(operator="is", value="Interior"))


def test_supported_and_unsupported_descriptions_are_json_friendly(metadata):
    catalogue = PropertyCatalogue(metadata, Registry.from_union(PropertyTest))

    description = json.loads(json.dumps(catalogue.describe()))

    assert len(description["fields"]) == 8
    assert [field["measure_type"] for field in description["fields"]] == [
        details.propertyMeasureType.value for details in metadata
    ]
    enabled = description["fields"][0]
    disabled = next(row for row in description["fields"] if row["name"] == "Position")
    assert enabled["supported"] is True
    assert enabled["unsupported_reason"] is None
    assert enabled["test_schema"]
    assert disabled["supported"] is False
    assert disabled["unsupported_reason"]
    assert disabled["operators"] == []
    assert disabled["test_schema"] is None


def test_lookup_accepts_shared_identifier_inputs_and_distinguishes_missing_from_malformed(metadata):
    catalogue = PropertyCatalogue(metadata, Registry.from_union(PropertyTest))

    assert catalogue.get(str(HEIGHT).upper()) is catalogue[HEIGHT]
    assert catalogue.get(metadata[2].propertyId) is catalogue[HEIGHT]
    assert catalogue.get(MISSING) is None
    with pytest.raises(KeyError):
        catalogue[MISSING]
    with pytest.raises(ValueError):
        catalogue.get("not-a-guid")


def test_search_matches_labels_case_insensitively_with_explicit_group_and_support_filters(metadata):
    catalogue = PropertyCatalogue(metadata, Registry.from_union(PropertyTest))

    heights = catalogue.search("HEIGHT")
    assert [field.group for field in heights] == ["WallProperties", "Wall"]
    assert catalogue.search("height", group="WallProperties") == (catalogue[HEIGHT],)
    assert catalogue.search("wallproperties / wall height") == (catalogue[HEIGHT],)
    assert catalogue.search("", supported_only=True) == catalogue.supported
    assert catalogue.search("POSITION") == (catalogue[POSITION],)
    assert catalogue.search("POSITION", supported_only=True) == ()
    assert catalogue.search("missing") == ()
    assert catalogue.search("general_opening_ids")[0].name == "General_Opening_IDs"


def test_empty_catalogue_is_an_explicit_empty_snapshot():
    catalogue = PropertyCatalogue([], Registry.from_union(PropertyTest))

    assert len(catalogue) == 0
    assert catalogue.fields == catalogue.supported == catalogue.unsupported == catalogue.search() == ()
    assert catalogue.describe() == {"fields": []}


def test_duplicate_guids_are_rejected_instead_of_overwriting_fields(metadata):
    with pytest.raises(ValueError, match="Duplicate field GUID"):
        PropertyCatalogue([metadata[0], metadata[0]], Registry.from_union(PropertyTest))


def test_ambiguity_and_unexpected_family_errors_are_not_misreported_as_unsupported(metadata):
    class OtherNumberTest(NumberTest):
        pass

    class BrokenNumberTest(NumberTest):
        @classmethod
        def accepts(cls, details: PropertyDetails) -> bool:
            raise RuntimeError("broken family")

    with pytest.raises(AmbiguousPropertyTypeError):
        PropertyCatalogue(metadata, Registry(NumberTest, OtherNumberTest))
    with pytest.raises(RuntimeError, match="broken family"):
        PropertyCatalogue(metadata, Registry(BrokenNumberTest))


def test_discovery_uses_one_batch_call_without_reading_element_values(metadata):
    api = MagicMock()
    api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult(properties=metadata)
    utilities = PropertyUtilities(api)

    catalogue = utilities.discover_query_fields()

    assert len(catalogue) == 8
    assert api.mock_calls == [call.tapir.property.get_all_properties()]
    assert isinstance(catalogue[HEIGHT].create_test(operator="is greater than", value=3), NumberTest)


def test_refresh_is_explicit_and_old_snapshots_do_not_change(metadata):
    api = MagicMock()
    api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult(properties=metadata)
    utilities = PropertyUtilities(api)
    first = utilities.discover_query_fields()

    metadata[2].propertyName = "New height"
    second = utilities.discover_query_fields()

    assert api.tapir.property.get_all_properties.call_count == 2
    assert first[HEIGHT].name == "Wall Height"
    assert second[HEIGHT].name == "New height"


def test_discovery_accepts_an_explicit_registry(metadata):
    api = MagicMock()
    api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult(properties=metadata)

    catalogue = PropertyUtilities(api).discover_query_fields(registry=Registry(NumberTest))

    assert len(catalogue.supported) == 2
    assert not catalogue[ELEMENT_ID].supported
    assert catalogue[HEIGHT].supported


def test_api_failures_propagate_instead_of_becoming_an_empty_catalogue():
    api = MagicMock()
    api.tapir.property.get_all_properties.side_effect = RuntimeError("API unavailable")

    with pytest.raises(RuntimeError, match="API unavailable"):
        PropertyUtilities(api).discover_query_fields()


@pytest.mark.parametrize("rows", [None, []], ids=["browse", "empty-draft"])
def test_combined_discovery_checks_tapir_support_before_reading_fields(project, rows):
    project.api.tapir.application.get_add_on_version.return_value = "1.8.0"

    with pytest.raises(MulticonnArchicadError, match="require Tapir 2.0.0 or newer"):
        project.api.utilities.element.discover_query_fields(rows)

    project.api.tapir.property.get_all_properties.assert_not_called()
    project.api.official.classification.get_all_classification_systems.assert_not_called()
