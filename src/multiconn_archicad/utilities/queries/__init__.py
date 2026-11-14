"""Supported query, editor, and extension API. See the query reference for scope."""

from .catalogue import FieldCatalogue, QueryFieldCatalogue, QueryFieldEntry
from .element_types import TYPES_2D, TYPES_3D, TYPES_3D_COMPONENTS, TYPES_3D_WITH_COMPONENTS, TYPES_ALL
from .discovery import (
    ClassificationCatalogue,
    DiscoveredProperty,
    PropertyCatalogue,
)
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
from .fields import (
    ClassificationInfo,
    ClassificationItemInfo,
    ElementTypeInfo,
    FieldInfo,
    PropertyInfo,
    UnsupportedPropertyInfo,
)
from .inputs import InputAvailability, TestInput, TestInputs

from .models import (
    AllOf,
    AnyOf,
    BooleanTest,
    ClassificationTest,
    ClassificationPredicate,
    ElementTypePredicate,
    ElementTypeTest,
    IntegerTest,
    RealTest,
    Predicate,
    PropertyPredicate,
    PropertyTest,
    PropertyTestModel,
    Query,
    TextTest,
    TestModel, evaluate_property,
)
from .registry import TestRegistry
from .operators import BooleanOperator, ClassificationOperator, NumberOperator, TextOperator
from .validation import (
    QueryValidationError,
    QueryValidationIssue,
    QueryValidationResult,
    validate_query,
)
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
    "InvalidClassificationTestError",
    "ContextBuilder",
    "ContextSource",
    "ElementTypeInfo",
    "ElementTypePredicate",
    "ElementTypeTest",
    "EvaluationContext",
    "evaluate_property",
    "DiscoveredProperty",
    "FieldInfo",
    "FieldCatalogue",
    "FindElementsResult",
    "InputAvailability",
    "IntegerTest",
    "InvalidPropertyTestError",
    "InvalidFieldTestError",
    "UnsupportedFieldTypeError",
    "RealTest",
    "NumberOperator",
    "Predicate",
    "PropertyPredicate",
    "PropertyInfo",
    "PropertyCatalogue",
    "PropertyTest",
    "PropertyTestModel",
    "Query",
    "QueryFieldCatalogue",
    "QueryFieldEntry",
    "QUERY_SCHEMA_VERSION",
    "QueryValidationError",
    "QueryValidationIssue",
    "QueryValidationResult",
    "TextTest",
    "TextOperator",
    "TestInput",
    "TestInputs",
    "TestRegistry",
    "TestModel",
    "TYPES_ALL",
    "TYPES_2D",
    "TYPES_3D",
    "TYPES_3D_COMPONENTS",
    "TYPES_3D_WITH_COMPONENTS",
    "UnsupportedPropertyInfo",
    "UnsupportedPropertyTypeError",
    "UnsupportedQueryVersionError",
    "validate_query",
    "validate_query_version",
]
