"""Load raw query columns, attribute metadata, and element-type membership."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.results.batch_results import BatchGrid, BatchResult, BatchSlot
from multiconn_archicad.utilities.identifiers import normalize_attribute_id

from .context import ContextSource
from .layer_data import LayerAttribute, LayerCombinationData

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
        grid = api.utilities.property.get_property_values_per_element_result(elements, keys, use_si_units=True)
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


def read_attribute_choices(api: UnifiedApi, attribute_type: tapir.AttributeType) -> tuple[LayerAttribute, ...]:
    headers = api.tapir.attribute.get_attributes_by_type(attribute_type).attributes
    return tuple(LayerAttribute(item.attributeId.guid, int(item.index), item.name) for item in headers)


class AttributeChoicesSource(ContextSource[tapir.AttributeType, Mapping[int, LayerAttribute]]):
    """Read GUID/index/name headers for each requested attribute domain once."""

    def load(
        self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem], keys: Sequence[tapir.AttributeType]
    ) -> Mapping[tapir.AttributeType, Mapping[int, LayerAttribute]]:
        return {
            attribute_type: {item.index: item for item in read_attribute_choices(api, attribute_type)}
            for attribute_type in keys
        }


# SDK built-in GeneralElemProperties / LayerIndex (Integer) by its built-in property GUID
_LAYER_INDEX_PROPERTY_ID = UUID("a74b66a1-629a-4807-83ac-5fff0553a3ac")


class ElementLayerIndicesSource(ContextSource[None, Mapping[UUID, BatchSlot[int]]]):
    """Read the built-in layer-index property, preserving each element's errors."""

    def load(
        self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem], keys: Sequence[None]
    ) -> Mapping[None, Mapping[UUID, BatchSlot[int]]]:
        grid = api.utilities.property.get_property_values_per_element_result(
            elements, [_LAYER_INDEX_PROPERTY_ID], use_si_units=True
        )
        values: dict[UUID, BatchSlot[int]] = {}
        for position, element in enumerate(elements):
            value = grid.rows[position].slots[0]
            try:
                values[element.elementId.guid] = value.map(int)
            except ValueError:
                values[element.elementId.guid] = BatchSlot.failure(
                    f"Cannot interpret layer index {value.value!r} as an integer"
                )
        return {None: values}


class LayerCombinationsSource(ContextSource[None, Mapping[UUID, LayerCombinationData]]):
    """Read saved combination names and visibility without evaluating queries."""

    def load(
        self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem], keys: Sequence[None]
    ) -> Mapping[None, Mapping[UUID, LayerCombinationData]]:
        attributes = read_attribute_choices(api, tapir.AttributeType.LAYER_COMBINATION)
        if not attributes:
            return {None: {}}
        results = api.tapir.attribute.get_layer_combinations([normalize_attribute_id(item.guid) for item in attributes])
        batch: BatchResult[tapir.LayerCombinationAttributeDetails] = BatchResult.from_items(
            results, accessor=lambda item: item.layerCombination
        )
        batch.raise_for_errors("Query layer combination visibility")
        combinations = {
            details.attributeId.guid: LayerCombinationData(
                details.name,
                frozenset(layer.attributeId.guid for layer in details.layers if not layer.isHidden),
            )
            for details in batch.successes
        }
        return {None: combinations}


PROPERTY_VALUES = PropertyValuesSource()
CLASSIFICATION_VALUES = ClassificationValuesSource()
CLASSIFICATION_FIELDS = ClassificationFieldsSource()
TYPE_MEMBERSHIP = TypeMembershipSource()
ATTRIBUTE_CHOICES = AttributeChoicesSource()
ELEMENT_LAYER_INDICES = ElementLayerIndicesSource()
LAYER_COMBINATIONS = LayerCombinationsSource()
