from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Generic, TypeAlias, TypeVar, cast

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir

T = TypeVar("T")
U = TypeVar("U")
ErrorType: TypeAlias = tapir.Error | official.Error
ValueCoordinate: TypeAlias = tuple[int, int]
ErrorCoordinate: TypeAlias = ValueCoordinate
BatchCoordinate: TypeAlias = int | ValueCoordinate

ERROR_CONTAINER_MODELS = (
    tapir.FailedExecutionResult,
    tapir.ErrorItem,
    official.FailedExecutionResult,
    official.ErrorItem,
)


@dataclass(frozen=True, slots=True)
class BatchError:
    error: ErrorType
    causes: tuple[BatchError, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "causes", tuple(self.causes))

    @classmethod
    def from_message(cls, message: str, *, code: int | str = 0) -> BatchError:
        """Create a BatchError directly from a message string and optional code."""
        return cls(tapir.Error(code=code, message=message))

    @property
    def code(self) -> int | str:
        return self.error.code

    @property
    def message(self) -> str:
        return self.error.message

    @classmethod
    def aggregate(cls, errors: Sequence[BatchError], *, context: str = "Batch") -> BatchError:
        """Create one summary error while retaining the original errors as causes."""
        causes = tuple(errors)
        if not causes:
            raise ValueError("Cannot aggregate an empty error sequence.")
        summary = "; ".join(f"[{error.code}] {error.message}" for error in causes)
        return cls(
            tapir.Error(code=-1, message=f"{context} contains {len(causes)} error(s): {summary}"),
            causes=causes,
        )

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def extract_error(item: Any) -> ErrorType | None:
    if isinstance(item, BatchError):
        return item.error
    if isinstance(item, ERROR_CONTAINER_MODELS):
        return item.error
    return item if isinstance(item, (tapir.Error, official.Error)) else None


def normalize_error(item: Any) -> BatchError | None:
    if isinstance(item, BatchError):
        return item
    error = extract_error(item)
    return BatchError(error) if error is not None else None


def is_row_sequence(item: Any) -> bool:
    """Return True if item is a row container (list, tuple, etc.), excluding scalar text/bytes."""
    return isinstance(item, Sequence) and not isinstance(item, (str, bytes))


def _project_slot(
    source_slot: BatchSlot[Any], raw_iter: Iterator[Any], accessor: Callable[[Any], U] | None
) -> BatchSlot[U]:
    """If source succeeded, consume next raw item; otherwise propagate failure or filter state."""
    if source_slot.is_success:
        return BatchSlot.from_raw(next(raw_iter), accessor=accessor)
    if source_slot.is_error or source_slot.is_upstream_failed:
        return BatchSlot.upstream_failed()
    return BatchSlot.filtered()


def _validate_raw_count(expected: int, raw_items: Sequence[Any]) -> Iterator[Any]:
    if len(raw_items) != expected:
        raise ValueError(f"Expected {expected} items to match source, got {len(raw_items)}.")
    return iter(raw_items)


class SlotState(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UPSTREAM_FAILED = "upstream_failed"
    FILTERED = "filtered"


@dataclass(frozen=True, slots=True)
class BatchSlot(Generic[T]):
    """An immutable slot representing a cell's outcome."""

    state: SlotState
    _value: T | None = None
    _error: BatchError | None = None

    def __post_init__(self) -> None:
        match self.state:
            case SlotState.SUCCESS:
                if self._error is not None:
                    raise ValueError("A SUCCESS slot cannot contain an error.")
            case SlotState.ERROR:
                if self._error is None:
                    raise ValueError("An ERROR slot must contain a BatchError.")
            case SlotState.UPSTREAM_FAILED | SlotState.FILTERED:
                if self._value is not None or self._error is not None:
                    raise ValueError(f"A {self.state.name} slot cannot contain a value or error.")

    @classmethod
    def success(cls, value: T) -> BatchSlot[T]:
        return cls(state=SlotState.SUCCESS, _value=value)

    @classmethod
    def failure(cls, error: BatchError | str, *, code: int = 0) -> BatchSlot[T]:
        if isinstance(error, BatchError):
            return cls(state=SlotState.ERROR, _error=error)
        else:
            return cls(state=SlotState.ERROR, _error=BatchError.from_message(error, code=code))

    @classmethod
    def upstream_failed(cls) -> BatchSlot[T]:
        return cls(state=SlotState.UPSTREAM_FAILED)

    @classmethod
    def filtered(cls) -> BatchSlot[T]:
        return cls(state=SlotState.FILTERED)

    @classmethod
    def from_raw(cls, raw: Any, *, accessor: Callable[[Any], T] | None = None) -> BatchSlot[T]:
        """Create a SUCCESS or ERROR slot by normalizing raw API output."""
        if (failure := normalize_error(raw)) is not None:
            return cls.failure(failure)
        return cls.success(accessor(raw) if accessor else raw)

    @property
    def is_success(self) -> bool:
        return self.state is SlotState.SUCCESS

    @property
    def is_error(self) -> bool:
        return self.state is SlotState.ERROR

    @property
    def is_upstream_failed(self) -> bool:
        return self.state is SlotState.UPSTREAM_FAILED

    @property
    def is_filtered(self) -> bool:
        return self.state is SlotState.FILTERED

    @property
    def value(self) -> T:
        if self.state is not SlotState.SUCCESS:
            raise ValueError(f"Slot in state {self.state!r} has no successful value.")
        return cast(T, self._value)

    @property
    def error(self) -> BatchError:
        if self.state is not SlotState.ERROR:
            raise ValueError(f"Slot in state {self.state!r} has no error.")
        return cast(BatchError, self._error)

    def item_val(self) -> T | BatchError | None:
        match self.state:
            case SlotState.SUCCESS:
                return self.value
            case SlotState.ERROR:
                return self.error
            case SlotState.UPSTREAM_FAILED | SlotState.FILTERED:
                return None

    def map(self, fn: Callable[[T], U]) -> BatchSlot[U]:
        match self.state:
            case SlotState.SUCCESS:
                return BatchSlot.success(fn(self.value))
            case SlotState.UPSTREAM_FAILED:
                return BatchSlot.upstream_failed()
            case SlotState.FILTERED:
                return BatchSlot.filtered()
            case SlotState.ERROR:
                return BatchSlot.failure(self.error)


class BatchResultBase(ABC, Generic[T]):
    """Abstract base container providing shared state-driven template methods."""

    __slots__ = ()

    @abstractmethod
    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[BatchCoordinate, BatchSlot[T]]]:
        """Yield (coordinate, slot) pairs, optionally filtered by state."""
        ...

    @abstractmethod
    def count(self, state: SlotState | None = None) -> int:
        """Return total slots if state is None, or count of slots matching state."""
        ...

    def iter_indices(self, state: SlotState) -> Iterator[BatchCoordinate]:
        for coord, _ in self.iter_slots(state):
            yield coord

    def indices(self, state: SlotState) -> tuple[BatchCoordinate, ...]:
        return tuple(self.iter_indices(state))

    def iter_successes(self) -> Iterator[tuple[BatchCoordinate, T]]:
        for coord, slot in self.iter_slots(SlotState.SUCCESS):
            yield coord, slot.value

    def iter_errors(self) -> Iterator[tuple[BatchCoordinate, BatchError]]:
        for coord, slot in self.iter_slots(SlotState.ERROR):
            yield coord, slot.error

    def has(self, state: SlotState) -> bool:
        return next(self.iter_slots(state), None) is not None

    def is_all(self, state: SlotState) -> bool:
        return self.count() > 0 and all(slot.state is state for _, slot in self.iter_slots())

    @property
    def items(self) -> tuple[T | BatchError | None, ...]:
        """Flat tuple of values for successes, BatchError for errors, and None for skipped slots."""
        return tuple(slot.item_val() for _, slot in self.iter_slots())

    @property
    def successes(self) -> list[T]:
        """Flat list of all successful payload values."""
        return [val for _, val in self.iter_successes()]

    @property
    def errors(self) -> tuple[BatchError, ...]:
        """Flat tuple of all BatchError payloads."""
        return tuple(error for _, error in self.iter_errors())

    @staticmethod
    def _format_coord(coord: Any) -> str:
        return ", ".join(map(str, coord)) if isinstance(coord, tuple) else str(coord)

    def raise_for_errors(self, operation_name: str = "Batch operation") -> None:
        if self.has(SlotState.ERROR):
            lines = "\n".join(
                f"  - [{self._format_coord(coord)}]: {error}" for coord, error in self.iter_errors()
            )
            raise BatchOperationError(
                f"{operation_name} failed with {self.count(SlotState.ERROR)} error(s):\n{lines}",
                result=self,
            )


@dataclass(frozen=True, slots=True)
class BatchResult(BatchResultBase[T]):
    """An immutable one-dimensional result with integer-indexed slots."""

    slots: tuple[BatchSlot[T], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))

    @classmethod
    def from_items(cls, raw_items: Sequence[Any], *, accessor: Callable[[Any], T] | None = None) -> BatchResult[T]:
        return cls(tuple(BatchSlot.from_raw(item, accessor=accessor) for item in raw_items))

    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[int, BatchSlot[T]]]:
        for idx, slot in enumerate(self.slots):
            if state is None or slot.state is state:
                yield idx, slot

    def count(self, state: SlotState | None = None) -> int:
        if state is None:
            return len(self.slots)
        return sum(1 for slot in self.slots if slot.state is state)

    def map(self, fn: Callable[[T], U]) -> BatchResult[U]:
        return BatchResult(tuple(s.map(fn) for s in self.slots))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult[U]:
        """Re-inflate flat items into this 1D shape, preserving failure and filter states."""
        raw_iter = _validate_raw_count(self.count(SlotState.SUCCESS), raw_items)
        return BatchResult(tuple(_project_slot(slot, raw_iter, accessor) for slot in self.slots))

    def project_rows(
        self, raw_items: Sequence[Any], row_length: int, *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        """Re-inflate flat items into an N x row_length matrix based on row success."""
        if row_length < 0:
            raise ValueError("row_length must be non-negative.")
        raw_iter = _validate_raw_count(self.count(SlotState.SUCCESS) * row_length, raw_items)
        projected_rows: list[BatchRow[U]] = []
        for slot in self.slots:
            if slot.is_success:
                projected_rows.append(
                    BatchRow(tuple(BatchSlot.from_raw(next(raw_iter), accessor=accessor) for _ in range(row_length)))
                )
            elif slot.is_upstream_failed or slot.is_error:
                projected_rows.append(BatchRow(tuple(BatchSlot.upstream_failed() for _ in range(row_length))))
            else:
                projected_rows.append(BatchRow(tuple(BatchSlot.filtered() for _ in range(row_length))))

        return BatchResult2D(tuple(projected_rows))


@dataclass(frozen=True, slots=True)
class BatchRow(BatchResultBase[T]):
    """An immutable row container holding ordered cell slots and an optional row error."""

    slots: tuple[BatchSlot[T], ...]
    error: BatchError | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))
        if self.error is not None:
            if len(self.slots) == 0:
                raise ValueError("A row with a whole-row error requires a positive row length.")
            if any(slot.error is not self.error for slot in self.slots):
                raise ValueError("Every cell in a failed row must reference the row error.")

    @classmethod
    def from_raw(
        cls,
        raw_row: Any,
        expected_len: int,
        *,
        accessor: Callable[[Any], T] | None = None,
        index: int | None = None,
    ) -> BatchRow[T]:
        prefix = f"Row {index} " if index is not None else "Row "

        if (row_error := normalize_error(raw_row)) is not None:
            if expected_len <= 0:
                raise ValueError(f"{prefix}has an API error and requires an explicit positive row length.")
            return cls(tuple(BatchSlot.failure(row_error) for _ in range(expected_len)), error=row_error)

        if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)):
            raise TypeError(f"{prefix}must be a sequence or a typed API error.")
        if len(raw_row) != expected_len:
            raise ValueError(f"{prefix}length ({len(raw_row)}) does not match expected ({expected_len}).")

        return cls(tuple(BatchSlot.from_raw(item, accessor=accessor) for item in raw_row))

    def __len__(self) -> int:
        return len(self.slots)

    def __iter__(self) -> Iterator[BatchSlot[T]]:
        return iter(self.slots)

    def __getitem__(self, index: int) -> BatchSlot[T]:
        return self.slots[index]

    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[int, BatchSlot[T]]]:
        for idx, slot in enumerate(self.slots):
            if state is None or slot.state is state:
                yield idx, slot

    def count(self, state: SlotState | None = None) -> int:
        if state is None:
            return len(self.slots)
        return sum(1 for slot in self.slots if slot.state is state)

    def map(self, fn: Callable[[T], U]) -> BatchRow[U]:
        return BatchRow(tuple(slot.map(fn) for slot in self.slots), error=self.error)

    def aggregate(self, context: str = "Row") -> BatchSlot[tuple[T, ...]]:
        """Aggregate row into a single slot."""
        if self.has(SlotState.ERROR):
            errors = [self.error] if self.error is not None else list(self.errors)
            return BatchSlot.failure(BatchError.aggregate(errors, context=context))
        if self.has(SlotState.UPSTREAM_FAILED):
            return BatchSlot.upstream_failed()
        if self.has(SlotState.FILTERED):
            return BatchSlot.filtered()
        return BatchSlot.success(tuple(self.successes))


@dataclass(frozen=True, slots=True)
class BatchResult2D(BatchResultBase[T]):
    """A ragged or regular 2D result preserving row and cell states."""

    rows: tuple[BatchRow[T], ...]

    @property
    def row_lengths(self) -> tuple[int, ...]:
        return tuple(len(row) for row in self.rows)

    @property
    def row_errors(self) -> tuple[BatchError | None, ...]:
        return tuple(row.error for row in self.rows)

    @property
    def row_items(self) -> tuple[tuple[T | BatchError | None, ...], ...]:
        """Row-partitioned items matching the 2D grid structure."""
        return tuple(row.items for row in self.rows)

    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[ValueCoordinate, BatchSlot[T]]]:
        for row_idx, row in enumerate(self.rows):
            for cell_idx, slot in enumerate(row.slots):
                if state is None or slot.state is state:
                    yield (row_idx, cell_idx), slot

    def count(self, state: SlotState | None = None) -> int:
        if state is None:
            return sum(len(row) for row in self.rows)
        return sum(1 for _ in self.iter_slots(state))

    def aggregate_rows(self) -> BatchResult[tuple[T, ...]]:
        """Return complete rows, replacing any failed row with an aggregate error/upstream/filtered slot."""
        return BatchResult(tuple(row.aggregate(context=f"Row {index}") for index, row in enumerate(self.rows)))

    def row_result(self) -> BatchResult[tuple[T | BatchError | None, ...]]:
        return BatchResult(
            tuple(
                BatchSlot.failure(row.error) if row.error is not None else BatchSlot.success(row.items)
                for row in self.rows
            )
        )

    def map(self, fn: Callable[[T], U]) -> BatchResult2D[U]:
        new_rows = tuple(row.map(fn) for row in self.rows)
        return replace(self, rows=new_rows)

    def project_successes(
            self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        raw_iter = _validate_raw_count(self.count(SlotState.SUCCESS), raw_items)
        projected = tuple(
            BatchRow(tuple(_project_slot(slot, raw_iter, accessor) for slot in row.slots))
            for row in self.rows
        )
        return replace(self, rows=projected)

    def flatten(self) -> BatchResult[T]:
        """Flatten cells row by row, from left to right, retaining errors."""
        return BatchResult(tuple(slot for _, slot in self.iter_slots()))


@dataclass(frozen=True, slots=True)
class BatchGrid(BatchResult2D[T]):
    """Rectangular 2D result where every row has identical width."""

    width: int

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be a positive integer.")
        for idx, row in enumerate(self.rows):
            if len(row) != self.width:
                raise ValueError(f"Row {idx} length ({len(row)}) does not match width ({self.width}).")

    @classmethod
    def from_rows(
        cls, raw_rows: Sequence[Any], *, width: int, accessor: Callable[[Any], T] | None = None
    ) -> BatchGrid[T]:
        if width <= 0:
            raise ValueError("width must be a positive integer.")
        rows = tuple(
            BatchRow.from_raw(raw_row, width, accessor=accessor, index=idx)
            for idx, raw_row in enumerate(raw_rows)
        )
        return cls(rows, width=width)

    def map(self, fn: Callable[[T], U]) -> BatchGrid[U]:
        return cast(BatchGrid[U], BatchResult2D.map(self, fn))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchGrid[U]:
        return cast(BatchGrid[U], BatchResult2D.project_successes(self, raw_items, accessor=accessor))


@dataclass(frozen=True, slots=True)
class RaggedBatchResult(BatchResult2D[T]):
    """Ragged 2D result with variable row lengths."""

    @classmethod
    def from_rows(
        cls, raw_rows: Sequence[Any], *, accessor: Callable[[Any], T] | None = None
    ) -> RaggedBatchResult[T]:
        lengths = tuple(len(row) if is_row_sequence(row) else 1 for row in raw_rows)
        rows = tuple(
            BatchRow.from_raw(raw_row, length, accessor=accessor, index=idx)
            for idx, (raw_row, length) in enumerate(zip(raw_rows, lengths))
        )
        return cls(rows)

    def map(self, fn: Callable[[T], U]) -> RaggedBatchResult[U]:
        return cast(RaggedBatchResult[U], BatchResult2D.map(self, fn))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> RaggedBatchResult[U]:
        return cast(RaggedBatchResult[U], BatchResult2D.project_successes(self, raw_items, accessor=accessor))