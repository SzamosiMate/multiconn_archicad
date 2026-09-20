"""Public utility and batch-result classes."""

from multiconn_archicad.errors import BatchOperationError

from .api import Utilities
from .batch_run import (
    BatchFailure,
    BatchOutcome,
    BatchReport,
    BatchResultType,
    BatchStatus,
    BatchStep,
    PopulationResults,
)
from .results import (
    BatchError,
    BatchGrid,
    BatchResult,
    BatchResult2D,
    BatchResultBase,
    BatchRow,
    BatchSlot,
    RaggedBatchResult,
    SlotState,
)

__all__ = [
    "Utilities",
    "BatchResultBase",
    "BatchResult",
    "BatchResult2D",
    "BatchGrid",
    "RaggedBatchResult",
    "BatchRow",
    "BatchSlot",
    "SlotState",
    "BatchError",
    "BatchOperationError",
    "PopulationResults",
    "BatchStep",
    "BatchFailure",
    "BatchOutcome",
    "BatchReport",
    "BatchStatus",
    "BatchResultType",
]
