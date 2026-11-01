"""Validate complete queries against an offline property catalogue."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.models.tapir.types import ElementType, PropertyDetails
from multiconn_archicad.utilities.queries import (
    AllOf,
    AmbiguousPropertyTypeError,
    AnyOf,
    ClassificationCatalogue,
    ClassificationPredicate,
    ClassificationTest,
    ElementTypePredicate,
    InvalidPropertyTestError,
    NumberTest,
    PropertyCatalogue,
    PropertyPredicate,
    PropertyTest,
    Query,
    QueryValidationContext,
    QueryValidationError,
    QueryValidationIssue,
    TextTest,
    validate_query,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "query_property_discovery_19723.json"
ELEMENT_ID = UUID("7E221F33-829B-4FBC-A670-E74DABCE6289")
HEIGHT = UUID("02DB7087-5E1D-4AF3-AF62-4D08C1B70C3E")
POSITION = UUID("53402BE5-29D9-44A5-B6D6-4FA90938DDC9")
MISSING = UUID("00000000-0000-0000-0000-000000000000")


def test_validation_issue_can_identify_a_classification_field():
    reference = {"kind": "classification", "field_id": str(MISSING)}
    issue = QueryValidationIssue(
        location=("where", "field_id"),
        code="unknown_field",
        message="Unknown system",
        reference=reference,
        name="Example",
        group="Classifications",
    )
    description = issue.describe()
    assert description["reference"] == reference
    assert description["qualified_name"] == "Classifications / Example"
    description["reference"]["field_id"] = "changed"
    assert issue.reference == reference
    reference["field_id"] = "changed input"
    assert issue.reference["field_id"] == str(MISSING)
    with pytest.raises(TypeError):
        issue.reference["field_id"] = "changed issue"


@pytest.fixture
def catalogue() -> PropertyCatalogue:
    metadata = GetAllPropertiesResult.model_validate_json(FIXTURE.read_text(encoding="utf-8")).properties
    return PropertyCatalogue(metadata, Registry.from_union(PropertyTest))


def property_test(property_id=HEIGHT, test=None) -> PropertyPredicate:
    return PropertyPredicate(
        field_id=property_id,
        test=NumberTest(operator="is greater than", value=3) if test is None else test,
    )


def test_context_indexes_catalogues_by_kind_and_captures_the_sequence(catalogue):
    classifications = ClassificationCatalogue([])
    catalogues = [classifications, catalogue]
    context = QueryValidationContext(catalogues)
    catalogues.clear()

    assert context.catalogues["property"] is catalogue
    assert context.catalogues["classification"] is classifications
    assert QueryValidationContext([]).catalogues.get("property") is None
    with pytest.raises(TypeError):
        context.catalogues["property"] = classifications


def test_catalogue_lookup_supports_subclasses(catalogue):
    class CustomPropertyCatalogue(PropertyCatalogue):
        pass

    custom = CustomPropertyCatalogue([catalogue[HEIGHT].details], Registry.from_union(PropertyTest))

    assert validate_query(Query(where=property_test()), [custom]).is_valid
    assert QueryValidationContext([custom]).catalogues["property"] is custom


def test_ambiguous_catalogues_raise_instead_of_choosing_one(catalogue):
    class CustomPropertyCatalogue(PropertyCatalogue):
        pass

    custom = CustomPropertyCatalogue([], Registry.from_union(PropertyTest))
    with pytest.raises(ValueError, match="Multiple catalogues for field kind 'property'"):
        validate_query(Query(where=property_test()), [catalogue, custom])


@pytest.mark.parametrize("reverse", [False, True])
def test_mixed_query_selects_catalogues_independently_of_sequence_order(catalogue, reverse):
    query = Query(
        where=AllOf(
            items=(
                property_test(),
                ClassificationPredicate(field_id=MISSING, test=ClassificationTest(operator="has no value")),
            )
        )
    )
    catalogues = [catalogue, ClassificationCatalogue([])]
    result = validate_query(query, catalogues[::-1] if reverse else catalogues)

    assert [(issue.code, issue.path) for issue in result.issues] == [("unknown_field", "where.items[1].field_id")]


def test_absent_catalogue_reports_an_unresolved_field():
    result = validate_query(Query(where=property_test()), [])

    assert [(issue.code, issue.path) for issue in result.issues] == [("unknown_field", "where.field_id")]


def test_valid_nested_query_and_metadata_are_not_transformed(catalogue):
    query = Query(
        where=AllOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                property_test(),
                AnyOf(
                    items=(
                        property_test(ELEMENT_ID, TextTest(operator="does not contain", value="Temporary")),
                        property_test(test=NumberTest(operator="is greater than or equal to", value=1)),
                    )
                ),
            )
        )
    )
    original_query = query.model_dump(mode="json")
    original_metadata = catalogue.describe()

    result = validate_query(query, [catalogue])

    assert result.is_valid
    assert result.issues == ()
    assert result.raise_for_errors() is None
    assert result.describe() == {"is_valid": True, "issues": []}
    assert query.model_dump(mode="json") == original_query
    assert catalogue.describe() == original_metadata


def test_collects_all_nested_issue_kinds_with_paths_and_field_context(catalogue):
    query = Query(
        where=AllOf(
            items=(
                property_test(MISSING),
                AnyOf(
                    items=(
                        property_test(test=TextTest(operator="contains", value="3")),
                        AllOf(items=(property_test(POSITION),)),
                    )
                ),
            )
        )
    )

    result = validate_query(query, [catalogue])

    assert not result.is_valid
    assert [(issue.code, issue.path) for issue in result.issues] == [
        ("unknown_field", "where.items[0].field_id"),
        ("invalid_test", "where.items[1].items[0].test"),
        ("unsupported_field", "where.items[1].items[1].items[0].test"),
    ]
    missing, wrong_type, unsupported = result.issues
    assert missing.reference == {"kind": "property", "field_id": str(MISSING)}
    assert missing.name is None and missing.group is None and missing.qualified_name is None
    assert wrong_type.qualified_name == "WallProperties / Wall Height"
    assert "requires NumberTest, got TextTest" in wrong_type.message
    assert unsupported.qualified_name == "CategoryPropertyDefinitionGroup / Position"
    assert unsupported.location == ("where", "items", 1, "items", 1, "items", 0, "test")


@pytest.mark.parametrize("group", [AllOf, AnyOf])
def test_groups_check_all_branches_even_after_valid_or_invalid_siblings(catalogue, group):
    query = Query(
        where=group(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                property_test(MISSING),
                property_test(test=TextTest(operator="is", value="3")),
            )
        )
    )

    result = validate_query(query, [catalogue])

    assert [issue.path for issue in result.issues] == ["where.items[1].field_id", "where.items[2].test"]


def test_negative_operator_does_not_hide_context_errors(catalogue):
    query = Query(where=property_test(MISSING, TextTest(operator="is not", value="Temporary")))
    result = validate_query(query, [catalogue])

    assert not result.is_valid
    assert result.issues[0].path == "where.field_id"
    assert result.issues[0].code == "unknown_field"


def test_repeated_properties_keep_an_issue_for_each_query_occurrence(catalogue):
    repeated = property_test(MISSING)
    query = Query(where=AllOf(items=(repeated, repeated)))

    result = validate_query(query, [catalogue])

    assert [issue.path for issue in result.issues] == ["where.items[0].field_id", "where.items[1].field_id"]


def test_subtree_validation_uses_supplied_location_without_accumulating_issues(catalogue):
    context = QueryValidationContext([catalogue])
    subtree = AnyOf(items=(property_test(), property_test(MISSING)))

    issues = subtree.validate_fields(context, ("where", "items", 2))

    assert [issue.path for issue in issues] == ["where.items[2].items[1].field_id"]
    assert property_test().validate_fields(context) == ()
    assert [issue.path for issue in subtree.validate_fields(context)] == ["where.items[1].field_id"]


def test_element_type_queries_need_no_property_metadata():
    query = Query(where=ElementTypePredicate(types=(ElementType.WALL,)))

    assert validate_query(query, []).is_valid


def test_result_and_exception_expose_complete_json_friendly_issues(catalogue):
    query = Query(where=AllOf(items=(property_test(MISSING), property_test(POSITION))))
    result = validate_query(query, [catalogue])

    description = json.loads(json.dumps(result.describe()))

    assert description["is_valid"] is False
    assert len(description["issues"]) == 2
    assert description["issues"][0]["reference"] == {"kind": "property", "field_id": str(MISSING)}
    assert description["issues"][0]["location"] == ["where", "items", 0, "field_id"]
    with pytest.raises(QueryValidationError) as caught:
        result.raise_for_errors()
    assert caught.value.result is result
    assert "where.items[0].field_id" in str(caught.value)
    assert "where.items[1].test" in str(caught.value)


class LimitedNumberTest(NumberTest):
    def validate_for(self, details: PropertyDetails) -> None:
        super().validate_for(details)
        if self.value > 10:
            raise InvalidPropertyTestError("Example operand limit is 10")


def test_family_operand_rules_are_validated_at_each_occurrence(catalogue):
    limited_catalogue = PropertyCatalogue([catalogue[HEIGHT].details], Registry(LimitedNumberTest))
    query = Query(
        where=AllOf(
            items=(
                property_test(test=LimitedNumberTest(operator="is", value=5)),
                property_test(test=LimitedNumberTest(operator="is", value=11)),
            )
        )
    )

    result = validate_query(query, [limited_catalogue])

    assert len(result.issues) == 1
    assert result.issues[0].code == "invalid_test"
    assert result.issues[0].path == "where.items[1].test"
    assert result.issues[0].message == "Example operand limit is 10"


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("broken validator"),
        ValueError("unexpected implementation error"),
        AmbiguousPropertyTypeError("ambiguous family"),
    ],
)
def test_unexpected_or_configuration_errors_propagate(catalogue, error):
    class BrokenNumberTest(NumberTest):
        def validate_for(self, details: PropertyDetails) -> None:
            raise error

    broken_catalogue = PropertyCatalogue([catalogue[HEIGHT].details], Registry(BrokenNumberTest))
    query = Query(where=property_test(test=BrokenNumberTest(operator="is", value=3)))

    with pytest.raises(type(error)) as caught:
        validate_query(query, [broken_catalogue])
    assert caught.value is error
