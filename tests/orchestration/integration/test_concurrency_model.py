import threading
import pytest

from multiconn_archicad import MultiConn
from multiconn_archicad.orchestration.conn_header import Status
from multiconn_archicad.orchestration.basic_types import PendingResponse, ProductInfo, APIResponseError


pytestmark = [
    pytest.mark.usefixtures("fuzz_threads"),
    pytest.mark.integration,
]


@pytest.fixture
def slow_archicad_api(archicad_api):
    """
    Wraps the mock server handlers with dynamic routing to simulate metadata endpoints.
    """

    def passthrough_handler(payload: dict) -> dict:
        command = payload.get("command")

        # Unwrap Tapir add-on command name if necessary
        if command == "API.ExecuteAddOnCommand":
            command_name = payload.get("parameters", {}).get("addOnCommandId", {}).get("commandName")
        else:
            command_name = command

        response_dict = archicad_api.get_response_data(command_name)
        if not response_dict:
            response_dict = {"succeeded": True, "result": {}}
        return response_dict

    # Register handlers for the metadata endpoints hit during init
    archicad_api.set_handler("API.GetProductInfo", passthrough_handler)
    archicad_api.set_handler("GetProjectInfo", passthrough_handler)
    archicad_api.set_handler("GetArchicadLocation", passthrough_handler)

    yield archicad_api


def test_fast_initialization_despite_slow_server(slow_archicad_api):
    """
    Test Case 1: Prove MultiConn() returns control to the user immediately
    without waiting for background server requests to complete.
    """
    server_entered = threading.Event()
    unblock_server = threading.Event()

    def blocking_handler(payload: dict) -> dict:
        server_entered.set()
        unblock_server.wait(timeout=5.0)
        return slow_archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    slow_archicad_api.set_handler("API.GetProductInfo", blocking_handler)
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    try:
        # MultiConn constructor must return immediately even while the server request is blocked
        conn = MultiConn()
        assert conn.primary is not None

        # Verify the background fetch was started and reached the server
        assert server_entered.wait(timeout=5.0), "Background fetch did not start as expected"

        # Verify the future is still in flight because the server has not responded
        assert not conn.primary.init_future.done()
    finally:
        unblock_server.set()


def test_ui_mode_returns_pending_immediately(slow_archicad_api):
    """
    Test Case 2: Prove ui_mode=True prevents thread freezing and uses placeholders
    while requests are in flight, then resolves once the background task finishes.
    """
    server_entered = threading.Event()
    unblock_server = threading.Event()

    def blocking_handler(payload: dict) -> dict:
        server_entered.set()
        unblock_server.wait(timeout=5.0)
        return slow_archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    slow_archicad_api.set_handler("API.GetProductInfo", blocking_handler)
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    try:
        conn = MultiConn(ui_mode=True)
        assert server_entered.wait(timeout=5.0)

        # In UI mode, while the future is still running, property access returns PendingResponse immediately
        product_info = conn.primary.product_info
        status = conn.primary.status

        assert isinstance(product_info, PendingResponse)
        assert status == Status.PENDING
    finally:
        unblock_server.set()

    # Wait for the future to finish
    conn.primary.init_future.result(timeout=5.0)

    # Now UI mode unpacks to READY
    assert isinstance(conn.primary.product_info, ProductInfo)
    assert conn.primary.status == Status.READY


def test_default_mode_blocks_and_waits(slow_archicad_api):
    """
    Test Case 3: Prove ui_mode=False blocks the caller's thread until the background fetch finishes.
    """
    server_entered = threading.Event()
    unblock_server = threading.Event()

    def blocking_handler(payload: dict) -> dict:
        server_entered.set()
        unblock_server.wait(timeout=5.0)
        return slow_archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    slow_archicad_api.set_handler("API.GetProductInfo", blocking_handler)
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn(ui_mode=False)
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
        # Verify caller thread is blocked waiting (caller_resolved is not yet set)
        assert not caller_resolved.is_set()
        assert t.is_alive()
    finally:
        # Unblock the server response
        unblock_server.set()

    t.join(timeout=5.0)
    assert caller_resolved.is_set()
    assert isinstance(resolved_product_info, ProductInfo)


def test_auto_connect_vs_manual_connect(slow_archicad_api):
    """
    Test Case 4: Prove that primary is ready immediately upon discovery,
    while batch active membership is explicitly controlled via MultiConn.
    """
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn()
    port = slow_archicad_api.server_port
    pool_header = conn.open_port_headers[port]

    # Block until fetch finishes
    _ = conn.primary.product_info

    # Both primary and pool header are the same object, and technically READY
    assert conn.primary is pool_header
    assert conn.primary.status == Status.READY

    # Port is not in the batch worklist by default
    assert port not in conn.active

    # Explicitly activate for batch execution
    conn.connect.from_ports(port)
    assert port in conn.active


def test_vanilla_archicad_no_addon_scenario(slow_archicad_api):
    """
    Test Case 5: Prove that if standard API commands succeed but Tapir Add-On
    commands fail, the connection gracefully survives and becomes READY.
    """

    def fail_project_info_handler(payload: dict) -> dict:
        return {"succeeded": False, "error": {"code": 1}}

    slow_archicad_api.set_handler("GetProjectInfo", fail_project_info_handler)

    conn = MultiConn()

    # Block to wait for background fetch
    _ = conn.primary.product_info

    # Primary should be READY despite Tapir command failure
    assert conn.primary.status == Status.READY
    assert isinstance(conn.primary.archicad_id, APIResponseError)


def test_primary_shared_metadata_and_independence(slow_archicad_api):
    """
    Test Case 6: Prove that primary and the pool header share canonical identity.
    """
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn()
    port = slow_archicad_api.server_port
    pool_header = conn.open_port_headers[port]

    # Verify canonical identity (no cloning)
    assert conn.primary is pool_header
    assert conn.primary.init_future is pool_header.init_future

    _ = conn.primary.product_info  # Wait for fetch to finish
    assert conn.primary.product_info is pool_header.product_info

    def v28_handler(payload: dict) -> dict:
        return {"succeeded": True, "result": {"version": 28, "buildNumber": 3001, "languageCode": "INT"}}

    slow_archicad_api.set_handler("API.GetProductInfo", v28_handler)

    conn.primary.refresh_metadata()

    # They share the exact same refreshed future
    assert conn.primary.init_future is pool_header.init_future

    _ = conn.primary.product_info  # Wait for new fetch to finish
    assert conn.primary.product_info.version == 28
    assert pool_header.product_info.version == 28


def test_stress_multiple_connections_performance(slow_archicad_api, monkeypatch):
    """
    STRESS TEST: Simulates a fully saturated environment (all 21 Archicad ports open).
    Proves that the ThreadPool processes them concurrently in parallel.
    """
    from multiconn_archicad.orchestration.basic_types import Port
    import httpx

    full_range = [Port(p) for p in range(19723, 19744)]
    num_ports = len(full_range)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.MultiConn._port_range", full_range)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", lambda url, port: True)

    mock_url = f"http://127.0.0.1:{slow_archicad_api.server_port}"
    original_post = httpx.Client.post

    def routed_post(self_client, url, *args, **kwargs):
        return original_post(self_client, mock_url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "post", routed_post)

    barrier = threading.Barrier(num_ports)

    def concurrent_handler(payload: dict) -> dict:
        command = payload.get("command")
        if command == "API.GetProductInfo":
            barrier.wait(timeout=10.0)
        return slow_archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    slow_archicad_api.set_handler("API.GetProductInfo", concurrent_handler)
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn(ui_mode=False)
    assert len(conn.open_port_headers) == num_ports

    # Trigger resolution
    _ = conn.primary.product_info
    _ = conn.open_port_headers[Port(19743)].product_info

    # All healthy headers are READY
    assert conn.primary.status == Status.READY
    assert conn.open_port_headers[Port(19743)].status == Status.READY
    # None are in the batch worklist by default
    assert len(conn.active) == 0