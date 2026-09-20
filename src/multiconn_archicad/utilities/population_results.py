from __future__ import annotations

from collections import deque
from collections.abc import Hashable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeAlias, TypeVar

from multiconn_archicad.utilities.results import (
    BatchError,
    BatchResult,
    BatchResult2D,
    BatchResultBase,
    SlotState,
)

T = TypeVar("T")
BatchResultType: TypeAlias = BatchResult[Any] | BatchResult2D[Any]
RecordedResult = TypeVar("RecordedResult", bound=BatchResultType)


class BatchStatus(str, Enum):
    INCOMPLETE = "incomplete"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UPSTREAM_FAILED = "upstream_failed"
    FILTERED = "filtered"


@dataclass(frozen=True, slots=True)
class BatchStep(Generic[T]):
    """Immutable record of one population step."""

    name: str
    index: int
    result: BatchResultBase[T]
    item_indices: tuple[int, ...]

    def iter_failures(self) -> Iterator[tuple[int, BatchFailure]]:
        """Yield direct failures paired with their original-item indices."""
        for coordinate, error in self.result.iter_errors():
            source_index = coordinate[0] if isinstance(coordinate, tuple) else coordinate
            yield self.item_indices[source_index], BatchFailure(self, coordinate, error)

    @property
    def slot_states_by_item(self) -> dict[int, list[SlotState]]:
        """Map original-item indices to every slot state recorded for them."""
        lookup: dict[int, list[SlotState]] = {}
        if isinstance(self.result, BatchResult2D):
            for position, original_index in enumerate(self.item_indices):
                lookup.setdefault(original_index, []).extend(slot.state for slot in self.result.rows[position].slots)
        elif isinstance(self.result, BatchResult):
            for position, original_index in enumerate(self.item_indices):
                lookup.setdefault(original_index, []).append(self.result.slots[position].state)
        return lookup


@dataclass(frozen=True, slots=True)
class BatchFailure:
    step: BatchStep[Any]
    source_coordinate: int | tuple[int, int]
    error: BatchError

    @property
    def step_ref(self) -> BatchStep[Any]:
        return self.step

    @property
    def step_index(self) -> int:
        return self.step.index

    @property
    def step_name(self) -> str:
        return self.step.name


@dataclass(frozen=True, slots=True)
class BatchOutcome(Generic[T]):
    original_item: T
    index: int
    failures: tuple[BatchFailure, ...]
    status: BatchStatus

    @property
    def failed(self) -> bool:
        return self.status is BatchStatus.FAILED

    @property
    def succeeded(self) -> bool:
        return self.status is BatchStatus.SUCCEEDED

    @property
    def incomplete(self) -> bool:
        return self.status is BatchStatus.INCOMPLETE

    @property
    def upstream_failed(self) -> bool:
        return self.status is BatchStatus.UPSTREAM_FAILED

    @property
    def filtered(self) -> bool:
        return self.status is BatchStatus.FILTERED


@dataclass(frozen=True, slots=True)
class BatchReport(Generic[T]):
    outcomes: tuple[BatchOutcome[T], ...]
    steps: tuple[BatchStep[Any], ...]
    status: BatchStatus

    def count(self, status: BatchStatus | None = None) -> int:
        """Return the total outcome count or the count for one status."""
        if status is None:
            return len(self.outcomes)
        return sum(outcome.status is status for outcome in self.outcomes)

    def has(self, status: BatchStatus) -> bool:
        """Return whether at least one outcome has the requested status."""
        return any(outcome.status is status for outcome in self.outcomes)

    def iter_failures(self) -> Iterator[tuple[BatchOutcome[T], BatchFailure]]:
        """Yield every direct failure together with its original-item outcome."""
        for outcome in self.outcomes:
            for failure in outcome.failures:
                yield outcome, failure

    def indices(self, status: BatchStatus) -> tuple[int, ...]:
        """Return the original-item indices whose outcome has ``status``."""
        return tuple(outcome.index for outcome in self.outcomes if outcome.status is status)

    @property
    def status_counts(self) -> Mapping[str, int]:
        return {
            "total": self.count(),
            "succeeded": self.count(BatchStatus.SUCCEEDED),
            "failed": self.count(BatchStatus.FAILED),
            "upstream_failed": self.count(BatchStatus.UPSTREAM_FAILED),
            "filtered": self.count(BatchStatus.FILTERED),
            "incomplete": self.count(BatchStatus.INCOMPLETE),
        }


class PopulationResults(Generic[T]):
    """Passive collection of ordered results recorded for an original population."""

    __slots__ = ("_original_items", "_steps")

    def __init__(self, original_items: Sequence[T]) -> None:
        self._original_items = tuple(original_items)
        self._steps: list[BatchStep[Any]] = []

    @property
    def original_items(self) -> tuple[T, ...]:
        return self._original_items

    @property
    def steps(self) -> tuple[BatchStep[Any], ...]:
        return tuple(self._steps)

    def failures_by_item(self) -> tuple[tuple[BatchFailure, ...], ...]:
        """Return direct failures grouped by original-item index."""
        return collect_failures_by_item(self._original_items, self._steps)

    def record(
        self,
        name: str,
        result: RecordedResult,
        *,
        item_indices: Sequence[int] | None = None,
        for_items: Sequence[T] | None = None,
    ) -> RecordedResult:
        """Record a result and its original-item mapping, then return ``result``."""
        indices = self._validate_record_inputs(result, item_indices, for_items)
        self._steps.append(BatchStep(name, len(self._steps), result, indices))
        return result

    def snapshot(self, *, completed: bool = False) -> BatchReport[T]:
        """Return an immutable report snapshot without closing this collection."""
        return build_batch_report(self._original_items, self._steps, completed=completed)

    def _validate_record_inputs(
        self,
        result: BatchResultType,
        item_indices: Sequence[int] | None,
        for_items: Sequence[T] | None,
    ) -> tuple[int, ...]:
        source_count = len(result.rows) if isinstance(result, BatchResult2D) else len(result.slots)

        if item_indices is not None and for_items is not None:
            raise ValueError("Specify either item_indices or for_items, not both.")

        if for_items is not None:
            if len(for_items) != source_count:
                raise ValueError("for_items length must match result slots or rows.")
            return self._resolve_items_by_key(self._original_items, for_items)

        if item_indices is not None:
            indices = tuple(item_indices)
            if len(indices) != source_count:
                raise ValueError("item_indices length must match result slots or rows.")
            if any(not isinstance(index, int) or index < 0 or index >= len(self._original_items) for index in indices):
                raise IndexError("item_indices contains an original-item index out of bounds.")
            return indices

        if source_count != len(self._original_items):
            raise ValueError("Default item_indices requires one slot/row per original item.")
        return tuple(range(source_count))

    def _resolve_items_by_key(self, original_items: Sequence[T], for_items: Sequence[T]) -> tuple[int, ...]:
        """O(N) FIFO resolution using hashable keys to preserve duplicate safety."""
        lookup: dict[Any, deque[int]] = {}
        for index, item in enumerate(original_items):
            key = self._make_item_key(item)
            lookup.setdefault(key, deque()).append(index)

        resolved: list[int] = []
        for item in for_items:
            key = self._make_item_key(item)
            queue = lookup.get(key)
            if not queue:
                raise ValueError(f"Item {item!r} in for_items was not found or specified too many times.")
            resolved.append(queue.popleft())

        return tuple(resolved)

    @staticmethod
    def _make_item_key(item: Any) -> Hashable:
        """Return a hashable key for any object (native hash or repr fingerprint)."""
        if isinstance(item, Hashable):
            return item
        return repr(item)


def collect_failures_by_item(
    original_items: Sequence[Any], steps: Sequence[BatchStep[Any]]
) -> tuple[tuple[BatchFailure, ...], ...]:
    """Collect direct failures from all steps in stable recording order."""
    failures: list[list[BatchFailure]] = [[] for _ in original_items]
    for step in steps:
        for original_index, failure in step.iter_failures():
            failures[original_index].append(failure)
    return tuple(tuple(item_failures) for item_failures in failures)


def reduce_population_outcomes(
    original_items: Sequence[T], steps: Sequence[BatchStep[Any]], *, completed: bool
) -> tuple[BatchOutcome[T], ...]:
    """Purely reduce recorded population facts to the default per-item outcomes.

    Direct failures accumulated in any step take priority. When processing is not
    complete, every otherwise-clean item is incomplete. Completed populations use
    the last recorded step as their terminal interpretation.
    """
    failures_by_item = collect_failures_by_item(original_items, steps)
    terminal_states = steps[-1].slot_states_by_item if steps else {}
    outcomes: list[BatchOutcome[T]] = []

    for index, item in enumerate(original_items):
        failures = failures_by_item[index]
        states = terminal_states.get(index)

        if failures:
            status = BatchStatus.FAILED
        elif not completed:
            status = BatchStatus.INCOMPLETE
        elif states is None:
            status = BatchStatus.SUCCEEDED if not steps else BatchStatus.FILTERED
        elif any(state is SlotState.UPSTREAM_FAILED for state in states):
            status = BatchStatus.UPSTREAM_FAILED
        elif all(state is SlotState.FILTERED for state in states):
            status = BatchStatus.FILTERED
        else:
            # A mixture containing a successful write is an intentional partial write.
            status = BatchStatus.SUCCEEDED

        outcomes.append(BatchOutcome(item, index, failures, status))

    return tuple(outcomes)


def reduce_batch_status(outcomes: Sequence[BatchOutcome[Any]], *, completed: bool) -> BatchStatus:
    """Purely reduce item outcomes to the legacy aggregate batch status."""
    if any(outcome.failed for outcome in outcomes):
        return BatchStatus.FAILED
    if not completed or any(outcome.incomplete for outcome in outcomes):
        return BatchStatus.INCOMPLETE
    if outcomes and all(outcome.filtered for outcome in outcomes):
        return BatchStatus.FILTERED
    if outcomes and all(outcome.upstream_failed for outcome in outcomes):
        return BatchStatus.UPSTREAM_FAILED
    return BatchStatus.SUCCEEDED


def build_batch_report(
    original_items: Sequence[T], steps: Sequence[BatchStep[Any]], *, completed: bool
) -> BatchReport[T]:
    """Build an immutable report from population facts without mutating them."""
    step_snapshot = tuple(steps)
    outcomes = reduce_population_outcomes(tuple(original_items), step_snapshot, completed=completed)
    return BatchReport(outcomes, step_snapshot, reduce_batch_status(outcomes, completed=completed))
