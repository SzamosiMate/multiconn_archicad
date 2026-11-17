"""Enumeration and GUID contracts, including metadata, editing and batch execution."""

import json
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from multiconn_archicad.utilities.queries import (
    AllOf,
    CollectionOperator,
    EnumOperator,
    EnumTest,
    GuidOperator,
    GuidTest,
    InvalidPropertyTestError,
    MultiEnumTest,
    PropertyCatalogue,
    PropertyInfo,
    PropertyPredicate,
    PropertyTest,
    Query,
    UnsupportedPropertyInfo,
    evaluate_property,
    validate_query,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry
from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query
from multiconn_archicad.utilities.results.batch_results import BatchSlot
from multiconn_archicad.utilities.results.property_errors import PropertyUnavailableError, PropertyUndefinedError

from .support import BAD, SHORT, SLAB, TALL, UNAVAILABLE, UNDEFINED, cell_error, guids, property_details

pytestmark = pytest.mark.unit

TARGET = UUID("abcdefab-1234-4234-8234-abcdefabcdef")
ENUM, GUID, MULTI = (UUID(int=index) for index in (101, 102, 103))


def enum_details(collection="SingleChoiceEnumeration", labels=("Red", "Blue", "Light Blue"), **changes):
    return property_details(
        propertyCollectionType=collection,
        propertyValueType="String",
        propertyMeasureType="Default",
        possibleEnumValues=[{"enumValue": {"displayValue": label, "guid": UUID(int=0)}} for label in labels],
        **changes,
    )


@pytest.mark.parametrize("operator, equal, different", [("is", True, False), ("is not", False, True)])
def test_single_enum_compares_exact_labels(operator, equal, different):
    test = EnumTest(operator=operator, value="Red")
    assert test.evaluate("Red").value is equal
    for raw in ("red", " Red", "Red ", "Blue"):
        assert test.evaluate(raw).value is different


@pytest.mark.parametrize("operator, equal, different", [("is", True, False), ("is not", False, True)])
def test_guid_comparison_normalizes_identity(operator, equal, different):
    test = GuidTest(operator=operator, value=TARGET)
    for spelling in (str(TARGET), str(TARGET).upper(), TARGET.hex, "{" + str(TARGET) + "}"):
        assert test.evaluate(spelling).value is equal
    assert test.evaluate(str(UUID(int=0))).value is different


@pytest.mark.parametrize("raw", ["", "not-a-guid", "<Undefined>"])
@pytest.mark.parametrize("operator", ["is", "is not"])
def test_malformed_guid_reads_remain_errors(raw, operator):
    result = GuidTest(operator=operator, value=TARGET).evaluate(raw)
    assert result.is_error
    assert repr(raw) in result.error.message


@pytest.mark.parametrize(
    "operator, operand, raw, matched",
    [
        ("is", ("Red", "Blue"), "Blue; Red", True),
        ("is", ("Red",), "Red; Blue", False),
        ("is", ("Red", "Blue"), "Red", False),
        ("is", (), "", True),
        ("is", ("Red",), "", False),
        ("is", (), "Red", False),
        ("contains", ("Blue",), "Red; Blue", True),
        ("contains", ("Blue",), "Light Blue", False),
        ("contains", ("Red",), "red", False),
        ("contains", ("Red",), "", False),
        ("contains", (" Red ",), "Blue;  Red ", True),
        ("does not contain", ("Blue",), "Light Blue", True),
        ("does not contain", ("Blue",), "Red; Blue", False),
        ("does not contain", ("Red",), "", True),
        ("contains", ("Blue", "Red"), "Red; Blue; Light Blue", True),
        ("contains", ("Blue", "Red"), "Red", False),
        ("contains", ("Red", "Light Blue"), "Red; Blue", False),
        ("does not contain", ("Red", "Light Blue"), "Red; Blue", False),
        ("does not contain", ("Red", "Light Blue"), "Blue", True),
        ("contains", (), "", True),
        ("does not contain", (), "Red; Blue", True),
    ],
)
def test_multi_enum_uses_whole_selection_equality_and_item_membership(operator, operand, raw, matched):
    result = MultiEnumTest(operator=operator, value=operand).evaluate(raw)
    assert result.is_success
    assert result.value is matched


@pytest.mark.parametrize(
    "family, collection", [(EnumTest, "SingleChoiceEnumeration"), (MultiEnumTest, "MultipleChoiceEnumeration")]
)
@pytest.mark.parametrize("source", ["StaticBuiltIn", "DynamicBuiltIn", "Custom"])
def test_enum_fields_offer_metadata_labels_even_with_zero_option_guids(family, collection, source):
    details = enum_details(collection, propertyType=source)
    info = PropertyInfo(details, Registry.from_union(PropertyTest))
    value = ("Blue", "Red") if family is MultiEnumTest else "Blue"
    test = info.create_test(operator="is", value=value)
    assert type(test) is family
    assert test.validate_for(details) is None
    schema = info.test_schema()
    operand = schema["properties"]["value"]
    if family is MultiEnumTest:
        operand = operand["items"]
    assert operand["enum"] == ["Red", "Blue", "Light Blue"]


@pytest.mark.parametrize(
    "test, collection",
    [
        (EnumTest(operator="is", value="red"), "SingleChoiceEnumeration"),
        (EnumTest(operator="is not", value="Old choice"), "SingleChoiceEnumeration"),
        (MultiEnumTest(operator="is", value=("Red", "Old choice")), "MultipleChoiceEnumeration"),
        (MultiEnumTest(operator="contains", value=("Red", "Old choice")), "MultipleChoiceEnumeration"),
        (MultiEnumTest(operator="does not contain", value=("Old choice",)), "MultipleChoiceEnumeration"),
    ],
)
def test_enum_operands_must_exist_in_current_metadata(test, collection):
    with pytest.raises(InvalidPropertyTestError, match="not a choice"):
        test.validate_for(enum_details(collection))


@pytest.mark.parametrize("source", ["StaticBuiltIn", "DynamicBuiltIn", "Custom"])
def test_guid_family_accepts_all_property_origins(source):
    details = property_details(propertyValueType="Guid", propertyType=source)
    info = PropertyInfo(details, Registry.from_union(PropertyTest))
    test = info.create_test(operator="is", value=str(TARGET))
    assert isinstance(test, GuidTest)
    assert test.value == TARGET
    assert info.test_schema()["properties"]["value"]["format"] == "uuid"


@pytest.mark.parametrize(
    "test, metadata",
    [
        (EnumTest(operator="is", value="Red"), {"propertyCollectionType": "Single"}),
        (EnumTest(operator="is", value="Red"), {"propertyCollectionType": "MultipleChoiceEnumeration"}),
        (MultiEnumTest(operator="contains", value=("Red",)), {"propertyCollectionType": "SingleChoiceEnumeration"}),
        (GuidTest(operator="is", value=TARGET), {"propertyCollectionType": "List", "propertyValueType": "Guid"}),
        (GuidTest(operator="is", value=TARGET), {"propertyValueType": "String"}),
    ],
)
def test_new_families_reject_incompatible_metadata(test, metadata):
    details = enum_details()
    data = details.model_dump()
    data.update(metadata)
    details = type(details).model_validate(data)
    assert not type(test).accepts(details)
    with pytest.raises(InvalidPropertyTestError):
        test.validate_for(details)
    with pytest.raises(InvalidPropertyTestError):
        type(test).schema_for(details)


@pytest.mark.parametrize("collection", ["SingleChoiceEnumeration", "MultipleChoiceEnumeration"])
@pytest.mark.parametrize("labels", [(), ("Red", "Red")])
def test_missing_or_ambiguous_enum_choices_remain_unsupported(collection, labels):
    details = enum_details(collection, labels=labels)
    catalogue = PropertyCatalogue([details], Registry.from_union(PropertyTest))
    assert isinstance(catalogue[details.propertyId], UnsupportedPropertyInfo)
    assert catalogue.unsupported[0].unsupported_reason


def test_empty_choice_can_only_be_supported_for_single_enums():
    single = enum_details(labels=("", "Red"))
    assert EnumTest.accepts(single)
    EnumTest(operator="is", value="").validate_for(single)
    assert not MultiEnumTest.accepts(enum_details("MultipleChoiceEnumeration", labels=("", "Red")))


@pytest.mark.parametrize(
    "family, collection, value",
    [
        (EnumTest, "SingleChoiceEnumeration", "A; B"),
        (MultiEnumTest, "MultipleChoiceEnumeration", ("A; B",)),
    ],
)
def test_semicolon_labels_are_accepted_under_the_initial_parsing_assumption(family, collection, value):
    details = enum_details(collection, labels=("A; B", "C"))
    info = PropertyInfo(details, Registry.from_union(PropertyTest))
    assert type(info.create_test(operator="is", value=value)) is family


@pytest.mark.parametrize(
    "family, operator, value",
    [
        (EnumTest, "is", 1),
        (EnumTest, "is", b"Red"),
        (GuidTest, "is", "not-a-guid"),
        (MultiEnumTest, "is", "Red"),
        (MultiEnumTest, "is", ("Red", "Red")),
        (MultiEnumTest, "is", ("Red", 1)),
        (MultiEnumTest, "contains", ("Red", "Red")),
        (MultiEnumTest, "does not contain", ("Red", "Red")),
        (MultiEnumTest, "contains", b"Red"),
        (MultiEnumTest, "contains", None),
        (MultiEnumTest, "contains", "Red"),
        (MultiEnumTest, "does not contain", "Red"),
    ],
)
def test_new_operands_are_strict_and_operator_specific(family, operator, value):
    with pytest.raises(ValidationError):
        family(operator=operator, value=value)


@pytest.mark.parametrize("family", [EnumTest, GuidTest, MultiEnumTest])
@pytest.mark.parametrize("operator", ["available", "is undefined", "has default value"])
def test_property_state_operators_are_not_advertised_or_accepted(family, operator):
    assert operator not in family.operators()
    with pytest.raises(ValidationError):
        family(operator=operator, value="Red")


@pytest.mark.parametrize(
    "test",
    [EnumTest(operator=operator, value="Red") for operator in EnumOperator]
    + [GuidTest(operator=operator, value=TARGET) for operator in GuidOperator]
    + [MultiEnumTest(operator=operator, value=("Blue", "Red")) for operator in CollectionOperator],
)
def test_every_new_operator_round_trips_through_queries_and_frozen_models(test):
    query = Query(where=PropertyPredicate(field_id=ENUM, test=test))
    payload = query.model_dump(mode="json")
    assert payload["where"]["test"]["operator"] == test.operator.value
    assert Query.model_validate_json(query.model_dump_json()) == query
    assert Draft202012Validator(Query.model_json_schema()).is_valid(payload)
    with pytest.raises(ValidationError, match="frozen"):
        test.value = "changed"
    with pytest.raises(ValidationError):
        type(test).model_validate({**test.model_dump(), "extra": True})


@pytest.mark.parametrize(
    "operator, value, valid",
    [
        ("is", [], True),
        ("is", ["Blue", "Red"], True),
        ("is", ["Red", "Red"], False),
        ("is", "Red", False),
        ("is", ["Unknown"], False),
        ("contains", "Red", False),
        ("contains", ["Red"], True),
        ("contains", ["Red", "Blue"], True),
        ("contains", ["Red", "Unknown"], False),
        ("contains", ["Red", "Red"], False),
        ("contains", "Unknown", False),
        ("does not contain", "Blue", False),
        ("does not contain", [], True),
        ("does not contain", ["Red", "Blue"], True),
    ],
)
def test_metadata_schema_enforces_choice_labels_and_collection_operands(operator, value, valid):
    schema = MultiEnumTest.schema_for(enum_details("MultipleChoiceEnumeration"))
    assert Draft202012Validator(schema).is_valid({"operator": operator, "value": value}) is valid


@pytest.mark.parametrize(
    "operator, value, operand_type",
    [
        ("is", ["Blue", "Red"], "array"),
        ("contains", ["Red", "Blue"], "array"),
        ("does not contain", ["Blue"], "array"),
    ],
)
def test_operator_specific_inputs_keep_metadata_choices_and_compile_drafts(operator, value, operand_type):
    info = PropertyInfo(enum_details("MultipleChoiceEnumeration"), Registry.from_union(PropertyTest))
    data = {"operator": operator, "value": value}
    before = json.dumps(info.test_schema(), sort_keys=True)
    description = info.describe_test_inputs(data)
    operator_input, value_input = description.fields
    assert operator_input.required and value_input.required
    assert value_input.schema["type"] == operand_type
    choices = value_input.schema["items"] if operand_type == "array" else value_input.schema
    assert choices["enum"] == ["Red", "Blue", "Light Blue"]
    row = QueryRow(predicate={**info.reference, "test": {"kind": "multi_enum", **data}})
    result = build_query(QueryRows(rows=[row]))
    assert result.query.where.test == info.create_test(**data)
    value_input.schema.clear()
    assert json.dumps(info.test_schema(), sort_keys=True) == before
    assert data == {"operator": operator, "value": value}


@pytest.mark.parametrize("data", [{}, {"operator": "unknown"}, {"operator": None}])
def test_incomplete_multi_enum_input_always_describes_a_collection(data):
    info = PropertyInfo(enum_details("MultipleChoiceEnumeration"), Registry.from_union(PropertyTest))
    description = info.describe_test_inputs(data)
    assert description.fields[1].schema["type"] == "array"
    assert description.fields[1].schema["items"]["enum"] == ["Red", "Blue", "Light Blue"]
    assert data.get("operator") in (None, "unknown")


@pytest.mark.parametrize(
    "test",
    [
        EnumTest(operator="is not", value="Red"),
        GuidTest(operator="is not", value=TARGET),
        MultiEnumTest(operator="does not contain", value=("Red",)),
    ],
)
@pytest.mark.parametrize("error", [PropertyUnavailableError("unavailable"), PropertyUndefinedError("undefined")])
def test_negative_new_comparisons_keep_unavailable_and_undefined_false(test, error):
    result = evaluate_property(test, BatchSlot.failure(error))
    assert result.is_success and result.value is False


def test_mixed_enum_guid_query_uses_one_property_batch_and_preserves_results(project):
    definitions = project.api.tapir.property.get_all_properties.return_value.properties
    definitions.extend(
        [
            enum_details(propertyId={"guid": ENUM}),
            property_details(propertyId={"guid": GUID}, propertyValueType="Guid"),
            enum_details("MultipleChoiceEnumeration", propertyId={"guid": MULTI}),
        ]
    )
    for guid, row in project.values.items():
        row[ENUM] = "Red"
        row[GUID] = str(TARGET)
        row[MULTI] = "Blue; Red" if guid != SHORT else "Blue"
    project.values[SLAB][ENUM] = "Blue"
    project.values[BAD][GUID] = "invalid guid"
    project.values[UNDEFINED][MULTI] = "<Undefined>"
    project.values[UNAVAILABLE][MULTI] = cell_error("Not available or not evaluated property", False)
    query = Query(
        where=AllOf(
            items=(
                PropertyPredicate(field_id=ENUM, test=EnumTest(operator="is", value="Red")),
                PropertyPredicate(field_id=GUID, test=GuidTest(operator="is", value=TARGET)),
                PropertyPredicate(field_id=MULTI, test=MultiEnumTest(operator="is", value=("Red", "Blue"))),
                PropertyPredicate(field_id=MULTI, test=MultiEnumTest(operator="contains", value=("Red", "Blue"))),
            )
        )
    )

    result = project.api.utilities.element.find_elements_result(query)

    assert guids(result.outcomes.successes) == [TALL]
    assert result.outcomes.slots[3].is_error
    assert "GUID" in result.outcomes.slots[3].error.message
    assert str(GUID) in result.outcomes.slots[3].error.message
    read = project.api.tapir.property.get_property_values_of_elements
    read.assert_called_once()
    assert [item.propertyId.guid for item in read.call_args.args[1]] == [ENUM, GUID, MULTI]
    assert read.call_args.kwargs == {"include_availability": True, "use_si_units": True}
    assert guids(project.api.utilities.element.find_elements(query)) == [TALL]
    filtered = project.api.utilities.element.filter_elements_by_query_result([TALL, SHORT, TALL], query)
    assert guids(filtered.successes) == [TALL, TALL]


def test_enum_choice_removal_is_reported_by_metadata_validation():
    details = enum_details(labels=("Red",))
    query = Query(where=PropertyPredicate(field_id=details.propertyId.guid, test=EnumTest(operator="is", value="Blue")))
    result = validate_query(query, [PropertyCatalogue([details], Registry.from_union(PropertyTest))])
    assert not result.is_valid
    assert result.issues[0].code == "invalid_test"
    assert result.issues[0].path == "where.test"
    assert "Blue" in result.issues[0].message
