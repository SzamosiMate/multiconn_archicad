import asyncio
from pprint import pformat

from multiconn_archicad.utilities.async_utils import run_sync
from multiconn_archicad.utilities.network_utils import is_port_listening
from multiconn_archicad.core.core_commands import CoreCommands
from multiconn_archicad.standard_connection import StandardConnection
from multiconn_archicad.unified_api.api import UnifiedApi
from multiconn_archicad.conn_header import ConnHeader, Status
from multiconn_archicad.basic_types import Port
from multiconn_archicad.actions import (
    Connect,
    Disconnect,
    Refresh,
    QuitAndDisconnect,
    FindArchicad,
    OpenProject,
    SwitchProject,
)
from multiconn_archicad.dialog_handlers import DialogHandlerBase, EmptyDialogHandler
from multiconn_archicad.utilities.cli_parser import get_cli_args_once

import logging

log = logging.getLogger(__name__)


class MultiConn:
    _port_range: list[Port] = [Port(port) for port in range(19723, 19744)]

    def __init__(
        self,
        dialog_handler: DialogHandlerBase = EmptyDialogHandler(),
        port: Port | None = None,
        host: str = "http://127.0.0.1",
        ui_mode: bool = False,
    ) -> None:
        cli_args = get_cli_args_once()
        self._base_url: str = cli_args.host if cli_args.host else host
        self.open_port_headers: dict[Port, ConnHeader] = {}
        self._primary: ConnHeader | None = None
        self.dialog_handler: DialogHandlerBase = dialog_handler
        self._ui_mode = ui_mode

        # command namespaces of new_value
        self.core: CoreCommands | type[CoreCommands] = CoreCommands
        self.standard: StandardConnection | type[StandardConnection] = StandardConnection
        self.unified: UnifiedApi | type[UnifiedApi] = UnifiedApi

        # load actions
        self.connect: Connect = Connect(self)
        self.disconnect: Disconnect = Disconnect(self)
        self.quit: QuitAndDisconnect = QuitAndDisconnect(self)
        self.refresh: Refresh = Refresh(self)
        self.find_archicad: FindArchicad = FindArchicad(self)
        self.open_project: OpenProject = OpenProject(self)
        self.switch_project: SwitchProject = SwitchProject(self)

        self.refresh.all_ports()
        port = Port(cli_args.port) if cli_args.port else port
        run_sync(self._set_primary(port))

    @property
    def pending(self) -> dict[Port, ConnHeader]:
        return self.get_all_port_headers_with_status(Status.PENDING)

    @property
    def active(self) -> dict[Port, ConnHeader]:
        return self.get_all_port_headers_with_status(Status.ACTIVE)

    @property
    def failed(self) -> dict[Port, ConnHeader]:
        return self.get_all_port_headers_with_status(Status.FAILED)

    @property
    def open_ports(self) -> list[Port]:
        return list(self.open_port_headers.keys())

    @property
    def closed_ports(self) -> list[Port]:
        return [port for port in self._port_range if port not in self.open_port_headers.keys()]

    @property
    def port_range(self) -> list[Port]:
        return self._port_range

    @property
    def primary(self) -> ConnHeader | None:
        return self._primary

    @primary.setter
    def primary(self, new_value: Port | ConnHeader) -> None:
        run_sync(self._set_primary(new_value))

    def __repr__(self) -> str:
        attrs = {name: getattr(self, name) for name in ["pending", "active", "failed", "primary", "dialog_handler"]}
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        attrs = {name: getattr(self, name) for name in ["pending", "active", "failed", "primary", "dialog_handler"]}
        return f"{self.__class__.__name__}(\n{pformat(attrs, indent=4)})"

    def get_all_port_headers_with_status(self, status: Status) -> dict[Port, ConnHeader]:
        return {
            conn_header.port: conn_header
            for conn_header in self.open_port_headers.values()
            if conn_header.status == status and conn_header.port
        }

    async def scan_ports(self, ports: list[Port]) -> None:
        tasks = [self.check_port(port) for port in ports]
        await asyncio.gather(*tasks)

    async def check_port(self, port: Port) -> None:
        if await is_port_listening(self._base_url, port):
            await self.create_or_refresh_connection(port)
        else:
            await self.close_if_open(port)


    async def create_or_refresh_connection(self, port: Port) -> None:
        if port not in self.open_port_headers.keys():
            self.open_port_headers[port] = ConnHeader(port, ui_mode=self._ui_mode)
        else:
            await self.open_port_headers[port].refresh_metadata()

    async def close_if_open(self, port: Port) -> None:
        if port in self.open_port_headers.keys():
            log.info(f"Removing connection header for inactive/unresponsive port {port}.")
            self.open_port_headers.pop(port)
            if self._primary and self._primary.port == port:
                await self._set_primary()

    async def _set_primary(self, new_value: None | Port | ConnHeader = None) -> None:
        if isinstance(new_value, Port):
            await self._set_primary_from_port(new_value)
        elif isinstance(new_value, ConnHeader):
            await self._set_primary_from_header(new_value)
        else:
            await self._set_primary_from_none()

    async def _set_primary_from_port(self, port: Port) -> None:
        if port in self.open_port_headers.keys():
            await self._set_primary_namespaces(port)
        else:
            raise KeyError(f"Failed to set primary. Port {port} is closed.")

    async def _set_primary_from_header(self, header: ConnHeader) -> None:
        if header in self.open_port_headers.values() and header.port:
            await self._set_primary_namespaces(header.port)
        else:
            raise KeyError(f"Failed to set primary. There is no open port with header: {header}")

    async def _set_primary_from_none(self) -> None:
        for port in self._port_range:
            if port in self.open_port_headers.keys():
                await self._set_primary_namespaces(port)
                return
        await self._clear_primary_namespaces()

    async def _set_primary_namespaces(self, port: Port) -> None:
        self._primary = ConnHeader(port, ui_mode=self._ui_mode)
        log.info(f"Primary connection set to Archicad instance on port {port}")
        self._primary.connect()
        self.core = self._primary.core
        self.standard = self._primary.standard
        self.unified = self._primary.unified

    async def _clear_primary_namespaces(self) -> None:
        self._primary = None
        log.info("Primary connection cleared")
        self.core = CoreCommands
        self.standard = StandardConnection
        self.unified = UnifiedApi
