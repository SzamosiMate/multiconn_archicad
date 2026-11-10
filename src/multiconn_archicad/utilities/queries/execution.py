"""Share read-only candidate listing, batch reads, and query evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.results.batch_results import BatchResult, BatchSlot
from multiconn_archicad.utilities.results.query_results import FindElementsResult

from .context import ContextBuilder, EvaluationContext
from .discovery import discover_query_catalogue
from .fields import ClassificationInfo
from .models import Predicate, Query
from .sources import CLASSIFICATION_FIELDS, PROPERTY_VALUES, TYPE_MEMBERSHIP
from .validation import validate_query
from .versioning import require_query_tapir_version, validate_query_version

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


def validate_execution_query(api: UnifiedApi, query: Query) -> ContextBuilder:
    """Check the complete query before narrowing candidates or skipping reads."""
    if not isinstance(query, Query):
        raise TypeError("Expected a Query instance; parse query JSON with Query.model_validate_json() first")
    validate_query_version(query.schema_version)
    require_query_tapir_version(api, api.read_header_metadata())
    # Discover only the field families requested by prepare(). Keep the same
    # builder so execution reuses validated classification metadata.
    builder = ContextBuilder()
    query.where.prepare(builder)
    system_ids = builder.requested_keys(CLASSIFICATION_FIELDS)
    catalogue = discover_query_catalogue(
        api, property_ids=builder.requested_keys(PROPERTY_VALUES), classification_ids=system_ids
    )
    validate_query(query, catalogue).raise_for_errors()
    for system_id in system_ids:
        field = catalogue.resolve({"kind": "classification", "field_id": system_id})
        if isinstance(field, ClassificationInfo):
            builder.provide(CLASSIFICATION_FIELDS, system_id, field)
    return builder


def _listed_elements(response: tapir.ElementsWithExecutionResults) -> list[tapir.ElementIdArrayItem]:
    BatchResult.from_items(response.executionResultForDatabases or ()).raise_for_errors(
        "List query candidate databases"
    )
    return response.elements


def list_query_candidates(
    api: UnifiedApi,
    query: Query,
    *,
    databases: Sequence[tapir.DatabaseIdArrayItem] | None,
    filters: Sequence[tapir.ElementFilter] | None,
) -> list[tapir.ElementIdArrayItem]:
    """List within a safe upper bound on matching element types.

    None means unrestricted; an empty bound means nothing can match. Keep all
    original predicates for evaluation after listing.
    """
    type_bound = query.where.candidate_types()
    if type_bound == frozenset():
        return []
    database_list = list(databases) if databases is not None else None
    filter_list = list(filters) if filters is not None else None
    elements: list[tapir.ElementIdArrayItem] = []

    if type_bound is None:
        response = api.tapir.element.get_all_elements(databases=database_list, filters=filter_list)
        elements.extend(_listed_elements(response))
    else:
        # Enum declaration order keeps results independent of set iteration.
        for element_type in tapir.ElementType:
            if element_type not in type_bound:
                continue
            response = api.tapir.element.get_elements_by_type(
                element_type, databases=database_list, filters=filter_list
            )
            elements.extend(_listed_elements(response))
    return elements


def evaluate_query_candidates(
    api: UnifiedApi,
    query: Query,
    elements: Sequence[tapir.ElementIdArrayItem],
    builder: ContextBuilder,
) -> FindElementsResult:
    """Evaluate candidates using the builder carrying validated field metadata."""
    if not elements:
        return FindElementsResult((), BatchResult(()))

    seen: set[UUID] = set()
    unique_candidates: list[tapir.ElementIdArrayItem] = []
    for element in elements:
        if element.elementId.guid not in seen:
            seen.add(element.elementId.guid)
            unique_candidates.append(element)

    type_bound = query.where.candidate_types()
    eligible_candidates = _narrow_candidates(api, unique_candidates, type_bound)
    context = _build_query_context(api, builder, eligible_candidates, type_bound)
    outcomes = _evaluate_candidates(query.where, unique_candidates, eligible_candidates, context)
    return FindElementsResult(tuple(unique_candidates), outcomes)


def _narrow_candidates(
    api: UnifiedApi,
    unique_candidates: list[tapir.ElementIdArrayItem],
    type_bound: frozenset[tapir.ElementType] | None,
) -> list[tapir.ElementIdArrayItem]:
    """Apply the overall type bound before preparing any predicate data."""
    if type_bound is None:
        return unique_candidates
    if not type_bound:
        return []
    return api.tapir.element.filter_elements(
        unique_candidates, element_types=[kind for kind in tapir.ElementType if kind in type_bound]
    )


def _build_query_context(
    api: UnifiedApi,
    builder: ContextBuilder,
    eligible_candidates: Sequence[tapir.ElementIdArrayItem],
    type_bound: frozenset[tapir.ElementType] | None,
) -> EvaluationContext:
    """Let predicates request data, reusing the completed candidate-bound filter."""
    if type_bound is not None:
        builder.provide(TYPE_MEMBERSHIP, type_bound, frozenset(item.elementId.guid for item in eligible_candidates))
    return builder.build(api, eligible_candidates)


def _evaluate_candidates(
    where: Predicate,
    unique_candidates: Sequence[tapir.ElementIdArrayItem],
    eligible_candidates: Sequence[tapir.ElementIdArrayItem],
    context: EvaluationContext,
) -> BatchResult[tapir.ElementIdArrayItem]:
    """Evaluate completed reads and translate Boolean decisions into element slots."""
    slots: list[BatchSlot[tapir.ElementIdArrayItem]] = []
    eligible_ids = {element.elementId.guid for element in eligible_candidates}
    for element in unique_candidates:
        guid = element.elementId.guid
        if guid not in eligible_ids:
            slots.append(BatchSlot.filtered())
            continue
        decision = where.evaluate(context, guid)
        if decision.is_error:
            slots.append(BatchSlot.failure(decision.error))
        elif decision.value:
            slots.append(BatchSlot.success(element))
        else:
            slots.append(BatchSlot.filtered())
    return BatchResult(tuple(slots))
