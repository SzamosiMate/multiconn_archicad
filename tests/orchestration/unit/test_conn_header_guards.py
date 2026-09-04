import pytest
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

pytestmark = pytest.mark.unit


@pytest.fixture
def base_header():
    """Returns an uninitialized ConnHeader without auto-fetching."""
    return ConnHeader(initialize=False)


@pytest.fixture
def ready_identity_header(base_header):
    """Configures header with full project identity metadata."""
    base_header._product_info = ProductInfo(version=27, buildNumber=3001, languageCode="INT")
    base_header._archicad_location = ArchicadLocation(archicadLocation="C:/Archicad/ARCHICAD.exe")
    base_header._archicad_id = SoloProjectID(
        projectPath="C:/Projects/Test.pln", projectName="Test.pln"
    )
    return base_header


@pytest.fixture
def ready_session_header(ready_identity_header):
    """Configures a fully active, session-ready header."""
    # Using public port setter initializes _core, _standard, and _unified
    ready_identity_header.port = Port(19723)
    ready_identity_header._status = Status.ACTIVE
    ready_identity_header._tapir_info = TapirInfo(version=SUPPORTED_TAPIR_VERSION)
    return ready_identity_header


# =========================================================================
# LEVEL 1: has_project_identity
# =========================================================================

def test_has_project_identity_solo(ready_identity_header):
    assert has_project_identity(ready_identity_header) is True


def test_has_project_identity_teamwork(ready_identity_header):
    ready_identity_header._archicad_id = TeamworkProjectID(
        projectPath="Project",
        serverAddress="https://server.com",
        projectName="TeamworkProject",
        teamworkCredentials=TeamworkCredentials(username="user", password="secret"),
    )
    assert has_project_identity(ready_identity_header) is True


def test_has_project_identity_fails_on_untitled(ready_identity_header):
    ready_identity_header._archicad_id = UntitledProjectID()
    assert has_project_identity(ready_identity_header) is False


@pytest.mark.parametrize(
    "invalid_field, placeholder",
    [
        ("_product_info", PendingResponse()),
        ("_archicad_location", PendingResponse()),
        ("_archicad_id", APIResponseError(code=500, message="Failed")),
    ],
)
def test_has_project_identity_fails_on_unresolved_metadata(ready_identity_header, invalid_field, placeholder):
    setattr(ready_identity_header, invalid_field, placeholder)
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
    ready_session_header._tapir_info = TapirInfo.not_installed()
    assert is_session_ready(ready_session_header) is True


@pytest.mark.parametrize("status", [Status.PENDING, Status.UNASSIGNED, Status.FAILED])
def test_is_session_ready_fails_when_not_active(ready_session_header, status):
    ready_session_header._status = status
    assert is_session_ready(ready_session_header) is False


def test_is_session_ready_fails_when_port_is_none(ready_session_header):
    ready_session_header._port = None
    assert is_session_ready(ready_session_header) is False


def test_is_session_ready_fails_when_tapir_unresolved(ready_session_header):
    ready_session_header._tapir_info = PendingResponse()
    assert is_session_ready(ready_session_header) is False


def test_is_session_ready_fails_when_identity_missing(ready_session_header):
    ready_session_header._archicad_id = UntitledProjectID()
    assert is_session_ready(ready_session_header) is False


# =========================================================================
# LEVEL 3: is_tapir_session_ready
# =========================================================================

def test_is_tapir_session_ready_success(ready_session_header):
    assert is_tapir_session_ready(ready_session_header) is True


def test_is_tapir_session_ready_fails_when_uninstalled(ready_session_header):
    ready_session_header._tapir_info = TapirInfo.not_installed()
    assert is_session_ready(ready_session_header) is True
    assert is_tapir_session_ready(ready_session_header) is False


def test_is_tapir_session_ready_fails_when_version_outdated(ready_session_header):
    ready_session_header._tapir_info = TapirInfo(version="0.0.1")
    assert is_session_ready(ready_session_header) is True
    assert is_tapir_session_ready(ready_session_header) is False


def test_is_tapir_session_ready_fails_when_session_not_ready(ready_session_header):
    ready_session_header._status = Status.PENDING
    assert is_tapir_session_ready(ready_session_header) is False