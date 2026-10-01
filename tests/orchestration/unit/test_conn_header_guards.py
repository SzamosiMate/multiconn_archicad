from dataclasses import replace

import pytest
from multiconn_archicad.orchestration.header_state import HeaderState
from multiconn_archicad.orchestration.conn_header import (
    ConnHeader,
    Status,
    has_project_identity,
    is_session_ready,
    is_tapir_session_ready,
    is_header_fully_initialized,
)
from multiconn_archicad.orchestration.basic_types import (
    ProductInfo,
    ArchicadLocation,
    SoloProjectID,
    TeamworkProjectID,
    UntitledProjectID,
    TapirInfo,
    PendingResponse,
    APIResponseError,
    Port,
    TeamworkCredentials,
)
from multiconn_archicad.constants import SUPPORTED_TAPIR_VERSION
from multiconn_archicad.errors import HeaderUnassignedError

pytestmark = pytest.mark.unit


def _with_metadata(header, **fields):
    snapshot = header._state.snapshot()
    header._state = HeaderState(snapshot.status, replace(snapshot.metadata, **fields))


def _with_status(header, status):
    header._state = HeaderState(status, header._state.snapshot().metadata)


@pytest.fixture
def base_header():
    """Returns an uninitialized ConnHeader without auto-fetching."""
    return ConnHeader(initialize=False)


@pytest.fixture
def ready_identity_header(base_header):
    """Configures header with full project identity metadata."""
    _with_metadata(
        base_header,
        product_info=ProductInfo(version=27, buildNumber=3001, languageCode="INT"),
        archicad_location=ArchicadLocation(archicadLocation="C:/Archicad/ARCHICAD.exe"),
        archicad_id=SoloProjectID(projectPath="C:/Projects/Test.pln", projectName="Test.pln"),
    )
    return base_header


@pytest.fixture
def ready_session_header(ready_identity_header):
    """Configures a fully ready, session-ready header."""
    ready_identity_header.port = Port(19723)
    _with_status(ready_identity_header, Status.READY)
    _with_metadata(ready_identity_header, tapir_info=TapirInfo(version=SUPPORTED_TAPIR_VERSION))
    return ready_identity_header


# =========================================================================
# LEVEL 1: has_project_identity
# =========================================================================

def test_has_project_identity_solo(ready_identity_header):
    assert has_project_identity(ready_identity_header) is True


def test_has_project_identity_teamwork(ready_identity_header):
    _with_metadata(
        ready_identity_header,
        archicad_id=TeamworkProjectID(
            projectPath="Project",
            serverAddress="https://server.com",
            projectName="TeamworkProject",
            teamworkCredentials=TeamworkCredentials(username="user", password="secret"),
        ),
    )
    assert has_project_identity(ready_identity_header) is True


def test_has_project_identity_fails_on_untitled(ready_identity_header):
    _with_metadata(ready_identity_header, archicad_id=UntitledProjectID())
    assert has_project_identity(ready_identity_header) is False


@pytest.mark.parametrize(
    "invalid_field, placeholder",
    [
        ("product_info", PendingResponse()),
        ("archicad_location", PendingResponse()),
        ("archicad_id", APIResponseError(code=500, message="Failed")),
    ],
)
def test_has_project_identity_fails_on_unresolved_metadata(ready_identity_header, invalid_field, placeholder):
    _with_metadata(ready_identity_header, **{invalid_field: placeholder})
    assert has_project_identity(ready_identity_header) is False


def test_is_header_fully_initialized_deprecation(ready_identity_header):
    with pytest.deprecated_call():
        result = is_header_fully_initialized(ready_identity_header)
    assert result is True


# =========================================================================
# LEVEL 2: is_session_ready
# =========================================================================

def test_is_session_ready_success(ready_session_header):
    assert is_session_ready(ready_session_header) is True


def test_is_session_ready_with_uninstalled_tapir(ready_session_header):
    _with_metadata(ready_session_header, tapir_info=TapirInfo.not_installed())
    assert is_session_ready(ready_session_header) is True


@pytest.mark.parametrize("status", [Status.PENDING, Status.UNASSIGNED, Status.FAILED])
def test_is_session_ready_fails_when_not_ready(ready_session_header, status):
    _with_status(ready_session_header, status)
    assert is_session_ready(ready_session_header) is False


def test_is_session_ready_fails_when_port_is_none(ready_session_header):
    ready_session_header.unassign()
    assert is_session_ready(ready_session_header) is False


def test_is_session_ready_fails_when_tapir_unresolved(ready_session_header):
    _with_metadata(ready_session_header, tapir_info=PendingResponse())
    assert is_session_ready(ready_session_header) is False


def test_is_session_ready_fails_when_identity_missing(ready_session_header):
    _with_metadata(ready_session_header, archicad_id=UntitledProjectID())
    assert is_session_ready(ready_session_header) is False


# =========================================================================
# LEVEL 3: is_tapir_session_ready
# =========================================================================

def test_is_tapir_session_ready_success(ready_session_header):
    assert is_tapir_session_ready(ready_session_header) is True


def test_is_tapir_session_ready_fails_when_uninstalled(ready_session_header):
    _with_metadata(ready_session_header, tapir_info=TapirInfo.not_installed())
    assert is_session_ready(ready_session_header) is True
    assert is_tapir_session_ready(ready_session_header) is False


def test_is_tapir_session_ready_fails_when_version_outdated(ready_session_header):
    _with_metadata(ready_session_header, tapir_info=TapirInfo(version="0.0.1"))
    assert is_session_ready(ready_session_header) is True
    assert is_tapir_session_ready(ready_session_header) is False


def test_is_tapir_session_ready_fails_when_session_not_ready(ready_session_header):
    ready_session_header._state.begin_fetch()
    assert is_tapir_session_ready(ready_session_header) is False


def test_is_tapir_session_ready_fails_when_tapir_unresolved(ready_session_header):
    _with_metadata(ready_session_header, tapir_info=PendingResponse())
    assert is_tapir_session_ready(ready_session_header) is False


# =========================================================================
# ConnHeader Invariants & Lifecycle Transitions
# =========================================================================

def test_port_immutability():
    """
    Verifies that a ConnHeader is strictly bound to its assigned port:
    - Setting to the same port is a safe no-op.
    - Reassigning to a different port raises ValueError.
    """
    header = ConnHeader(port=Port(19723), initialize=False)

    # Same port: safe no-op
    header.port = Port(19723)
    assert header.port == Port(19723)

    # Different port: strictly forbidden
    with pytest.raises(ValueError, match="Cannot reassign ConnHeader from port 19723 to 19724"):
        header.port = Port(19724)


def test_port_lifecycle_binding_and_unassign():
    """
    Verifies the UNASSIGNED -> PENDING -> UNASSIGNED state lifecycle:
    - None -> Port: initializes sub-clients, sets PENDING, but does NOT auto-fetch.
    - Port -> None: fully unassigns, clears port, and prevents client access.
    """
    header = ConnHeader(initialize=False)
    assert header.status == Status.UNASSIGNED
    assert header.port is None

    # None -> Port (Template binding)
    header.port = Port(19723)
    assert header.status == Status.PENDING
    assert header.port == Port(19723)
    assert header._fetch_task is None  # Fetch must be explicitly invoked
    assert header.core is not None

    # Port -> None (Unassign)
    header.port = None
    assert header.status == Status.UNASSIGNED
    assert header.port is None

    with pytest.raises(HeaderUnassignedError):
        _ = header.core


def test_standard_connection_jit_binding():
    """
    Verifies that StandardConnection is stateless until ProductInfo is resolved,
    at which point accessing .standard dynamically binds JIT.
    """
    header = ConnHeader(port=Port(19723), initialize=False)

    # Unversioned initially
    assert not header.standard.is_versioned

    # Assign metadata and access property to trigger JIT binding
    _with_metadata(header, product_info=ProductInfo(version=27, buildNumber=3001, languageCode="INT"))
    assert header.standard.is_versioned
