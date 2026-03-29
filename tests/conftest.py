import json
import sys
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, Callable

import pytest

# Import modules for configuration patching
import multiconn_archicad.multi_conn as multi_conn
import multiconn_archicad.utilities.cli_parser as cli_parser
from multiconn_archicad.basic_types import Port

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class QuietThreadingHTTPServer(ThreadingHTTPServer):
    """A custom server that suppresses ONLY expected socket teardown errors."""

    def handle_error(self, request, client_address):
        # socketserver leaves the exception in sys.exc_info()
        exc_type, exc_value, exc_traceback = sys.exc_info()
        # These are the exact errors raised when a socket is killed during teardown
        expected_teardown_errors = (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)

        if exc_type and issubclass(exc_type, expected_teardown_errors):
            # It's an expected shutdown interruption. Suppress it cleanly.
            return

        super().handle_error(request, client_address)

class ServerController:
    """A controller to manage the state of the fake Archicad server for tests."""

    def __init__(self):
        self.server_host = "127.0.0.1"
        self.server_port = None  # Will be assigned dynamically
        self._default_responses = {
            "API.GetProductInfo": "get_product_info_AC27_INT.json",
            "GetArchicadLocation": "get_archicad_location_win.json",
            "API.IsAlive": "is_alive_true.json",
        }
        self.responses: Dict[str, str] = {}
        self.command_handlers: Dict[str, Callable[[dict], dict]] = {}
        self.reset()

    def reset(self):
        self.responses = self._default_responses.copy()
        self.command_handlers = {}

    def set_response(self, command: str, response_filename: str):
        self.responses[command] = response_filename

    def set_handler(self, command: str, handler: Callable[[dict], dict]):
        """Set a custom function to handle a specific command.
        The handler takes the JSON payload (dict) and returns a JSON response (dict).
        """
        self.command_handlers[command] = handler

    def get_response_data(self, command: str) -> Dict[str, Any] | None:
        filename = self.responses.get(command)
        if filename:
            filepath = FIXTURES_DIR / filename
            if filepath.exists():
                return json.loads(filepath.read_text())
        return None


def create_handler_class(controller: ServerController):
    """Factory to create a RequestHandler bound to our controller."""

    class ArchicadAPIHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress HTTP server logging to keep test output clean

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Server is alive")

        def do_POST(self):
            # Parse the incoming JSON
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)

            command = payload.get("command")
            command_name = command
            # Unwrap Tapir AddOn commands
            if command == "API.ExecuteAddOnCommand":
                command_name = payload.get("parameters", {}).get("addOnCommandId", {}).get("commandName")

            # Route to a custom handler if defined, otherwise load from fixtures
            if handler := controller.command_handlers.get(command_name):
                response_dict = handler(payload)
            else:
                response_dict = controller.get_response_data(command_name)
                if not response_dict:
                    # Generic fallback success
                    response_dict = {"succeeded": True, "result": {}}

            # Send the response back
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_dict).encode('utf-8'))

    return ArchicadAPIHandler


@pytest.fixture
def isolate_executor(monkeypatch):
    """
    Gives every test a completely blank, isolated ThreadPool.
    Prevents zombie threads from previous tests from exhausting the worker pool.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=25, thread_name_prefix="MultiConnWorker")
    monkeypatch.setattr("multiconn_archicad.multi_conn.EXECUTOR", executor)
    monkeypatch.setattr("multiconn_archicad.conn_header.EXECUTOR", executor)
    yield
    executor.shutdown(wait=False, cancel_futures=True)


def pytest_collection_modifyitems(config, items):
    """ Dynamically apply the 'isolate_executor' fixture to all tests marked with 'integration'. """
    for item in items:
        if item.get_closest_marker("integration"):
            if "isolate_executor" not in item.fixturenames:
                item.fixturenames.append("isolate_executor")


@pytest.fixture
def archicad_api(monkeypatch):
    """
    Starts the synchronous mock server on a background thread within the Archicad port range,
    and patches the library configuration.
    """
    controller = ServerController()

    valid_ports = range(19723, 19745)
    server = None
    assigned_port = None

    HandlerClass = create_handler_class(controller)
    for port in valid_ports:
        try:
            server = QuietThreadingHTTPServer((controller.server_host, port), HandlerClass)
            assigned_port = port
            break
        except OSError:
            continue

    if server is None:
        raise RuntimeError(f"Could not find an open port in the Archicad range {valid_ports} for the mock server.")

    controller.server_port = assigned_port
    controller.http_server = server

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Patch library configuration to connect to our mock server
    class MockArgs:
        host = f"http://{controller.server_host}"
        port = controller.server_port

    monkeypatch.setattr(multi_conn.MultiConn, "_port_range", [Port(assigned_port)])
    monkeypatch.setattr(Port, "__new__", lambda cls, value: int.__new__(cls, value))
    monkeypatch.setattr("multiconn_archicad.utilities.cli_parser.get_cli_args_once", lambda: MockArgs())

    yield controller

    # Teardown: Safely shut down the server and thread
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=1.0)
    cli_parser._parsed_cli_args_cache = None