"""Discover classification trees and read aligned assignments through one API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.identifiers import (
    ClassificationSystemIdLike,
    ElementIdLike,
    normalize_classification_system_ids,
    normalize_element_ids,
)
from multiconn_archicad.utilities.queries.discovery import ClassificationCatalogue
from multiconn_archicad.utilities.queries.fields import ClassificationInfo
from multiconn_archicad.utilities.results.batch_results import BatchGrid

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


def _assignment_item_id(assignment: tapir.ClassificationId) -> UUID | None:
    """Treat a successful missing/zero item identifier as unclassified."""
    item = assignment.classificationItemId
    return item.guid if item is not None and item.guid.int != 0 else None


class ClassificationUtilities:
    """Fetch classification metadata and assignments, without cross-call caching."""

    def __init__(self, api: UnifiedApi):
        self._api = api

    def discover_query_fields(
        self,
        system_ids: Sequence[ClassificationSystemIdLike] | None = None,
    ) -> ClassificationCatalogue:
        """Load system fields and complete trees into a disconnected snapshot.

        None selects every system in API order. Explicit identifiers select
        systems in request order, once each; [] returns an empty catalogue.
        Missing systems raise KeyError before any trees are requested. Command
        failures propagate. No element assignments are read by discovery.
        """
        requested = normalize_classification_system_ids(system_ids) if system_ids is not None else None
        if requested == []:
            return ClassificationCatalogue(())
        systems = self._api.official.classification.get_all_classification_systems()
        by_id = {system.classificationSystemId.guid: system for system in systems}
        selected = (
            systems
            if requested is None
            else [by_id[guid] for guid in dict.fromkeys(item.classificationSystemId.guid for item in requested)]
        )
        fields = []
        for system in selected:
            tree = self._api.official.classification.get_all_classifications_in_system(
                official.ClassificationSystemId(guid=system.classificationSystemId.guid)
            )
            fields.append(ClassificationInfo(system, tree))
        return ClassificationCatalogue(fields)

    def get_classifications_per_element_result(
        self,
        elements: Sequence[ElementIdLike],
        system_ids: Sequence[ClassificationSystemIdLike],
    ) -> BatchGrid[UUID | None]:
        """Read one aligned element-by-system grid through Tapir, including subelements.

        Input order and duplicate identifiers are preserved on both axes.
        Successful values are assigned item GUIDs or None for unclassified.
        Per-cell and whole-row errors remain errors; whole-command failures
        raise. At least one system is required. Empty elements return an empty
        grid with the requested width and make no API request.
        """
        systems = normalize_classification_system_ids(system_ids)
        if not systems:
            raise ValueError("At least one classification system must be specified.")
        candidates = normalize_element_ids(elements)
        items = (
            self._api.tapir.classification.get_classifications_of_elements(candidates, systems) if candidates else []
        )
        rows = [item if isinstance(item, tapir.ErrorItem) else item.classificationIds for item in items]
        return BatchGrid[tapir.ClassificationId].from_rows(rows, width=len(systems)).map(_assignment_item_id)

    def get_classifications_per_element(
        self,
        elements: Sequence[ElementIdLike],
        system_ids: Sequence[ClassificationSystemIdLike],
    ) -> list[list[UUID | None]]:
        """Return aligned assignment values, raising BatchOperationError on row/cell failures."""
        result = self.get_classifications_per_element_result(elements, system_ids)
        result.raise_for_errors("Batch classification assignments read")
        return [[slot.value for slot in row] for row in result.rows]
