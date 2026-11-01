"""Load typed field columns, classification metadata and element-type membership."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.results.batch_results import BatchGrid, BatchSlot

from .context import ContextSource

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi
    from .fields import ClassificationInfo


@dataclass(frozen=True, slots=True)
class ColumnData[T]:
    """View one typed column, sharing the grid and row index with other columns."""

    grid: BatchGrid[T]
    row_indices: Mapping[UUID, int]
    column: int

    def value(self, element_id: UUID) -> BatchSlot[T]:
        """Return the original successful/error slot for one element."""
        return self.grid.rows[self.row_indices[element_id]].slots[self.column]


class PropertyValuesSource(ContextSource[UUID, ColumnData[str]]):
    """Read every distinct requested property in one batch for all candidates."""

    def load(
        self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem], keys: Sequence[UUID]
    ) -> Mapping[UUID, ColumnData[str]]:
        grid = api.utilities.property.get_property_values_per_element_result(elements, keys)
        rows = {element.elementId.guid: index for index, element in enumerate(elements)}
        return {key: ColumnData(grid, rows, column) for column, key in enumerate(keys)}


class ClassificationValuesSource(ContextSource[UUID, ColumnData[UUID | None]]):
    """Read all requested systems together, retaining row and cell errors."""

    def load(
        self,
        api: UnifiedApi,
        elements: Sequence[tapir.ElementIdArrayItem],
        keys: Sequence[UUID],
    ) -> Mapping[UUID, ColumnData[UUID | None]]:
        grid = api.utilities.classification.get_classifications_per_element_result(elements, keys)
        rows = {element.elementId.guid: index for index, element in enumerate(elements)}
        return {key: ColumnData(grid, rows, column) for column, key in enumerate(keys)}


class ClassificationFieldsSource(ContextSource[UUID, "ClassificationInfo"]):
    """Identify per-execution classification metadata; this object stores no data.

    Normal search/filter execution provides the validation snapshot to the builder,
    so load() is skipped. Direct prepare/build callers load missing metadata here.
    """

    def load(
        self,
        api: UnifiedApi,
        elements: Sequence[tapir.ElementIdArrayItem],
        keys: Sequence[UUID],
    ) -> Mapping[UUID, ClassificationInfo]:
        catalogue = api.utilities.classification.discover_query_fields(keys)
        return {key: catalogue[key] for key in keys}


class TypeMembershipSource(ContextSource[frozenset[tapir.ElementType], frozenset[UUID]]):
    """Use FilterElements to obtain matching GUIDs for each distinct type set."""

    def load(
        self,
        api: UnifiedApi,
        elements: Sequence[tapir.ElementIdArrayItem],
        keys: Sequence[frozenset[tapir.ElementType]],
    ) -> Mapping[frozenset[tapir.ElementType], frozenset[UUID]]:
        candidates = list(elements)
        memberships: dict[frozenset[tapir.ElementType], frozenset[UUID]] = {}
        for types in keys:
            # Enum declaration order makes request payloads reproducible.
            ordered_types = [kind for kind in tapir.ElementType if kind in types]
            matching_elements = api.tapir.element.filter_elements(candidates, element_types=ordered_types)
            memberships[types] = frozenset(item.elementId.guid for item in matching_elements)
        return memberships


PROPERTY_VALUES = PropertyValuesSource()
CLASSIFICATION_VALUES = ClassificationValuesSource()
CLASSIFICATION_FIELDS = ClassificationFieldsSource()
TYPE_MEMBERSHIP = TypeMembershipSource()
