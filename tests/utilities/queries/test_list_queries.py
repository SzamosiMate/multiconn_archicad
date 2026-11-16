"""Ordered list equality, whole-item membership, strict operands and query integration."""

import json
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AllOf,
    CollectionOperator,
    IntegerListTest,
    InvalidPropertyTestError,
    PropertyInfo,
    PropertyPredicate,
    PropertyTest,
    Query,
    RealListTest,
    StringListTest,
    evaluate_property,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry
from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query
from multiconn_archicad.utilities.results.batch_results import BatchSlot, SlotState
from multiconn_archicad.utilities.results.property_errors import PropertyUnavailableError, PropertyUndefinedError

from .support import BAD, SHORT, SLAB, TALL, UNAVAILABLE, UNDEFINED, cell_error, guids, property_details

pytestmark = pytest.mark.unit

FAMILIES = [(StringListTest, "String", "A"), (IntegerListTest, "Integer", 2), (RealListTest, "Real", 2.0)]
STRINGS, INTEGERS, REALS = (UUID(int=index) for index in (111, 112, 113))


@pytest.mark.parametrize(
    "family, raw, first, second",
    [
        (StringListTest, "A; B; A", "A", "B"),
        (IntegerListTest, "1; 2; 1", 1, 2),
        (RealListTest, "1.0; 2.000; 1", 1.0, 2.0),
    ],
)
def test_whole_list_equality_preserves_order_and_duplicates(family, raw, first, second):
    assert family(operator="is", value=(first, second, first)).evaluate(raw).value is True
    for operand in ((first, second), (first, first, second), (second, first, first), ()):
        assert family(operator="is", value=operand).evaluate(raw).value is False


@pytest.mark.parametrize("family, value_type, item", FAMILIES)
@pytest.mark.parametrize("operator", list(CollectionOperator))
def test_empty_lists_are_empty_collections(family, value_type, item, operator):
    operand = () if operator.requires_collection else item
    expected = operator is not CollectionOperator.CONTAINS
    result = family(operator=operator, value=operand).evaluate("")
    assert result.is_success and result.value is expected


@pytest.mark.parametrize(
    "operator, raw, operand, expected",
    [
        ("is", "Straße; BLUE", ("STRASSE", "blue"), True),
        ("is", " A ; B", ("A", "B"), False),
        ("contains", "AB; C", "A", False),
        ("contains", "A; B", "a", True),
        ("does not contain", "AB; C", "A", True),
        ("does not contain", "A; B", "a", False),
        ("contains", "; A", "", True),
        ("is", "; A", ("", "A"), True),
        ("is", "A; ", ("A", ""), True),
        # A flattened empty read is interpreted as []; [""] cannot be recovered.
        ("is", "", ("",), False),
        ("contains", "", "", False),
    ],
)
def test_string_list_items_use_text_casefold_and_significant_whitespace(operator, raw, operand, expected):
    assert StringListTest(operator=operator, value=operand).evaluate(raw).value is expected


@pytest.mark.parametrize("operator", ["is", "contains", "does not contain"])
def test_integer_lists_preserve_adjacent_values_above_float_precision(operator):
    large = 2**53 + 1
    operand = (large,) if operator == "is" else large
    test = IntegerListTest(operator=operator, value=operand)
    assert test.evaluate(str(large)).value is (operator != "does not contain")
    assert test.evaluate(str(large - 1)).value is (operator == "does not contain")


@pytest.mark.parametrize("operator", list(CollectionOperator))
@pytest.mark.parametrize(
    "raw, operand, equal",
    [
        ("2.000", 2, True),
        ("29.999999999999996", 30, True),
        ("0.00000000001", 0, True),
        ("0.0000000002", 0, False),
        ("10000.0000005", 10000, True),
        ("10000.000002", 10000, False),
    ],
)
def test_real_list_comparisons_share_scalar_tolerance(operator, raw, operand, equal):
    value = (operand,) if operator.requires_collection else operand
    result = RealListTest(operator=operator, value=value).evaluate(raw)
    assert result.is_success
    assert result.value is (not equal if operator is CollectionOperator.DOES_NOT_CONTAIN else equal)


@pytest.mark.parametrize(
    "family, bad",
    [
        (IntegerListTest, "2.0"),
        (IntegerListTest, "nan"),
        (IntegerListTest, "2,000"),
        (RealListTest, "nan"),
        (RealListTest, "inf"),
        (RealListTest, "-inf"),
        (RealListTest, "2,0"),
        (RealListTest, "2 m"),
        (RealListTest, "1e999"),
        (IntegerListTest, ""),
        (RealListTest, ""),
    ],
)
@pytest.mark.parametrize("operator", list(CollectionOperator))
def test_every_numeric_item_is_parsed_even_after_a_matching_item(family, bad, operator):
    test = family(operator=operator, value=(2,) if operator.requires_collection else 2)
    raw = f"2; {bad}"
    result = test.evaluate(raw)
    assert result.is_error
    assert repr(raw) in result.error.message


@pytest.mark.parametrize("family, value_type, item", FAMILIES)
@pytest.mark.parametrize("source", ["StaticBuiltIn", "DynamicBuiltIn", "Custom"])
def test_list_discovery_resolves_one_typed_family(family, value_type, item, source):
    details = property_details(propertyCollectionType="List", propertyValueType=value_type, propertyType=source)
    registry = Registry.from_union(PropertyTest)
    assert registry.resolve(details) is family
    info = PropertyInfo(details, registry)
    assert type(info.create_test(operator="is", value=(item, item))) is family
    assert info.operators() == ("is", "contains", "does not contain")


@pytest.mark.parametrize("measure", list(tapir.PropertyMeasureType))
def test_real_lists_support_every_measure_without_new_test_types(measure):
    details = property_details(propertyCollectionType="List", propertyMeasureType=measure)
    assert RealListTest.accepts(details)
    RealListTest(operator="contains", value=2).validate_for(details)


@pytest.mark.parametrize("family, value_type, item", FAMILIES)
def test_list_families_reject_scalar_and_other_item_types(family, value_type, item):
    test = family(operator="contains", value=item)
    scalar = property_details(propertyValueType=value_type)
    assert not family.accepts(scalar)
    with pytest.raises(InvalidPropertyTestError):
        test.validate_for(scalar)
    for other_type in {"String", "Integer", "Real", "Boolean", "Guid", "Undefined"} - {value_type}:
        details = property_details(propertyCollectionType="List", propertyValueType=other_type)
        assert not family.accepts(details)
        with pytest.raises(InvalidPropertyTestError):
            family.schema_for(details)


@pytest.mark.parametrize(
    "family, value",
    [
        (StringListTest, 2),
        (StringListTest, b"A"),
        (StringListTest, None),
        (IntegerListTest, True),
        (IntegerListTest, 2.0),
        (IntegerListTest, "2"),
        (RealListTest, True),
        (RealListTest, "2"),
        (RealListTest, float("nan")),
        (RealListTest, float("inf")),
        (RealListTest, -float("inf")),
    ],
)
def test_list_item_types_are_strict_in_scalar_and_collection_operands(family, value):
    for operator, operand in (("contains", value), ("is", (value,))):
        with pytest.raises(ValidationError):
            family(operator=operator, value=operand)


@pytest.mark.parametrize("family, value_type, item", FAMILIES)
def test_list_operand_shape_is_operator_specific_in_models_and_json_schema(family, value_type, item):
    schema = family.model_json_schema()
    validator = Draft202012Validator(schema)
    for operator, value in (("is", item), ("contains", [item]), ("does not contain", [])):
        data = {"operator": operator, "value": value}
        assert not validator.is_valid(data)
        with pytest.raises(ValidationError):
            family.model_validate(data)
    for operator in ("is not", "available", "is undefined"):
        assert operator not in family.operators()
        with pytest.raises(ValidationError):
            family(operator=operator, value=item)


@pytest.mark.parametrize("family, value_type, item", FAMILIES)
@pytest.mark.parametrize("operator", list(CollectionOperator))
def test_typed_list_schemas_drafts_and_queries_agree(family, value_type, item, operator):
    info = PropertyInfo(
        property_details(propertyCollectionType="List", propertyValueType=value_type), Registry.from_union(PropertyTest)
    )
    value = [item, item] if operator.requires_collection else item
    data = {"operator": operator.value, "value": value}
    schema_before = json.dumps(info.test_schema(), sort_keys=True)
    description = info.describe_test_inputs(data)
    operand = description.fields[1].schema
    item_type = {"String": "string", "Integer": "integer", "Real": "number"}[value_type]
    assert operand["type"] == ("array" if operator.requires_collection else item_type)
    if operator.requires_collection:
        assert operand["items"]["type"] == item_type
        assert not operand.get("uniqueItems", False)
    test = info.create_test(**data)
    query = Query(where=PropertyPredicate(field_id=info.property_id, test=test))
    payload = query.model_dump(mode="json")
    assert Draft202012Validator(Query.model_json_schema()).is_valid(payload)
    assert Query.model_validate_json(query.model_dump_json()) == query
    draft = QueryRows(rows=[QueryRow(predicate=payload["where"])])
    assert build_query(QueryRows.model_validate_json(draft.model_dump_json())).query == query
    assert json.dumps(info.test_schema(), sort_keys=True) == schema_before
    with pytest.raises(ValidationError, match="frozen"):
        test.value = item
    with pytest.raises(ValidationError):
        family.model_validate({**data, "extra": True})


@pytest.mark.parametrize("family, value_type, item", FAMILIES)
@pytest.mark.parametrize("error", [PropertyUnavailableError("unavailable"), PropertyUndefinedError("undefined")])
def test_missing_property_states_remain_false_for_negative_membership(family, value_type, item, error):
    test = family(operator="does not contain", value=item)
    result = evaluate_property(test, BatchSlot.failure(error))
    assert result.is_success and result.value is False


def test_mixed_list_queries_share_one_si_read_and_preserve_errors_and_alignment(project):
    definitions = project.api.tapir.property.get_all_properties.return_value.properties
    for property_id, value_type in ((STRINGS, "String"), (INTEGERS, "Integer"), (REALS, "Real")):
        definitions.append(
            property_details(
                propertyId={"guid": property_id}, propertyCollectionType="List", propertyValueType=value_type
            )
        )
    for row in project.values.values():
        row.update({STRINGS: "A; B; A", INTEGERS: "1; 2; 1", REALS: "29.999999999999996; 0"})
    project.values[SHORT][INTEGERS] = "1; 1; 2"
    project.values[BAD][REALS] = "30; invalid"
    project.values[UNDEFINED][STRINGS] = "<Undefined>"
    project.values[UNAVAILABLE][STRINGS] = cell_error("Not available or not evaluated property", False)
    query = Query(
        where=AllOf(
            items=(
                PropertyPredicate(field_id=STRINGS, test=StringListTest(operator="contains", value="a")),
                PropertyPredicate(field_id=INTEGERS, test=IntegerListTest(operator="is", value=(1, 2, 1))),
                PropertyPredicate(field_id=REALS, test=RealListTest(operator="contains", value=30)),
                PropertyPredicate(field_id=REALS, test=RealListTest(operator="does not contain", value=1)),
            )
        )
    )

    result = project.api.utilities.element.find_elements_result(query)

    assert guids(result.outcomes.successes) == [TALL, SLAB]
    assert [slot.state for slot in result.outcomes.slots] == [
        SlotState.SUCCESS,
        SlotState.SUCCESS,
        SlotState.FILTERED,
        SlotState.ERROR,
        SlotState.FILTERED,
        SlotState.FILTERED,
    ]
    assert str(REALS) in result.outcomes.slots[3].error.message
    read = project.api.tapir.property.get_property_values_of_elements
    read.assert_called_once()
    assert [item.propertyId.guid for item in read.call_args.args[1]] == [STRINGS, INTEGERS, REALS]
    assert read.call_args.kwargs == {"include_availability": True, "use_si_units": True}
    assert guids(project.api.utilities.element.find_elements(query)) == [TALL, SLAB]
    filtered = project.api.utilities.element.filter_elements_by_query_result([TALL, SHORT, TALL], query)
    assert guids(filtered.successes) == [TALL, TALL]
