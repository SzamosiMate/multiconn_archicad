import pytest
import time
from unittest.mock import MagicMock

from multiconn_archicad import MultiConn, Port, ConnHeader
from multiconn_archicad.errors import StandardAPIError, TapirCommandError, CommandTimeoutError

pytestmark = [
    pytest.mark.usefixtures("archicad_api"),
    pytest.mark.integration,
]


def test_successful_core_post_tapir_command(archicad_api):
    """
    Verifies that a successful async tapir command returns the parsed 'result' dict.
    (Test Case Plan 3.1)
    """
    # ARRANGE
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()

    # ACT
    result = conn.core.post_tapir_command("GetProjectInfo")

    # ASSERT
    assert isinstance(result, dict)
    assert result.get("projectName") == "My Solo Project.pln"
    assert "succeeded" not in result
    assert "addOnCommandResponse" not in result


def test_iterating_active_connections_to_run_commands(archicad_api):
    """
    Verifies the pattern of iterating over multiple active connections.
    """
    # ARRANGE
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()

    # Manually add a second connection to simulate multiple instances
    original_header = conn.open_port_headers[archicad_api.server_port]
    second_header = ConnHeader.from_dict(original_header.to_dict())
    second_port = Port(19742)
    second_header.port = second_port

    second_header.core.post_tapir_command = MagicMock(return_value={"projectName": "Simulated Project"})

    conn.open_port_headers[second_port] = second_header

    conn.connect.all()
    assert len(conn.active) == 2

    # ACT
    results = {
        port: header.core.post_tapir_command("GetProjectInfo")
        for port, header in conn.active.items()
    }

    # ASSERT
    assert len(results) == 2
    assert "projectName" in results[archicad_api.server_port]
    assert results[second_port] == {"projectName": "Simulated Project"}



def test_standard_api_error_is_raised(archicad_api):
    """
    Verifies that StandardAPIError is raised for a failed standard command.
    (Test Case Plan 4.1)
    """
    # ARRANGE
    archicad_api.set_response("API.GetAttributesByType", "standard_api_error.json")
    archicad_api.set_response("GetProjectInfo", "get_project_info_teamwork.json")
    conn = MultiConn()

    # ACT & ASSERT
    with pytest.raises(StandardAPIError) as exc_info:
        conn.core.post_command("API.GetAttributesByType")

    assert exc_info.value.code == 1234
    assert "A standard API error occurred" in exc_info.value.message



def test_tapir_command_error_is_raised(archicad_api):
    """
    Verifies that TapirCommandError is raised for a failed Tapir command.
    (Test Case Plan 4.2)
    """
    # ARRANGE
    archicad_api.set_response("DeleteElements", "tapir_command_error.json")
    archicad_api.set_response("GetProjectInfo", "get_project_info_untitled.json")
    conn = MultiConn()

    # ACT & ASSERT
    with pytest.raises(TapirCommandError) as exc_info:
        conn.core.post_tapir_command("DeleteElements", {"elements": []})

    assert exc_info.value.code == 5678
    assert "A Tapir add-on command failed" in exc_info.value.message


def test_command_timeout_error_is_raised(archicad_api):
    """
    Verifies that CommandTimeoutError is raised when a request exceeds the timeout.
    """
    # ARRANGE
    def timeout_handler(payload: dict) -> dict:
        time.sleep(0.5)
        return {"succeeded": True, "result": {}}

    archicad_api.set_handler("Test.Timeout", timeout_handler)
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn()

    # ACT & ASSERT
    with pytest.raises(CommandTimeoutError):
        conn.core.post_command("Test.Timeout", timeout=0.1)