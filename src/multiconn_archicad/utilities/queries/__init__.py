"""Expose query definitions, test families, and field information."""

from .discovery import DiscoveredProperty, PropertyCatalogue
from .errors import InvalidPropertyTestError, UnsupportedPropertyTypeError, AmbiguousPropertyTypeError
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
from .validation import QueryValidationError, QueryValidationIssue, QueryValidationResult, validate_query

__all__ = [
    "AllOf",
    "AmbiguousPropertyTypeError",
    "AnyOf",
    "ElementTypePredicate",
    "DiscoveredProperty",
    "FieldInfo",
    "InvalidPropertyTestError",
    "NumberTest",
    "NumberOperator",
    "Predicate",
    "PropertyPredicate",
    "PropertyInfo",
    "PropertyCatalogue",
    "PropertyTest",
    "PropertyTestModel",
    "Query",
    "QueryValidationError",
    "QueryValidationIssue",
    "QueryValidationResult",
    "TextTest",
    "TextOperator",
    "TestRegistry",
    "UnsupportedPropertyInfo",
    "UnsupportedPropertyTypeError",
    "evaluate_property",
    "validate_query",
]
