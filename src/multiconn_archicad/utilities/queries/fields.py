"""Expose field information from supplied metadata, without Archicad access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import JsonValue

from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir.types import ElementType, PropertyDetails
from multiconn_archicad.utilities.identifiers import ClassificationItemIdLike, normalize_classification_item_id

from .errors import (
    InvalidClassificationTestError,
    InvalidFieldTestError,
    InvalidPropertyTestError,
    UnsupportedPropertyTypeError,
)
from .inputs import TestInput, TestInputs
from .models import ClassificationTest, ElementTypeTest, PropertyTestModel, TestModel
from .registry import TestRegistry

TestT = TypeVar("TestT", bound=TestModel)


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

    @property
    @abstractmethod
    def test_model(self) -> type[TestT]:
        """Return the selected test class, raising if the field is unsupported."""
        ...

    def operators(self) -> tuple[str, ...]:
        """Return readable operator choices directly."""
        return self.test_model.operators() if self.supported else ()

    def create_test(self, **data: Any) -> TestT:
        """Validate test structure and then the selected field's context."""
        test = self.test_model.model_validate(data)
        self.validate(test)
        return test

    @abstractmethod
    def validate(self, test: TestT) -> None:
        """Validate an already constructed test against this field's context."""
        ...

    def test_schema(self) -> dict[str, Any] | None:
        """Describe the test and operand format, or return None when unsupported."""
        return self.test_model.model_json_schema() if self.supported else None

    def describe_test_inputs(self, current_data: Mapping[str, JsonValue]) -> TestInputs | None:
        """Resolve active inputs against this field's schema without editing the draft."""
        schema = self.test_schema()
        if schema is None:
            return None

        availability = self.test_model.input_availability(current_data)
        snapshot = deepcopy(schema)
        properties = snapshot["properties"]
        return TestInputs(
            fields=tuple(
                TestInput(name, properties[name], name in availability.required) for name in availability.visible
            ),
            definitions=snapshot.get("$defs", {}),
            forbidden_fields=availability.forbidden,
        )

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


class ElementTypeInfo(FieldInfo[ElementTypeTest]):
    """Describe the built-in element-type criterion without project metadata."""

    @property
    def name(self) -> str:
        return "Element type"

    @property
    def group(self) -> str:
        return "Built-in"

    @property
    def reference(self) -> dict[str, str]:
        return {"kind": "element_type"}

    @property
    def test_model(self) -> type[ElementTypeTest]:
        return ElementTypeTest

    def validate(self, test: ElementTypeTest) -> None:
        if not isinstance(test, self.test_model):
            raise InvalidFieldTestError(f"{self.qualified_name} requires {self.test_model.__name__}")

    def test_schema(self) -> dict[str, Any]:
        """Offer each individual type as a named choice for one editor row."""
        schema = self.test_model.model_json_schema()
        schema["properties"]["types"]["oneOf"] = [
            {"const": [element_type.value], "title": element_type.value} for element_type in ElementType
        ]
        return schema


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
        return self._details.propertyId.guid

    @property
    def reference(self) -> dict[str, str]:
        """Return the identity fields used by a property predicate."""
        return {"kind": "property", "field_id": str(self.property_id)}

    @property
    def details(self) -> PropertyDetails:
        """Return a copy of the snapshot, including its original measure metadata."""
        return self._details.model_copy(deep=True)

    def describe(self) -> dict[str, Any]:
        """Include the upstream measure type for supported and unsupported properties."""
        return {**super().describe(), "measure_type": self._details.propertyMeasureType.value}


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

    def validate(self, test: PropertyTestModel) -> None:
        """Require the selected family and run its property-context rules."""
        if not isinstance(test, self._test_model):
            raise InvalidPropertyTestError(
                f"{self.qualified_name} requires {self._test_model.__name__}, got {type(test).__name__}"
            )
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

    @property
    def test_model(self) -> type[PropertyTestModel]:
        raise UnsupportedPropertyTypeError(self._reason)

    def validate(self, test: PropertyTestModel) -> None:
        raise UnsupportedPropertyTypeError(self._reason)


@dataclass(frozen=True, slots=True)
class ClassificationItemInfo:
    """Retain an item's code, name and tree links independently of mutable API models."""

    item_id: UUID
    code: str
    name: str
    description: str
    parent_id: UUID | None
    children: tuple[UUID, ...]


class ClassificationInfo(FieldInfo[ClassificationTest]):
    """Represent one system as a field, retaining its complete ordered item tree."""

    def __init__(self, system: official.ClassificationSystem, items: Sequence[official.ClassificationItemArrayItem]):
        self._system = system.model_copy(deep=True)
        self._items: dict[UUID, ClassificationItemInfo] = {}
        self._register_items(items, parent_id=None)

    def _register_items(self, items: Sequence[official.ClassificationItemArrayItem], parent_id: UUID | None) -> None:
        for wrapper in items:
            item = wrapper.classificationItem
            guid = item.classificationItemId.guid
            children = item.children or ()
            self._items[guid] = ClassificationItemInfo(
                item_id=guid,
                code=item.id,
                name=item.name,
                description=item.description,
                parent_id=parent_id,
                children=tuple(child.classificationItem.classificationItemId.guid for child in children),
            )
            self._register_items(children, guid)

    @property
    def system_id(self) -> UUID:
        return self._system.classificationSystemId.guid

    @property
    def details(self) -> official.ClassificationSystem:
        return self._system.model_copy(deep=True)

    @property
    def group(self) -> str:
        return "Classifications"

    @property
    def name(self) -> str:
        return self._system.name

    @property
    def reference(self) -> dict[str, str]:
        return {"kind": "classification", "field_id": str(self.system_id)}

    @property
    def items(self) -> tuple[ClassificationItemInfo, ...]:
        """Return items in depth-first API tree order, with parent/child GUIDs."""
        return tuple(self._items.values())

    def item(self, item_id: ClassificationItemIdLike) -> ClassificationItemInfo:
        """Look up an item in this system; raise KeyError when it is absent."""
        return self._items[normalize_classification_item_id(item_id).classificationItemId.guid]

    def descendant_ids(self, item_id: ClassificationItemIdLike, *, include_self: bool = False) -> frozenset[UUID]:
        """Traverse the captured tree locally, optionally including the root item."""
        item = self.item(item_id)
        found = {item.item_id} if include_self else set()
        pending = list(item.children)
        while pending:
            guid = pending.pop()
            found.add(guid)
            pending.extend(self._items[guid].children)
        return frozenset(found)

    @property
    def test_model(self) -> type[ClassificationTest]:
        return ClassificationTest

    def validate(self, test: ClassificationTest) -> None:
        if not isinstance(test, ClassificationTest):
            raise InvalidClassificationTestError(f"{self.qualified_name} requires ClassificationTest")
        if test.value is not None and test.value not in self._items:
            raise InvalidClassificationTestError(f"Item {test.value} is not present in {self.qualified_name}")

    def test_schema(self) -> dict[str, Any]:
        schema = self.test_model.model_json_schema()
        choices = [
            {"const": str(item.item_id), "title": " / ".join(part for part in (item.code, item.name) if part)}
            for item in self._items.values()
        ]
        if choices:
            schema["properties"]["value"]["oneOf"] = choices
        else:
            schema["properties"]["value"]["not"] = {}
        return schema

    def describe(self) -> dict[str, Any]:
        return {
            **super().describe(),
            "items": [
                {
                    "item_id": str(item.item_id),
                    "code": item.code,
                    "name": item.name,
                    "description": item.description,
                    "parent_id": str(item.parent_id) if item.parent_id else None,
                    "children": [str(guid) for guid in item.children],
                }
                for item in self._items.values()
            ],
        }
