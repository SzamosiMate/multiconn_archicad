from __future__ import annotations

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import BatchResult, BatchResult2D, BatchRun, BatchStatus
from multiconn_archicad.utilities.results import BatchError, BatchSlot, SlotState, BatchRow


def error(code: int = 1):
    return tapir.ErrorItem(error=tapir.Error(code=code, message="failed"))


def test_one_dimensional_slots_allow_none_and_expose_indices():
    result = BatchResult.from_items([None, error()])
    assert result.successes == [None]
    assert result.slots[0].success_value is None
    with pytest.raises(ValueError, match="successful value"):
        result.slots[1].success_value
    assert result.success_indices == (0,)
    assert result.failure_indices == (1,)
    assert [(index, item.code) for index, item in result.iter_errors()] == [(1, 1)]


@pytest.mark.parametrize("item", [error(), tapir.Error(code=2, message="direct")])
def test_error_normalization_preserves_typed_api_error_identity(item):
    result = BatchResult.from_items([item])
    assert result.slots[0].error.error is (item.error if isinstance(item, tapir.ErrorItem) else item)


def test_one_dimensional_map_skips_error_and_propagates_callback_exception():
    result = BatchResult.from_items(["ok", error()])
    assert result.map(str.upper).successes == ["OK"]
    with pytest.raises(ZeroDivisionError):
        BatchResult.from_items(["ok"]).map(lambda _: 1 / 0)


def test_matrix_retains_ragged_lengths_and_whole_row_error_coordinate():
    result = BatchResult2D.from_rows([["a"], error()], row_lengths=[1, 3])
    assert result.row_lengths == (1, 3)
    assert result.failure_indices == ((1, 0), (1, 1), (1, 2))
    assert result.flatten().total_errors == 3
    assert result.successes == ["a"]
    assert result.success_indices == ((0, 0),)


def test_matrix_supports_empty_matrix_empty_rows_and_cell_errors():
    assert BatchResult2D.from_rows([], row_lengths=[]).items == ()
    result = BatchResult2D.from_rows([[], [error(), "ok"]], row_lengths=[0, 2])
    assert list(result.iter_errors())[0][0] == (1, 0)
    assert tuple(result.iter_successes()) == (((1, 1), "ok"),)
    mixed = BatchResult2D.from_rows([[error()], error(2)], row_lengths=[1, 4])
    assert mixed.failure_indices == ((0, 0), (1, 0), (1, 1), (1, 2), (1, 3))


def test_items_and_error_iteration_share_expanded_cells():
    result = BatchResult2D.from_rows([["ok", error()], error(2), []], row_lengths=[2, 3, 0])
    items = result.items
    assert tuple(map(len, items)) == (2, 3, 0)
    assert items[0][0] == "ok"
    assert items[0][1] is result.rows[0][1].error
    assert all(item is result.row_errors[1] for item in items[1])
    assert items[2] == ()
    assert result.failure_indices == ((0, 1), (1, 0), (1, 1), (1, 2))
    rebuilt = BatchResult2D.from_rows(items)
    assert rebuilt.total_errors == 4
    assert rebuilt.items == items


def test_matrix_map_and_flatten_share_row_major_filtering():
    result = BatchResult2D.from_rows([["a", error()], ["b"]], row_lengths=[2, 1])
    mapped = result.map(str.upper)
    flat = mapped.flatten()
    assert flat.successes == ["A", "B"]
    assert flat.failure_indices == (1,)
    assert mapped.successes == ["A", "B"]
    assert mapped.success_indices == ((0, 0), (1, 0))
    with pytest.raises(ZeroDivisionError):
        BatchResult2D.from_rows([["a"]], row_lengths=[1]).map(lambda _: 1 / 0)


def test_row_views_distinguish_partial_cells_from_original_row_errors():
    matrix = BatchResult2D[str].from_rows([["a", "b"], ["c", error()], error(2), []], row_lengths=[2, 2, 3, 0])
    aggregate = matrix.aggregate_rows()
    original = matrix.row_result()
    assert aggregate.failure_indices == (1, 2)
    assert aggregate.successes == [("a", "b"), ()]
    assert original.failure_indices == (2,)
    assert original.success_indices == (0, 1, 3)
    assert original.items[1] == matrix.items[1]
    assert original.errors[0] is matrix.row_errors[2]
    assert aggregate.errors[1].causes == (matrix.row_errors[2],)
    mapped = matrix.map(str.upper)
    assert mapped.row_result().errors[0] is original.errors[0]
    assert mapped.aggregate_rows().successes == [("A", "B"), ()]
    run = BatchRun(range(4))
    run.record("cells", matrix)
    assert len(run.report.outcomes[2].failures) == 3
    row_run = BatchRun(range(4))
    row_run.record("rows", aggregate)
    assert len(row_run.report.outcomes[2].failures) == 1


@pytest.mark.parametrize("lengths", [None, [0]])
def test_whole_row_errors_require_known_positive_lengths(lengths):
    with pytest.raises(ValueError, match="positive row length"):
        BatchResult2D.from_rows([error()], row_lengths=lengths)


def test_finish_marks_clean_success_and_empty_run_is_clean():
    empty_report = BatchRun([]).finish()
    assert empty_report.outcomes == ()
    assert empty_report.status is BatchStatus.SUCCEEDED
    run = BatchRun(["only"])
    run.record("read", BatchResult.from_items(["ok"]))
    assert run.finish().outcomes[0].succeeded
    with pytest.raises(RuntimeError):
        run.record("retry", BatchResult.from_items(["ok"]))


# ==============================================================================
# New Tests: SlotState & BatchSlot
# ==============================================================================


def test_slot_state_factories_and_invariants():
    success_slot = BatchSlot.success("val")
    assert success_slot.state is SlotState.SUCCESS
    assert success_slot.is_success
    assert not success_slot.is_error
    assert not success_slot.is_skipped
    assert success_slot.success_value == "val"
    assert success_slot.item_val() == "val"

    err = BatchError(tapir.Error(code=1, message="err"))
    failure_slot = BatchSlot.failure(err)
    assert failure_slot.state is SlotState.ERROR
    assert failure_slot.is_error
    assert failure_slot.error is err
    assert failure_slot.item_val() is err
    with pytest.raises(ValueError, match="has no successful value"):
        _ = failure_slot.success_value

    skipped_slot = BatchSlot.skipped()
    assert skipped_slot.state is SlotState.SKIPPED
    assert skipped_slot.is_skipped
    assert skipped_slot.item_val() is None
    with pytest.raises(ValueError, match="has no successful value"):
        _ = skipped_slot.success_value

    # Invariant violations
    with pytest.raises(ValueError, match="SUCCESS slot cannot contain an error"):
        BatchSlot(state=SlotState.SUCCESS, value="ok", error=err)
    with pytest.raises(ValueError, match="ERROR slot must contain a BatchError"):
        BatchSlot(state=SlotState.ERROR, error=None)
    with pytest.raises(ValueError, match="SKIPPED slot cannot contain a value"):
        BatchSlot(state=SlotState.SKIPPED, value="bad")


def test_slot_from_raw_and_map():
    slot_ok = BatchSlot.from_raw("hello", accessor=str.upper)
    assert slot_ok.is_success
    assert slot_ok.success_value == "HELLO"

    slot_err = BatchSlot.from_raw(error(5))
    assert slot_err.is_error
    assert slot_err.error.code == 5

    # Slot map
    assert slot_ok.map(lambda s: f"{s}!").success_value == "HELLO!"
    assert slot_err.map(lambda s: s).is_error
    assert BatchSlot.skipped().map(lambda s: s).is_skipped


# ==============================================================================
# Projection (1D & 2D)
# ==============================================================================


def test_batch_result_1d_project_successes():
    # Source: [OK("a"), ERROR, OK("b")]
    source = BatchResult.from_items(["a", error(1), "b"])
    assert source.success_indices == (0, 2)
    assert source.skipped_indices == ()

    # Project 2 items onto the 2 successes: 1 succeeds, 1 fails
    projected = source.project_successes([10, error(2)])
    assert len(projected.slots) == 3
    assert projected.slots[0].is_success and projected.slots[0].success_value == 10
    assert projected.slots[1].is_skipped
    assert projected.slots[2].is_error and projected.slots[2].error.code == 2

    assert projected.success_indices == (0,)
    assert projected.skipped_indices == (1,)
    assert projected.failure_indices == (2,)
    assert projected.items == (10, None, projected.slots[2].error)

    # Length mismatch validation
    with pytest.raises(ValueError, match="Expected 2 items"):
        source.project_successes([10])


def test_batch_result_1d_project_rows():
    # Source: 3 elements [OK("a"), ERROR, OK("b")]
    source = BatchResult.from_items(["a", error(1), "b"])

    # Expand to 2 columns per successful row (2 rows * 2 = 4 items)
    matrix = source.project_rows([1, 2, error(3), 4], row_length=2)
    assert isinstance(matrix, BatchResult2D)
    assert matrix.row_lengths == (2, 2, 2)

    # Row 0: Succeeded -> [1, 2]
    assert matrix.rows[0][0].success_value == 1
    assert matrix.rows[0][1].success_value == 2

    # Row 1: Skipped (because source was error) -> [SKIPPED, SKIPPED]
    assert matrix.rows[1][0].is_skipped
    assert matrix.rows[1][1].is_skipped

    # Row 2: Succeeded in source, but cell (2, 0) failed in raw items -> [ERROR, 4]
    assert matrix.rows[2][0].is_error and matrix.rows[2][0].error.code == 3
    assert matrix.rows[2][1].success_value == 4

    assert matrix.skipped_indices == ((1, 0), (1, 1))
    assert matrix.failure_indices == ((2, 0),)

    # Negative row_length & count mismatch
    with pytest.raises(ValueError, match="non-negative"):
        source.project_rows([], row_length=-1)
    with pytest.raises(ValueError, match="Expected 4 items"):
        source.project_rows([1, 2], row_length=2)


def test_batch_result_2d_project_successes():
    # 2 elements x 2 properties
    source = BatchResult2D.from_rows([["a", "b"], [error(1), "c"]], row_lengths=[2, 2])
    assert len(source.successes) == 3

    # Project 3 raw items: ["x", error(2), "y"]
    projected = source.project_successes(["x", error(2), "y"])
    assert projected.row_lengths == (2, 2)

    # (0, 0) -> "x", (0, 1) -> error(2)
    assert projected.rows[0][0].success_value == "x"
    assert projected.rows[0][1].is_error and projected.rows[0][1].error.code == 2

    # (1, 0) -> SKIPPED (source was error), (1, 1) -> "y"
    assert projected.rows[1][0].is_skipped
    assert projected.rows[1][1].success_value == "y"

    assert projected.has_skipped
    assert projected.skipped_indices == ((1, 0),)
    assert projected.success_indices == ((0, 0), (1, 1))
    assert projected.failure_indices == ((0, 1),)


def test_batch_result_2d_aggregate_rows_with_skips():
    # Row 0: Clean success -> Success(("a", "b"))
    # Row 1: Partial skip -> Skipped
    # Row 2: Has error -> Failure
    slot_ok_a = BatchSlot.success("a")
    slot_ok_b = BatchSlot.success("b")
    slot_skipped = BatchSlot.skipped()
    slot_err = BatchSlot.failure(BatchError(tapir.Error(code=1, message="fail")))

    matrix = BatchResult2D(
        rows=(
            BatchRow((slot_ok_a, slot_ok_b)),
            BatchRow((slot_ok_a, slot_skipped)),
            BatchRow((slot_ok_a, slot_err)),
        )
    )
    aggregated = matrix.aggregate_rows()

    assert len(aggregated.slots) == 3
    assert aggregated.slots[0].is_success and aggregated.slots[0].success_value == ("a", "b")
    assert aggregated.slots[1].is_skipped
    assert aggregated.slots[2].is_error and aggregated.slots[2].error.causes[0].code == 1


def test_is_all_success_requires_no_errors_and_no_skips():
    clean = BatchResult.from_items(["a", "b"])
    assert clean.is_all_success

    mixed = BatchResult((BatchSlot.success("a"), BatchSlot.skipped()))
    assert not mixed.is_all_success
    assert mixed.has_skipped
    assert not mixed.has_errors


