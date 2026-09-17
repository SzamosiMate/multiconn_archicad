from __future__ import annotations

import pytest

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities import BatchResult, BatchResult2D
from multiconn_archicad.utilities.results import BatchError, BatchRow, BatchSlot, SlotState


def error(code: int = 1):
    return tapir.ErrorItem(error=tapir.Error(code=code, message="failed"))


# ==============================================================================
# 1D Result Tests
# ==============================================================================


def test_one_dimensional_slots_allow_none_and_expose_indices():
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


@pytest.mark.parametrize("item", [error(), tapir.Error(code=2, message="direct")])
def test_error_normalization_preserves_typed_api_error_identity(item):
    result = BatchResult.from_items([item])
    assert result.slots[0].error.error is (item.error if isinstance(item, tapir.ErrorItem) else item)


def test_one_dimensional_map_skips_error_and_propagates_callback_exception():
    result = BatchResult.from_items(["ok", error()])
    assert result.map(str.upper).successes == ["OK"]
    with pytest.raises(ZeroDivisionError):
        BatchResult.from_items(["ok"]).map(lambda _: 1 / 0)


# ==============================================================================
# 2D Result Construction & Mode Enforcement
# ==============================================================================


def test_from_rows_requires_width():
    with pytest.raises(TypeError):
        BatchResult2D.from_rows([["a", "b"]])  # type: ignore[call-arg]


@pytest.mark.parametrize("invalid_width", [0, -1, -5])
def test_from_rows_rejects_non_positive_width(invalid_width):
    with pytest.raises(ValueError, match="width must be a positive integer"):
        BatchResult2D.from_rows([["a"]], width=invalid_width)


def test_rectangular_mode_enforces_width_and_expands_whole_row_errors():
    # Sequence length mismatch raises immediately
    with pytest.raises(ValueError, match="does not match specified width"):
        BatchResult2D.from_rows([["a", "b"], ["c"]], width=2)

    # Whole-row error expands to width slots
    matrix = BatchResult2D.from_rows([error(1), ["a", "b"]], width=2)
    assert matrix.row_lengths == (2, 2)
    assert matrix.indices(SlotState.ERROR) == ((0, 0), (0, 1))
    assert matrix.rows[0].error is not None
    assert matrix.rows[0].error.code == 1
    assert matrix.rows[0][0].error is matrix.rows[0].error
    assert matrix.rows[0][1].error is matrix.rows[0].error

    # 100% error data succeeds without crashing
    all_err = BatchResult2D.from_rows([error(1), error(2)], width=3)
    assert all_err.row_lengths == (3, 3)
    assert all_err.count(SlotState.ERROR) == 6
    assert all_err.is_all(SlotState.ERROR)


def test_ragged_mode_infers_lengths_and_defaults_errors_to_one():
    result = BatchResult2D.from_ragged_rows([["a", "b"], error(1), ["c", "d", "e"]])
    assert result.row_lengths == (2, 1, 3)
    assert result.indices(SlotState.ERROR) == ((1, 0),)
    assert result.rows[1].error is not None
    assert result.rows[1].error.code == 1

    # 100% error data in ragged mode defaults each row to 1 slot
    all_err_ragged = BatchResult2D.from_ragged_rows([error(1), error(2)])
    assert all_err_ragged.row_lengths == (1, 1)
    assert all_err_ragged.count(SlotState.ERROR) == 2


@pytest.mark.parametrize("bad_row", ["hello", b"binary"])
def test_strings_and_bytes_rejected_as_rows(bad_row):
    with pytest.raises(TypeError, match="must be a sequence or a typed API error"):
        BatchResult2D.from_rows([bad_row], width=len(bad_row))

    with pytest.raises(TypeError, match="must be a sequence or a typed API error"):
        BatchResult2D.from_ragged_rows([bad_row])


# ==============================================================================
# 2D Matrix Operations & Views
# ==============================================================================


def test_matrix_supports_empty_matrix_and_empty_rows():
    assert BatchResult2D.from_rows([], width=3).items == ()
    assert BatchResult2D.from_rows([], width=3).row_items == ()
    assert BatchResult2D.from_ragged_rows([]).items == ()

    # Ragged mode supporting an empty row
    result = BatchResult2D.from_ragged_rows([[], [error(), "ok"]])
    assert result.row_lengths == (0, 2)
    assert list(result.iter_errors())[0][0] == (1, 0)
    assert tuple(result.iter_successes()) == (((1, 1), "ok"),)


def test_items_and_error_iteration_share_expanded_cells():
    result = BatchResult2D.from_rows([["ok", error()], error(2)], width=2)
    row_items = result.row_items
    assert tuple(map(len, row_items)) == (2, 2)
    assert row_items[0][0] == "ok"
    assert row_items[0][1] is result.rows[0][1].error
    assert all(item is result.row_errors[1] for item in row_items[1])
    assert result.indices(SlotState.ERROR) == ((0, 1), (1, 0), (1, 1))

    # Flat items view inherited from BatchResultBase
    assert result.items == ("ok", result.rows[0][1].error, result.rows[1][0].error, result.rows[1][1].error)

    rebuilt = BatchResult2D.from_rows(row_items, width=2)
    assert rebuilt.count(SlotState.ERROR) == 3
    assert rebuilt.row_items == row_items


def test_matrix_map_and_flatten_share_row_major_filtering():
    result = BatchResult2D.from_ragged_rows([["a", error()], ["b"]])
    mapped = result.map(str.upper)
    flat = mapped.flatten()
    assert flat.successes == ["A", "B"]
    assert flat.indices(SlotState.ERROR) == (1,)
    assert mapped.successes == ["A", "B"]
    assert mapped.indices(SlotState.SUCCESS) == ((0, 0), (1, 0))
    with pytest.raises(ZeroDivisionError):
        BatchResult2D.from_rows([["a"]], width=1).map(lambda _: 1 / 0)


def test_row_views_distinguish_partial_cells_from_original_row_errors():
    matrix = BatchResult2D[str].from_rows([["a", "b"], ["c", error()], error(2)], width=2)
    aggregate = matrix.aggregate_rows()
    original = matrix.row_result()

    assert aggregate.indices(SlotState.ERROR) == (1, 2)
    assert aggregate.successes == [("a", "b")]

    assert original.indices(SlotState.ERROR) == (2,)
    assert original.indices(SlotState.SUCCESS) == (0, 1)
    assert original.items[1] == matrix.row_items[1]
    assert original.errors[0] is matrix.row_errors[2]
    assert aggregate.errors[1].causes == (matrix.row_errors[2],)

    mapped = matrix.map(str.upper)
    assert mapped.row_result().errors[0] is original.errors[0]
    assert mapped.aggregate_rows().successes == [("A", "B")]


# ==============================================================================
# SlotState & BatchSlot Invariants
# ==============================================================================


def test_slot_state_factories_and_invariants():
    success_slot = BatchSlot.success("val")
    assert success_slot.state is SlotState.SUCCESS
    assert success_slot.is_success
    assert not success_slot.is_error
    assert not success_slot.is_upstream_failed
    assert not success_slot.is_filtered
    assert success_slot.value == "val"
    assert success_slot.item_val() == "val"
    with pytest.raises(ValueError, match="has no error"):
        _ = success_slot.error

    filtered_slot = BatchSlot.filtered()
    assert filtered_slot.state is SlotState.FILTERED
    assert filtered_slot.is_filtered
    assert not filtered_slot.is_success

    upstream_slot = BatchSlot.upstream_failed()
    assert upstream_slot.state is SlotState.UPSTREAM_FAILED
    assert upstream_slot.is_upstream_failed
    assert not upstream_slot.is_success

    err = BatchError(tapir.Error(code=1, message="err"))
    failure_slot = BatchSlot.failure(err)
    assert failure_slot.state is SlotState.ERROR
    assert failure_slot.is_error
    assert failure_slot.error is err
    assert failure_slot.item_val() is err
    with pytest.raises(ValueError, match="has no successful value"):
        _ = failure_slot.value

    # Invariant violations
    with pytest.raises(ValueError, match="SUCCESS slot cannot contain an error"):
        BatchSlot(state=SlotState.SUCCESS, _value="ok", _error=err)
    with pytest.raises(ValueError, match="ERROR slot must contain a BatchError"):
        BatchSlot(state=SlotState.ERROR, _error=None)
    with pytest.raises(ValueError, match="UPSTREAM_FAILED slot cannot contain a value"):
        BatchSlot(state=SlotState.UPSTREAM_FAILED, _value="bad")
    with pytest.raises(ValueError, match="FILTERED slot cannot contain a value"):
        BatchSlot(state=SlotState.FILTERED, _value="bad")


def test_slot_from_raw_and_map():
    slot_ok = BatchSlot.from_raw("hello", accessor=str.upper)
    assert slot_ok.is_success
    assert slot_ok.value == "HELLO"

    slot_err = BatchSlot.from_raw(error(5))
    assert slot_err.is_error
    assert slot_err.error.code == 5

    assert slot_ok.map(lambda s: f"{s}!").value == "HELLO!"
    assert slot_err.map(lambda s: s).is_error
    assert BatchSlot.filtered().map(lambda s: s).is_filtered
    assert BatchSlot.upstream_failed().map(lambda s: s).is_upstream_failed


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


def test_batch_result_2d_project_successes():
    source = BatchResult2D.from_rows([["a", "b"], [error(1), "c"]], width=2)
    assert len(source.successes) == 3

    # Project 3 raw items: ["x", error(2), "y"]
    projected = source.project_successes(["x", error(2), "y"])
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


def test_batch_result_2d_aggregate_rows_with_skips():
    slot_ok_a = BatchSlot.success("a")
    slot_ok_b = BatchSlot.success("b")
    slot_filtered = BatchSlot.filtered()

    row_ok = BatchRow((slot_ok_a, slot_ok_b))
    row_filtered = BatchRow((slot_filtered, slot_ok_b))
    row_err = BatchRow((BatchSlot.from_raw(error(1)), slot_ok_b))

    matrix = BatchResult2D((row_ok, row_filtered, row_err))
    aggregate = matrix.aggregate_rows()

    assert aggregate.slots[0].is_success
    assert aggregate.slots[1].is_filtered
    assert aggregate.slots[2].is_error


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
    with pytest.raises(BatchOperationError, match=r"1D failed with 1 error\(s\):\n  - \[1\]: \[404\] failed"):
        failed_1d.raise_for_errors("1D")

    failed_2d = BatchResult2D.from_rows([["ok", error(500)]], width=2)
    with pytest.raises(BatchOperationError, match=r"2D failed with 1 error\(s\):\n  - \[0, 1\]: \[500\] failed"):
        failed_2d.raise_for_errors("2D")