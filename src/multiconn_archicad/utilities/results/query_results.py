"""Retain candidate identities alongside element-query search outcomes."""

from dataclasses import dataclass

from multiconn_archicad.models.tapir.types import ElementIdArrayItem

from .batch_results import BatchResult


@dataclass(frozen=True, slots=True)
class FindElementsResult:
    """Align one outcome to each unique candidate in first-listing order.

    Search captures candidates after its listing scope/type choices and before
    subsequent narrowing. A successful slot contains a matching element, a
    filtered slot a non-match, and an error slot its evaluation diagnostic.
    Candidates do not represent every element in the project.
    """

    candidates: tuple[ElementIdArrayItem, ...]
    outcomes: BatchResult[ElementIdArrayItem]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if len(self.candidates) != len(self.outcomes.slots):
            raise ValueError("Candidate count must match the number of search outcome slots")
