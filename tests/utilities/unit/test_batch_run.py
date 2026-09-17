from __future__ import annotations

from dataclasses import dataclass

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import BatchRun, BatchResult, BatchReport, BatchStatus, BatchResult2D


def error(code: int = 1):
    return tapir.ErrorItem(error=tapir.Error(code=code, message="failed"))


def test_batch_run_records_one_dimensional_errors_and_preserves_repeated_step_names():
    run = BatchRun(["a", "b"])
    first = BatchResult.from_items(["ok", error()])
    assert run.record("write", first) is first
    run.record("write", BatchResult.from_items(["ok", error(2)]), item_indices=[1, 0])
    assert run.report.failed_indices == (0, 1)
    assert {failure.step.index for outcome in run.outcomes for failure in outcome.failures} == {0, 1}


def test_batch_run_dataclass_normalizes_original_items_and_hides_internal_state():
    source = ["a"]
    run = BatchRun(source)
    source.append("later")
    assert run.original_items == ("a",)
    with pytest.raises(TypeError):
        BatchRun(["a"], _steps=[])


def test_batch_run_record_validation_is_atomic_and_abort_keeps_clean_items_incomplete():
    run = BatchRun(["a", "b"])
    with pytest.raises(ValueError):
        run.record("short", BatchResult.from_items([error()]))
    assert run.steps == ()
    report = run.abort(RuntimeError("fatal"))
    assert isinstance(report, BatchReport)
    assert isinstance(report.fatal_error, RuntimeError)
    assert report.status is BatchStatus.FAILED
    assert report.incomplete_indices == (0, 1)
    assert report.status_counts == {
        "total": 2,
        "succeeded": 0,
        "failed": 0,
        "upstream_failed": 0,
        "filtered": 0,
        "incomplete": 2,
    }
    with pytest.raises(RuntimeError):
        run.finish()


def test_batch_run_2d_and_multiple_failures_are_ordered_per_outcome():
    run = BatchRun(["first", "second"])
    matrix = BatchResult2D.from_ragged_rows([[error(1), error(2)], ["ok"]])
    run.record("matrix", matrix, item_indices=[1, 0])

    # Element 1 ("second") received row 0 (which has 2 errors)
    failures = run.outcomes[1].failures
    assert len(failures) == 2
    assert failures[0].error.code == 1
    assert failures[0].source_coordinate == (0, 0)
    assert failures[1].error.code == 2
    assert failures[1].source_coordinate == (0, 1)

    # Element 0 ("first") received row 1 (which succeeded)
    assert run.outcomes[0].failures == ()


def test_run_repeated_targets_and_invalid_arguments_are_atomic():
    run = BatchRun(["a", "b"])
    run.record("repeat", BatchResult.from_items([error(), error(2)]), item_indices=[1, 1])
    assert [failure.error.code for failure in run.outcomes[1].failures] == [1, 2]
    before = run.steps
    with pytest.raises(IndexError):
        run.record("bad", BatchResult.from_items(["a", "b"]), item_indices=[0, 2])
    with pytest.raises(ValueError):
        run.record("bad", BatchResult.from_items(["a", "b"]), item_indices=[0])
    assert run.steps == before


def test_run_finish_and_abort_statuses_and_separate_retry():
    run = BatchRun(["a", "b"])
    run.record("write", BatchResult.from_items([error(), "ok"]))
    report = run.finish()
    assert [outcome.status for outcome in report.outcomes] == [BatchStatus.FAILED, BatchStatus.SUCCEEDED]
    assert report.status is BatchStatus.FAILED
    aborted = BatchRun(["a", "b"])
    aborted.record("write", BatchResult.from_items([error(), "ok"]))
    aborted_report = aborted.abort(RuntimeError("fatal"))
    assert [outcome.status for outcome in aborted_report.outcomes] == [BatchStatus.FAILED, BatchStatus.INCOMPLETE]
    assert aborted_report.status is BatchStatus.FAILED
    with pytest.raises(RuntimeError):
        aborted.abort(RuntimeError("again"))
    retry = BatchRun(["a"])
    assert retry.finish().outcomes[0].succeeded


def test_batch_run_report_is_a_snapshot_and_tracks_open_state():
    run = BatchRun(["a"])
    before = run.report
    assert before.status is BatchStatus.INCOMPLETE
    run.record("read", BatchResult.from_items([error()]))
    after = run.report
    assert before.outcomes[0].status is BatchStatus.INCOMPLETE
    assert before.steps == ()
    assert after.status is BatchStatus.FAILED
    assert len(after.steps) == 1


def test_batch_run_for_items_subset_and_mutual_exclusion():
    run = BatchRun(["e0", "e1", "e2"])

    # Step 1: operates only on subset ["e0", "e2"]
    sub_res = BatchResult.from_items(["ok", error(99)])
    run.record("subset_step", sub_res, for_items=["e0", "e2"])

    # e0 succeeded, e1 incomplete, e2 failed
    assert run.outcomes[0].succeeded is False  # Run is open, so incomplete
    assert len(run.outcomes[2].failures) == 1
    assert run.outcomes[2].failures[0].error.code == 99

    # Specifying both item_indices and for_items raises ValueError
    with pytest.raises(ValueError, match="Specify either item_indices or for_items"):
        run.record("conflict", sub_res, item_indices=[0, 2], for_items=["e0", "e2"])

    # Item not found in original items
    with pytest.raises(ValueError, match="not found"):
        run.record("unknown", sub_res, for_items=["e0", "unknown_elem"])


def test_batch_run_for_items_duplicate_elements_fifo_resolution():
    # Demonstrates repeat elements resolve to successive occurrences
    run = BatchRun(["dup", "other", "dup"])

    # First dup succeeds, second dup fails
    res = BatchResult.from_items(["first_ok", error(42)])
    run.record("dup_step", res, for_items=["dup", "dup"])

    # Failure must be assigned to index 2, NOT index 0!
    assert len(run.outcomes[0].failures) == 0
    assert len(run.outcomes[2].failures) == 1
    assert run.outcomes[2].failures[0].error.code == 42


def test_batch_run_for_items_unhashable_objects_fallback():
    # Mutable objects that don't implement __hash__
    @dataclass
    class UnhashableItem:
        val: str

    item1 = UnhashableItem("a")
    item2 = UnhashableItem("b")
    item3 = UnhashableItem("a")

    run = BatchRun([item1, item2, item3])
    # Pass both occurrences of "a": first succeeds, second fails
    res = BatchResult.from_items(["ok", error(10)])
    run.record("unhashable", res, for_items=[item1, item3])

    # Resolves to item1 (index 0) and item3 (index 2) via duplicate-safe equality comparison
    assert len(run.outcomes[0].failures) == 0
    assert len(run.outcomes[2].failures) == 1
    assert run.outcomes[2].failures[0].error.code == 10


def test_context_manager_aborts_and_suppresses_exception():
    # BatchRun.__exit__ intentionally suppresses Exception to populate fatal_error on run.report
    with BatchRun(["a", "b"]) as run:
        run.record("step1", BatchResult.from_items(["ok", "ok"]))
        raise ValueError("boom")

    # Run was automatically closed, aborted, and fatal_error recorded
    assert run.report.status is BatchStatus.FAILED
    assert isinstance(run.fatal_error, ValueError)
    assert str(run.fatal_error) == "boom"

    # Verify BaseException (e.g. KeyboardInterrupt) is NOT suppressed
    with pytest.raises(KeyboardInterrupt):
        with BatchRun(["a", "b"]):
            raise KeyboardInterrupt()
