"""Public utility and batch-result classes."""

from multiconn_archicad.errors import BatchOperationError

from .api import Utilities
from .population_results import (
    BatchFailure,
    BatchOutcome,
    BatchReport,
    BatchResultType,
    BatchStatus,
    BatchStep,
    PopulationResults,
)
from .multi_population_results import (
    MultiPopulationResults,
    PopulationRelation,
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
    "MultiPopulationResults",
    "PopulationRelation",
]
