from dataclasses import replace

import pytest

from multiconn_archicad.orchestration.basic_types import (
    APIResponseError,
    ArchicadLocation,
    ProductInfo,
    SoloProjectID,
    TapirInfo,
)
from multiconn_archicad.orchestration.header_state import HeaderMetadata, HeaderSnapshot, HeaderState, Status

pytestmark = pytest.mark.unit


@pytest.fixture
def metadata():
    return HeaderMetadata(
        product_info=ProductInfo(version=27, buildNumber=3001, languageCode="INT"),
        archicad_id=SoloProjectID(projectPath="C:/Projects/Test.pln", projectName="Test"),
        archicad_location=ArchicadLocation(archicadLocation="C:/Archicad/ARCHICAD.exe"),
        tapir_info=TapirInfo.not_installed(),
    )


def test_refresh_replaces_metadata_without_changing_previous_snapshot(metadata):
    state = HeaderState(Status.PENDING)
    partial = replace(metadata, archicad_id=APIResponseError(message="no project"))
    state.complete(state.begin_fetch(), partial)
    before = state.snapshot()

    updated = replace(metadata, product_info=ProductInfo(version=28, buildNumber=4000, languageCode="INT"))
    state.complete(state.begin_fetch(), updated)

    assert before == HeaderSnapshot(Status.READY, partial, partial)
    assert state.snapshot() == HeaderSnapshot(Status.READY, updated, updated)


@pytest.mark.parametrize("unexpected_failure", [False, True])
def test_failed_refresh_preserves_successful_metadata(metadata, unexpected_failure):
    state = HeaderState(Status.READY, metadata)
    error = APIResponseError(message="not responding")
    fetched = None if unexpected_failure else HeaderMetadata(error, error, error, error)
    token = state.begin_fetch()
    state.complete(token, fetched)

    assert state.snapshot() == HeaderSnapshot(Status.FAILED, metadata, fetched)
    assert state.resolved_token() is token


def test_cancel_invalidates_completed_fetch_without_clearing_metadata(metadata):
    state = HeaderState(Status.PENDING)
    token = state.begin_fetch()
    state.complete(token, metadata)
    state.cancel()

    assert not state.complete(token, None)
    assert state.snapshot() == HeaderSnapshot(Status.READY, metadata)
    assert state.resolved_token() is None


def test_latest_metadata_is_cleared_on_refresh_and_stale_fetch_cannot_restore_it(metadata):
    state = HeaderState(Status.PENDING)
    old_token = state.begin_fetch()
    state.complete(old_token, metadata)
    current_token = state.begin_fetch()
    assert state.snapshot().metadata == metadata
    assert state.snapshot().latest_metadata is None
    assert not state.complete(old_token, metadata)
    assert state.snapshot().latest_metadata is None

    current = replace(metadata, archicad_id=APIResponseError(message="project query failed"))
    state.complete(current_token, current)
    assert state.snapshot().metadata == metadata
    assert state.snapshot().latest_metadata == current


@pytest.mark.parametrize("operation", ["cancel", "unassign", "assign"])
def test_lifecycle_reset_clears_latest_metadata_but_preserves_history(metadata, operation):
    state = HeaderState(Status.PENDING)
    state.complete(state.begin_fetch(), metadata)
    getattr(state, operation)()
    assert state.snapshot().metadata == metadata
    assert state.snapshot().latest_metadata is None


def test_unassign_and_reassign_preserve_project_identity(metadata):
    state = HeaderState(Status.READY, metadata)
    token = state.begin_fetch()
    state.unassign()

    assert not state.complete(token, None)
    assert state.snapshot() == HeaderSnapshot(Status.UNASSIGNED, metadata)

    state.assign()
    assert state.snapshot() == HeaderSnapshot(Status.PENDING, metadata)
    assert state.resolved_token() is None
