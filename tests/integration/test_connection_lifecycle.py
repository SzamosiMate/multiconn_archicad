import pytest
import asyncio

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.conn_header import Status
import multiconn_archicad.utilities.cli_parser as cli_parser

pytestmark = [
    pytest.mark.usefixtures("archicad_api"),
    pytest.mark.integration,
]


def test_no_running_archicad_and_no_port_arg(monkeypatch):
    """
    Verifies that with no running AC and no port argument, primary is None.
    """
    # ARRANGE
    cli_parser._parsed_cli_args_cache = None
    monkeypatch.setattr("multiconn_archicad.multi_conn.MultiConn._port_range", [])

    # ACT
    conn = MultiConn()

    # ASSERT
    assert len(conn.open_port_headers) == 0
    assert conn.primary is None


def test_init_with_invalid_port_raises_error(monkeypatch):
    """
    Verifies that providing a port with no running AC raises an error immediately.
    """
    # ARRANGE
    cli_parser._parsed_cli_args_cache = None
    monkeypatch.setattr("multiconn_archicad.multi_conn.MultiConn._port_range", [])

    # ACT & ASSERT
    with pytest.raises(KeyError, match="Failed to set primary"):
        MultiConn(port=Port(19723))


@pytest.mark.asyncio
async def test_discover_single_instance(archicad_api):
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = await asyncio.to_thread(MultiConn)
    assert len(conn.open_port_headers) == 1
    managed_header = conn.open_port_headers[archicad_api.server.port]
    assert managed_header.status == Status.PENDING
    assert conn.primary is not None
    assert conn.primary.status == Status.ACTIVE


@pytest.mark.asyncio
async def test_connect_all_and_status_change(archicad_api):
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = await asyncio.to_thread(MultiConn)
    managed_header = conn.open_port_headers[archicad_api.server.port]
    assert managed_header.status == Status.PENDING
    conn.connect.all()
    assert managed_header.status == Status.ACTIVE


@pytest.mark.asyncio
async def test_disconnect_and_status_change(archicad_api):
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = await asyncio.to_thread(MultiConn)
    conn.connect.all()
    managed_header = conn.open_port_headers[archicad_api.server.port]
    assert managed_header.status == Status.ACTIVE
    conn.disconnect.from_headers(managed_header)
    assert managed_header.status == Status.PENDING


@pytest.mark.asyncio
async def test_refresh_detects_closed_instance(archicad_api):
    """
    Verifies that refresh removes headers for closed instances.
    """
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = await asyncio.to_thread(MultiConn)
    assert len(conn.open_port_headers) == 1

    await archicad_api.server.close()

    await conn.scan_ports(conn.port_range)
    await conn._set_primary()

    assert len(conn.open_port_headers) == 0
    assert conn.primary is None


@pytest.mark.asyncio
async def test_quit_all_sends_command_and_removes_header(archicad_api):
    """
    Verifies that quit sends the command and removes the header.
    """
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    archicad_api.set_response("QuitArchicad", "success_empty_tapir.json")
    conn = await asyncio.to_thread(MultiConn)

    header_to_quit = conn.open_port_headers[archicad_api.server.port]

    processed_headers = []
    for header in list(conn.open_port_headers.values()):
        await header.core.post_tapir_command_async("QuitArchicad")
        await conn.close_if_open(header.port)
        header.unassign()
        processed_headers.append(header)

    assert len(processed_headers) == 1
    assert processed_headers[0] is header_to_quit
    assert len(conn.open_port_headers) == 0
    assert header_to_quit.status == Status.UNASSIGNED
