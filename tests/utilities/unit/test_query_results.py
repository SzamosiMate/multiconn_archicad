"""Check the public search snapshot's alignment and immutable sequence shape."""

from uuid import UUID

import pytest

from multiconn_archicad.models.tapir.types import ElementId, ElementIdArrayItem
from multiconn_archicad.utilities import BatchResult, BatchSlot, FindElementsResult
from multiconn_archicad.utilities.queries import FindElementsResult as QueryFindElementsResult

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(("candidate_count", "outcome_count"), [(1, 0), (0, 1), (2, 1)])
def test_search_result_rejects_misaligned_candidates_and_outcomes(candidate_count, outcome_count):
    candidates = tuple(
        ElementIdArrayItem(elementId=ElementId(guid=UUID(int=index + 1))) for index in range(candidate_count)
    )
    outcomes = BatchResult(tuple(BatchSlot.filtered() for _ in range(outcome_count)))

    with pytest.raises(ValueError, match="Candidate count must match"):
        FindElementsResult(candidates, outcomes)


def test_search_result_copies_candidate_sequence_to_a_tuple():
    candidates = [ElementIdArrayItem(elementId=ElementId(guid=UUID(int=1)))]
    result = FindElementsResult(candidates, BatchResult((BatchSlot.filtered(),)))
    candidates.clear()

    assert isinstance(result.candidates, tuple)
    assert len(result.candidates) == 1
    assert QueryFindElementsResult is FindElementsResult
