"""Store searchable field snapshots and adapt source-specific metadata."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import Any, Generic, TypeAlias, TypeVar
from uuid import UUID

from multiconn_archicad.models.tapir.types import PropertyDetails
from multiconn_archicad.utilities.identifiers import (
    ClassificationSystemIdLike,
    PropertyIdLike,
    normalize_classification_system_id,
    normalize_property_id,
)

from .fields import ClassificationInfo, FieldInfo, PropertyInfo, UnsupportedPropertyInfo
from .registry import TestRegistry
from .errors import UnsupportedPropertyTypeError

DiscoveredProperty: TypeAlias = PropertyInfo | UnsupportedPropertyInfo
FieldT = TypeVar("FieldT", bound=FieldInfo[Any])
IdT = TypeVar("IdT")


class FieldCatalogue(ABC, Generic[FieldT, IdT]):
    """Keep ordered field snapshots with shared lookup, search and descriptions.

    Subclasses adapt metadata to UUID/field pairs and normalize their accepted
    identifier inputs. Catalogues retain no API connection or live cache.
    """

    def __init__(self, fields: Iterable[tuple[UUID, FieldT]]):
        self._by_id: dict[UUID, FieldT] = {}
        for guid, field in fields:
            if guid in self._by_id:
                raise ValueError(f"Duplicate field GUID in catalogue: {guid}")
            self._by_id[guid] = field

    @staticmethod
    @abstractmethod
    def _normalize_id(identifier: IdT) -> UUID:
        """Normalize a source-specific identifier for catalogue lookup."""
        ...

    @property
    def fields(self) -> tuple[FieldT, ...]:
        return tuple(self._by_id.values())

    @property
    def supported(self) -> tuple[FieldT, ...]:
        return tuple(field for field in self if field.supported)

    @property
    def unsupported(self) -> tuple[FieldT, ...]:
        return tuple(field for field in self if not field.supported)

    def __iter__(self) -> Iterator[FieldT]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __getitem__(self, identifier: IdT) -> FieldT:
        return self._by_id[self._normalize_id(identifier)]

    def get(self, identifier: IdT) -> FieldT | None:
        return self._by_id.get(self._normalize_id(identifier))

    def search(
        self,
        text: str = "",
        *,
        group: str | None = None,
        supported_only: bool = False,
    ) -> tuple[FieldT, ...]:
        """Find case-insensitive label substrings, optionally within an exact group."""
        needle = text.casefold()
        return tuple(
            field
            for field in self
            if (not supported_only or field.supported)
            and (group is None or field.group == group)
            and needle in field.qualified_name.casefold()
        )

    def describe(self) -> dict[str, Any]:
        return {"fields": [field.describe() for field in self]}


class PropertyCatalogue(FieldCatalogue[DiscoveredProperty, PropertyIdLike]):
    """Adapt property definitions through a registry, retaining unsupported fields."""

    def __init__(self, properties: Iterable[PropertyDetails], registry: TestRegistry):
        super().__init__(self._discover_properties(properties, registry))

    @staticmethod
    def _discover_properties(
        properties: Iterable[PropertyDetails],
        registry: TestRegistry,
    ) -> Iterator[tuple[UUID, DiscoveredProperty]]:
        for details in properties:
            field: DiscoveredProperty
            try:
                field = PropertyInfo(details, registry)
            except UnsupportedPropertyTypeError as error:
                field = UnsupportedPropertyInfo(details, str(error))
            yield details.propertyId.guid, field

    @staticmethod
    def _normalize_id(identifier: PropertyIdLike) -> UUID:
        return normalize_property_id(identifier).propertyId.guid

    # Narrow these selections to their concrete property types for callers.
    @property
    def supported(self) -> tuple[PropertyInfo, ...]:
        return tuple(field for field in self if isinstance(field, PropertyInfo))

    @property
    def unsupported(self) -> tuple[UnsupportedPropertyInfo, ...]:
        return tuple(field for field in self if isinstance(field, UnsupportedPropertyInfo))


class ClassificationCatalogue(FieldCatalogue[ClassificationInfo, ClassificationSystemIdLike]):
    """Index captured system fields, using the common catalogue operations."""

    def __init__(self, fields: Iterable[ClassificationInfo]):
        super().__init__((field.system_id, field) for field in fields)

    @staticmethod
    def _normalize_id(identifier: ClassificationSystemIdLike) -> UUID:
        return normalize_classification_system_id(identifier).classificationSystemId.guid
