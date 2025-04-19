import json
from typing import Any, Awaitable, cast, Callable, Coroutine
import aiohttp
import asyncio

from multiconn_archicad.basic_types import Port
from multiconn_archicad.errors import (
    CommandTimeoutError,
    APIConnectionError,
    InvalidResponseFormatError,
    RequestError,
    StandardAPIError,
    TapirCommandError,
)
from multiconn_archicad.utilities.async_utils import callable_from_sync_or_async_context

import logging
log = logging.getLogger(__name__)

class CoreCommands:
    _BASE_URL: str = "http://127.0.0.1"

    def __init__(self, port: Port):
        self.port: Port = port
        self.url: str = f"{self._BASE_URL:}:{self.port}"

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        return self.__repr__()


    @callable_from_sync_or_async_context
    async def post_command(self, command: str, parameters: dict | None = None, timeout: float | int | None = None) -> dict[str, Any]:
        if parameters is None:
            parameters = {}
        payload = {"command": command, "parameters": parameters}

        log.debug(f"command: {command} parameters:\n {json.dumps(parameters, indent=4)}")

        response = await self._try_command(self._post_with_aiohttp, payload, timeout)

        if response.get("succeeded"):
            response = response.get("result", {})
            log.debug(f"response: {json.dumps(response, indent=4)}")
        else:
            log.warning(f"response: {response}")
            raise StandardAPIError(message=response.get("error", {}).get("message", "no message"),
                                   code=response.get("error", {}).get("code", None))
        return response


    @callable_from_sync_or_async_context
    async def post_tapir_command(self, command: str, parameters: dict | None = None, timeout: float | int | None = None) -> dict[str, Any]:
        if parameters is None:
            parameters = {}

        response = await cast(
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

        response = response.get("addOnCommandResponse", {})
        if not response.get("success", True):
            log.warning(f"response: {response}")
            raise TapirCommandError(message=response["result"].get("error", {}).get("message", "no message"),
                                    code=response["result"].get("error", {}).get("code", None))
        return response

    async def _post_with_aiohttp(self, payload: dict, timeout: float | int | None) -> dict[str, Any]:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(self.url, json=payload) as response:
                result = await response.text()
                return json.loads(result)

    async def _try_command(self, function: Callable[...,Coroutine[Any, Any, dict[str, Any]]],
                           payload: dict, timeout: float | int | None) -> dict[str, Any]:
        command_name = payload.get("command")
        try:
            return await function(payload, timeout)
        except asyncio.TimeoutError as e:
            message = f"Command '{command_name}' to {self.url} timed out after {timeout} seconds."
            log.warning(message)
            raise CommandTimeoutError(message) from e
        except aiohttp.ClientResponseError as e:
            message = f"HTTP error for command '{command_name}' to {self.url}: {e.status} {e.message}"
            log.error(message)
            raise APIConnectionError(message) from e
        except json.JSONDecodeError as e:
            message = "Failed to decode JSON response."
            log.error(message)
            raise InvalidResponseFormatError(message) from e
        except Exception as e:
            message = f"Unexpected error during post_command '{command_name}': {type(e).__name__} - {e}"
            log.exception(message)
            raise RequestError(message) from e

