"""
test_architecture.py
Integration tests validating the synchronous background-fetch architecture.
"""

import pytest
import time
import os

from multiconn_archicad import MultiConn
from multiconn_archicad.conn_header import Status
from multiconn_archicad.basic_types import PendingResponse, ProductInfo, APIResponseError


pytestmark = [
    pytest.mark.integration,
]

skip_on_github = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") == "true",
    reason="GitHub Runners are too slow/unpredictable for timing-sensitive tests"
)


@pytest.fixture
def slow_archicad_api(archicad_api):
    """
    Wraps the mock server handlers with a 0.2s delay for the metadata endpoints
    to simulate network latency and test lazy evaluation/blocking.
    """

    def slow_handler(payload: dict) -> dict:
        time.sleep(0.2)
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

    # Register the slow handler for the endpoints hit during init
    archicad_api.set_handler("API.GetProductInfo", slow_handler)
    archicad_api.set_handler("GetProjectInfo", slow_handler)
    archicad_api.set_handler("GetArchicadLocation", slow_handler)

    yield archicad_api


@skip_on_github
def test_fast_initialization_despite_slow_server(slow_archicad_api):
    """
    Test Case 1: Prove MultiConn() returns control to the user immediately.
    """
    # ARRANGE
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    # ACT
    start_time = time.time()
    conn = MultiConn()
    duration = time.time() - start_time

    # ASSERT
    assert duration < 0.1, f"Initialization blocked the thread, took {duration:.2f}s"
    assert conn.primary is not None


@skip_on_github
def test_ui_mode_returns_pending_immediately(slow_archicad_api):
    """
    Test Case 2: Prove ui_mode=True prevents thread freezing and uses placeholders.
    """
    # ARRANGE
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    # ACT
    conn = MultiConn(ui_mode=True)

    start_time = time.time()
    product_info = conn.primary.product_info
    status = conn.primary.status
    duration = time.time() - start_time

    # ASSERT 1 (Instant)
    assert duration < 0.1, f"UI Mode blocked the thread, took {duration:.2f}s"

    # ASSERT 2 (Placeholders)
    assert isinstance(product_info, PendingResponse)
    assert status == Status.PENDING

    # ASSERT 3 (Resolution)
    time.sleep(1.0)

    assert isinstance(conn.primary.product_info, ProductInfo)
    assert conn.primary.status == Status.ACTIVE


@skip_on_github
def test_default_mode_blocks_and_waits(slow_archicad_api):
    """
    Test Case 3: Prove ui_mode=False blocks the caller's thread until the background fetch finishes.
    """
    # ARRANGE
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    # ACT
    conn = MultiConn(ui_mode=False)

    start_time = time.time()
    product_info = conn.primary.product_info
    duration = time.time() - start_time

    # ASSERT 1 (Blocking): 3 sequentially fetched endpoints at 0.2s each = 0.6s
    assert 0.6 <= duration < 0.7, f"Blocking duration was {duration:.2f}s, expected[0.6, 0.8)"

    # ASSERT 2 (Final Data)
    assert isinstance(product_info, ProductInfo)


@skip_on_github
def test_auto_connect_vs_manual_connect(slow_archicad_api):
    """
    Test Case 4: Prove that conn.primary automatically connects when data is ready,
    while headers in the pool wait.
    """
    # ARRANGE
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    # ACT
    conn = MultiConn()

    # Block until fetch finishes (accessing product_info triggers the wait,
    # ensuring the background threads are done before we check statuses)
    _ = conn.primary.product_info

    # ASSERT 1
    assert conn.primary.status == Status.ACTIVE

    # ASSERT 2
    port = slow_archicad_api.server_port
    pool_header = conn.open_port_headers[port]
    assert pool_header.status == Status.PENDING

    # ASSERT 3
    pool_header.connect()
    assert pool_header.status == Status.ACTIVE


@skip_on_github
def test_vanilla_archicad_no_addon_scenario(slow_archicad_api):
    """
    Test Case 5: Prove that if standard API commands succeed but Tapir Add-On
    commands fail, the connection gracefully survives and becomes active.
    """

    # ARRANGE
    def fail_project_info_handler(payload: dict) -> dict:
        time.sleep(0.2)
        return {"succeeded": False, "error": {"code": 1}}

    slow_archicad_api.set_handler("GetProjectInfo", fail_project_info_handler)

    # ACT
    conn = MultiConn()

    # Block to wait for background fetch
    _ = conn.primary.product_info

    # ASSERT
    assert conn.primary.status == Status.ACTIVE
    assert isinstance(conn.primary.archicad_id, APIResponseError)


@skip_on_github
def test_primary_shared_metadata_and_independence(slow_archicad_api):
    """
    Test Case 6: Prove the link and the detachment logic between primary and pool headers.
    """
    # ARRANGE
    slow_archicad_api.set_response("GetProjectInfo", "get_project_info_solo.json")

    # STEP 1 (Link)
    conn = MultiConn()
    port = slow_archicad_api.server_port
    pool_header = conn.open_port_headers[port]

    # ASSERTION 1 (Update this!)
    # We no longer assert 'is', we just assert they both have active Futures
    assert conn.primary.init_future is not None
    assert pool_header.init_future is not None

    # STEP 2 (Shared Result)
    _ = conn.primary.product_info  # Wait for fetch to finish

    # ASSERTION 2
    assert conn.primary.product_info is pool_header.product_info

    # STEP 3 (Detachment)
    def v28_handler(payload: dict) -> dict:
        time.sleep(0.2)
        return {"succeeded": True, "result": {"version": 28, "buildNumber": 3001, "languageCode": "INT"}}

    slow_archicad_api.set_handler("API.GetProductInfo", v28_handler)

    conn.primary.refresh_metadata()

    # ASSERTION 3 (New Future)
    assert conn.primary.init_future is not pool_header.init_future

    # ASSERTION 4 (Independence)
    _ = conn.primary.product_info  # Block and wait for the new fetch to finish
    assert conn.primary.product_info.version == 28
    assert pool_header.product_info.version == 27


@skip_on_github
def test_stress_multiple_connections_performance(slow_archicad_api, monkeypatch):
    """
    STRESS TEST: Simulates a fully saturated environment (all 21 Archicad ports open).
    Proves that the ThreadPool processes them in parallel and does not degrade linearly.
    """
    from multiconn_archicad.basic_types import Port
    import httpx

    # 1. Restore the full 21-port range
    full_range =[Port(p) for p in range(19723, 19744)]
    monkeypatch.setattr("multiconn_archicad.multi_conn.MultiConn._port_range", full_range)

    # 2. Mock the TCP knock so MultiConn thinks all 21 ports are actively listening
    monkeypatch.setattr("multiconn_archicad.multi_conn.is_port_listening", lambda url, port: True)

    # 3. ROUTING FIX: Silently redirect all httpx requests to the single mock server!
    mock_url = f"http://127.0.0.1:{slow_archicad_api.server_port}"
    original_post = httpx.Client.post

    def routed_post(self_client, url, *args, **kwargs):
        # Ignore the port CoreCommands thinks it's hitting, and force the mock port
        return original_post(self_client, mock_url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "post", routed_post)

    # ACT 1: Initialization
    start_time = time.perf_counter()
    conn = MultiConn(ui_mode=False)
    init_duration = time.perf_counter() - start_time

    # ASSERT 1: The TCP knock and thread spawning must remain lightning fast (< 0.2s)
    assert init_duration < 0.2, f"Init bottlenecked with 21 ports! Took {init_duration:.2f}s"
    assert len(conn.open_port_headers) == 21  # 21 ports in range

    # ACT 2: Data Fetching
    fetch_start = time.perf_counter()

    # Trigger the sync tollbooth on the primary
    _ = conn.primary.product_info

    # Trigger the sync tollbooth on the last port to ensure everything finished
    _ = conn.open_port_headers[Port(19743)].product_info

    fetch_duration = time.perf_counter() - fetch_start

    # ASSERT 2: The Parallelism Proof
    # 21 parallel batches of 3 sequential requests (0.2s * 3 = 0.6s total expected)
    # Allowed threshold is < 1.5s to account for OS thread scheduling overhead
    assert 0.6 <= fetch_duration < 1.5, f"Parallel fetch failed or bottlenecked! Took {fetch_duration:.2f}s"

    # Ensure they resolved correctly
    assert conn.primary.status == Status.ACTIVE
    assert conn.open_port_headers[Port(19743)].status == Status.PENDING
