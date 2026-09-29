"""Represent aligned batch values, errors, and skipped states."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Generic, TypeAlias, TypeVar, cast

from multiconn_archicad.errors import BatchNotFullySuccessfulError, BatchOperationError
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
    """Store an API error and, optionally, the errors summarized by it.

    Attributes:
        error: The normalized Tapir or Official API error.
        causes: Original errors retained when this error summarizes a group.
    """

    error: ErrorType
    causes: tuple[BatchError, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "causes", tuple(self.causes))

    @classmethod
    def from_message(cls, message: str, *, code: int | str = 0) -> BatchError:
        """Create an error from a message and optional code."""
        return cls(tapir.Error(code=code, message=message))

    @property
    def code(self) -> int | str:
        """Return the API error code."""
        return self.error.code

    @property
    def message(self) -> str:
        """Return the API error message."""
        return self.error.message

    @classmethod
    def aggregate(cls, errors: Sequence[BatchError], *, context: str = "Batch") -> BatchError:
        """Summarize errors while retaining them as causes.

        Args:
            errors: Errors to include in the summary.
            context: Name used to describe the failing operation or group.

        Raises:
            ValueError: If ``errors`` is empty.
        """
        causes = tuple(errors)
        if not causes:
            raise ValueError("Cannot aggregate an empty error sequence.")
        summary = "; ".join(f"[{error.code}] {error.message}" for error in causes)
        return cls(
            tapir.Error(code=-1, message=f"{context} contains {len(causes)} error(s): {summary}"),
            causes=causes,
        )

    def __str__(self) -> str:
        """Format the error code and message for display."""
        return f"[{self.code}] {self.message}"


def extract_error(item: Any) -> ErrorType | None:
    """Return the API error contained in a supported error item, if any."""
    if isinstance(item, BatchError):
        return item.error
    if isinstance(item, ERROR_CONTAINER_MODELS):
        return item.error
    return item if isinstance(item, (tapir.Error, official.Error)) else None


def normalize_error(item: Any) -> BatchError | None:
    """Wrap a supported API error as ``BatchError``; return ``None`` otherwise."""
    if isinstance(item, BatchError):
        return item
    error = extract_error(item)
    return BatchError(error) if error is not None else None


def is_row_sequence(item: Any) -> bool:
    """Return whether ``item`` is a non-text sequence suitable for a row."""
    return isinstance(item, Sequence) and not isinstance(item, (str, bytes))


def _project_slot(
    source_slot: BatchSlot[Any], raw_iter: Iterator[Any], accessor: Callable[[Any], U] | None
) -> BatchSlot[U]:
    """Project one successful raw item or propagate a source skip state."""
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
    """Identify whether a result slot succeeded, failed, or was skipped.

    ``UPSTREAM_FAILED`` marks work blocked by an earlier failure; ``FILTERED``
    marks work intentionally excluded from processing.
    """

    SUCCESS = "success"
    ERROR = "error"
    UPSTREAM_FAILED = "upstream_failed"
    FILTERED = "filtered"


@dataclass(frozen=True, slots=True)
class BatchSlot(Generic[T]):
    """Represent one successful value, error, upstream failure, or filter.

    Attributes:
        state: Outcome state for this slot.

    The ``value`` property is available only in the success state; ``error``
    is available only in the error state.
    """

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
        """Create a successful slot containing ``value``."""
        return cls(state=SlotState.SUCCESS, _value=value)

    @classmethod
    def failure(cls, error: BatchError | str, *, code: int = 0) -> BatchSlot[T]:
        """Create an error slot from a batch error or message."""
        if isinstance(error, BatchError):
            return cls(state=SlotState.ERROR, _error=error)
        else:
            return cls(state=SlotState.ERROR, _error=BatchError.from_message(error, code=code))

    @classmethod
    def upstream_failed(cls) -> BatchSlot[T]:
        """Create a slot blocked by an earlier failure."""
        return cls(state=SlotState.UPSTREAM_FAILED)

    @classmethod
    def filtered(cls) -> BatchSlot[T]:
        """Create a slot intentionally excluded from processing."""
        return cls(state=SlotState.FILTERED)

    @classmethod
    def from_raw(cls, raw: Any, *, accessor: Callable[[Any], T] | None = None) -> BatchSlot[T]:
        """Convert raw API output to a success or error slot.

        Args:
            raw: A successful API value or a supported API error item.
            accessor: Optional function that extracts the successful payload.
        """
        if (failure := normalize_error(raw)) is not None:
            return cls.failure(failure)
        return cls.success(accessor(raw) if accessor else raw)

    @property
    def is_success(self) -> bool:
        """Return whether this slot contains a successful value."""
        return self.state is SlotState.SUCCESS

    @property
    def is_error(self) -> bool:
        """Return whether this slot contains an API or batch error."""
        return self.state is SlotState.ERROR

    @property
    def is_upstream_failed(self) -> bool:
        """Return whether an earlier failure blocked this slot."""
        return self.state is SlotState.UPSTREAM_FAILED

    @property
    def is_filtered(self) -> bool:
        """Return whether this slot was intentionally filtered out."""
        return self.state is SlotState.FILTERED

    @property
    def value(self) -> T:
        """Return the successful value.

        Raises:
            ValueError: If this slot is not in the success state.
        """
        if self.state is not SlotState.SUCCESS:
            raise ValueError(f"Slot in state {self.state!r} has no successful value.")
        return cast(T, self._value)

    @property
    def error(self) -> BatchError:
        """Return the error for a failed slot.

        Raises:
            ValueError: If this slot is not in the error state.
        """
        if self.state is not SlotState.ERROR:
            raise ValueError(f"Slot in state {self.state!r} has no error.")
        return cast(BatchError, self._error)

    def item_val(self) -> T | BatchError | None:
        """Return the value, error, or ``None`` for a skipped slot."""
        match self.state:
            case SlotState.SUCCESS:
                return self.value
            case SlotState.ERROR:
                return self.error
            case SlotState.UPSTREAM_FAILED | SlotState.FILTERED:
                return None

    def map(self, fn: Callable[[T], U]) -> BatchSlot[U]:
        """Map the successful value and preserve every non-success state."""
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
    """Provide state-aware operations shared by 1D and 2D results."""

    __slots__ = ()

    @abstractmethod
    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[BatchCoordinate, BatchSlot[T]]]:
        """Yield coordinate and slot pairs, optionally filtered by state.

        A 1D result uses integer coordinates; a 2D result uses ``(row, cell)``.
        """
        ...

    @abstractmethod
    def count(self, state: SlotState | None = None) -> int:
        """Return the total slot count or the count matching ``state``."""
        ...

    def iter_indices(self, state: SlotState) -> Iterator[BatchCoordinate]:
        """Yield coordinates of slots in ``state``."""
        for coord, _ in self.iter_slots(state):
            yield coord

    def indices(self, state: SlotState) -> tuple[BatchCoordinate, ...]:
        """Return coordinates of slots in ``state`` as a tuple."""
        return tuple(self.iter_indices(state))

    def iter_successes(self) -> Iterator[tuple[BatchCoordinate, T]]:
        """Yield coordinates and values for successful slots."""
        for coord, slot in self.iter_slots(SlotState.SUCCESS):
            yield coord, slot.value

    def iter_errors(self) -> Iterator[tuple[BatchCoordinate, BatchError]]:
        """Yield coordinates and errors for failed slots."""
        for coord, slot in self.iter_slots(SlotState.ERROR):
            yield coord, slot.error

    def has(self, state: SlotState) -> bool:
        """Return whether at least one slot has ``state``."""
        return next(self.iter_slots(state), None) is not None

    def is_all(self, state: SlotState) -> bool:
        """Return whether every slot has ``state``; empty results return false."""
        return self.count() > 0 and all(slot.state is state for _, slot in self.iter_slots())

    @property
    def items(self) -> tuple[T | BatchError | None, ...]:
        """Return flat values, errors, or ``None`` for skipped slots."""
        return tuple(slot.item_val() for _, slot in self.iter_slots())

    @property
    def successes(self) -> list[T]:
        """Return successful payloads in result iteration order."""
        return [val for _, val in self.iter_successes()]

    @property
    def errors(self) -> tuple[BatchError, ...]:
        """Return errors in result iteration order."""
        return tuple(error for _, error in self.iter_errors())

    def raise_for_errors(self, operation_name: str = "Batch operation") -> None:
        """Raise if any slot is an error; filtered and upstream slots are ignored.

        Args:
            operation_name: Name included in the raised exception.

        Raises:
            BatchOperationError: If at least one slot is in the error state.
        """
        if self.has(SlotState.ERROR):
            raise BatchOperationError(operation_name, self)

    def raise_for_non_success(self, operation_name: str = "Batch operation") -> None:
        """Raise if any slot is not successful; an empty result passes.

        Args:
            operation_name: Name included in the raised exception.

        Raises:
            BatchNotFullySuccessfulError: If any slot is an error, upstream
                failure, or filtered slot.
        """
        if all(slot.is_success for _, slot in self.iter_slots()):
            return
        raise BatchNotFullySuccessfulError(operation_name, self)


@dataclass(frozen=True, slots=True)
class BatchResult(BatchResultBase[T]):
    """Store an immutable 1D result aligned to integer input positions.

    Attributes:
        slots: One slot for each input item, in input order.
    """

    slots: tuple[BatchSlot[T], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", tuple(self.slots))

    @classmethod
    def from_items(cls, raw_items: Sequence[Any], *, accessor: Callable[[Any], T] | None = None) -> BatchResult[T]:
        """Convert raw items to slots in input order."""
        return cls(tuple(BatchSlot.from_raw(item, accessor=accessor) for item in raw_items))

    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[int, BatchSlot[T]]]:
        """Yield integer indices and slots, optionally filtered by state."""
        for idx, slot in enumerate(self.slots):
            if state is None or slot.state is state:
                yield idx, slot

    def count(self, state: SlotState | None = None) -> int:
        """Return the total slot count or the count matching ``state``."""
        if state is None:
            return len(self.slots)
        return sum(1 for slot in self.slots if slot.state is state)

    def map(self, fn: Callable[[T], U]) -> BatchResult[U]:
        """Map successful payloads and preserve slot states and errors."""
        return BatchResult(tuple(s.map(fn) for s in self.slots))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult[U]:
        """Project raw outcomes onto successful positions in this 1D result.

        Args:
            raw_items: One raw outcome for each successful source slot.
            accessor: Optional function that extracts each successful payload.

        Returns:
            A result with the same length. Source errors and upstream failures
            become upstream-failed; filtered slots remain filtered.

        Raises:
            ValueError: If the number of raw items differs from the number of
                successful source slots.
        """
        raw_iter = _validate_raw_count(self.count(SlotState.SUCCESS), raw_items)
        return BatchResult(tuple(_project_slot(slot, raw_iter, accessor) for slot in self.slots))

    def project_rows(
        self, raw_items: Sequence[Any], row_length: int, *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        """Expand each successful source slot into a row of ``row_length`` cells.

        Args:
            raw_items: One raw outcome per cell in successful source rows.
            row_length: Number of cells for each successful row.
            accessor: Optional function that extracts each successful payload.

        Returns:
            A 2D result with one row per source slot. Rows from source errors
            or upstream failures are filled with upstream-failed cells;
            filtered rows are filled with filtered cells.

        Raises:
            ValueError: If ``row_length`` is negative or the raw item count is
                not the expected size.
        """
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
    """Store ordered cell slots and an optional whole-row error.

    Attributes:
        slots: Cell outcomes in column order.
        error: Whole-row error, when the API failed before returning cells.
    """

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
    def from_error(
        cls, error: BatchError | str, *, width: int, code: int = 0
    ) -> BatchRow[T]:
        """Create a whole-row failure with one error slot per cell.

        Raises:
            ValueError: If ``width`` is not positive.
        """
        if width <= 0:
            raise ValueError("A failed row requires a positive width.")
        batch_error = error if isinstance(error, BatchError) else BatchError.from_message(error, code=code)
        return cls(
            tuple(BatchSlot.failure(batch_error) for _ in range(width)),
            error=batch_error,
        )

    @classmethod
    def from_raw(
        cls,
        raw_row: Any,
        expected_len: int,
        *,
        accessor: Callable[[Any], T] | None = None,
        index: int | None = None,
    ) -> BatchRow[T]:
        """Convert a raw row or row-level API error to cell slots.

        Args:
            raw_row: A sequence of cell results or a whole-row API error.
            expected_len: Required number of cells.
            accessor: Optional function that extracts each successful payload.
            index: Optional row index included in validation errors.

        Raises:
            TypeError: If a successful raw row is not a non-text sequence.
            ValueError: If the row length differs or an error row has no
                positive expected length.
        """
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
        """Return the number of cells in the row."""
        return len(self.slots)

    def __iter__(self) -> Iterator[BatchSlot[T]]:
        """Iterate over cells from left to right."""
        return iter(self.slots)

    def __getitem__(self, index: int) -> BatchSlot[T]:
        """Return the cell at ``index`` using normal tuple indexing."""
        return self.slots[index]

    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[int, BatchSlot[T]]]:
        """Yield column indices and slots, optionally filtered by state."""
        for idx, slot in enumerate(self.slots):
            if state is None or slot.state is state:
                yield idx, slot

    def count(self, state: SlotState | None = None) -> int:
        """Return the total cell count or the count matching ``state``."""
        if state is None:
            return len(self.slots)
        return sum(1 for slot in self.slots if slot.state is state)

    def map(self, fn: Callable[[T], U]) -> BatchRow[U]:
        """Map successful cell payloads and preserve row and slot errors."""
        return BatchRow(tuple(slot.map(fn) for slot in self.slots), error=self.error)

    def aggregate(self, context: str = "Row") -> BatchSlot[tuple[T, ...]]:
        """Reduce the row to one slot, prioritizing errors then skipped states.

        A row without non-success cells contains its values as a tuple. A row
        error or cell errors become one aggregate error; otherwise upstream
        failure takes precedence over filtering.
        """
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
    """Store rows of cell results while preserving row and cell states.

    Rows may have different lengths unless the instance is a ``BatchGrid``.

    Attributes:
        rows: Result rows in input order.
    """

    rows: tuple[BatchRow[T], ...]

    @property
    def row_lengths(self) -> tuple[int, ...]:
        """Return each row's cell count."""
        return tuple(len(row) for row in self.rows)

    @property
    def row_errors(self) -> tuple[BatchError | None, ...]:
        """Return each row's whole-row error, if present."""
        return tuple(row.error for row in self.rows)

    @property
    def row_items(self) -> tuple[tuple[T | BatchError | None, ...], ...]:
        """Return row-partitioned values, errors, and skipped ``None`` cells."""
        return tuple(row.items for row in self.rows)

    def iter_slots(self, state: SlotState | None = None) -> Iterator[tuple[ValueCoordinate, BatchSlot[T]]]:
        """Yield ``(row, cell)`` coordinates and slots, optionally filtered."""
        for row_idx, row in enumerate(self.rows):
            for cell_idx, slot in enumerate(row.slots):
                if state is None or slot.state is state:
                    yield (row_idx, cell_idx), slot

    def count(self, state: SlotState | None = None) -> int:
        """Return the total cell count or the count matching ``state``."""
        if state is None:
            return sum(len(row) for row in self.rows)
        return sum(1 for _ in self.iter_slots(state))

    def aggregate_rows(self) -> BatchResult[tuple[T, ...]]:
        """Reduce each row to one slot containing its complete values or state.

        A row with errors becomes an aggregate error; otherwise upstream
        failure takes precedence over filtering. Rows without non-success cells
        contain value tuples, including empty rows.
        """
        return BatchResult(tuple(row.aggregate(context=f"Row {index}") for index, row in enumerate(self.rows)))

    def row_result(self) -> BatchResult[tuple[T | BatchError | None, ...]]:
        """Return one slot per row, preserving whole-row errors.

        Rows without a whole-row error become successful tuples of their cell
        items, which may themselves include errors or ``None`` values.
        """
        return BatchResult(
            tuple(
                BatchSlot.failure(row.error) if row.error is not None else BatchSlot.success(row.items)
                for row in self.rows
            )
        )

    def map(self, fn: Callable[[T], U]) -> BatchResult2D[U]:
        """Map successful cell payloads and preserve the 2D row structure."""
        new_rows = tuple(row.map(fn) for row in self.rows)
        return replace(self, rows=new_rows)

    def project_successes(
            self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchResult2D[U]:
        """Project raw outcomes onto successful cells in row-major order.

        Args:
            raw_items: One raw outcome for each successful source cell.
            accessor: Optional function that extracts each successful payload.

        Returns:
            A result with the same row lengths. Source errors and upstream
            failures become upstream-failed cells; filtered cells stay filtered.

        Raises:
            ValueError: If the number of raw items differs from the successful
                source cell count.
        """
        raw_iter = _validate_raw_count(self.count(SlotState.SUCCESS), raw_items)
        projected = tuple(
            BatchRow(tuple(_project_slot(slot, raw_iter, accessor) for slot in row.slots))
            for row in self.rows
        )
        return replace(self, rows=projected)

    def flatten(self) -> BatchResult[T]:
        """Return cells in row-major order with their states preserved."""
        return BatchResult(tuple(slot for _, slot in self.iter_slots()))


@dataclass(frozen=True, slots=True)
class BatchGrid(BatchResult2D[T]):
    """Store a rectangular 2D result whose rows share one positive width.

    Attributes:
        rows: Result rows in input order.
        width: Number of cells in every row.
    """

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
        """Build a rectangular result from raw rows or whole-row errors.

        Args:
            raw_rows: Rows of cell results, or one API error per failed row.
            width: Required positive number of cells per row.
            accessor: Optional function that extracts successful payloads.

        Raises:
            TypeError: If a successful row is not a non-text sequence.
            ValueError: If ``width`` is not positive or any row has the wrong
                length.

        Notes:
            An empty input creates a grid with no rows and the requested width.
        """
        if width <= 0:
            raise ValueError("width must be a positive integer.")
        rows = tuple(
            BatchRow.from_raw(raw_row, width, accessor=accessor, index=idx)
            for idx, raw_row in enumerate(raw_rows)
        )
        return cls(rows, width=width)

    def map(self, fn: Callable[[T], U]) -> BatchGrid[U]:
        """Map successful values and preserve the grid shape and states."""
        return cast(BatchGrid[U], BatchResult2D.map(self, fn))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> BatchGrid[U]:
        """Project outcomes onto successful cells and preserve the grid shape."""
        return cast(BatchGrid[U], BatchResult2D.project_successes(self, raw_items, accessor=accessor))


@dataclass(frozen=True, slots=True)
class RaggedBatchResult(BatchResult2D[T]):
    """Store a 2D result whose rows may have different lengths."""

    @classmethod
    def from_rows(
        cls, raw_rows: Sequence[Any], *, accessor: Callable[[Any], T] | None = None
    ) -> RaggedBatchResult[T]:
        """Build a ragged result from raw rows or whole-row API errors.

        Args:
            raw_rows: Rows of cell results or API errors.
            accessor: Optional function that extracts successful payloads.

        Raises:
            TypeError: If a successful row is not a non-text sequence.

        Notes:
            A non-sequence API error occupies one cell because its row width
            cannot be inferred.
        """
        lengths = tuple(len(row) if is_row_sequence(row) else 1 for row in raw_rows)
        rows = tuple(
            BatchRow.from_raw(raw_row, length, accessor=accessor, index=idx)
            for idx, (raw_row, length) in enumerate(zip(raw_rows, lengths))
        )
        return cls(rows)

    def map(self, fn: Callable[[T], U]) -> RaggedBatchResult[U]:
        """Map successful values and preserve row lengths and states."""
        return cast(RaggedBatchResult[U], BatchResult2D.map(self, fn))

    def project_successes(
        self, raw_items: Sequence[Any], *, accessor: Callable[[Any], U] | None = None
    ) -> RaggedBatchResult[U]:
        """Project outcomes onto successful cells and preserve ragged rows."""
        return cast(RaggedBatchResult[U], BatchResult2D.project_successes(self, raw_items, accessor=accessor))
