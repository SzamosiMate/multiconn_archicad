from __future__ import annotations

from dataclasses import dataclass

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import BatchReport, BatchResult, BatchStatus, PopulationResults
from multiconn_archicad.utilities.population_results import reduce_population_outcomes
from multiconn_archicad.utilities.results import BatchGrid, BatchRow, BatchSlot, RaggedBatchResult


def error(code: int = 1) -> tapir.ErrorItem:
    return tapir.ErrorItem(error=tapir.Error(code=code, message="failed"))


def test_population_results_normalizes_original_items_and_hides_internal_state() -> None:
    source = ["a"]
    results = PopulationResults(source)

    source.append("later")

    assert results.original_items == ("a",)
    assert results.steps == ()
    with pytest.raises(TypeError):
        PopulationResults(["a"], _steps=[])


def test_record_returns_result_and_preserves_repeated_step_names_in_order() -> None:
    results = PopulationResults(["a", "b"])
    first = BatchResult.from_items(["ok", error()])
    second = BatchResult.from_items(["ok", error(2)])

    assert results.record("write", first) is first
    assert results.record("write", second, item_indices=[1, 0]) is second

    report = results.snapshot(completed=False)
    assert [step.name for step in report.steps] == ["write", "write"]
    assert [step.index for step in report.steps] == [0, 1]
    assert report.indices(BatchStatus.FAILED) == (0, 1)
    assert report.count(BatchStatus.FAILED) == 2
    assert report.has(BatchStatus.FAILED)
    assert {failure.step.index for _, failure in report.iter_failures()} == {0, 1}


def test_one_dimensional_direct_failures_take_priority_over_incomplete_processing() -> None:
    results = PopulationResults(["a", "b"])
    results.record("write", BatchResult.from_items([error(), "ok"]))

    report = results.snapshot(completed=False)

    assert [outcome.status for outcome in report.outcomes] == [BatchStatus.FAILED, BatchStatus.INCOMPLETE]
    assert report.status is BatchStatus.FAILED
    assert report.status_counts == {
        "total": 2,
        "succeeded": 0,
        "failed": 1,
        "upstream_failed": 0,
        "filtered": 0,
        "incomplete": 1,
    }
    assert results.failures_by_item() == tuple(outcome.failures for outcome in report.outcomes)


def test_direct_failures_accumulate_and_override_a_clean_terminal_step() -> None:
    results = PopulationResults(["a", "b"])
    results.record("read", BatchResult.from_items([error(7), "ok"]))
    results.record("write", BatchResult.from_items(["ok", "ok"]))

    report = results.snapshot(completed=True)

    assert [outcome.status for outcome in report.outcomes] == [BatchStatus.FAILED, BatchStatus.SUCCEEDED]
    assert report.outcomes[0].failures[0].step_name == "read"


def test_pure_outcome_reducer_uses_only_inputs_and_completed_flag() -> None:
    results = PopulationResults(["failed", "clean"])
    results.record("write", BatchResult.from_items([error(), "ok"]))
    original_items = results.original_items
    steps = results.steps

    incomplete = reduce_population_outcomes(original_items, steps, completed=False)
    completed = reduce_population_outcomes(original_items, steps, completed=True)

    assert [outcome.status for outcome in incomplete] == [BatchStatus.FAILED, BatchStatus.INCOMPLETE]
    assert [outcome.status for outcome in completed] == [BatchStatus.FAILED, BatchStatus.SUCCEEDED]
    assert results.original_items == original_items
    assert results.steps == steps


def test_two_dimensional_failures_are_attributed_and_ordered_per_original_item() -> None:
    results = PopulationResults(["first", "second"])
    matrix = RaggedBatchResult.from_rows([[error(1), error(2)], ["ok"]])

    results.record("matrix", matrix, item_indices=[1, 0])

    report = results.snapshot(completed=True)
    failures = report.outcomes[1].failures
    assert [(failure.error.code, failure.source_coordinate) for failure in failures] == [
        (1, (0, 0)),
        (2, (0, 1)),
    ]
    assert report.outcomes[0].failures == ()


def test_batch_grid_failure_is_attributed_to_its_row_item() -> None:
    results = PopulationResults(["first", "second"])
    grid = BatchGrid.from_rows([["ok", error(10)], ["ok", "ok"]], width=2)

    results.record("grid", grid)

    report = results.snapshot(completed=True)
    assert report.outcomes[0].failed
    assert report.outcomes[0].failures[0].error.code == 10
    assert report.outcomes[0].failures[0].source_coordinate == (0, 1)
    assert report.outcomes[1].succeeded


def test_completed_false_keeps_otherwise_clean_items_incomplete() -> None:
    results = PopulationResults(["a", "b"])
    results.record("read", BatchResult.from_items(["ok", "ok"]))

    report = results.snapshot(completed=False)

    assert report.indices(BatchStatus.INCOMPLETE) == (0, 1)
    assert report.status is BatchStatus.INCOMPLETE


def test_completed_population_uses_last_step_terminal_states_and_omitted_items() -> None:
    results = PopulationResults(["upstream", "filtered", "partial", "omitted"])
    results.record(
        "terminal",
        BatchResult(
            (
                BatchSlot.upstream_failed(),
                BatchSlot.filtered(),
                BatchSlot.filtered(),
                BatchSlot.filtered(),
                BatchSlot.success("written"),
            )
        ),
        item_indices=[0, 1, 1, 2, 2],
    )

    report = results.snapshot(completed=True)

    assert [outcome.status for outcome in report.outcomes] == [
        BatchStatus.UPSTREAM_FAILED,
        BatchStatus.FILTERED,
        BatchStatus.SUCCEEDED,
        BatchStatus.FILTERED,
    ]
    # The legacy aggregate reduction treats a mixed non-failing terminal population as succeeded.
    assert report.status is BatchStatus.SUCCEEDED


def test_completed_population_uses_only_the_last_recorded_step_as_terminal() -> None:
    results = PopulationResults(["a"])
    results.record("earlier", BatchResult((BatchSlot.upstream_failed(),)))
    results.record("terminal", BatchResult.from_items(["ok"]))

    assert results.snapshot(completed=True).outcomes[0].succeeded


def test_completed_population_with_no_steps_succeeds() -> None:
    report = PopulationResults(["a", "b"]).snapshot(completed=True)

    assert report.indices(BatchStatus.SUCCEEDED) == (0, 1)
    assert report.status is BatchStatus.SUCCEEDED


def test_empty_population_preserves_completed_flag_in_aggregate_status() -> None:
    results = PopulationResults([])

    assert results.snapshot(completed=False).status is BatchStatus.INCOMPLETE
    assert results.snapshot(completed=True).status is BatchStatus.SUCCEEDED


@pytest.mark.parametrize(
    ("slots", "expected_outcomes", "expected_status"),
    [
        (
            (BatchSlot.filtered(), BatchSlot.filtered()),
            (BatchStatus.FILTERED, BatchStatus.FILTERED),
            BatchStatus.FILTERED,
        ),
        (
            (BatchSlot.upstream_failed(), BatchSlot.upstream_failed()),
            (BatchStatus.UPSTREAM_FAILED, BatchStatus.UPSTREAM_FAILED),
            BatchStatus.UPSTREAM_FAILED,
        ),
        (
            (BatchSlot.filtered(), BatchSlot.upstream_failed()),
            (BatchStatus.FILTERED, BatchStatus.UPSTREAM_FAILED),
            BatchStatus.SUCCEEDED,
        ),
    ],
)
def test_completed_aggregate_status_reduction_is_preserved(
    slots: tuple[BatchSlot[object], ...],
    expected_outcomes: tuple[BatchStatus, ...],
    expected_status: BatchStatus,
) -> None:
    results = PopulationResults(["a", "b"])
    results.record("terminal", BatchResult(slots))

    report = results.snapshot(completed=True)

    assert tuple(outcome.status for outcome in report.outcomes) == expected_outcomes
    assert report.status is expected_status


def test_record_with_repeated_item_indices_attributes_each_source_slot() -> None:
    results = PopulationResults(["a", "b"])
    results.record("repeat", BatchResult.from_items([error(), error(2)]), item_indices=[1, 1])

    failures = results.snapshot(completed=True).outcomes[1].failures

    assert [failure.error.code for failure in failures] == [1, 2]


def test_invalid_record_inputs_are_atomic() -> None:
    results = PopulationResults(["a", "b"])
    valid_result = BatchResult.from_items(["a", "b"])

    invalid_calls = (
        lambda: results.record("default-size", BatchResult.from_items(["a"])),
        lambda: results.record("bad-index", valid_result, item_indices=[0, 2]),
        lambda: results.record("short-indices", valid_result, item_indices=[0]),
        lambda: results.record("conflict", valid_result, item_indices=[0, 1], for_items=["a", "b"]),
        lambda: results.record("unknown", valid_result, for_items=["a", "unknown"]),
        lambda: results.record("too-many", valid_result, for_items=["a", "a"]),
    )

    for invalid_call in invalid_calls:
        before = results.steps
        with pytest.raises((IndexError, ValueError)):
            invalid_call()
        assert results.steps == before


def test_record_accepts_batch_row_as_one_dimensional_result() -> None:
    results = PopulationResults(["a", "b"])
    row = BatchRow((BatchSlot.success("first"), BatchSlot.success("second")))

    assert results.record("row", row) is row  # type: ignore[type-var]
    assert results.steps[0].result is row
    assert results.steps[0].item_indices == (0, 1)


def test_for_items_resolves_duplicate_original_items_fifo() -> None:
    results = PopulationResults(["dup", "other", "dup"])
    results.record("duplicates", BatchResult.from_items(["ok", error(42)]), for_items=["dup", "dup"])

    report = results.snapshot(completed=True)

    assert report.outcomes[0].failures == ()
    assert report.outcomes[2].failures[0].error.code == 42


def test_for_items_resolves_duplicate_unhashable_items_fifo() -> None:
    @dataclass
    class UnhashableItem:
        value: str

    first = UnhashableItem("a")
    middle = UnhashableItem("b")
    last = UnhashableItem("a")
    results = PopulationResults([first, middle, last])
    results.record("unhashable", BatchResult.from_items(["ok", error(10)]), for_items=[first, last])

    report = results.snapshot(completed=True)

    assert report.outcomes[0].failures == ()
    assert report.outcomes[2].failures[0].error.code == 10


def test_snapshots_are_immutable_and_do_not_stop_later_recording() -> None:
    results = PopulationResults(["a"])
    before = results.snapshot(completed=False)
    completed_view = results.snapshot(completed=True)

    results.record("read", BatchResult.from_items([error()]))
    after = results.snapshot(completed=False)

    assert before.steps == ()
    assert before.outcomes[0].incomplete
    assert completed_view.outcomes[0].succeeded
    assert len(after.steps) == 1
    assert after.outcomes[0].failed


def test_passive_collection_and_report_have_no_execution_lifecycle_or_fatal_error() -> None:
    results = PopulationResults(["a"])
    report = results.snapshot()

    assert isinstance(report, BatchReport)
    for name in ("finish", "abort", "fatal_error", "report", "__enter__", "__exit__"):
        assert not hasattr(results, name)
    assert not hasattr(report, "fatal_error")
