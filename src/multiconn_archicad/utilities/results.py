from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

from multiconn_archicad.models.official import types as official_types
from multiconn_archicad.models.tapir import types as tapir_types

T = TypeVar("T")
ErrorType = tapir_types.Error | official_types.Error

ERROR_CONTAINER_MODELS = (
    tapir_types.FailedExecutionResult,
    tapir_types.ErrorItem,
    official_types.FailedExecutionResult,
    official_types.ErrorItem,
)


def extract_error(item: Any) -> Optional[ErrorType]:
    """
    Extract an Archicad API Error instance from typed response items.
    Returns None if the item is successful or not an API error container.
    """
    if isinstance(item, ERROR_CONTAINER_MODELS):
        return item.error
    return None


@dataclass(frozen=True, slots=True, repr=False)
class BatchResult(Generic[T]):
    """Immutable batch execution container preserving 1:1 index alignment.

    Guarantees:
    - len(items) == len(input_items)
    - Failed indices contain `None` in `items` and the typed Error in `errors[idx]`.
    - Truthiness evaluates to True only when all operations succeeded (is_all_success).
    """

    items: Sequence[T | None]
    errors: Mapping[int, ErrorType]

    @property
    def has_errors(self) -> bool:
        """True if one or more operations in the batch failed."""
        return len(self.errors) > 0

    @property
    def is_all_success(self) -> bool:
        """True if every operation in the batch succeeded without errors."""
        return len(self.errors) == 0

    @property
    def successes(self) -> list[T]:
        """Returns only the successful items, omitting failures (None values)."""
        return [item for item in self.items if item is not None]

    def raise_for_errors(self) -> None:
        """Raises a consolidated RuntimeError if any operation in the batch failed."""
        if not self.has_errors:
            return
        details = [
            f"  - Index {i}: [{getattr(e, 'code', 'ERR')}] {getattr(e, 'message', str(e))}"
            for i, e in sorted(self.errors.items())
        ]
        raise RuntimeError(f"Batch operation failed with {len(self.errors)} error(s):\n" + "\n".join(details))

    def __bool__(self) -> bool:
        """Falsy if partial or total batch failure occurred."""
        return self.is_all_success

    def _infer_item_type(self) -> str:
        """Infers the item type name of successful items without deep recursion."""
        if not self.items:
            return "empty"
        sample = self.successes[0] if self.successes else None
        if sample is None:
            return "Unknown"
        return type(sample).__name__

    def __repr__(self) -> str:
        type_name = self._infer_item_type()
        total = len(self.items)
        num_errors = len(self.errors)
        num_successes = total - num_errors
        return f"BatchResult[{type_name}](total={total}, successes={num_successes}, errors={num_errors})"

    def __str__(self) -> str:
        type_name = self._infer_item_type()
        if not self.items:
            return f"BatchResult[{type_name}]: empty"
        if self.is_all_success:
            return f"BatchResult[{type_name}]: All {len(self.items)} succeeded"
        return (
            f"BatchResult[{type_name}]: {len(self.successes)}/{len(self.items)} succeeded ({len(self.errors)} failed)"
        )

    def debug_dump(self) -> dict[str, Any]:
        """Returns the full uncompressed dictionary of items and errors for debugging."""
        return {"items": list(self.items), "errors": dict(self.errors)}

    @classmethod
    def from_items(cls, raw_items: Sequence[Any], *, accessor: Optional[Callable[[Any], T]] = None) -> BatchResult[T]:
        """Factory for query/read responses operating directly on API response items.

        Args:
            raw_items: The direct response sequence from the Archicad endpoint.
            accessor: Optional callable to access/drill into nested values on successful items.
        """
        items: list[T | None] = []
        errors: dict[int, ErrorType] = {}

        for idx, raw_item in enumerate(raw_items):
            err = extract_error(raw_item)
            if err is not None:
                items.append(None)
                errors[idx] = err
            else:
                items.append(accessor(raw_item) if accessor is not None else raw_item)

        return cls(items=items, errors=errors)

    @classmethod
    def from_masked(
        cls, items: Sequence[Any], mask: Sequence[Any], *, accessor: Optional[Callable[[Any], T]] = None
    ) -> BatchResult[T]:
        """Factory for write/mutation operations masking data items against a status mask.

        Args:
            items: The primary sequence of data items to store or pad.
            mask: The corresponding status sequence (e.g. executionResults) containing errors.
            accessor: Optional callable to extract/access values from data items before storage.
        """
        if len(items) != len(mask):
            raise ValueError(f"Items length ({len(items)}) must match mask length ({len(mask)})")

        result_items: list[T | None] = []
        errors: dict[int, ErrorType] = {}

        for idx, mask_item in enumerate(mask):
            err = extract_error(mask_item)
            if err is not None:
                result_items.append(None)
                errors[idx] = err
            else:
                source_item = items[idx]
                result_items.append(accessor(source_item) if accessor is not None else source_item)

        return cls(items=result_items, errors=errors)
