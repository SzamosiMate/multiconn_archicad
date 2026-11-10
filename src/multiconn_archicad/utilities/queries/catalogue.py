"""Index query fields independently of API discovery and predicate models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from itertools import chain
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from uuid import UUID

if TYPE_CHECKING:
    from .fields import FieldInfo

FieldT = TypeVar("FieldT", bound="FieldInfo[Any]")
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

    @property
    @abstractmethod
    def kind(self) -> str:
        """Identify the predicate kind whose fields this catalogue contains."""
        ...

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

    def get_field(self, field_id: UUID) -> FieldT | None:
        """Look up a query field by its normalized identity."""
        return self._by_id.get(field_id)

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


@dataclass(frozen=True, slots=True)
class QueryFieldEntry:
    field: FieldInfo[Any]
    group_path: tuple[str, ...]


def _reference_key(reference: Mapping[str, object]) -> tuple[str, UUID | None] | None:
    kind = reference.get("kind")
    if not isinstance(kind, str):
        return None
    field_id = reference.get("field_id")
    if isinstance(field_id, UUID) or field_id is None:
        return kind, field_id
    if isinstance(field_id, str):
        try:
            return kind, UUID(field_id)
        except ValueError:
            pass
    return None


class QueryFieldCatalogue:
    """Resolve exact field references and expose a separate browse view."""

    def __init__(
        self,
        catalogues: Iterable[FieldCatalogue[Any, Any]] = (),
        *,
        fields: Iterable[FieldInfo[Any]] = (),
        browse_ids_by_kind: Mapping[str, Collection[UUID]] | None = None,
    ) -> None:
        by_kind: dict[str, FieldCatalogue[Any, Any]] = {}
        for catalogue in catalogues:
            if catalogue.kind in by_kind:
                raise ValueError(f"Multiple catalogues for field kind {catalogue.kind!r}")
            by_kind[catalogue.kind] = catalogue
        self.catalogues = MappingProxyType(by_kind)
        self._fields = {_reference_key(field.reference): field for field in fields}
        self._browse_ids_by_kind = {kind: frozenset(ids) for kind, ids in (browse_ids_by_kind or {}).items()}

    def resolve(self, reference: Mapping[str, object]) -> FieldInfo[Any] | None:
        key = _reference_key(reference)
        if key is None:
            return None
        kind, field_id = key
        catalogue = self.catalogues.get(kind)
        if catalogue is not None and field_id is not None:
            return catalogue.get_field(field_id)
        return self._fields.get(key)

    def browse_fields(self) -> Iterator[QueryFieldEntry]:
        for field in chain(self._fields.values(), chain.from_iterable(self.catalogues.values())):
            key = _reference_key(field.reference)
            if not field.supported or key is None:
                continue
            kind, field_id = key
            offered_ids = self._browse_ids_by_kind.get(kind)
            if offered_ids is None or field_id in offered_ids:
                yield QueryFieldEntry(field, field.group_path)
