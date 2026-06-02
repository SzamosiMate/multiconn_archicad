import pytest
import threading
from unittest.mock import MagicMock
from concurrent.futures import Future

from multiconn_archicad import ConnHeader, Port
from multiconn_archicad.basic_types import ProductInfo, SoloProjectID, ArchicadLocation


def test_reproduce_metadata_callback_deadlock():
    """
    Verifies that calling sync_from_master_future with an already completed
    master_future causes a deadlock when the inline callback calls connect()
    on a non-worker thread.
    """
    # 1. Arrange: Create dummy metadata
    prod_info = ProductInfo(version=27, build=3001, lang="INT")
    ac_id = SoloProjectID(projectPath="C:/path/to/project.pln", projectName="Test Project")
    ac_loc = ArchicadLocation(archicadLocation="C:/Archicad")

    # 2. Create a master future that is ALREADY completed
    master_future = Future()
    master_future.set_result((prod_info, ac_id, ac_loc))

    # 3. Instantiate a ConnHeader with initialize=False (so it doesn't spin up its own worker)
    header = ConnHeader(port=Port(19723), initialize=False)

    # Mock the standard connection interface to ensure we don't make network calls in this test
    header._standard = MagicMock()

    # 4. Run sync_from_master_future on a separate test thread.
    # If the bug is present, the inline callback will fire immediately,
    # invoke connect(), check _sync_if_needed(), and block forever on self.init_future.result().
    def execute_sync():
        header.sync_from_master_future(master_future)

    test_thread = threading.Thread(target=execute_sync, name="TestRunnerThread")
    test_thread.start()

    # 5. Join with a 1-second timeout. If it is deadlocked, the thread won't exit.
    test_thread.join(timeout=1.0)

    # 6. Assert that the thread managed to exit successfully.
    is_alive = test_thread.is_alive()

    assert not is_alive, (
        "DEADLOCK DETECTED! sync_from_master_future hung because the master future "
        "was already completed, forcing the callback to execute inline on the main thread."
    )
