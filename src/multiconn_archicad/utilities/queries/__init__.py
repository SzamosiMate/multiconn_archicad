"""Expose query definitions, test families, and field information."""

from .discovery import DiscoveredProperty, PropertyCatalogue
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
from .registry import AmbiguousPropertyTypeError, TestRegistry, UnsupportedPropertyTypeError

__all__ = [
    "AllOf",
    "AnyOf",
    "ElementTypePredicate",
    "DiscoveredProperty",
    "FieldInfo",
    "Negate",
    "NumberTest",
    "Predicate",
    "PropertyPredicate",
    "PropertyInfo",
    "PropertyCatalogue",
    "PropertyTest",
    "PropertyTestModel",
    "Query",
    "TextTest",
    "TestRegistry",
    "UnsupportedPropertyTypeError",
    "UnsupportedPropertyInfo",
    "AmbiguousPropertyTypeError",
]
