"""Expose query definitions, test families, and field information."""

from .discovery import DiscoveredProperty, PropertyCatalogue
from .errors import (
    InvalidPropertyTestError,
    UnsupportedPropertyTypeError,
    AmbiguousPropertyTypeError,
)
from .context import ContextBuilder, ContextSource, EvaluationContext
from .evaluation import evaluate_property
from .fields import FieldInfo, PropertyInfo, UnsupportedPropertyInfo

from .models import (
    AllOf,
    AnyOf,
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
from .operators import NumberOperator, TextOperator
from .sources import PROPERTY_VALUES, TYPE_MEMBERSHIP, PropertyValuesData, PropertyValuesSource, TypeMembershipSource
from .validation import QueryValidationError, QueryValidationIssue, QueryValidationResult, validate_query

__all__ = [
    "AllOf",
    "AmbiguousPropertyTypeError",
    "AnyOf",
    "ContextBuilder",
    "ContextSource",
    "ElementTypePredicate",
    "EvaluationContext",
    "DiscoveredProperty",
    "FieldInfo",
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
    "evaluate_property",
    "validate_query",
]
