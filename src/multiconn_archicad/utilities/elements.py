"""Select, filter, group, and query Archicad elements."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.identifiers import (
    ElementIdLike,
    PropertyIdLike,
    normalize_element_ids,
    normalize_property_id,
)
from multiconn_archicad.utilities.results import (
    BatchResult,
    BatchSlot,
)

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


TYPES_3D: tuple[tapir.ElementType, ...] = (
    tapir.ElementType.WALL,
    tapir.ElementType.COLUMN,
    tapir.ElementType.BEAM,
    tapir.ElementType.WINDOW,
    tapir.ElementType.DOOR,
    tapir.ElementType.OBJECT,
    tapir.ElementType.LAMP,
    tapir.ElementType.SLAB,
    tapir.ElementType.ROOF,
    tapir.ElementType.MESH,
    tapir.ElementType.ZONE,
    tapir.ElementType.CURTAIN_WALL,
    tapir.ElementType.SHELL,
    tapir.ElementType.SKYLIGHT,
    tapir.ElementType.MORPH,
    tapir.ElementType.STAIR,
    tapir.ElementType.RAILING,
    tapir.ElementType.OPENING,
)
"""Ordered main 3D element types, excluding component subelement types."""


class ElementUtilities:
    """Query and update elements through one Unified API instance.

    The utility stores the API reference and does not cache element state.
    """

    def __init__(self, api: UnifiedApi):
        """Bind element operations to ``api``."""
        self._api = api

    def set_selected_elements_result(
        self, elements: Sequence[ElementIdLike]
    ) -> BatchResult[tapir.ElementIdArrayItem]:
        """Replace the selection and retain per-request add outcomes.

        Args:
            elements: Desired selection in result order.

        Returns:
            A 1D result aligned with ``elements``. Already-selected elements
            count as successes; add failures remain error slots.

        Raises:
            BatchOperationError: If removing an element fails, because the
                requested selection could not be established.
        """
        desired = normalize_element_ids(elements)
        desired_by_guid = {element.elementId.guid: element for element in desired}
        current = self._api.tapir.element.get_selected_elements()
        current_guids = {element.elementId.guid for element in current}

        to_remove = [element for element in current if element.elementId.guid not in desired_by_guid]
        to_add = [element for guid, element in desired_by_guid.items() if guid not in current_guids]

        added_slots: dict[UUID, BatchSlot[tapir.ElementIdArrayItem]] = {}
        if to_remove or to_add:
            response = self._api.tapir.element.change_selection_of_elements(
                add_elements_to_selection=to_add or None,
                remove_elements_from_selection=to_remove or None,
            )
            BatchResult.from_items(response.executionResultsOfRemoveFromSelection).raise_for_errors(
                "Remove elements from selection"
            )
            added_slots = {
                element.elementId.guid: BatchSlot.from_raw(raw, accessor=lambda _: element)
                for element, raw in zip(to_add, response.executionResultsOfAddToSelection)
            }

        return BatchResult(
            tuple(
                BatchSlot.success(element) if element.elementId.guid in current_guids else added_slots[element.elementId.guid]
                for element in desired
            )
        )

    def set_selected_elements(self, elements: Sequence[ElementIdLike]) -> None:
        """Replace the selection, raising if any add or removal fails.

        Args:
            elements: Element IDs to leave selected. An empty sequence clears
                the selection.

        Raises:
            BatchOperationError: If an element cannot be added or removed.
        """
        self.set_selected_elements_result(elements).raise_for_errors("Select elements")

    def get_3d_elements(self) -> list[tapir.ElementIdArrayItem]:
        """Return independent main 3D elements in the configured type order.

        The list includes doors, windows, and openings, but excludes component
        subelements.
        """
        elements: list[tapir.ElementIdArrayItem] = []
        for element_type in TYPES_3D:
            response = self._api.tapir.element.get_elements_by_type(
                element_type,
                filters=[tapir.ElementFilter.IS_INDEPENDENT],
            )
            elements.extend(response.elements)
        return elements

    def filter_elements_by_property_values_result(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
        values: Sequence[str],
    ) -> BatchResult[tapir.ElementIdArrayItem]:
        """Keep elements whose property display string exactly matches ``values``.

        Args:
            elements: Elements in result order.
            property_id: Property to read.
            values: Accepted display strings. If empty, every element is
                returned as FILTERED without reading the property.

        Returns:
            A 1D result aligned with ``elements``. Non-matches are FILTERED and
            property read errors retain their element positions.
        """
        normalized_elements = normalize_element_ids(elements)
        normalized_property = normalize_property_id(property_id)

        if not values:
            return BatchResult(tuple(BatchSlot.filtered() for _ in normalized_elements))

        read = self._api.utilities.property.get_flat_property_values_result(
            normalized_elements,
            normalized_property,
        )
        accepted_values = frozenset(values)

        slots: list[BatchSlot[tapir.ElementIdArrayItem]] = []
        for element, value_slot in zip(normalized_elements, read.slots):
            if value_slot.is_error:
                slots.append(BatchSlot.failure(value_slot.error))
            elif value_slot.value in accepted_values:
                slots.append(BatchSlot.success(element))
            else:
                slots.append(BatchSlot.filtered())

        return BatchResult(tuple(slots))

    def filter_elements_by_property_values(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
        values: Sequence[str],
    ) -> list[tapir.ElementIdArrayItem]:
        """Return matching elements and raise if a property read fails.

        Args:
            elements: Elements to test.
            property_id: Property to read.
            values: Accepted display strings.

        Raises:
            BatchOperationError: If Archicad reports a property read error.
        """
        result = self.filter_elements_by_property_values_result(elements, property_id, values)
        result.raise_for_errors("Filter elements by property values")
        return result.successes

    def group_elements_by_property_value(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
    ) -> dict[str, list[tapir.ElementIdArrayItem]]:
        """Group elements by property display value in first-seen key order.

        Args:
            elements: Elements to group.
            property_id: Property whose display values form the keys.

        Raises:
            BatchOperationError: If a property read fails.
        """
        normalized_elements = normalize_element_ids(elements)
        values = self._api.utilities.property.get_flat_property_values(normalized_elements, property_id)
        groups: dict[str, list[tapir.ElementIdArrayItem]] = {}
        for value, element in zip(values, normalized_elements):
            groups.setdefault(value, []).append(element)
        return groups

    def get_elements_in_layer_combination_result(self, name: str) -> BatchResult[tapir.ElementIdArrayItem]:
        """Find main 3D elements on visible layers in a named combination.

        Returns:
            A 1D result aligned with the listed main 3D elements. Property read
            failures remain in their element slots.

        Notes:
            Layer membership is matched by display name using the built-in
            ``ModelView_LayerName`` property. Attribute lookup and element
            listing are prerequisites and retain their fail-fast behavior.
        """
        layer_names = self._api.utilities.attribute.get_layer_names_of_combination(name)
        elements = self.get_3d_elements()
        property_id = self._api.utilities.property.resolve_property_id(
            official.BuiltInPropertyUserId(nonLocalizedName="ModelView_LayerName")
        )
        return self.filter_elements_by_property_values_result(elements, property_id, layer_names)

    def get_elements_in_layer_combination(self, name: str) -> list[tapir.ElementIdArrayItem]:
        """Return main 3D elements on visible layers in a named combination.

        Raises:
            BatchOperationError: If a property read fails.
        """
        result = self.get_elements_in_layer_combination_result(name)
        result.raise_for_errors("Get elements in layer combination")
        return result.successes
