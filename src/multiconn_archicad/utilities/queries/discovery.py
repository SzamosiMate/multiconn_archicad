"""Store searchable field snapshots and adapt source-specific metadata."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias
from uuid import UUID

from multiconn_archicad.models.tapir.types import (
    ElementType,
    PropertyDetails,
    ToolDefaultProperties,
    ToolDefaultPropertyFilter,
)
from multiconn_archicad.utilities.identifiers import (
    ClassificationSystemIdLike,
    PropertyIdLike,
    normalize_classification_system_id,
    normalize_property_id,
)

from multiconn_archicad.utilities.server_versions import read_archicad_major

from .catalogue import FieldCatalogue, QueryFieldCatalogue, _reference_key
from .fields import ClassificationInfo, ElementTypeInfo, FieldInfo, PropertyInfo, UnsupportedPropertyInfo
from .registry import TestRegistry
from .errors import UnsupportedPropertyTypeError
from .versioning import require_query_tapir_version

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi

DiscoveredProperty: TypeAlias = PropertyInfo | UnsupportedPropertyInfo

BUILTIN_QUERY_FIELDS: tuple[FieldInfo[Any], ...] = (ElementTypeInfo(),)


class PropertyCatalogue(FieldCatalogue[DiscoveredProperty, PropertyIdLike]):
    """Adapt property definitions through a registry, retaining unsupported fields."""

    kind = "property"

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

    kind = "classification"

    def __init__(self, fields: Iterable[ClassificationInfo]):
        super().__init__((field.system_id, field) for field in fields)

    @staticmethod
    def _normalize_id(identifier: ClassificationSystemIdLike) -> UUID:
        return normalize_classification_system_id(identifier).classificationSystemId.guid


def _legacy_browsable_property_ids(api: UnifiedApi) -> set[UUID]:
    """Exclude fundamental built-ins from the picker on Archicad 26/27."""
    ids = {item.propertyId.guid for item in api.official.property.get_all_property_ids()}
    defaults = api.tapir.property.get_properties_of_tool_defaults(
        [kind for kind in ElementType if kind is not ElementType.UNKNOWN],
        filter=ToolDefaultPropertyFilter.USER_LEVEL_BUILT_IN,
    )
    for result in defaults:
        if isinstance(result, ToolDefaultProperties):
            ids.update(prop.propertyId.guid for prop in result.properties)
    return ids


def discover_query_catalogue(
    api: UnifiedApi,
    *,
    property_ids: Sequence[UUID] | None,
    classification_ids: Sequence[UUID] | None,
    browse_ids_by_kind: Mapping[str, set[UUID]] | None = None,
) -> QueryFieldCatalogue:
    catalogues: list[FieldCatalogue[Any, Any]] = []
    if property_ids is None or property_ids:
        catalogues.append(api.utilities.property.discover_query_fields(property_ids=property_ids))
    if classification_ids is None or classification_ids:
        catalogues.append(api.utilities.classification.discover_query_fields(classification_ids))
    return QueryFieldCatalogue(catalogues, fields=BUILTIN_QUERY_FIELDS, browse_ids_by_kind=browse_ids_by_kind)


def discover_row_catalogue(api: UnifiedApi, references: Iterable[Mapping[str, object]] | None) -> QueryFieldCatalogue:
    metadata = api.read_header_metadata()
    require_query_tapir_version(api, metadata)
    if references is None:
        browse_ids_by_kind = None
        if read_archicad_major(api, metadata) < 28:
            browse_ids_by_kind = {"property": _legacy_browsable_property_ids(api)}
        return discover_query_catalogue(
            api, property_ids=None, classification_ids=None, browse_ids_by_kind=browse_ids_by_kind
        )
    ids_by_kind: dict[str, list[UUID]] = {}
    for reference in references:
        key = _reference_key(reference)
        if key is not None and key[1] is not None:
            kind, field_id = key
            ids_by_kind.setdefault(kind, []).append(field_id)
    return discover_query_catalogue(
        api, property_ids=ids_by_kind.get("property", ()), classification_ids=ids_by_kind.get("classification", ())
    )
