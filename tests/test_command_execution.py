import pytest
import asyncio
from aiohttp import web
from copy import deepcopy

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.errors import StandardAPIError, TapirCommandError, CommandTimeoutError

pytestmark = pytest.mark.usefixtures("archicad_api")


@pytest.mark.asyncio
async def test_successful_core_post_tapir_command_async(archicad_api):
    """
    Verifies that a successful async tapir command returns the parsed 'result' dict.
    (Test Case Plan 3.1)
    """
    # ARRANGE
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = await asyncio.to_thread(MultiConn)

    # ACT
    result = await conn.core.post_tapir_command_async("GetProjectInfo")

    # ASSERT
    assert isinstance(result, dict)
    assert result.get("projectName") == "My Solo Project.pln"
    assert "succeeded" not in result
    assert "addOnCommandResponse" not in result


@pytest.mark.asyncio
async def test_iterating_active_connections_to_run_commands(archicad_api):
    """
    Verifies the pattern of iterating over multiple active connections.
    (Test Case Plan 3.3 - Enhanced)
    """
    # ARRANGE
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    conn = await asyncio.to_thread(MultiConn)

    # Manually add a second connection to simulate multiple instances
    original_header = conn.open_port_headers[archicad_api.server.port]
    second_header = deepcopy(original_header)
    second_port = Port(19742)
    second_header.port = second_port # Manually set the new port
    conn.open_port_headers[second_port] = second_header

    conn.connect.all()
    assert len(conn.active) == 2

    # ACT
    results = {
        port: await header.core.post_tapir_command_async("GetProjectInfo")
        for port, header in conn.active.items()
    }

    # ASSERT
    assert len(results) == 2
    assert archicad_api.server.port in results
    assert second_port in results
    assert results[archicad_api.server.port]["projectName"] == "My Solo Project.pln"


@pytest.mark.asyncio
async def test_standard_api_error_is_raised_async(archicad_api):
    """
    Verifies that StandardAPIError is raised for a failed standard command.
    (Test Case Plan 4.1)
    """
    # ARRANGE
    archicad_api.set_response("API.GetAttributesByType", "standard_api_error.json")
    archicad_api.set_response("GetProjectInfo", "get_project_info_teamwork.json")
    conn = await asyncio.to_thread(MultiConn)

    # ACT & ASSERT
    with pytest.raises(StandardAPIError) as exc_info:
        await conn.core.post_command_async("API.GetAttributesByType")

    assert exc_info.value.code == 1234
    assert "A standard API error occurred" in exc_info.value.message


@pytest.mark.asyncio
async def test_tapir_command_error_is_raised_async(archicad_api):
    """
    Verifies that TapirCommandError is raised for a failed Tapir command.
    (Test Case Plan 4.2)
    """
    # ARRANGE
    archicad_api.set_response("DeleteElements", "tapir_command_error.json")
    archicad_api.set_response("GetProjectInfo", "get_project_info_untitled.json")
    conn = await asyncio.to_thread(MultiConn)

    # ACT & ASSERT
    with pytest.raises(TapirCommandError) as exc_info:
        await conn.core.post_tapir_command_async("DeleteElements", {"elements": []})

    assert exc_info.value.code == 5678
    assert "A Tapir add-on command failed" in exc_info.value.message


@pytest.mark.asyncio
async def test_command_timeout_error_is_raised_async(archicad_api):
    """
    Verifies that CommandTimeoutError is raised when a request exceeds the timeout.
    (Test Case Plan 4.3)
    """
    # ARRANGE
    async def timeout_handler(request):
        await asyncio.sleep(0.5)
        return web.json_response({"succeeded": True, "result": {}})

    archicad_api.set_handler("Test.Timeout", timeout_handler)
    archicad_api.set_response("GetProjectInfo", "get_project_info_teamwork.json")
    conn = await asyncio.to_thread(MultiConn)

    # ACT & ASSERT
    with pytest.raises(CommandTimeoutError):
        await conn.core.post_command_async("Test.Timeout", timeout=0.1)