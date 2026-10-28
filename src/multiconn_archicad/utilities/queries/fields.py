"""Expose field information from supplied metadata, without Archicad access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from multiconn_archicad.models.tapir.types import PropertyDetails

from .models import PropertyTestModel
from .registry import TestRegistry, UnsupportedPropertyTypeError

TestT = TypeVar("TestT", bound=BaseModel)


class FieldInfo(ABC, Generic[TestT]):
    """Provide uniform display names, identity, and test creation for a field.

    Concrete field sources supply their own references and test behavior. This
    interface does not require property metadata or perform API calls.
    """

    @property
    def supported(self) -> bool:
        """Whether this field has an implemented query-test family."""
        return True

    @property
    def unsupported_reason(self) -> str | None:
        """Explain missing query support, independently of element-value availability."""
        return None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the field's name without its group."""
        ...

    @property
    @abstractmethod
    def group(self) -> str:
        """Return the field's UI grouping name."""
        ...

    @property
    def qualified_name(self) -> str:
        """Combine group and name without storing a second mutable label."""
        return f"{self.group} / {self.name}" if self.group else self.name

    @property
    @abstractmethod
    def reference(self) -> dict[str, str]:
        """Return a JSON-friendly source reference, independent of display names."""
        ...

    @abstractmethod
    def operators(self) -> tuple[str, ...]:
        """Return readable operator choices directly."""
        ...

    @abstractmethod
    def create_test(self, **data: Any) -> TestT:
        """Validate test structure and then the selected field's context."""
        ...

    @abstractmethod
    def validate(self, test: TestT) -> None:
        """Validate an already constructed test against this field's context."""
        ...

    @abstractmethod
    def test_schema(self) -> dict[str, Any] | None:
        """Describe the test and operand format, or return None when unsupported."""
        ...

    def describe(self) -> dict[str, Any]:
        """Serialize discovery information without runtime classes or behavior."""
        return {
            "reference": self.reference,
            "name": self.name,
            "group": self.group,
            "qualified_name": self.qualified_name,
            "supported": self.supported,
            "unsupported_reason": self.unsupported_reason,
            "operators": list(self.operators()),
            "test_schema": self.test_schema(),
        }


class _PropertyMetadata(FieldInfo[PropertyTestModel]):
    """Share immutable-by-interface metadata snapshots across property outcomes."""

    def __init__(self, details: PropertyDetails):
        self._details = details.model_copy(deep=True)

    @property
    def name(self) -> str:
        """Return the upstream name unchanged, including technical identifiers."""
        return self._details.propertyName

    @property
    def group(self) -> str:
        """Return the upstream group unchanged."""
        return self._details.propertyGroupName

    @property
    def property_id(self) -> UUID:
        """Return the property's identity independently of its display labels."""
        return UUID(str(self._details.propertyId.guid))

    @property
    def reference(self) -> dict[str, str]:
        """Return the identity fields used by a property predicate."""
        return {"kind": "property", "property_id": str(self.property_id)}

    @property
    def details(self) -> PropertyDetails:
        """Return a copy of the snapshot, including its original measure metadata."""
        return self._details.model_copy(deep=True)


class PropertyInfo(_PropertyMetadata):
    """Expose a property metadata snapshot and its registered test family.

    Metadata is copied at construction so caller edits cannot invalidate the
    selected family's compatibility. Construct a new instance to refresh it.
    There is no live API reference or project-wide cache.
    """

    def __init__(self, details: PropertyDetails, registry: TestRegistry):
        super().__init__(details)
        self._test_model = registry.resolve(self._details)

    @property
    def test_model(self) -> type[PropertyTestModel]:
        """Return the family selected for this property."""
        return self._test_model

    def operators(self) -> tuple[str, ...]:
        return self._test_model.operators()

    def create_test(self, **data: Any) -> PropertyTestModel:
        """Parse an operand/operator, then run explicit property-context validation."""
        test = self._test_model.model_validate(data)
        self.validate(test)
        return test

    def validate(self, test: PropertyTestModel) -> None:
        """Require the selected family and run its property-context rules."""
        if not isinstance(test, self._test_model):
            raise ValueError(f"{self.qualified_name} requires {self._test_model.__name__}, got {type(test).__name__}")
        test.validate_for(self._details)

    def test_schema(self) -> dict[str, Any]:
        """Return the selected family's metadata-aware test schema."""
        return self._test_model.schema_for(self._details)


class UnsupportedPropertyInfo(_PropertyMetadata):
    """Retain property identity and metadata when no test family supports it."""

    def __init__(self, details: PropertyDetails, reason: str):
        super().__init__(details)
        self._reason = reason

    @property
    def supported(self) -> bool:
        return False

    @property
    def unsupported_reason(self) -> str:
        return self._reason

    def operators(self) -> tuple[str, ...]:
        return ()

    def create_test(self, **data: Any) -> PropertyTestModel:
        raise UnsupportedPropertyTypeError(self._reason)

    def validate(self, test: PropertyTestModel) -> None:
        raise UnsupportedPropertyTypeError(self._reason)

    def test_schema(self) -> None:
        return None
