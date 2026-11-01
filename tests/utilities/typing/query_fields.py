"""Check that shared field/catalogue behavior preserves concrete public types."""

from typing import assert_type
from uuid import UUID

from multiconn_archicad.utilities.queries import (
    ClassificationCatalogue,
    ClassificationInfo,
    ClassificationOperator,
    ClassificationTest,
    ClassificationPredicate,
    FieldCheck,
    FieldPredicate,
    NumberTest,
    NumberOperator,
    PropertyCatalogue,
    PropertyInfo,
    PropertyTestModel,
    PropertyTest,
    PropertyPredicate,
    QueryValidationContext,
    QueryValidationResult,
    QueryValidationIssue,
    Query,
    UnsupportedPropertyInfo,
    validate_query,
)


def check_field_types(properties: PropertyCatalogue, classifications: ClassificationCatalogue, guid: UUID) -> None:
    assert_type(properties.get(guid), PropertyInfo | UnsupportedPropertyInfo | None)
    assert_type(properties.get_field(guid), PropertyInfo | UnsupportedPropertyInfo | None)
    assert_type(properties.supported, tuple[PropertyInfo, ...])
    assert_type(properties.unsupported, tuple[UnsupportedPropertyInfo, ...])
    assert_type(classifications.get(guid), ClassificationInfo | None)
    assert_type(classifications.get_field(guid), ClassificationInfo | None)
    assert_type(classifications.search("example"), tuple[ClassificationInfo, ...])
    assert_type(classifications.supported, tuple[ClassificationInfo, ...])
    assert_type(classifications[guid].create_test(operator="is", value=guid), ClassificationTest)
    assert_type(properties[guid].create_test(operator="is", value=1), PropertyTestModel)


def check_validation_catalogue_types(
    query: Query, properties: PropertyCatalogue, classifications: ClassificationCatalogue
) -> None:
    context = QueryValidationContext([properties, classifications])
    assert_type(validate_query(query, [classifications, properties]), QueryValidationResult)
    property_check = FieldCheck(
        predicate=PropertyPredicate(field_id=UUID(int=1), test=NumberTest(operator=NumberOperator.IS, value=1)),
        location=("where",),
    )
    classification_check = FieldCheck(
        predicate=ClassificationPredicate(
            field_id=UUID(int=1), test=ClassificationTest(operator=ClassificationOperator.HAS_VALUE)
        ),
        location=("where",),
    )
    assert_type(property_check.predicate, FieldPredicate[PropertyTest])
    assert_type(classification_check.predicate, FieldPredicate[ClassificationTest])
    assert_type(context.check_field(classification_check), tuple[QueryValidationIssue, ...])
