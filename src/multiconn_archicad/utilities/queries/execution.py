"""Share read-only candidate listing, batch reads, and query evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.results.batch_results import BatchResult, BatchSlot

from .context import ContextBuilder, EvaluationContext
from .models import Predicate, Query
from .sources import PROPERTY_VALUES, TYPE_MEMBERSHIP
from .validation import validate_query

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


def validate_execution_query(api: UnifiedApi, query: Query) -> None:
    """Check the complete query before narrowing candidates or skipping reads."""
    if not isinstance(query, Query):
        raise TypeError("Expected a Query instance; parse query JSON with Query.model_validate_json() first")
    # Type-only queries have no metadata-dependent criteria. Their structure was
    # validated by Pydantic, so no property discovery request is necessary.
    builder = ContextBuilder()
    query.where.prepare(builder)
    if builder.requires(PROPERTY_VALUES):
        catalogue = api.utilities.property.discover_query_fields()
        validate_query(query, catalogue).raise_for_errors()


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
    """Use safe type bounds for listing, retaining every original predicate."""
    bounds = query.where.candidate_types()
    if bounds == frozenset():
        return []
    database_list = list(databases) if databases is not None else None
    filter_list = list(filters) if filters is not None else None
    elements: list[tapir.ElementIdArrayItem] = []

    if bounds is None:
        response = api.tapir.element.get_all_elements(databases=database_list, filters=filter_list)
        elements.extend(_listed_elements(response))
    else:
        # Enum declaration order keeps results independent of set iteration.
        for element_type in tapir.ElementType:
            if element_type not in bounds:
                continue
            response = api.tapir.element.get_elements_by_type(
                element_type, databases=database_list, filters=filter_list
            )
            elements.extend(_listed_elements(response))
    return elements


def evaluate_query_candidates(
    api: UnifiedApi, query: Query, elements: Sequence[tapir.ElementIdArrayItem]
) -> dict[UUID, BatchSlot[tapir.ElementIdArrayItem]]:
    """Evaluate each distinct candidate once; callers choose search/filter output."""
    if not elements:
        return {}

    seen: set[UUID] = set()
    candidates: list[tapir.ElementIdArrayItem] = []
    for element in elements:
        if element.elementId.guid not in seen:
            seen.add(element.elementId.guid)
            candidates.append(element)

    bounds = query.where.candidate_types()
    eligible = _narrow_candidates(api, candidates, bounds)
    context = _build_query_context(api, query.where, eligible, bounds)
    return _evaluate_candidates(query.where, candidates, eligible, context)


def _narrow_candidates(
    api: UnifiedApi,
    candidates: list[tapir.ElementIdArrayItem],
    bounds: frozenset[tapir.ElementType] | None,
) -> list[tapir.ElementIdArrayItem]:
    """Apply the overall type bound before preparing any predicate data."""
    if bounds is None:
        return candidates
    if not bounds:
        return []
    return api.tapir.element.filter_elements(
        candidates, element_types=[kind for kind in tapir.ElementType if kind in bounds]
    )


def _build_query_context(
    api: UnifiedApi,
    where: Predicate,
    candidates: Sequence[tapir.ElementIdArrayItem],
    bounds: frozenset[tapir.ElementType] | None,
) -> EvaluationContext:
    """Let predicates request data, reusing the completed candidate-bound filter."""
    builder = ContextBuilder()
    where.prepare(builder)
    if bounds is not None:
        builder.provide(TYPE_MEMBERSHIP, bounds, frozenset(item.elementId.guid for item in candidates))
    return builder.build(api, candidates)


def _evaluate_candidates(
    where: Predicate,
    candidates: Sequence[tapir.ElementIdArrayItem],
    eligible: Sequence[tapir.ElementIdArrayItem],
    context: EvaluationContext,
) -> dict[UUID, BatchSlot[tapir.ElementIdArrayItem]]:
    """Evaluate completed reads and translate Boolean decisions into element slots."""
    results: dict[UUID, BatchSlot[tapir.ElementIdArrayItem]] = {}
    eligible_ids = {element.elementId.guid for element in eligible}
    for element in candidates:
        guid = element.elementId.guid
        if guid not in eligible_ids:
            results[guid] = BatchSlot.filtered()
            continue
        decision = where.evaluate(context, guid)
        if decision.is_error:
            results[guid] = BatchSlot.failure(decision.error)
        elif decision.value:
            results[guid] = BatchSlot.success(element)
        else:
            results[guid] = BatchSlot.filtered()
    return results
