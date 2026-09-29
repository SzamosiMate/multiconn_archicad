from __future__ import annotations

import pytest

from multiconn_archicad.errors import BatchNotFullySuccessfulError, BatchOperationError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import BatchResult, BatchResult2D
from multiconn_archicad.utilities.results import (
    BatchError,
    BatchGrid,
    BatchRow,
    BatchSlot,
    RaggedBatchResult,
    SlotState,
)


def error(code: int = 1):
    return tapir.ErrorItem(error=tapir.Error(code=code, message="failed"))


# ==============================================================================
# 1D Result Tests
# ==============================================================================


def test_one_dimensional_slots_normalize_errors_and_expose_indices():
    result = BatchResult.from_items([None, error()])
    assert result.successes == [None]
    assert result.slots[0].value is None
    with pytest.raises(ValueError, match="successful value"):
        _ = result.slots[1].value
    assert result.indices(SlotState.SUCCESS) == (0,)
    assert result.indices(SlotState.ERROR) == (1,)
    assert [(index, item.code) for index, item in result.iter_errors()] == [(1, 1)]
    assert result.count() == 2
    assert result.count(SlotState.SUCCESS) == 1
    assert result.count(SlotState.ERROR) == 1

    direct_error = tapir.Error(code=2, message="direct")
    assert BatchResult.from_items([direct_error]).slots[0].error.error is direct_error


def test_one_dimensional_map_skips_errors():
    result = BatchResult.from_items(["ok", error()])
    assert result.map(str.upper).successes == ["OK"]


# ==============================================================================
# 2D Result Construction & Mode Enforcement
# ==============================================================================


def test_rectangular_results_validate_width_and_row_shape():
    with pytest.raises(TypeError):
        BatchGrid.from_rows([["a", "b"]])  # type: ignore[call-arg]

    for invalid_width in (0, -1):
        with pytest.raises(ValueError, match="width must be a positive integer"):
            BatchGrid.from_rows([["a"]], width=invalid_width)

    row = BatchRow((BatchSlot.success("a"),))
    with pytest.raises(ValueError, match="width must be a positive integer"):
        BatchGrid((row,), width=0)
    with pytest.raises(ValueError, match=r"Row 0 length \(1\) does not match width \(2\)"):
        BatchGrid((row,), width=2)


def test_failed_rows_expand_errors_and_preserve_rectangular_shape():
    row = BatchRow.from_error("row failed", width=2, code=-1)

    assert row.error is not None
    assert row.error.code == -1
    assert row.error.message == "row failed"
    assert all(slot.error is row.error for slot in row.slots)

    with pytest.raises(ValueError, match="positive width"):
        BatchRow.from_error("row failed", width=0)

    # Sequence length mismatch raises immediately
    with pytest.raises(ValueError, match=r"length \(1\) does not match expected \(2\)"):
        BatchGrid.from_rows([["a", "b"], ["c"]], width=2)

    # Whole-row error expands to width slots
    matrix = BatchGrid.from_rows([error(1), ["a", "b"]], width=2)
    assert matrix.width == 2
    assert matrix.row_lengths == (2, 2)
    assert matrix.indices(SlotState.ERROR) == ((0, 0), (0, 1))
    assert matrix.rows[0].error is not None
    assert matrix.rows[0].error.code == 1
    assert matrix.rows[0][0].error is matrix.rows[0].error
    assert matrix.rows[0][1].error is matrix.rows[0].error

    # 100% error data succeeds without crashing
    all_err = BatchGrid.from_rows([error(1), error(2)], width=3)
    assert all_err.width == 3
    assert all_err.row_lengths == (3, 3)
    assert all_err.count(SlotState.ERROR) == 6
    assert all_err.is_all(SlotState.ERROR)


def test_ragged_mode_infers_lengths_and_defaults_errors_to_one():
    result = RaggedBatchResult.from_rows([["a", "b"], error(1), ["c", "d", "e"]])
    assert result.row_lengths == (2, 1, 3)
    assert result.indices(SlotState.ERROR) == ((1, 0),)
    assert result.rows[1].error is not None
    assert result.rows[1].error.code == 1

    # 100% error data in ragged mode defaults each row to 1 slot
    all_err_ragged = RaggedBatchResult.from_rows([error(1), error(2)])
    assert all_err_ragged.row_lengths == (1, 1)
    assert all_err_ragged.count(SlotState.ERROR) == 2

    with pytest.raises(TypeError, match="must be a sequence or a typed API error"):
        BatchGrid.from_rows(["hello"], width=5)
    with pytest.raises(TypeError, match="must be a sequence or a typed API error"):
        RaggedBatchResult.from_rows([b"binary"])


# ==============================================================================
# 2D Matrix Operations & Views
# ==============================================================================


def test_matrix_supports_empty_matrix_and_empty_rows():
    assert BatchGrid.from_rows([], width=3).items == ()
    assert BatchGrid.from_rows([], width=3).row_items == ()
    assert RaggedBatchResult.from_rows([]).items == ()

    # Ragged mode supporting an empty row
    result = RaggedBatchResult.from_rows([[], [error(), "ok"]])
    assert result.row_lengths == (0, 2)
    assert list(result.iter_errors())[0][0] == (1, 0)
    assert tuple(result.iter_successes()) == (((1, 1), "ok"),)


def test_matrix_map_and_flatten_share_row_major_filtering():
    result = RaggedBatchResult.from_rows([["a", error()], ["b"]])
    mapped = result.map(str.upper)
    assert isinstance(mapped, RaggedBatchResult)
    flat = mapped.flatten()
    assert flat.successes == ["A", "B"]
    assert flat.indices(SlotState.ERROR) == (1,)
    assert mapped.successes == ["A", "B"]
    assert mapped.indices(SlotState.SUCCESS) == ((0, 0), (1, 0))


def test_row_views_distinguish_partial_cells_from_original_row_errors():
    matrix = BatchGrid[str].from_rows([["a", "b"], ["c", error()], error(2)], width=2)
    aggregate = matrix.aggregate_rows()
    original = matrix.row_result()

    assert aggregate.indices(SlotState.ERROR) == (1, 2)
    assert aggregate.successes == [("a", "b")]

    assert original.indices(SlotState.ERROR) == (2,)
    assert original.indices(SlotState.SUCCESS) == (0, 1)
    assert original.items[1] == matrix.row_items[1]
    assert original.errors[0] is matrix.row_errors[2]
    assert aggregate.errors[1].causes == (matrix.row_errors[2],)
    assert matrix.items[0] == "a"
    assert matrix.items[-1] is matrix.row_errors[2]

    mapped = matrix.map(str.upper)
    assert isinstance(mapped, BatchGrid)
    assert mapped.width == 2
    assert mapped.row_result().errors[0] is original.errors[0]
    assert mapped.aggregate_rows().successes == [("A", "B")]


# ==============================================================================
# SlotState & BatchSlot Invariants
# ==============================================================================


def test_slot_factories_map_states_and_validate_invariants():
    success_slot = BatchSlot.success("val")
    assert success_slot.state is SlotState.SUCCESS
    assert success_slot.is_success
    assert success_slot.value == "val"
    assert success_slot.item_val() == "val"
    with pytest.raises(ValueError, match="has no error"):
        _ = success_slot.error

    filtered_slot = BatchSlot.filtered()
    assert filtered_slot.state is SlotState.FILTERED
    assert filtered_slot.is_filtered

    upstream_slot = BatchSlot.upstream_failed()
    assert upstream_slot.state is SlotState.UPSTREAM_FAILED
    assert upstream_slot.is_upstream_failed

    err = BatchError(tapir.Error(code=1, message="err"))
    failure_slot = BatchSlot.failure(err)
    assert failure_slot.state is SlotState.ERROR
    assert failure_slot.is_error
    assert failure_slot.error is err
    assert failure_slot.item_val() is err

    with pytest.raises(ValueError, match="SUCCESS slot cannot contain an error"):
        BatchSlot(state=SlotState.SUCCESS, _value="ok", _error=err)
    with pytest.raises(ValueError, match="ERROR slot must contain a BatchError"):
        BatchSlot(state=SlotState.ERROR, _error=None)
    with pytest.raises(ValueError, match="UPSTREAM_FAILED slot cannot contain a value"):
        BatchSlot(state=SlotState.UPSTREAM_FAILED, _value="bad")
    with pytest.raises(ValueError, match="FILTERED slot cannot contain a value"):
        BatchSlot(state=SlotState.FILTERED, _value="bad")

    slot_ok = BatchSlot.from_raw("hello", accessor=str.upper)
    assert slot_ok.is_success
    assert slot_ok.value == "HELLO"

    slot_err = BatchSlot.from_raw(error(5))
    assert slot_err.is_error
    assert slot_err.error.code == 5

    assert slot_ok.map(lambda s: f"{s}!").value == "HELLO!"
    assert [slot.map(str).state for slot in (slot_err, filtered_slot, upstream_slot)] == [
        SlotState.ERROR,
        SlotState.FILTERED,
        SlotState.UPSTREAM_FAILED,
    ]


# ==============================================================================
# Projections (1D & 2D)
# ==============================================================================


def test_batch_result_1d_project_successes():
    source = BatchResult.from_items(["a", error(1), "b"])
    assert source.indices(SlotState.SUCCESS) == (0, 2)

    # Project 2 items onto the 2 successes: 1 succeeds, 1 fails
    projected = source.project_successes([10, error(2)])
    assert projected.count() == 3
    assert projected.slots[0].is_success and projected.slots[0].value == 10
    assert projected.slots[1].is_upstream_failed
    assert projected.slots[2].is_error and projected.slots[2].error.code == 2

    assert projected.indices(SlotState.SUCCESS) == (0,)
    assert projected.indices(SlotState.UPSTREAM_FAILED) == (1,)
    assert projected.indices(SlotState.ERROR) == (2,)
    assert projected.items == (10, None, projected.slots[2].error)

    # Count mismatch validation
    with pytest.raises(ValueError, match="Expected 2 items"):
        source.project_successes([10])


def test_batch_result_1d_project_rows():
    source = BatchResult.from_items(["a", error(1), "b"])

    # Expand to 2 columns per successful row (2 rows * 2 = 4 items)
    matrix = source.project_rows([1, 2, error(3), 4], row_length=2)
    assert isinstance(matrix, BatchResult2D)
    assert matrix.row_lengths == (2, 2, 2)

    # Row 0: Succeeded -> [1, 2]
    assert matrix.rows[0][0].value == 1
    assert matrix.rows[0][1].value == 2

    # Row 1: Upstream failed (because source was error) -> [UPSTREAM_FAILED, UPSTREAM_FAILED]
    assert matrix.rows[1][0].is_upstream_failed
    assert matrix.rows[1][1].is_upstream_failed
    assert matrix.rows[1].is_all(SlotState.UPSTREAM_FAILED)

    # Row 2: Succeeded in source, cell (2, 0) failed in raw items -> [ERROR, 4]
    assert matrix.rows[2][0].is_error and matrix.rows[2][0].error.code == 3
    assert matrix.rows[2][1].value == 4

    assert matrix.indices(SlotState.UPSTREAM_FAILED) == ((1, 0), (1, 1))
    assert matrix.indices(SlotState.ERROR) == ((2, 0),)

    with pytest.raises(ValueError, match="non-negative"):
        source.project_rows([], row_length=-1)
    with pytest.raises(ValueError, match="Expected 4 items"):
        source.project_rows([1, 2], row_length=2)


def test_batch_grid_project_successes():
    source = BatchGrid.from_rows([["a", "b"], [error(1), "c"]], width=2)
    assert len(source.successes) == 3

    # Project 3 raw items: ["x", error(2), "y"]
    projected = source.project_successes(["x", error(2), "y"])
    assert isinstance(projected, BatchGrid)
    assert projected.width == 2
    assert projected.row_lengths == (2, 2)

    # (0, 0) -> "x", (0, 1) -> error(2)
    assert projected.rows[0][0].value == "x"
    assert projected.rows[0][1].is_error and projected.rows[0][1].error.code == 2

    # (1, 0) -> UPSTREAM_FAILED (source was error), (1, 1) -> "y"
    assert projected.rows[1][0].is_upstream_failed
    assert projected.rows[1][1].value == "y"

    assert projected.has(SlotState.UPSTREAM_FAILED)
    assert projected.indices(SlotState.UPSTREAM_FAILED) == ((1, 0),)
    assert projected.indices(SlotState.SUCCESS) == ((0, 0), (1, 1))
    assert projected.indices(SlotState.ERROR) == ((0, 1),)


def test_ragged_batch_result_project_successes():
    source = RaggedBatchResult.from_rows([["a", "b"], [error(1)]])
    assert len(source.successes) == 2

    projected = source.project_successes(["x", "y"])
    assert isinstance(projected, RaggedBatchResult)
    assert projected.row_lengths == (2, 1)
    assert projected.rows[0][0].value == "x"
    assert projected.rows[0][1].value == "y"
    assert projected.rows[1][0].is_upstream_failed


# ==============================================================================
# ABC Template Methods & Failure Reporting
# ==============================================================================


def test_is_all_and_has_predicates():
    clean = BatchResult.from_items(["a", "b"])
    assert clean.is_all(SlotState.SUCCESS)
    assert clean.has(SlotState.SUCCESS)
    assert not clean.has(SlotState.ERROR)
    assert not clean.has(SlotState.FILTERED)

    mixed = BatchResult((BatchSlot.success("a"), BatchSlot.filtered()))
    assert not mixed.is_all(SlotState.SUCCESS)
    assert mixed.has(SlotState.SUCCESS)
    assert mixed.has(SlotState.FILTERED)

    empty = BatchResult.from_items([])
    assert not empty.is_all(SlotState.SUCCESS)
    assert not empty.has(SlotState.SUCCESS)
    assert empty.count() == 0


def test_raise_for_errors():
    clean = BatchResult.from_items(["ok", "fine"])
    clean.raise_for_errors("Clean operation")  # Should not raise

    failed_1d = BatchResult.from_items(["ok", error(404)])
    with pytest.raises(BatchOperationError) as raised:
        failed_1d.raise_for_errors("1D")
    assert raised.value.succeeded_count == 1
    assert raised.value.error_count == 1
    assert "1D partially failed" in str(raised.value)

    failed_2d = BatchGrid.from_rows([["ok", error(500)]], width=2)
    with pytest.raises(BatchOperationError, match=r"(?s)2D partially failed.*\[0, 1\]: \[500\] failed"):
        failed_2d.raise_for_errors("2D")


def test_raise_for_non_success_reports_every_non_success_state_and_allows_empty_results():
    BatchResult.from_items([]).raise_for_non_success("Empty batch")
    BatchResult.from_items(["ok"]).raise_for_non_success("Clean batch")

    result = BatchResult(
        (
            BatchSlot.success("ok"),
            BatchSlot.failure("invalid", code=7),
            BatchSlot.upstream_failed(),
            BatchSlot.filtered(),
        )
    )

    with pytest.raises(BatchNotFullySuccessfulError) as raised:
        result.raise_for_non_success("Dense input")

    assert raised.value.result is result
    assert raised.value.error_count == 1
    assert raised.value.upstream_failed_count == 1
    assert raised.value.filtered_count == 1
    assert "Dense input requires every item to succeed" in str(raised.value)
