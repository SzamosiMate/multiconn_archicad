import pytest

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.orchestration.conn_header import Status

pytestmark = [
    pytest.mark.usefixtures("archicad_api"),
    pytest.mark.usefixtures("fuzz_threads"),
    pytest.mark.integration,
]


def test_no_running_archicad_and_no_port_arg(monkeypatch):
    """
    Verifies that with no running AC and no port argument, primary is None.
    """

    class EmptyArgs:
        host = "http://127.0.0.1"
        port = None

    monkeypatch.setattr("multiconn_archicad.orchestration.system.cli_parser.get_cli_args_once", lambda: EmptyArgs())
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.MultiConn._port_range", [])

    conn = MultiConn()
    assert len(conn.open_port_headers) == 0
    assert conn.primary is None


def test_init_with_invalid_port_raises_error(monkeypatch):
    """
    Verifies that providing a port with no running AC raises an error immediately.
    """

    class EmptyArgs:
        host = "http://127.0.0.1"
        port = None

    monkeypatch.setattr("multiconn_archicad.orchestration.system.cli_parser.get_cli_args_once", lambda: EmptyArgs())
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.MultiConn._port_range", [])

    with pytest.raises(KeyError, match="Failed to set primary"):
        MultiConn(port=Port(19723))


def test_discover_single_instance(archicad_api):
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()
    assert len(conn.open_port_headers) == 1

    managed_header = conn.open_port_headers[archicad_api.server_port]
    assert conn.primary is managed_header
    assert conn.primary.status == Status.READY
    assert archicad_api.server_port not in conn.active


def test_batch_worklist_connect_and_disconnect(archicad_api):
    """
    Verifies adding and removing headers from the active batch worklist
    without mutating the header's READY status or primary reference.
    """
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()
    port = archicad_api.server_port
    managed_header = conn.open_port_headers[port]

    # Connect adds to batch list
    conn.connect.all()
    assert port in conn.active
    assert conn.active[port] is managed_header
    assert managed_header.status == Status.READY

    # Disconnect via header removes from batch list
    conn.disconnect.from_headers(managed_header)
    assert port not in conn.active
    assert managed_header.status == Status.READY
    assert conn.primary is managed_header

    # Re-add and disconnect.all()
    conn.connect.all()
    assert port in conn.active
    conn.disconnect.all()
    assert port not in conn.active
    assert conn.primary is managed_header


def test_failed_metadata_populates_failed_queue_and_can_connect(slow_archicad_api):
    """
    Verifies that handshake failure marks the header FAILED in conn.failed,
    and conn.connect.failed() adds it to the active worklist for retry.
    """
    slow_archicad_api.set_handler("API.GetProductInfo", lambda p: {"succeeded": False, "error": {"code": 500}})

    conn = MultiConn()
    port = slow_archicad_api.server_port
    _ = conn.primary.product_info

    assert port in conn.failed
    assert port not in conn.ready
    assert conn.failed[port].status == Status.FAILED
    assert port not in conn.active

    conn.connect.failed()
    assert port in conn.active
    assert conn.active[port] is conn.failed[port]


def test_refresh_detects_closed_instance(archicad_api):
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = MultiConn()
    assert len(conn.open_port_headers) == 1

    archicad_api.http_server.shutdown()
    archicad_api.http_server.server_close()

    conn.refresh.all_ports()

    assert len(conn.open_port_headers) == 0
    assert conn.primary is None


def test_quit_all_sends_command_and_removes_header(archicad_api):
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    archicad_api.set_response("QuitArchicad", "success_empty_tapir.json")
    conn = MultiConn()

    header_to_quit = conn.open_port_headers[archicad_api.server_port]
    conn.primary = archicad_api.server_port
    primary_changes = []
    conn.events.subscribe_primary_changed(lambda previous, current: primary_changes.append((previous, current)))
    processed_headers = conn.quit.all()

    assert len(processed_headers) == 1
    assert processed_headers[0] is header_to_quit
    assert len(conn.open_port_headers) == 0
    assert header_to_quit.status == Status.UNASSIGNED
    assert header_to_quit.port is None
    assert any(previous is header_to_quit and current is None for previous, current in primary_changes)
