"""Adapt property metadata into an explicit, searchable discovery snapshot."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, TypeAlias
from uuid import UUID

from multiconn_archicad.models.tapir.types import PropertyDetails
from multiconn_archicad.utilities.identifiers import PropertyIdLike, normalize_property_id

from .fields import PropertyInfo, UnsupportedPropertyInfo
from .registry import TestRegistry
from . import UnsupportedPropertyTypeError

DiscoveredProperty: TypeAlias = PropertyInfo | UnsupportedPropertyInfo


class PropertyCatalogue:
    """Store one batch's field information, preserving source order and identity.

    Unsupported properties remain visible. Registry ambiguity and other failures
    propagate. This is a metadata snapshot with no project or connection binding.
    Refresh by constructing a new snapshot; it stores no API reference and makes
    no requests.
    """

    def __init__(self, properties: Iterable[PropertyDetails], registry: TestRegistry):
        self._by_id: dict[UUID, DiscoveredProperty] = {}
        self._fields: list[DiscoveredProperty] = []
        self._register_properties(properties, registry)

    def _register_properties(self, properties: Iterable[PropertyDetails], registry: TestRegistry) -> None:
        for details in properties:
            field: DiscoveredProperty
            try:
                field = PropertyInfo(details, registry)
            except UnsupportedPropertyTypeError as error:
                field = UnsupportedPropertyInfo(details, str(error))
            if field.property_id in self._by_id:
                raise ValueError(f"Duplicate property GUID in properties: {field.property_id}")
            self._by_id[field.property_id] = field
            self._fields.append(field)

    @property
    def fields(self) -> tuple[DiscoveredProperty, ...]:
        return tuple(self._fields)

    @property
    def supported(self) -> tuple[PropertyInfo, ...]:
        return tuple(field for field in self._fields if isinstance(field, PropertyInfo))

    @property
    def unsupported(self) -> tuple[UnsupportedPropertyInfo, ...]:
        return tuple(field for field in self._fields if isinstance(field, UnsupportedPropertyInfo))

    def __iter__(self) -> Iterator[DiscoveredProperty]:
        return iter(self._fields)

    def __len__(self) -> int:
        return len(self._fields)

    def __getitem__(self, property_id: PropertyIdLike) -> DiscoveredProperty:
        """Look up a supported or unsupported field; raise KeyError if absent."""
        return self._by_id[normalize_property_id(property_id).propertyId.guid]

    def get(self, property_id: PropertyIdLike) -> DiscoveredProperty | None:
        """Return a field or None for an unknown GUID; malformed IDs still raise."""
        return self._by_id.get(normalize_property_id(property_id).propertyId.guid)

    def search(
        self,
        text: str = "",
        *,
        group: str | None = None,
        supported_only: bool = False,
    ) -> tuple[DiscoveredProperty, ...]:
        """Find case-insensitive label substrings, optionally within an exact group."""
        needle = text.casefold()
        return tuple(
            field
            for field in self._fields
            if (not supported_only or field.supported)
            and (group is None or field.group == group)
            and needle in field.qualified_name.casefold()
        )

    def describe(self) -> dict[str, Any]:
        """Return JSON-friendly supported and unsupported field descriptions."""
        return {"fields": [field.describe() for field in self._fields]}
