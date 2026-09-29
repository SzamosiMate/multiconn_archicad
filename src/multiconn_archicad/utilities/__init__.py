"""Expose utility groups, batch results, and population reports."""

from multiconn_archicad.errors import BatchNotFullySuccessfulError, BatchOperationError, BatchWriteError

from .api import Utilities
from multiconn_archicad.utilities.namespaces.attributes import AttributeUtilities
from multiconn_archicad.utilities.namespaces.elements import ElementUtilities
from multiconn_archicad.utilities.namespaces.properties import PropertyUtilities
from multiconn_archicad.utilities.results.population import (
    BatchFailure,
    BatchOutcome,
    BatchReport,
    BatchResultType,
    BatchStatus,
    BatchStep,
    PopulationResults,
)
from multiconn_archicad.utilities.results.multi_population import (
    MultiPopulationResults,
    PopulationRelation,
)
from multiconn_archicad.utilities.results.batch_results import (
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
    "PropertyUtilities",
    "AttributeUtilities",
    "ElementUtilities",
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
    "BatchNotFullySuccessfulError",
    "BatchWriteError",
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
