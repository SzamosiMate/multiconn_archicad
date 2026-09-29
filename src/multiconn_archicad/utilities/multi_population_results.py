"""Relate populations and project results between their item coordinates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias, TypeVar

from multiconn_archicad.utilities.results import (
    BatchResult,
    BatchResult2D,
    SlotState,
    BatchSlot,
    BatchRow,
    BatchGrid
)
from multiconn_archicad.utilities.population_results import (
    PopulationResults,
    BatchReport
)

T = TypeVar("T")
BatchResultType: TypeAlias = BatchResult[Any] | BatchResult2D[Any]
RecordedResult = TypeVar("RecordedResult", bound=BatchResultType)


def _resolve_unmatched_slot(val: SlotState | BatchSlot[T]) -> BatchSlot[T]:
    if isinstance(val, BatchSlot):
        return val
    if val is SlotState.FILTERED:
        return BatchSlot.filtered()
    if val is SlotState.UPSTREAM_FAILED:
        return BatchSlot.upstream_failed()
    raise ValueError(f"Cannot default unmatched target to {val.name}; provide an explicit BatchSlot.")


def _resolve_unmatched_row(default_state: SlotState | BatchSlot[T] | BatchRow[T], result: BatchResult2D[T]) -> BatchRow[T]:
    width = _infer_width(default_state, result)
    if isinstance(default_state, BatchRow):
        if len(default_state) != width:
            raise ValueError(f"Unmatched row width ({len(default_state)}) does not match matrix width ({width}).")
        return default_state
    slot = _resolve_unmatched_slot(default_state)
    return BatchRow(tuple(slot for _ in range(width)))

def _infer_width(default_state: SlotState | BatchSlot[T] | BatchRow[T], result: BatchResult2D[T]) -> int:
    if isinstance(result, BatchGrid):
        width = result.width
    elif result.rows:
        width = len(result.rows[0])
    elif isinstance(default_state, BatchRow):
        width = len(default_state)
    else:
        raise ValueError("Cannot infer row width from an empty 2D result without an explicit BatchRow unmatched.")
    return width


# ==============================================================================
# Multiple Populations & Relationships
# ==============================================================================


@dataclass(frozen=True, slots=True)
class PopulationRelation:
    """Map original-item indices between a source and target population.

    The relation is directional: each pair is ``(source_index, target_index)``.

    Attributes:
        source: Population whose indices are projected from.
        target: Population whose indices are projected to.
        pairs: Validated, deduplicated index pairs in supplied order.
    """

    source: PopulationResults[Any]
    target: PopulationResults[Any]
    pairs: tuple[tuple[int, int], ...]
    _forward: Mapping[int, tuple[int, ...]]
    _reverse: Mapping[int, tuple[int, ...]]

    @classmethod
    def create(
        cls,
        source: PopulationResults[Any],
        target: PopulationResults[Any],
        pairs: Sequence[tuple[int, int]],
    ) -> PopulationRelation:
        """Validate and create a relation from source-target index pairs.

        Args:
            source: Source population.
            target: Target population.
            pairs: ``(source_index, target_index)`` pairs. Duplicate pairs are
                ignored after their first occurrence.

        Raises:
            IndexError: If either index is not an integer in its population.
        """
        max_s = len(source.original_items)
        max_t = len(target.original_items)
        forward: dict[int, list[int]] = {}
        reverse: dict[int, list[int]] = {}
        deduped: list[tuple[int, int]] = []

        for s, t in dict.fromkeys(pairs):
            if not isinstance(s, int) or not isinstance(t, int) or not (0 <= s < max_s and 0 <= t < max_t):
                raise IndexError(f"Pair ({s}, {t}) out of bounds for source ({max_s}) or target ({max_t}).")
            forward.setdefault(s, []).append(t)
            reverse.setdefault(t, []).append(s)
            deduped.append((s, t))

        return cls(
            source=source,
            target=target,
            pairs=tuple(deduped),
            _forward={k: tuple(v) for k, v in forward.items()},
            _reverse={k: tuple(v) for k, v in reverse.items()},
        )

    def targets_for_source(self, source_index: int) -> tuple[int, ...]:
        """Return target indices mapped from ``source_index``."""
        return self._forward.get(source_index, ())

    def sources_for_target(self, target_index: int) -> tuple[int, ...]:
        """Return source indices mapped to ``target_index``."""
        return self._reverse.get(target_index, ())

    def project(
        self, result: BatchResult[T], *, default_state: SlotState | BatchSlot[T] = SlotState.FILTERED,
    ) -> BatchResult[T]:
        """Project a 1D source-aligned result onto target item positions.

        Args:
            result: One slot per source item.
            default_state: Slot to use for unmatched targets. Use a
                ``BatchSlot`` for a success or error; enum defaults may be
                ``FILTERED`` or ``UPSTREAM_FAILED``.

        Returns:
            A 1D result aligned with the target population. Matched slots keep
            their states and values.

        Raises:
            ValueError: If the source length does not match, a target has
                multiple source matches, or ``default_state`` is unsupported.
        """
        if len(result.slots) != len(self.source.original_items):
            raise ValueError(
                f"Result length ({len(result.slots)}) does not match source count ({len(self.source.original_items)})."
            )

        unmatched_slot = _resolve_unmatched_slot(default_state)
        slots: list[BatchSlot[T]] = []

        for t_idx in range(len(self.target.original_items)):
            sources = self._reverse.get(t_idx, ())
            if len(sources) > 1:
                raise ValueError(
                    f"Target index {t_idx} matches multiple sources ({sources}); direct projection is ambiguous."
                )
            if len(sources) == 1:
                slots.append(result.slots[sources[0]])
            else:
                slots.append(unmatched_slot)

        return BatchResult(tuple(slots))

    def project_rows(
        self,
        result: BatchResult2D[T],
        *,
        default_state: SlotState | BatchSlot[T] | BatchRow[T] = SlotState.FILTERED,
    ) -> BatchResult2D[T]:
        """Project a 2D source-aligned result onto target item positions.

        Args:
            result: One row per source item.
            default_state: Row or slot to use for unmatched targets. A slot is
                repeated across the row. Enum defaults may be ``FILTERED`` or
                ``UPSTREAM_FAILED``. An empty non-grid result needs an explicit
                ``BatchRow`` so its width can be inferred.

        Returns:
            A result aligned with the target population. A ``BatchGrid`` input
            remains a grid with the same width.

        Raises:
            ValueError: If the source row count does not match, a target has
                multiple source matches, or an unmatched row cannot be formed.
        """
        if len(result.rows) != len(self.source.original_items):
            raise ValueError(
                f"Result rows ({len(result.rows)}) does not match source count ({len(self.source.original_items)})."
            )

        unmatched_row = _resolve_unmatched_row(default_state, result)
        rows: list[BatchRow[T]] = []

        for t_idx in range(len(self.target.original_items)):
            sources = self._reverse.get(t_idx, ())
            if len(sources) > 1:
                raise ValueError(
                    f"Target index {t_idx} matches multiple sources ({sources}); direct projection is ambiguous."
                )
            if len(sources) == 1:
                rows.append(result.rows[sources[0]])
            else:
                rows.append(unmatched_row)

        if isinstance(result, BatchGrid):
            return BatchGrid(tuple(rows), width=result.width)
        return BatchResult2D(tuple(rows))


class MultiPopulationResults:
    """Register named populations and the relations between them."""

    __slots__ = ("_populations", "_relations")

    def __init__(self) -> None:
        """Create an empty population and relation registry."""
        self._populations: dict[str, PopulationResults[Any]] = {}
        self._relations: list[PopulationRelation] = []

    @property
    def populations(self) -> Mapping[str, PopulationResults[Any]]:
        """Return registered population collectors keyed by name."""
        return self._populations

    @property
    def relations(self) -> tuple[PopulationRelation, ...]:
        """Return registered population relations in creation order."""
        return tuple(self._relations)

    def __getitem__(self, name: str) -> PopulationResults[Any]:
        """Return the registered population named ``name``."""
        return self._populations[name]

    def add_population(self, name: str, items: Sequence[T]) -> PopulationResults[T]:
        """Create and register a population collector.

        Args:
            name: Non-empty unique name for this population.
            items: Original items in population order.

        Raises:
            ValueError: If ``name`` is empty, not a string, or already used.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Population name must be a non-empty string.")
        if name in self._populations:
            raise ValueError(f"Population {name!r} is already registered.")

        pop = PopulationResults(items)
        self._populations[name] = pop
        return pop

    def relate(
        self,
        source: PopulationResults[Any],
        target: PopulationResults[Any],
        pairs: Sequence[tuple[int, int]],
    ) -> PopulationRelation:
        """Create and register a relation between registered populations.

        Args:
            source: Registered source population.
            target: Registered target population.
            pairs: Source-target index pairs.

        Raises:
            ValueError: If either population is not registered.
            IndexError: If a pair contains an out-of-range index.
        """
        known = set(self._populations.values())
        if source not in known or target not in known:
            raise ValueError("Source and target populations must be registered with this MultiPopulationResults instance.")

        relation = PopulationRelation.create(source, target, pairs)
        self._relations.append(relation)
        return relation

    def snapshot(self, *, completed: bool = False) -> dict[str, BatchReport[Any]]:
        """Build one report snapshot for each registered population.

        Args:
            completed: Whether processing is complete for every population.
        """
        return {name: pop.snapshot(completed=completed) for name, pop in self._populations.items()}
