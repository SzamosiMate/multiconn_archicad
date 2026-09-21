from __future__ import annotations

import pytest

from multiconn_archicad.utilities import (
    BatchGrid,
    BatchResult,
    BatchRow,
    BatchSlot,
    BatchStatus,
    MultiPopulationResults,
    PopulationResults,
    SlotState,
)


def test_add_population_registration() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0", "s1"])
    targets = multi.add_population("targets", ["t0", "t1", "t2"])

    assert isinstance(sources, PopulationResults)
    assert len(multi.populations) == 2
    assert multi["sources"] is sources
    assert multi["targets"] is targets


def test_add_population_invalid_names() -> None:
    multi = MultiPopulationResults()
    multi.add_population("sources", ["s0"])

    with pytest.raises(ValueError, match="already registered"):
        multi.add_population("sources", ["s1"])

    with pytest.raises(ValueError, match="non-empty string"):
        multi.add_population("", ["s0"])


def test_relate_validates_membership() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0"])
    foreign = PopulationResults(["f0"])

    with pytest.raises(ValueError, match="must be registered"):
        multi.relate(sources, foreign, [(0, 0)])


def test_relate_bounds_checking() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0", "s1"])
    targets = multi.add_population("targets", ["t0", "t1"])

    with pytest.raises(IndexError, match="out of bounds"):
        multi.relate(sources, targets, [(2, 0)])  # source index 2 >= 2

    with pytest.raises(IndexError, match="out of bounds"):
        multi.relate(sources, targets, [(0, -1)])  # negative target index


def test_relate_deduplication_and_queries() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0", "s1"])
    targets = multi.add_population("targets", ["t0", "t1", "t2"])

    # Source 0 matches Target 0 and Target 1; Source 1 matches Target 2.
    # Include duplicate pair (0, 0)
    matching = multi.relate(sources, targets, [(0, 0), (0, 1), (0, 0), (1, 2)])

    assert len(matching.pairs) == 3
    assert matching.targets_for_source(0) == (0, 1)
    assert matching.targets_for_source(1) == (2,)
    assert matching.sources_for_target(0) == (0,)
    assert matching.sources_for_target(1) == (0,)
    assert matching.sources_for_target(2) == (1,)
    assert matching.sources_for_target(999) == ()


def test_project_1d_with_default_filtered() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0", "s1"])
    targets = multi.add_population("targets", ["t0", "t1", "t2"])

    # t0 <- s0, t1 <- s0, t2 is unmatched
    matching = multi.relate(sources, targets, [(0, 0), (0, 1)])

    read_result = BatchResult.from_items(["val_s0", "val_s1"])
    projected = matching.project(read_result)

    assert len(projected.slots) == 3
    assert projected.slots[0].value == "val_s0"
    assert projected.slots[1].value == "val_s0"
    assert projected.slots[2].is_filtered


def test_project_1d_custom_unmatched() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0"])
    targets = multi.add_population("targets", ["t0", "t1"])

    matching = multi.relate(sources, targets, [(0, 0)])
    read = BatchResult.from_items(["A"])

    # Upstream failed
    proj_upstream = matching.project(read, unmatched=SlotState.UPSTREAM_FAILED)
    assert proj_upstream.slots[1].is_upstream_failed

    # Fallback value slot
    proj_custom = matching.project(read, unmatched=BatchSlot.success("DEFAULT"))
    assert proj_custom.slots[1].value == "DEFAULT"


def test_project_ambiguous_matching_raises() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0", "s1"])
    targets = multi.add_population("targets", ["t0"])

    # Multiple sources match target 0
    matching = multi.relate(sources, targets, [(0, 0), (1, 0)])
    read = BatchResult.from_items(["A", "B"])

    with pytest.raises(ValueError, match="ambiguous"):
        matching.project(read)


def test_project_rows_2d_broadcasting() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0", "s1"])
    targets = multi.add_population("targets", ["t0", "t1", "t2"])

    # t0 <- s0, t1 unmatched, t2 <- s1
    matching = multi.relate(sources, targets, [(0, 0), (1, 2)])

    source_grid = BatchGrid.from_rows(
        [
            ["A0", "B0"],
            ["A1", "B1"],
        ],
        width=2,
    )

    # Broadcast default FILTERED across unmatched row
    target_grid = matching.project_rows(source_grid)

    assert isinstance(target_grid, BatchGrid)
    assert target_grid.width == 2
    assert len(target_grid.rows) == 3

    assert [s.value for s in target_grid.rows[0].slots] == ["A0", "B0"]
    assert target_grid.rows[1].is_all(SlotState.FILTERED)
    assert [s.value for s in target_grid.rows[2].slots] == ["A1", "B1"]


def test_project_rows_custom_row() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0"])
    targets = multi.add_population("targets", ["t0", "t1"])

    matching = multi.relate(sources, targets, [(0, 0)])
    grid = BatchGrid.from_rows([["A", "B"]], width=2)

    custom_row = BatchRow((BatchSlot.upstream_failed(), BatchSlot.upstream_failed()))
    res = matching.project_rows(grid, default_state=custom_row)
    assert res.rows[1].is_all(SlotState.UPSTREAM_FAILED)

    # Mismatched row width
    bad_row = BatchRow((BatchSlot.filtered(),))
    with pytest.raises(ValueError, match="does not match matrix width"):
        matching.project_rows(grid, default_state=bad_row)


def test_snapshot_completed_and_immutability() -> None:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", ["s0"])
    targets = multi.add_population("targets", ["t0"])

    sources.record("Read", BatchResult.from_items(["val"]))
    targets.record("Write", BatchResult.from_items(["ok"]))

    # Snapshot incomplete
    snap_incom = multi.snapshot(completed=False)
    assert snap_incom["sources"].status is BatchStatus.INCOMPLETE
    assert snap_incom["targets"].status is BatchStatus.INCOMPLETE

    # Snapshot completed
    snap_comp = multi.snapshot(completed=True)
    assert snap_comp["sources"].status is BatchStatus.SUCCEEDED
    assert snap_comp["targets"].status is BatchStatus.SUCCEEDED

    # Recording after snapshot does not mutate earlier snapshots
    targets.record("Extra", BatchResult.from_items(["extra"]))
    assert len(snap_comp["targets"].steps) == 1
    assert len(targets.steps) == 2