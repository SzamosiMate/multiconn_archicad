import pytest
import threading
from unittest.mock import MagicMock, patch
import psutil


from multiconn_archicad import MultiConn, ConnHeader, Port
from multiconn_archicad.basic_types import TeamworkProjectID, SoloProjectID


pytestmark = [
    pytest.mark.usefixtures("archicad_api"),
    pytest.mark.integration,
]



def test_find_archicad_from_header_success(archicad_api):
    """
    Verifies that find_archicad can locate a running instance from a deserialized header.
    (Test Case Plan 5.1)
    """
    # ARRANGE
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()

    # Simulate saving and loading a header
    original_header = conn.open_port_headers[archicad_api.server_port]
    header_dict = original_header.to_dict()
    deserialized_header = ConnHeader.from_dict(header_dict)

    assert original_header == deserialized_header

    # ACT
    found_port = conn.find_archicad.from_header(deserialized_header)

    # ASSERT
    assert found_port is not None
    assert found_port == archicad_api.server_port


def test_switch_project_success(archicad_api):
    # ARRANGE
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()
    original_port = archicad_api.server_port
    original_header = conn.open_port_headers[original_port]

    assert isinstance(original_header.archicad_id, SoloProjectID)

    open_project_called = threading.Event()

    def open_project_handler(payload: dict) -> dict:
        archicad_api.set_response("GetProjectInfo", "get_project_info_teamwork.json")
        open_project_called.set()
        return {"succeeded": True, "result": {"addOnCommandResponse": {"success": True}}}

    archicad_api.set_handler("OpenProject", open_project_handler)

    # ACT
    new_header_state = conn.switch_project.from_path(original_port, "C:/fake/new/project.pln")

    # ASSERT
    assert open_project_called.wait(timeout=1.0), "Command never sent!"

    assert new_header_state is not original_header
    assert conn.open_port_headers[original_port] is new_header_state
    assert isinstance(new_header_state.archicad_id, TeamworkProjectID)


@patch("multiconn_archicad.actions.project_handler.subprocess.Popen")
@patch("multiconn_archicad.actions.project_handler.psutil.Process")
@patch("multiconn_archicad.actions.refresh")
@patch("multiconn_archicad.multi_conn.get_cli_args_once")
def test_open_project_calls_dependencies_correctly(
    mock_get_cli_args, mock_refresh, mock_psutil_process, mock_popen, archicad_api
):
    """
    Verifies that open_project calls Popen and psutil correctly without
    actually starting a process. (Test Case Plan 5.3)
    """
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")  # Fixes the warning!

    # Mock the CLI args...
    mock_get_cli_args.return_value.port = None
    mock_get_cli_args.return_value.host = f"http://{archicad_api.server_host}"

    conn = MultiConn()
    conn.dialog_handler.start = MagicMock()

    # Configure mock for Popen
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_popen.return_value = mock_process

    # Configure mock for psutil
    mock_psutil_instance = MagicMock()

    new_port = Port(archicad_api.server_port)
    mock_conn_obj = MagicMock()
    mock_conn_obj.status = psutil.CONN_LISTEN
    mock_conn_obj.laddr.port = new_port

    mock_psutil_instance.net_connections.side_effect = [[], [], [mock_conn_obj]]
    mock_psutil_process.return_value = mock_psutil_instance

    # Prepare a header to open
    header_to_open = ConnHeader.from_dict(
        {
            "port": 19723,  # This port is just a placeholder in the saved data
            "productInfo": {"version": 27, "build": 3001, "lang": "INT"},
            "archicadId": {"projectPath": "C:\\path\\to\\project.pln", "projectName": "My Test Project.pln"},
            "archicadLocation": {"archicadLocation": "C:\\Archicad\\ARCHICAD.exe"},
        }
    )

    # ACT
    opened_port = conn.open_project.from_header(header_to_open)

    # ASSERT
    assert opened_port == new_port

    # 1. Verify subprocess.Popen was called correctly
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]
    assert "C:\\Archicad\\ARCHICAD.exe" in call_args
    assert "C:\\path\\to\\project.pln" in call_args

    # 2. Verify dialog handler was started
    conn.dialog_handler.start.assert_called_once_with(mock_process)

    # 3. Verify psutil was used to find the port
    mock_psutil_process.assert_called_once_with(12345)
    assert mock_psutil_instance.net_connections.call_count == 3

    # 4. Verify a new header was added for the new port
    assert new_port in conn.open_port_headers