import threading
import pytest

from multiconn_archicad import MultiConn
from multiconn_archicad.orchestration.conn_header import Status
from multiconn_archicad.orchestration.basic_types import PendingResponse, ProductInfo, APIResponseError


pytestmark = [
    pytest.mark.usefixtures("fuzz_threads"),
    pytest.mark.integration,
]


def test_fast_initialization_despite_slow_server(slow_archicad_api):
    """
    Prove MultiConn() returns control to the user immediately
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
        conn = MultiConn()
        assert conn.primary is not None
        assert server_entered.wait(timeout=5.0), "Background fetch did not start as expected"
        assert not conn.primary._fetch_task[1].done()
    finally:
        unblock_server.set()


def test_ui_mode_lifecycle_pending_to_ready(slow_archicad_api):
    """
    Prove ui_mode=True returns pending placeholders and populates conn.pending,
    then transitions cleanly to conn.ready and unpacks to ProductInfo once complete.
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
        _ = conn.primary
        assert server_entered.wait(timeout=5.0)
        port = slow_archicad_api.server_port

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


def test_default_mode_blocks_and_waits(slow_archicad_api):
    """
    Prove ui_mode=False blocks the caller's thread until the background fetch finishes.
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


def test_vanilla_archicad_no_addon_scenario(slow_archicad_api):
    """
    Prove that if standard API commands succeed but Tapir Add-On commands fail,
    the connection gracefully survives and becomes READY.
    """
    slow_archicad_api.set_handler("GetProjectInfo", lambda p: {"succeeded": False, "error": {"code": 1}})

    conn = MultiConn()
    _ = conn.primary.product_info  # Wait for fetch

    assert conn.primary.status == Status.READY
    assert isinstance(conn.primary.archicad_id, APIResponseError)


def test_primary_canonical_identity_shared_with_pool(slow_archicad_api):
    """
    Prove that primary and the pool header share canonical identity.
    """
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn()
    port = slow_archicad_api.server_port
    pool_header = conn.open_port_headers[port]

    assert conn.primary is pool_header
    assert conn.primary._fetch_task is pool_header._fetch_task

    _ = conn.primary.product_info
    assert conn.primary.product_info is pool_header.product_info

    slow_archicad_api.set_handler(
        "API.GetProductInfo",
        lambda p: {"succeeded": True, "result": {"version": 28, "buildNumber": 3001, "languageCode": "INT"}},
    )

    conn.primary.refresh_metadata()
    assert conn.primary._fetch_task is pool_header._fetch_task

    _ = conn.primary.product_info
    assert conn.primary.product_info.version == 28


def test_stress_multiple_connections_performance(slow_archicad_api, monkeypatch):
    """
    STRESS TEST: Simulates all 21 Archicad ports open concurrently.
    """
    from multiconn_archicad.orchestration.basic_types import Port
    import httpx

    full_range = [Port(p) for p in range(19723, 19744)]
    num_ports = len(full_range)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.MultiConn._port_range", full_range)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", lambda url, port: True)

    mock_url = f"http://127.0.0.1:{slow_archicad_api.server_port}"
    original_post = httpx.Client.post

    monkeypatch.setattr(httpx.Client, "post", lambda s, u, *a, **k: original_post(s, mock_url, *a, **k))

    barrier = threading.Barrier(num_ports)

    def concurrent_handler(payload: dict) -> dict:
        if payload.get("command") == "API.GetProductInfo":
            barrier.wait(timeout=10.0)
        return slow_archicad_api.get_response_data("API.GetProductInfo") or {"succeeded": True, "result": {}}

    slow_archicad_api.set_handler("API.GetProductInfo", concurrent_handler)
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    conn = MultiConn(ui_mode=False)
    assert len(conn.open_port_headers) == num_ports

    _ = conn.primary.product_info
    assert conn.primary.status == Status.READY
    assert len(conn.active) == 0
