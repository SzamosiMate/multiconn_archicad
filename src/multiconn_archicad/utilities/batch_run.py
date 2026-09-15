from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping, Sequence, Hashable
from dataclasses import dataclass, field
from enum import Enum
from types import TracebackType
from typing import Any, Generic, TypeAlias, TypeVar

from multiconn_archicad.utilities.results import BatchError, BatchResult, BatchResult2D, BatchSlot, SlotState

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
    name: str
    index: int
    result: BatchResult[T] | BatchResult2D[T]
    item_indices: tuple[int, ...]

    def iter_failures(self) -> Iterator[tuple[int, BatchFailure]]:
        """Yield (original_item_index, BatchFailure) directly from this step's result."""
        if isinstance(self.result, BatchResult):
            for source_idx, error in self.result.iter_errors():
                yield self.item_indices[source_idx], BatchFailure(self, source_idx, error)
        else:
            for coord, error in self.result.iter_errors():
                row_idx = coord[0]
                yield self.item_indices[row_idx], BatchFailure(self, coord, error)

    @property
    def slot_states_by_item(self) -> dict[int, list[SlotState]]:
        """Map original item index -> list of SlotStates in this step."""
        lookup: dict[int, list[SlotState]] = {}
        if isinstance(self.result, BatchResult):
            for pos, orig in enumerate(self.item_indices):
                lookup[orig] = self.result.slots[pos].state
        else:
            for pos, orig in enumerate(self.item_indices):
                lookup.setdefault(orig, []).extend(s.state for s in self.result.rows[pos].slots)
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
    fatal_error: Exception | None = None

    @property
    def failed_indices(self) -> tuple[int, ...]:
        return tuple(outcome.index for outcome in self.outcomes if outcome.failed)

    @property
    def incomplete_indices(self) -> tuple[int, ...]:
        return tuple(outcome.index for outcome in self.outcomes if outcome.incomplete)

    @property
    def upstream_failed_indices(self) -> tuple[int, ...]:
        return tuple(outcome.index for outcome in self.outcomes if outcome.upstream_failed)

    @property
    def filtered_indices(self) -> tuple[int, ...]:
        return tuple(outcome.index for outcome in self.outcomes if outcome.filtered)

    @property
    def succeeded_indices(self) -> tuple[int, ...]:
        return tuple(outcome.index for outcome in self.outcomes if outcome.succeeded)

    @property
    def status_counts(self) -> Mapping[str, int]:
        return {
            "total": len(self.outcomes),
            "succeeded": sum(outcome.succeeded for outcome in self.outcomes),
            "failed": sum(outcome.failed for outcome in self.outcomes),
            "upstream_failed": sum(outcome.upstream_failed for outcome in self.outcomes),
            "filtered": sum(outcome.filtered for outcome in self.outcomes),
            "incomplete": sum(outcome.incomplete for outcome in self.outcomes),
        }


@dataclass(slots=True)
class BatchRun(Generic[T]):
    """Atomic ledger of batch steps; derives outcomes directly from step results."""

    original_items: Sequence[T]
    _steps: list[BatchStep[Any]] = field(default_factory=list, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _aborted: bool = field(default=False, init=False, repr=False)
    _fatal_error: Exception | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.original_items = tuple(self.original_items)

    def __enter__(self) -> BatchRun[T]:
        self._ensure_open()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool:
        if exc_val is not None:
            if isinstance(exc_val, Exception):
                if not self._closed:
                    self.abort(exc_val)
                else:
                    self._aborted = True
                    self._fatal_error = exc_val
                return True
            return False

        if not self._closed:
            self.finish()
        return False

    @property
    def steps(self) -> tuple[BatchStep[Any], ...]:
        return tuple(self._steps)

    @property
    def fatal_error(self) -> Exception | None:
        return self._fatal_error

    @property
    def report(self) -> BatchReport[T]:
        return self._build_report()

    def failures_by_item(self) -> list[list[BatchFailure]]:
        """Collects failures from all steps"""
        failures_by_item = [[] for _ in self.original_items]
        for step in self._steps:
            for orig_idx, failure in step.iter_failures():
                failures_by_item[orig_idx].append(failure)
        return failures_by_item

    @property
    def outcomes(self) -> tuple[BatchOutcome[T], ...]:
        """Derive the final status and accumulated failures for each original item across all steps."""
        failures_by_item = self.failures_by_item()
        terminal_states = self._steps[-1].slot_states_by_item if self._steps else {}

        values = []
        for idx, item in enumerate(self.original_items):
            failures = tuple(failures_by_item[idx])
            states = terminal_states.get(idx)

            if failures:
                status = BatchStatus.FAILED
            elif not self._closed or self._aborted:
                status = BatchStatus.INCOMPLETE
            elif states is None:
                status = BatchStatus.SUCCEEDED if not self._steps else BatchStatus.FILTERED
            elif any(s is SlotState.UPSTREAM_FAILED for s in states):
                status = BatchStatus.UPSTREAM_FAILED
            elif all(s is SlotState.FILTERED for s in states): # intentional partial writes are successes
                status = BatchStatus.FILTERED
            else:
                status = BatchStatus.SUCCEEDED

            values.append(BatchOutcome(item, idx, failures, status))
        return tuple(values)

    def _build_report(self) -> BatchReport[T]:
        outcomes = self.outcomes
        if self._aborted or any(outcome.failed for outcome in outcomes):
            status = BatchStatus.FAILED
        elif not self._closed or any(outcome.incomplete for outcome in outcomes):
            status = BatchStatus.INCOMPLETE
        elif all(outcome.filtered for outcome in outcomes) and len(outcomes) > 0:
            status = BatchStatus.FILTERED
        elif all(outcome.upstream_failed for outcome in outcomes) and len(outcomes) > 0:
            status = BatchStatus.UPSTREAM_FAILED
        else:
            status = BatchStatus.SUCCEEDED
        return BatchReport(outcomes, self.steps, status, self._fatal_error)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("This BatchRun is closed.")

    def record(
        self, name: str, result: RecordedResult, *, item_indices: Sequence[int] | None = None, for_items: Sequence[T] | None = None
    ) -> RecordedResult:
        """Atomically record a step into the ledger and return the result."""
        indices = self._validate_record_inputs(result, item_indices, for_items)
        self._steps.append(BatchStep(name, len(self._steps), result, indices))
        return result

    def _validate_record_inputs(
        self, result: BatchResultType, item_indices: Sequence[int] | None, for_items: Sequence[T] | None
    ) -> tuple[int, ...]:
        self._ensure_open()
        source_count = len(result.slots) if isinstance(result, BatchResult) else len(result.rows)

        if item_indices is not None and for_items is not None:
            raise ValueError("Specify either item_indices or for_items, not both.")

        if for_items is not None:
            if len(for_items) != source_count:
                raise ValueError("for_items length must match result slots or rows.")
            return self._resolve_items_by_key(self.original_items, for_items)
        elif item_indices is not None:
            indices = tuple(item_indices)
            if len(indices) != source_count:
                raise ValueError("item_indices length must match result slots or rows.")
            if any(not isinstance(idx, int) or idx < 0 or idx >= len(self.original_items) for idx in indices):
                raise IndexError("item_indices contains an original-item index out of bounds.")
            return indices
        else:
            if source_count != len(self.original_items):
                raise ValueError("Default item_indices requires one slot/row per original item.")
            return tuple(range(source_count))

    def _resolve_items_by_key(self, original_items: Sequence[T], for_items: Sequence[T]) -> tuple[int, ...]:
        """O(N) FIFO resolution using hashable keys to preserve duplicate safety."""
        lookup: dict[Any, deque[int]] = {}
        for idx, item in enumerate(original_items):
            key = self._make_item_key(item)
            lookup.setdefault(key, deque()).append(idx)

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

    def finish(self) -> BatchReport[T]:
        self._ensure_open()
        self._closed = True
        return self.report

    def abort(self, exception: Exception) -> BatchReport[T]:
        self._ensure_open()
        self._closed = True
        self._aborted = True
        self._fatal_error = exception
        return self.report