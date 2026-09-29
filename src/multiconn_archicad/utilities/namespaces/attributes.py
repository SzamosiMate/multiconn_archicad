"""Look up Archicad attributes and layer combinations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.identifiers import normalize_attribute_id
from multiconn_archicad.utilities.results.batch_results import BatchResult

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


class AttributeUtilities:
    """Look up attributes and visible layers through one Unified API instance."""

    def __init__(self, api: UnifiedApi):
        """Bind attribute operations to ``api``."""
        self._api = api

    def get_names_of_attributes(self, attribute_type: tapir.AttributeType) -> list[str]:
        """Return names for attributes of the requested type in API order.

        Args:
            attribute_type: Attribute category to list.
        """
        attributes = self._api.tapir.attribute.get_attributes_by_type(attribute_type)
        return [attribute_header.name for attribute_header in attributes.attributes]

    def get_layers_of_combination(self, name: str) -> list[tapir.LayersOfLayerCombinationItem]:
        """Return layer membership entries for the named layer combination.

        Match the combination by its name. Return an empty list when no matching
        combination is returned by the API.
        """
        attributes = self._api.tapir.attribute.get_attributes_by_type(tapir.AttributeType.LAYER_COMBINATION)
        matches = [attribute for attribute in attributes.attributes if attribute.name == name]
        selected = [normalize_attribute_id(attribute.attributeId) for attribute in matches]
        combinations = self._api.tapir.attribute.get_layer_combinations(selected)
        if combinations and isinstance(combinations[0], tapir.LayerCombinationAttribute):
            return combinations[0].layerCombination.layers
        return []

    def _get_names_of_visible_layers(self, layers: Sequence[tapir.LayersOfLayerCombinationItem]) -> list[str]:
        """Resolve visible layer IDs to names, raising on lookup errors."""
        visible_ids = [normalize_attribute_id(layer.attributeId) for layer in layers if not layer.isHidden]
        raw_layers = self._api.tapir.attribute.get_layers(visible_ids)
        result = BatchResult.from_items(raw_layers, accessor=lambda layer: layer.name)
        result.raise_for_errors("Visible layer names lookup")
        return result.successes

    def get_layer_names_of_combination(self, name: str) -> list[str]:
        """Return visible layer names from a layer combination in API response order.

        Raises:
            BatchOperationError: If Archicad reports an error while looking up
                any visible layer name.
        """
        return self._get_names_of_visible_layers(self.get_layers_of_combination(name))
