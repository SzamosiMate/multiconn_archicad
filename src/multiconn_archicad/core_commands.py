import json
from typing import Any, Awaitable, cast
import aiohttp
import asyncio

from multiconn_archicad.basic_types import Port
from multiconn_archicad.utilities.async_utils import callable_from_sync_or_async_context


class CoreCommands:
    _BASE_URL: str = "http://127.0.0.1"

    def __init__(self, port: Port):
        self.port: Port = port

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        return self.__repr__()

    @callable_from_sync_or_async_context
    async def post_command(self, command: str, parameters: dict | None = None, timeout: float | int | None = None) -> dict[str, Any]:
        if parameters is None:
            parameters = {}
        url = f"{self._BASE_URL:}:{self.port}"
        payload = {"command": command, "parameters": parameters}
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            try:
                async with session.post(url, json=payload) as response:
                    result = await response.text()
                    return json.loads(result)
            except asyncio.TimeoutError:
                print(f"ERROR (multi_conn_ac): Command '{command}' to {url} timed out after {timeout} seconds.")
                raise TimeoutError(f"aiohttp request timed out after {timeout} seconds") from None
            except aiohttp.ClientResponseError as e:
                 print(f"ERROR (multi_conn_ac): HTTP error for command '{command}' to {url}: {e.status} {e.message}")
                 raise e
            except Exception as e:
                 print(f"ERROR (multi_conn_ac): Unexpected error during post_command '{command}': {type(e).__name__} - {e}")
                 raise e

    @callable_from_sync_or_async_context
    async def post_tapir_command(self, command: str, parameters: dict | None = None, timeout: float | int | None = None) -> dict[str, Any]:
        if parameters is None:
            parameters = {}

        return await cast(
            Awaitable[dict[str, Any]],
            self.post_command(
                command="API.ExecuteAddOnCommand",
                parameters={
                    "addOnCommandId": {
                        "commandNamespace": "TapirCommand",
                        "commandName": command,
                    },
                    "addOnCommandParameters": parameters,
                },
                timeout=timeout,
            ),
        )
