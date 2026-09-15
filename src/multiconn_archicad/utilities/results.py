from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, TypeAlias, TypeVar, cast
from enum import Enum

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
        projected = tuple(
            tuple(BatchSlot.from_raw(next(raw_iter), accessor=accessor) for _ in range(row_length))
            if slot.is_success
            else tuple(BatchSlot.skipped() for _ in range(row_length))
            for slot in self.slots
        )
        return BatchResult2D(projected, (row_length,) * len(self.slots))

    def raise_for_errors(self, operation_name: str = "Batch operation") -> None:
        if self.has_errors:
            lines = "\n".join(f"  - [{index}]: {error}" for index, error in self.iter_errors())
            raise BatchOperationError(
                f"{operation_name} failed with {self.total_errors} error(s):\n{lines}", result=self
            )


@dataclass(frozen=True, slots=True)
class BatchResult2D(Generic[T]):
    """A ragged or regular 2D result preserving row and cell states."""

    rows: tuple[tuple[BatchSlot[T], ...], ...]
    row_lengths: tuple[int, ...]
    row_errors: tuple[BatchError | None, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        rows = tuple(tuple(row) for row in self.rows)
        row_lengths = tuple(self.row_lengths)
        row_errors = tuple(self.row_errors) if self.row_errors else (None,) * len(rows)

        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "row_lengths", row_lengths)
        object.__setattr__(self, "row_errors", row_errors)

        if len(rows) != len(row_lengths) or len(rows) != len(row_errors):
            raise ValueError("rows, row_lengths, and row_errors must all have the same length.")

        for idx, (row, length, error) in enumerate(zip(rows, row_lengths, row_errors)):
            if length < 0:
                raise ValueError(f"Row {idx} length must be non-negative.")
            if len(row) != length:
                raise ValueError(f"Row {idx} slot count ({len(row)}) does not match expected length ({length}).")
            if error is not None:
                if length == 0:
                    raise ValueError(f"Row {idx} has a whole-row error and requires a positive row length.")
                if any(slot.error is not error for slot in row):
                    raise ValueError(f"Every cell in failed Row {idx} must reference the row error.")

    @classmethod
    def from_rows(
            cls, raw_rows: Sequence[Any],
            *,
            row_lengths: Sequence[int] | None = None,
            accessor: Callable[[Any], T] | None = None,
    ) -> BatchResult2D[T]:
        lengths = cls._infer_row_lengths(raw_rows, row_lengths)

        parsed = [
            cls._parse_row(idx, raw_row, length, accessor)
            for idx, (raw_row, length) in enumerate(zip(raw_rows, lengths))
        ]

        rows, row_errors = zip(*parsed) if parsed else ((), ())
        return cls(tuple(rows), lengths, tuple(row_errors))

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

    @staticmethod
    def _parse_row(
            index: int, raw_row: Any, expected_len: int, accessor: Callable[[Any], T] | None
    ) -> tuple[tuple[BatchSlot[T], ...], BatchError | None]:
        """Parse a single raw row (or whole-row API error) into slots and optional row error."""
        # 1. Whole-row API failure
        if (row_error := normalize_error(raw_row)) is not None:
            if expected_len <= 0:
                raise ValueError(f"Row {index} has an API error and requires an explicit positive row length.")
            return tuple(BatchSlot.failure(row_error) for _ in range(expected_len)), row_error

        # 2. Sequence validation
        if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)):
            raise TypeError(f"Row {index} must be a sequence or a typed API error.")
        if len(raw_row) != expected_len:
            raise ValueError(f"Row {index} length ({len(raw_row)}) does not match expected ({expected_len}).")

        # 3. Successful row cells
        row_slots = tuple(BatchSlot.from_raw(item, accessor=accessor) for item in raw_row)
        return row_slots, None

    @property
    def has_errors(self) -> bool:
        return any(slot.is_error for row in self.rows for slot in row)

    @property
    def has_skipped(self) -> bool:
        return any(slot.is_skipped for row in self.rows for slot in row)

    @property
    def is_all_success(self) -> bool:
        return len(self.rows) > 0 and all(slot.is_success for row in self.rows for slot in row)

    def _iter_flattened_cells(self, *, successes_only: bool) -> Iterator[tuple[ValueCoordinate, BatchSlot[T]]]:
        for row_index, row in enumerate(self.rows):
            for cell_index, slot in enumerate(row):
                if successes_only and not slot.is_success:
                    continue
                yield (row_index, cell_index), slot

    def iter_successes(self) -> Iterator[tuple[ValueCoordinate, T]]:
        for coordinate, slot in self._iter_flattened_cells(successes_only=True):
            yield coordinate, slot.success_value

    def iter_errors(self) -> Iterator[tuple[ErrorCoordinate, BatchError]]:
        for row_index, row in enumerate(self.rows):
            for cell_index, slot in enumerate(row):
                if slot.is_error and slot.error is not None:
                    yield (row_index, cell_index), slot.error

    def iter_skipped(self) -> Iterator[tuple[int, int]]:
        for row_index, row in enumerate(self.rows):
            for cell_index, slot in enumerate(row):
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
        return tuple(tuple(slot.item_val() for slot in row) for row in self.rows)

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
        slots: list[BatchSlot[tuple[T, ...]]] = []
        for index, (row, row_error) in enumerate(zip(self.rows, self.row_errors)):
            errors = [row_error] if row_error is not None else [slot.error for slot in row if slot.is_error and slot.error is not None]
            if errors:
                slots.append(BatchSlot.failure(BatchError.aggregate(cast(list[BatchError], errors), context=f"Row {index}")))
            elif any(slot.is_skipped for slot in row):
                slots.append(BatchSlot.skipped())
            else:
                slots.append(BatchSlot.success(tuple(slot.success_value for slot in row)))

        return BatchResult(tuple(slots))

    def row_result(self) -> BatchResult[tuple[T | BatchError | None, ...]]:
        return BatchResult(
            tuple(
                BatchSlot.failure(error) if error is not None else BatchSlot.success(items)
                for items, error in zip(self.items, self.row_errors)
            )
        )

    def map(self, fn: Callable[[T], U]) -> BatchResult2D[U]:
        mapped_rows: list[tuple[BatchSlot[U], ...]] = []
        for row in self.rows:
            mapped_row: list[BatchSlot[U]] = []
            for slot in row:
                mapped_row.append(slot.map(fn))
            mapped_rows.append(tuple(mapped_row))

        return BatchResult2D(tuple(mapped_rows), self.row_lengths, self.row_errors)

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        """Project raw flat items onto successful cell coordinates, marking others SKIPPED."""
        raw_iter = _validate_raw_count(len(self.successes), raw_items)
        projected = tuple(
            tuple(_project_slot(slot, raw_iter, accessor) for slot in row)
            for row in self.rows
        )
        return BatchResult2D(projected, self.row_lengths)

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