"""Exercise discovery with a minimal sample of the saved port-19723 probe."""

import json
from pathlib import Path
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.models.tapir.types import PropertyDetails
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
    assert len(catalogue.supported) == 4
    assert len(catalogue.unsupported) == 4
    assert all(isinstance(field, PropertyInfo) for field in catalogue.supported)
    assert all(isinstance(field, UnsupportedPropertyInfo) for field in catalogue.unsupported)


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
    with pytest.raises(ValueError, match="Duplicate property GUID"):
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
