"""Expose query definitions, test families, and field information."""

from .discovery import DiscoveredProperty, PropertyCatalogue
from .errors import (
    InvalidPropertyTestError,
    UnsupportedPropertyTypeError,
    AmbiguousPropertyTypeError,
    UnsupportedQueryVersionError,
)
from .context import ContextBuilder, ContextSource, EvaluationContext
from .evaluation import evaluate_property
from .fields import FieldInfo, PropertyInfo, UnsupportedPropertyInfo

from .models import (
    AllOf,
    AnyOf,
    BooleanTest,
    ElementTypePredicate,
    NumberTest,
    Predicate,
    PropertyPredicate,
    PropertyTest,
    PropertyTestModel,
    Query,
    TextTest,
)
from .registry import TestRegistry
from .operators import BooleanOperator, NumberOperator, TextOperator
from .sources import PROPERTY_VALUES, TYPE_MEMBERSHIP, PropertyValuesData, PropertyValuesSource, TypeMembershipSource
from .validation import QueryValidationError, QueryValidationIssue, QueryValidationResult, validate_query
from .versioning import QUERY_SCHEMA_VERSION, validate_query_version
from multiconn_archicad.utilities.results.query_results import FindElementsResult

__all__ = [
    "AllOf",
    "AmbiguousPropertyTypeError",
    "AnyOf",
    "BooleanTest",
    "BooleanOperator",
    "ContextBuilder",
    "ContextSource",
    "ElementTypePredicate",
    "EvaluationContext",
    "DiscoveredProperty",
    "FieldInfo",
    "FindElementsResult",
    "InvalidPropertyTestError",
    "NumberTest",
    "NumberOperator",
    "Predicate",
    "PropertyPredicate",
    "PropertyInfo",
    "PropertyCatalogue",
    "PROPERTY_VALUES",
    "PropertyValuesData",
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
    "TYPE_MEMBERSHIP",
    "TypeMembershipSource",
    "UnsupportedPropertyInfo",
    "UnsupportedPropertyTypeError",
    "UnsupportedQueryVersionError",
    "evaluate_property",
    "validate_query",
    "validate_query_version",
]
