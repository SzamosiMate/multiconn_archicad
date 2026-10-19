from concurrent.futures import wait
import threading
from types import SimpleNamespace
import pytest

from multiconn_archicad import MultiConn
from multiconn_archicad.orchestration.conn_header import Status
from multiconn_archicad.orchestration.basic_types import PendingResponse, ProductInfo, APIResponseError


pytestmark = [
    pytest.mark.usefixtures("fuzz_threads"),
    pytest.mark.integration,
]


def test_fast_initialization_despite_slow_server(archicad_api):
    """
    Prove MultiConn() returns control to the user immediately
    without waiting for background server requests to complete.
    """
    server_entered = threading.Event()
    unblock_server = threading.Event()

    def blocking_handler(payload: dict) -> dict:
        server_entered.set()
        unblock_server.wait(timeout=5.0)
        return archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    archicad_api.set_handler("API.GetProductInfo", blocking_handler)
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    try:
        conn = MultiConn()
        assert conn.primary is not None
        assert server_entered.wait(timeout=5.0), "Background fetch did not start as expected"
        assert not conn.primary._fetch_task[1].done()
    finally:
        unblock_server.set()


def test_ui_mode_lifecycle_pending_to_ready(archicad_api):
    """
    Prove ui_mode=True returns pending placeholders and populates conn.pending,
    then transitions cleanly to conn.ready and unpacks to ProductInfo once complete.
    """
    server_entered = threading.Event()
    unblock_server = threading.Event()

    def blocking_handler(payload: dict) -> dict:
        server_entered.set()
        unblock_server.wait(timeout=5.0)
        return archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    archicad_api.set_handler("API.GetProductInfo", blocking_handler)
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    try:
        conn = MultiConn(ui_mode=True)
        _ = conn.primary
        assert server_entered.wait(timeout=5.0)
        port = archicad_api.server_port

        # In-flight: properties return PendingResponse and port is in conn.pending
        assert isinstance(conn.primary.product_info, PendingResponse)
        assert conn.primary.status == Status.PENDING
        assert port in conn.pending
        assert port not in conn.ready
    finally:
        unblock_server.set()

    # Wait for completion
    conn.primary._fetch_task[1].result(timeout=5.0)

    # Resolved: unpacks to ProductInfo and transitions to conn.ready
    assert isinstance(conn.primary.product_info, ProductInfo)
    assert conn.primary.status == Status.READY
    assert port in conn.ready
    assert port not in conn.pending


def test_default_mode_blocks_and_waits(archicad_api):
    """
    Prove ui_mode=False blocks the caller's thread until the background fetch finishes.
    """
    server_entered = threading.Event()
    unblock_server = threading.Event()

    def blocking_handler(payload: dict) -> dict:
        server_entered.set()
        unblock_server.wait(timeout=5.0)
        return archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    archicad_api.set_handler("API.GetProductInfo", blocking_handler)
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn(ui_mode=False)
    _ = conn.primary
    assert server_entered.wait(timeout=5.0)

    caller_resolved = threading.Event()
    resolved_product_info = None

    def caller_thread():
        nonlocal resolved_product_info
        resolved_product_info = conn.primary.product_info
        caller_resolved.set()

    t = threading.Thread(target=caller_thread)
    t.start()

    try:
        assert not caller_resolved.is_set()
        assert t.is_alive()
    finally:
        unblock_server.set()

    t.join(timeout=5.0)
    assert caller_resolved.is_set()
    assert isinstance(resolved_product_info, ProductInfo)


def test_vanilla_archicad_no_addon_scenario(archicad_api):
    """
    Prove that if standard API commands succeed but Tapir Add-On commands fail,
    the connection gracefully survives and becomes READY.
    """
    archicad_api.set_handler("GetProjectInfo", lambda p: {"succeeded": False, "error": {"code": 1}})

    conn = MultiConn()
    _ = conn.primary.product_info  # Wait for fetch

    assert conn.primary.status == Status.READY
    assert isinstance(conn.primary.archicad_id, APIResponseError)


def test_primary_canonical_identity_shared_with_pool(archicad_api):
    """
    Prove that primary and the pool header share canonical identity.
    """
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn()
    port = archicad_api.server_port
    pool_header = conn.open_port_headers[port]

    assert conn.primary is pool_header
    assert conn.primary._fetch_task is pool_header._fetch_task

    _ = conn.primary.product_info
    assert conn.primary.product_info is pool_header.product_info

    archicad_api.set_handler(
        "API.GetProductInfo",
        lambda p: {"succeeded": True, "result": {"version": 28, "buildNumber": 3001, "languageCode": "INT"}},
    )

    conn.primary.refresh_metadata()
    assert conn.primary._fetch_task is pool_header._fetch_task

    _ = conn.primary.product_info
    assert conn.primary.product_info.version == 28


def test_stress_multiple_connections_performance(archicad_api, monkeypatch):
    """
    Prove all 21 ports can fetch metadata before any fetch completes.
    """
    from multiconn_archicad.clients.core.core_commands import CoreCommands
    from multiconn_archicad.constants import SUPPORTED_TAPIR_VERSION
    from multiconn_archicad.orchestration.basic_types import Port
    from multiconn_archicad.orchestration.system.ram_monitor import RamMonitor

    full_range = [Port(p) for p in range(19723, 19744)]
    expected_ports = set(full_range)
    num_ports = len(full_range)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.MultiConn._port_range", full_range)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", lambda url, port: True)
    monkeypatch.setattr(
        "multiconn_archicad.orchestration.multi_conn.get_cli_args_once",
        lambda: SimpleNamespace(host=None, port=None),
    )
    monkeypatch.setattr(RamMonitor, "get_current_rss", lambda self: None)

    # Keep response parsing and metadata validation real, but exclude disk I/O,
    # TLS setup and socket deadlines from the concurrency assertion.
    archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")
    responses = {
        command: archicad_api.get_response_data(command)
        for command in ("API.GetProductInfo", "GetProjectInfo", "GetArchicadLocation")
    }
    responses["GetAddOnVersion"] = {
        "succeeded": True,
        "result": {"addOnCommandResponse": {"version": SUPPORTED_TAPIR_VERSION}},
    }
    entered_ports = set()
    entered_lock = threading.Lock()
    all_entered = threading.Event()
    release = threading.Event()

    def in_memory_request(core, payload: dict, timeout) -> dict:
        command = payload["command"]
        if command == "API.GetProductInfo":
            with entered_lock:
                entered_ports.add(core.port)
                if entered_ports == expected_ports:
                    all_entered.set()
            # This is a hang safeguard, not a simulated HTTP timeout. The main
            # thread releases every worker together after observing overlap.
            assert release.wait(timeout=60.0), "Test did not release metadata workers"
        elif command == "API.ExecuteAddOnCommand":
            command = payload["parameters"]["addOnCommandId"]["commandName"]
        return responses[command]

    monkeypatch.setattr(CoreCommands, "_post_command", in_memory_request)

    conn = MultiConn(ui_mode=False)
    try:
        assert set(conn.open_port_headers) == expected_ports
        started = all_entered.wait(timeout=30.0)
        with entered_lock:
            missing_ports = expected_ports - entered_ports
        assert started, (
            f"Only {num_ports - len(missing_ports)}/{num_ports} workers entered; missing: {sorted(missing_ports)}"
        )
    finally:
        release.set()
        # Use the existing pool directly: cleanup must not trigger another scan.
        futures = [
            header._fetch_task[1]
            for header in conn._open_port_headers.values()
            if header._fetch_task is not None
        ]
        _, unfinished = wait(futures, timeout=30.0)
        assert not unfinished, f"{len(unfinished)} metadata workers did not finish after release"

    statuses = [header.status for header in conn.open_port_headers.values()]
    assert statuses == [Status.READY] * num_ports
    assert len(conn.active) == 0
