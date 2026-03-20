"""
test_architecture.py
Integration tests validating the synchronous background-fetch architecture.
"""

import pytest
import time

from multiconn_archicad import MultiConn
from multiconn_archicad.conn_header import Status
from multiconn_archicad.basic_types import PendingResponse, ProductInfo, APIResponseError


pytestmark = [
    pytest.mark.integration,
]


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
    time.sleep(1.0)  # Wait for 3 * 0.2s background fetches to complete

    resolved_product_info = conn.primary.product_info
    resolved_status = conn.primary.status

    assert isinstance(resolved_product_info, ProductInfo)
    assert resolved_status == Status.ACTIVE


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
    assert 0.6 <= duration < 0.8, f"Blocking duration was {duration:.2f}s, expected[0.6, 0.8)"

    # ASSERT 2 (Final Data)
    assert isinstance(product_info, ProductInfo)


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

    # ASSERTION 1
    assert conn.primary.init_future is pool_header.init_future

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
