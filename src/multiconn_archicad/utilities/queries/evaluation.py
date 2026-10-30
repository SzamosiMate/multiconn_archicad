"""Evaluate one property test against an already completed property read."""

from __future__ import annotations

from typing import TYPE_CHECKING

from multiconn_archicad.utilities.results.batch_results import BatchSlot
from multiconn_archicad.utilities.results.property_errors import PropertyUnavailableError, PropertyUndefinedError

if TYPE_CHECKING:
    from .models import PropertyTestModel


def evaluate_property(test: PropertyTestModel, value: BatchSlot[str]) -> BatchSlot[bool]:
    """Interpret a success/error read slot, then delegate successful values.

    Known unavailability and undefined values are false, even for negative
    operators. Other read failures retain their original errors. Skipped slots are not
    completed reads and cannot be evaluated. The query must already have passed
    structure and metadata-context validation; no API calls are made here.
    """
    if value.is_error:
        if isinstance(value.error, (PropertyUnavailableError, PropertyUndefinedError)):
            return BatchSlot.success(False)
        return BatchSlot.failure(value.error)
    return test.evaluate(value.value)
