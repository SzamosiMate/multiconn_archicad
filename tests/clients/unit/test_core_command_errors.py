"""Verify whole-command Tapir errors at the existing core boundary, without HTTP."""

import asyncio
from unittest.mock import MagicMock

import pytest

from multiconn_archicad.clients.core.core_commands import CoreCommands
from multiconn_archicad.errors import TapirCommandError

pytestmark = pytest.mark.unit


def make_core(payload):
    core = CoreCommands.__new__(CoreCommands)
    core._post_command = MagicMock(
        return_value={
            "succeeded": True,
            "result": {"addOnCommandResponse": payload},
        }
    )
    return core


@pytest.mark.parametrize("failed_execution", [False, True])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_root_error_item_and_failed_execution_raise_in_core(failed_execution, asynchronous, monkeypatch):
    payload = {"error": {"code": 1234, "message": "Command failed"}}
    if failed_execution:
        payload["success"] = False
    core = make_core(payload)

    with pytest.raises(TapirCommandError) as caught:
        if asynchronous:

            async def inline_worker(function, *args):
                return function(*args)

            monkeypatch.setattr(asyncio, "to_thread", inline_worker)
            core.post_tapir_command_async("GetAllElements").send(None)
        else:
            core.post_tapir_command("GetAllElements")

    assert caught.value.code == 1234
    assert caught.value.message == "Command failed"


def test_nested_per_element_error_items_are_returned_as_data():
    payload = {"propertyValuesForElements": [{"error": {"code": 7, "message": "One element failed"}}]}

    assert make_core(payload).post_tapir_command("GetPropertyValuesOfElements") is payload
