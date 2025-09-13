import json
from pathlib import Path
from typing import Dict, Any

import pytest
from aiohttp import web

# Import modules for configuration patching
import multiconn_archicad.multi_conn as multi_conn
import multiconn_archicad.utilities.cli_parser as cli_parser
from multiconn_archicad.basic_types import Port

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_PORT = 19743


class ServerController:
    """A controller to manage the state of the fake Archicad server for tests."""
    def __init__(self):
        self.server = None
        self._default_responses = {
            "API.GetProductInfo": "get_product_info_AC27_INT.json",
            "GetArchicadLocation": "get_archicad_location_win.json",
            "API.IsAlive": "is_alive_true.json",
        }
        self.responses: Dict[str, str] = {}
        self.reset()

    def reset(self):
        self.responses = self._default_responses.copy()

    def set_response(self, command: str, response_filename: str):
        self.responses[command] = response_filename

    def get_response_data(self, command: str) -> Dict[str, Any] | None:
        filename = self.responses.get(command)
        if filename:
            filepath = FIXTURES_DIR / filename
            if filepath.exists():
                return json.loads(filepath.read_text())
        return None


async def handle_get(request: web.Request):
    return web.Response(status=200, text="Server is alive")

async def archicad_api_handler(request: web.Request):
    """
    Finds the correct fixture based on the request and returns its contents.
    """
    controller: ServerController = request.app["controller"]
    payload = await request.json()
    command = payload.get("command")

    command_name = command
    if command == "API.ExecuteAddOnCommand":
        command_name = payload.get("parameters", {}).get("addOnCommandId", {}).get("commandName")

    response_data = controller.get_response_data(command_name)

    if response_data:
        return web.json_response(response_data)
    else:
        # Return a generic success if no specific response is configured
        return web.json_response({"succeeded": True, "result": {}})


@pytest.fixture
async def archicad_api(aiohttp_server, monkeypatch):
    """
    Starts the mock server and applies configuration patches to the library.
    """
    app = web.Application()
    controller = ServerController()
    app["controller"] = controller
    app.router.add_get("/", handle_get)
    app.router.add_post("/", archicad_api_handler)

    server = await aiohttp_server(app, port=TEST_PORT)
    controller.server = server

    # Patch library configuration to connect to our mock server
    class MockArgs:
        host = f"http://{server.host}"
        port = server.port
    cli_parser._parsed_cli_args_cache = MockArgs()
    monkeypatch.setattr(multi_conn.MultiConn, "_port_range", [Port(server.port)])
    monkeypatch.setattr(Port, "__new__", lambda cls, value: int.__new__(cls, value))

    yield controller

    cli_parser._parsed_cli_args_cache = None