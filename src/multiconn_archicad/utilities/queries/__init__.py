"""Expose query definitions, test families, and field information."""

from .discovery import DiscoveredProperty, PropertyCatalogue
from .errors import InvalidPropertyTestError, UnsupportedPropertyTypeError, AmbiguousPropertyTypeError
from .fields import FieldInfo, PropertyInfo, UnsupportedPropertyInfo

from .models import (
    AllOf,
    AnyOf,
    ElementTypePredicate,
    Negate,
    NumberTest,
    Predicate,
    PropertyPredicate,
    PropertyTest,
    PropertyTestModel,
    Query,
    TextTest,
)
from .registry import TestRegistry
from .validation import QueryValidationError, QueryValidationIssue, QueryValidationResult, validate_query

__all__ = [
    "AllOf",
    "AnyOf",
    "ElementTypePredicate",
    "DiscoveredProperty",
    "FieldInfo",
    "InvalidPropertyTestError",
    "Negate",
    "NumberTest",
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
    "TestRegistry",
    "UnsupportedPropertyInfo",
    "validate_query",
]
