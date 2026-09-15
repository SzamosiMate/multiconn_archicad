from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
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


def _project_slot(source_slot: BatchSlot[Any], raw_iter: Iterator[Any], accessor: Callable[[Any], U] | None) -> BatchSlot[U]:
    """If source succeeded, consume next raw item; otherwise emit a SKIPPED slot."""
    if source_slot.is_success:
        return BatchSlot.from_raw(next(raw_iter), accessor=accessor)
    return BatchSlot.skipped()


def _validate_raw_count(expected: int, raw_items: Sequence[Any]) -> Iterator[Any]:
    if len(raw_items) != expected:
        raise ValueError(f"Expected {expected} items to match source, got {len(raw_items)}.")
    return iter(raw_items)


class SlotState(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class BatchSlot(Generic[T]):
    """An immutable slot representing a cell's outcome."""

    state: SlotState
    value: T | None = None
    error: BatchError | None = None

    def __post_init__(self) -> None:
        match self.state:
            case SlotState.SUCCESS:
                if self.error is not None:
                    raise ValueError("A SUCCESS slot cannot contain an error.")
            case SlotState.ERROR:
                if self.error is None:
                    raise ValueError("An ERROR slot must contain a BatchError.")
            case SlotState.SKIPPED:
                if self.value is not None or self.error is not None:
                    raise ValueError("A SKIPPED slot cannot contain a value or error.")

    @classmethod
    def success(cls, value: T) -> BatchSlot[T]:
        return cls(state=SlotState.SUCCESS, value=value)

    @classmethod
    def failure(cls, error: BatchError) -> BatchSlot[T]:
        return cls(state=SlotState.ERROR, error=error)

    @classmethod
    def skipped(cls) -> BatchSlot[T]:
        return cls(state=SlotState.SKIPPED)

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
    def is_skipped(self) -> bool:
        return self.state is SlotState.SKIPPED

    @property
    def success_value(self) -> T:
        if self.state is not SlotState.SUCCESS:
            raise ValueError(f"Slot in state {self.state.value!r} has no successful value.")
        return cast(T, self.value)

    def item_val(self) -> T | BatchError | None:
        match self.state:
            case SlotState.SUCCESS:
                return self.success_value
            case SlotState.ERROR:
                return self.error
            case SlotState.SKIPPED:
                return None

    def map(self, fn: Callable[[T], U]) -> BatchSlot[U]:
        match self.state:
            case SlotState.SUCCESS:
                return BatchSlot.success(fn(self.success_value))
            case SlotState.SKIPPED:
                return BatchSlot.skipped()
            case SlotState.ERROR:
                return BatchSlot.failure(cast(BatchError, self.error))


@dataclass(frozen=True, slots=True)
class BatchResult(Generic[T]):
    """An immutable one-dimensional result with integer-indexed slots."""

    slots: tuple[BatchSlot[T], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))

    @classmethod
    def from_items(cls, raw_items: Sequence[Any], *, accessor: Callable[[Any], T] | None = None) -> BatchResult[T]:
        return cls(tuple(BatchSlot.from_raw(item, accessor=accessor) for item in raw_items))

    @property
    def items(self) -> tuple[T | BatchError | None, ...]:
        """Return values for successes, errors for failures, and None for skipped slots."""
        return tuple(slot.item_val() for slot in self.slots)

    @property
    def errors(self) -> tuple[BatchError, ...]:
        return tuple(slot.error for slot in self.slots if slot.is_error and slot.error is not None)

    @property
    def all_errors(self) -> tuple[BatchError, ...]:
        return self.errors

    @property
    def successes(self) -> list[T]:
        return [slot.success_value for slot in self.slots if slot.is_success]

    def iter_successes(self) -> Iterator[tuple[int, T]]:
        for index, slot in enumerate(self.slots):
            if slot.is_success:
                yield index, slot.success_value

    def iter_errors(self) -> Iterator[tuple[int, BatchError]]:
        for index, slot in enumerate(self.slots):
            if slot.is_error and slot.error is not None:
                yield index, slot.error

    def iter_skipped(self) -> Iterator[int]:
        for index, slot in enumerate(self.slots):
            if slot.is_skipped:
                yield index

    @property
    def success_indices(self) -> tuple[int, ...]:
        return tuple(index for index, _ in self.iter_successes())

    @property
    def failure_indices(self) -> tuple[int, ...]:
        return tuple(index for index, _ in self.iter_errors())

    @property
    def skipped_indices(self) -> tuple[int, ...]:
        return tuple(self.iter_skipped())

    @property
    def has_errors(self) -> bool:
        return any(slot.is_error for slot in self.slots)

    @property
    def has_skipped(self) -> bool:
        return any(slot.is_skipped for slot in self.slots)

    @property
    def is_all_success(self) -> bool:
        return len(self.slots) > 0 and all(slot.is_success for slot in self.slots)

    @property
    def total_errors(self) -> int:
        return len(self.errors)

    def map(self, fn: Callable[[T], U]) -> BatchResult[U]:
        return BatchResult(tuple(s.map(fn) for s in self.slots))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult[U]:
        """Re-inflate flat items into this 1D shape, marking unattempted slots SKIPPED."""
        raw_iter = _validate_raw_count(len(self.successes), raw_items)
        return BatchResult(tuple(_project_slot(slot, raw_iter, accessor) for slot in self.slots))

    def project_rows(
        self, raw_items: Sequence[Any], row_length: int, *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        """Re-inflate flat items into an N x row_length matrix based on row success."""
        if row_length < 0:
            raise ValueError("row_length must be non-negative.")
        raw_iter = _validate_raw_count(len(self.successes) * row_length, raw_items)
        projected_rows = tuple(
            BatchRow(tuple(BatchSlot.from_raw(next(raw_iter), accessor=accessor) for _ in range(row_length)))
            if slot.is_success
            else BatchRow(tuple(BatchSlot.skipped() for _ in range(row_length)))
            for slot in self.slots
        )
        return BatchResult2D(projected_rows)

    def raise_for_errors(self, operation_name: str = "Batch operation") -> None:
        if self.has_errors:
            lines = "\n".join(f"  - [{index}]: {error}" for index, error in self.iter_errors())
            raise BatchOperationError(
                f"{operation_name} failed with {self.total_errors} error(s):\n{lines}", result=self
            )


@dataclass(frozen=True, slots=True)
class BatchRow(Generic[T]):
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
        """Parse a single raw row (or whole-row API error) into slots and an optional row error."""
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

    @property
    def is_all_success(self) -> bool:
        return self.error is None and len(self.slots) > 0 and all(slot.is_success for slot in self.slots)

    @property
    def has_errors(self) -> bool:
        return self.error is not None or any(slot.is_error for slot in self.slots)

    @property
    def is_skipped(self) -> bool:
        return len(self.slots) > 0 and all(slot.is_skipped for slot in self.slots)

    @property
    def has_skipped(self) -> bool:
        return any(slot.is_skipped for slot in self.slots)

    @property
    def items(self) -> tuple[T | BatchError | None, ...]:
        return tuple(slot.item_val() for slot in self.slots)

    @property
    def success_values(self) -> tuple[T, ...]:
        return tuple(slot.success_value for slot in self.slots if slot.is_success)

    @property
    def errors(self) -> tuple[BatchError, ...]:
        return tuple(slot.error for slot in self.slots if slot.is_error and slot.error is not None)

    def map(self, fn: Callable[[T], U]) -> BatchRow[U]:
        return BatchRow(tuple(slot.map(fn) for slot in self.slots), error=self.error)

    def aggregate(self, context: str = "Row") -> BatchSlot[tuple[T, ...]]:
        """Aggregate row into a single slot: failure if any error, skipped if skipped, else success tuple."""
        errors = (
            [self.error]
            if self.error is not None
            else [slot.error for slot in self.slots if slot.is_error and slot.error is not None]
        )
        if errors:
            return BatchSlot.failure(BatchError.aggregate(cast(list[BatchError], errors), context=context))
        if any(slot.is_skipped for slot in self.slots):
            return BatchSlot.skipped()
        return BatchSlot.success(self.success_values)


@dataclass(frozen=True, slots=True)
class BatchResult2D(Generic[T]):
    """A ragged or regular 2D result preserving row and cell states."""

    rows: tuple[BatchRow[T], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))

    @property
    def row_lengths(self) -> tuple[int, ...]:
        return tuple(len(row) for row in self.rows)

    @property
    def row_errors(self) -> tuple[BatchError | None, ...]:
        return tuple(row.error for row in self.rows)

    @classmethod
    def from_rows(
        cls,
        raw_rows: Sequence[Any],
        *,
        row_lengths: Sequence[int] | None = None,
        accessor: Callable[[Any], T] | None = None,
    ) -> BatchResult2D[T]:
        lengths = cls._infer_row_lengths(raw_rows, row_lengths)
        rows = tuple(
            BatchRow.from_raw(raw_row, length, accessor=accessor, index=idx)
            for idx, (raw_row, length) in enumerate(zip(raw_rows, lengths))
        )
        return cls(rows)

    @staticmethod
    def _infer_row_lengths(raw_rows: Sequence[Any], row_lengths: Sequence[int] | None) -> tuple[int, ...]:
        if row_lengths is None:
            return tuple(
                len(row) if isinstance(row, Sequence) and not isinstance(row, (str, bytes)) else 0
                for row in raw_rows
            )
        lengths = tuple(row_lengths)
        if len(raw_rows) != len(lengths):
            raise ValueError("raw_rows and row_lengths must have the same length.")
        return lengths

    @property
    def has_errors(self) -> bool:
        return any(row.has_errors for row in self.rows)

    @property
    def has_skipped(self) -> bool:
        return any(row.has_skipped for row in self.rows)

    @property
    def is_all_success(self) -> bool:
        return len(self.rows) > 0 and all(row.is_all_success for row in self.rows)

    def _iter_flattened_cells(self, *, successes_only: bool) -> Iterator[tuple[ValueCoordinate, BatchSlot[T]]]:
        for row_index, row in enumerate(self.rows):
            for cell_index, slot in enumerate(row.slots):
                if successes_only and not slot.is_success:
                    continue
                yield (row_index, cell_index), slot

    def iter_successes(self) -> Iterator[tuple[ValueCoordinate, T]]:
        for coordinate, slot in self._iter_flattened_cells(successes_only=True):
            yield coordinate, slot.success_value

    def iter_errors(self) -> Iterator[tuple[ErrorCoordinate, BatchError]]:
        for row_index, row in enumerate(self.rows):
            for cell_index, slot in enumerate(row.slots):
                if slot.is_error and slot.error is not None:
                    yield (row_index, cell_index), slot.error

    def iter_skipped(self) -> Iterator[tuple[int, int]]:
        for row_index, row in enumerate(self.rows):
            for cell_index, slot in enumerate(row.slots):
                if slot.is_skipped:
                    yield row_index, cell_index

    @property
    def errors(self) -> tuple[BatchError, ...]:
        return tuple(error for _, error in self.iter_errors())

    @property
    def all_errors(self) -> tuple[BatchError, ...]:
        return self.errors

    @property
    def total_errors(self) -> int:
        return len(self.errors)

    @property
    def items(self) -> tuple[tuple[T | BatchError | None, ...], ...]:
        return tuple(row.items for row in self.rows)

    @property
    def successes(self) -> list[T]:
        return [slot.success_value for _, slot in self._iter_flattened_cells(successes_only=True)]

    @property
    def success_indices(self) -> tuple[ValueCoordinate, ...]:
        return tuple(coordinate for coordinate, _ in self._iter_flattened_cells(successes_only=True))

    @property
    def failure_indices(self) -> tuple[ValueCoordinate, ...]:
        return tuple(coordinate for coordinate, _ in self.iter_errors())

    @property
    def skipped_indices(self) -> tuple[tuple[int, int], ...]:
        return tuple(self.iter_skipped())

    def aggregate_rows(self) -> BatchResult[tuple[T, ...]]:
        """Return complete rows, replacing any failed row with an aggregate error, and skipped rows with SKIPPED."""
        return BatchResult(tuple(row.aggregate(context=f"Row {index}") for index, row in enumerate(self.rows)))

    def row_result(self) -> BatchResult[tuple[T | BatchError | None, ...]]:
        return BatchResult(
            tuple(
                BatchSlot.failure(row.error) if row.error is not None else BatchSlot.success(row.items)
                for row in self.rows
            )
        )

    def map(self, fn: Callable[[T], U]) -> BatchResult2D[U]:
        return BatchResult2D(tuple(row.map(fn) for row in self.rows))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        """Project raw flat items onto successful cell coordinates, marking others SKIPPED."""
        raw_iter = _validate_raw_count(len(self.successes), raw_items)
        projected = tuple(
            BatchRow(tuple(_project_slot(slot, raw_iter, accessor) for slot in row.slots))
            for row in self.rows
        )
        return BatchResult2D(projected)

    def flatten(self) -> BatchResult[T]:
        """Flatten cells row by row, from left to right, retaining errors."""
        return BatchResult(tuple(slot for _, slot in self._iter_flattened_cells(successes_only=False)))

    def raise_for_errors(self, operation_name: str = "Batch operation") -> None:
        if self.has_errors:
            lines = "\n".join(
                f"  - [{', '.join(map(str, coordinate))}]: {error}" for coordinate, error in self.iter_errors()
            )
            raise BatchOperationError(
                f"{operation_name} failed with {self.total_errors} error(s):\n{lines}", result=self
            )