"""Expose query definitions, test families, and field information."""

from .discovery import ClassificationCatalogue, DiscoveredProperty, FieldCatalogue, PropertyCatalogue
from .errors import (
    InvalidFieldTestError,
    UnsupportedFieldTypeError,
    InvalidClassificationTestError,
    InvalidPropertyTestError,
    UnsupportedPropertyTypeError,
    AmbiguousPropertyTypeError,
    UnsupportedQueryVersionError,
)
from .context import ContextBuilder, ContextSource, EvaluationContext
from .evaluation import evaluate_property
from .fields import ClassificationInfo, ClassificationItemInfo, FieldInfo, PropertyInfo, UnsupportedPropertyInfo

from .models import (
    AllOf,
    AnyOf,
    BooleanTest,
    ClassificationTest,
    ClassificationPredicate,
    ElementTypePredicate,
    NumberTest,
    Predicate,
    PropertyPredicate,
    PropertyTest,
    PropertyTestModel,
    Query,
    TextTest,
    TestModel,
)
from .registry import TestRegistry
from .operators import BooleanOperator, ClassificationOperator, NumberOperator, TextOperator
from .sources import (
    CLASSIFICATION_FIELDS,
    CLASSIFICATION_VALUES,
    PROPERTY_VALUES,
    TYPE_MEMBERSHIP,
    ClassificationFieldsSource,
    ClassificationValuesSource,
    ColumnData,
    PropertyValuesSource,
    TypeMembershipSource,
)
from .validation import QueryValidationError, QueryValidationIssue, QueryValidationResult, validate_query
from .versioning import QUERY_SCHEMA_VERSION, validate_query_version
from multiconn_archicad.utilities.results.query_results import FindElementsResult

__all__ = [
    "AllOf",
    "AmbiguousPropertyTypeError",
    "AnyOf",
    "BooleanTest",
    "BooleanOperator",
    "ClassificationCatalogue",
    "ClassificationInfo",
    "ClassificationItemInfo",
    "ClassificationOperator",
    "ClassificationTest",
    "ClassificationPredicate",
    "CLASSIFICATION_FIELDS",
    "CLASSIFICATION_VALUES",
    "ClassificationFieldsSource",
    "ClassificationValuesSource",
    "InvalidClassificationTestError",
    "ContextBuilder",
    "ContextSource",
    "ElementTypePredicate",
    "EvaluationContext",
    "DiscoveredProperty",
    "FieldInfo",
    "FieldCatalogue",
    "FindElementsResult",
    "InvalidPropertyTestError",
    "InvalidFieldTestError",
    "UnsupportedFieldTypeError",
    "NumberTest",
    "NumberOperator",
    "Predicate",
    "PropertyPredicate",
    "PropertyInfo",
    "PropertyCatalogue",
    "PROPERTY_VALUES",
    "ColumnData",
    "PropertyValuesSource",
    "PropertyTest",
    "PropertyTestModel",
    "Query",
    "QUERY_SCHEMA_VERSION",
    "QueryValidationError",
    "QueryValidationIssue",
    "QueryValidationResult",
    "TextTest",
    "TextOperator",
    "TestRegistry",
    "TestModel",
    "TYPE_MEMBERSHIP",
    "TypeMembershipSource",
    "UnsupportedPropertyInfo",
    "UnsupportedPropertyTypeError",
    "UnsupportedQueryVersionError",
    "evaluate_property",
    "validate_query",
    "validate_query_version",
]
