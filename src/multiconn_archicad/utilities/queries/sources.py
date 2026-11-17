"""Load typed columns, classification metadata, and type/layer memberships."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.results.batch_results import BatchGrid, BatchResult, BatchSlot
from multiconn_archicad.utilities.identifiers import normalize_attribute_id

from .context import ContextSource
from .layer_data import LayerAttribute, LayerRequest, attribute_choices

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


class AttributeChoicesSource(ContextSource[tapir.AttributeType, tuple[LayerAttribute, ...]]):
    """Read GUID/index/name headers for each requested attribute domain once."""

    def load(
        self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem], keys: Sequence[tapir.AttributeType]
    ) -> Mapping[tapir.AttributeType, tuple[LayerAttribute, ...]]:
        choices: dict[tapir.AttributeType, tuple[LayerAttribute, ...]] = {}
        for attribute_type in keys:
            headers = api.tapir.attribute.get_attributes_by_type(attribute_type).attributes
            if any(item.index != int(item.index) for item in headers):
                raise ValueError("Layer query metadata contains a non-integer attribute index")
            choices[attribute_type] = attribute_choices(
                tuple(LayerAttribute(item.attributeId.guid, int(item.index), item.name) for item in headers)
            )
        return choices


def _visible_layers_of_combinations(
    api: UnifiedApi, combination_ids: frozenset[UUID]
) -> Mapping[UUID, frozenset[UUID]]:
    """Read each requested combination's visible layer GUIDs in one batch."""
    if not combination_ids:
        return {}
    results = api.tapir.attribute.get_layer_combinations(
        [normalize_attribute_id(guid) for guid in sorted(combination_ids, key=str)]
    )
    if len(results) != len(combination_ids):
        raise ValueError("Layer combination response does not match the requested attribute count")
    BatchResult.from_items(results).raise_for_errors("Query layer combination visibility")
    visible: dict[UUID, frozenset[UUID]] = {}
    for result in results:
        if isinstance(result, tapir.LayerCombinationAttribute):
            details = result.layerCombination
            visible[details.attributeId.guid] = frozenset(
                item.attributeId.guid for item in details.layers if not item.isHidden
            )
    if set(visible) != combination_ids:
        raise ValueError("Layer combination response does not match the requested attribute GUIDs")

    return visible


def _indices_of_layers(api: UnifiedApi, layer_ids: frozenset[UUID]) -> Mapping[UUID, int]:
    """Resolve layer GUIDs using only the always-returned GUID/index/name header."""
    if not layer_ids:
        return {}
    layers = api.tapir.attribute.get_layers(
        [normalize_attribute_id(guid) for guid in sorted(layer_ids, key=str)], fields=[]
    )
    if len(layers) != len(layer_ids):
        raise ValueError("Layer index response does not match the requested attribute count")
    BatchResult.from_items(layers).raise_for_errors("Query visible layer indices")
    indices = {layer.attributeId.guid: layer.index for layer in layers if isinstance(layer, tapir.LayerAttribute)}
    if set(indices) != layer_ids:
        raise ValueError("Layer index response does not match the requested attribute GUIDs")
    return indices


def _combination_layer_indices(api: UnifiedApi, combination_ids: frozenset[UUID]) -> Mapping[UUID, frozenset[int]]:
    visible = _visible_layers_of_combinations(api, combination_ids)
    indices = _indices_of_layers(api, frozenset(guid for layers in visible.values() for guid in layers))
    return {guid: frozenset(indices[layer] for layer in layers) for guid, layers in visible.items()}


class LayerMembershipSource(ContextSource[LayerRequest, frozenset[UUID]]):
    """Load declarative layer requests without knowing predicate or test types."""

    def load(
        self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem], keys: Sequence[LayerRequest]
    ) -> Mapping[LayerRequest, frozenset[UUID]]:
        missing_types = tuple(dict.fromkeys(key.attribute_type for key in keys if key.attributes is None))
        choices = ATTRIBUTE_CHOICES.load(api, elements, missing_types)
        selections = {
            key: key.select(key.attributes if key.attributes is not None else choices[key.attribute_type])
            for key in keys
        }
        indices_by_key: dict[LayerRequest, frozenset[int]] = {}
        combinations_by_key: dict[LayerRequest, frozenset[UUID]] = {}
        for key, selected in selections.items():
            if key.attribute_type is tapir.AttributeType.LAYER:
                indices_by_key[key] = frozenset(item.index for item in selected)
            else:
                combinations_by_key[key] = frozenset(item.guid for item in selected)
        combination_ids = frozenset(guid for ids in combinations_by_key.values() for guid in ids)
        combinations = _combination_layer_indices(api, combination_ids)
        for key, ids in combinations_by_key.items():
            indices_by_key[key] = frozenset(index for guid in ids for index in combinations[guid])

        memberships: dict[frozenset[int], frozenset[UUID]] = {frozenset(): frozenset()}
        for indices in indices_by_key.values():
            if indices not in memberships:
                matched = api.tapir.element.filter_elements(list(elements), layer_indices=sorted(indices))
                memberships[indices] = frozenset(item.elementId.guid for item in matched)
        return {key: memberships[indices] for key, indices in indices_by_key.items()}


PROPERTY_VALUES = PropertyValuesSource()
CLASSIFICATION_VALUES = ClassificationValuesSource()
CLASSIFICATION_FIELDS = ClassificationFieldsSource()
TYPE_MEMBERSHIP = TypeMembershipSource()
ATTRIBUTE_CHOICES = AttributeChoicesSource()
LAYER_MEMBERSHIP = LayerMembershipSource()
