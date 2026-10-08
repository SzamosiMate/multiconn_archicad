from argparse import Namespace
from pprint import pformat

from multiconn_archicad.constants import DEFAULT_PORT_RANGE, DEFAULT_HOST, SUPPORTED_TAPIR_VERSION
from multiconn_archicad.orchestration.system.network_utils import is_port_listening
from multiconn_archicad.orchestration.system.thread_utils import EXECUTOR
from multiconn_archicad.clients.core.core_commands import CoreCommands
from multiconn_archicad.clients.standard_connection import StandardConnection
from multiconn_archicad.clients.unified_api.api import UnifiedApi
from multiconn_archicad.orchestration.conn_header import ConnHeader, Status
from multiconn_archicad.orchestration.events import ConnectionEvents, Dispatcher
from multiconn_archicad.orchestration.basic_types import Port
from multiconn_archicad.orchestration.actions import (
    Connect,
    Disconnect,
    Refresh,
    QuitAndDisconnect,
    FindArchicad,
    OpenProject,
    SwitchProject,
)
from multiconn_archicad.orchestration.dialog_handlers import DialogHandlerBase, EmptyDialogHandler
from multiconn_archicad.orchestration.system.cli_parser import get_cli_args_once

import logging

log = logging.getLogger(__name__)


class MultiConn:
    """Manage connections to multiple Archicad instances and select a primary connection."""

    _port_range: list[Port] = [Port(port) for port in DEFAULT_PORT_RANGE]

    def __init__(
        self,
        dialog_handler: DialogHandlerBase = EmptyDialogHandler(),
        port: Port | None = None,
        host: str | None = None,
        ui_mode: bool = False,
        dispatcher: Dispatcher | None = None,
    ) -> None:
        cli_args = get_cli_args_once()
        self._base_url: str = host if host else cli_args.host if cli_args.host else DEFAULT_HOST
        self._open_port_headers: dict[Port, ConnHeader] = {}
        self._active_ports: set[Port] = set()
        self._primary: ConnHeader | None = None
        self.events = ConnectionEvents(
            dispatcher,
            get_primary=lambda: self._primary,
            get_headers=lambda: self._open_port_headers.copy(),
        )
        self.dialog_handler: DialogHandlerBase = dialog_handler
        self._ui_mode = ui_mode

        self._fleet_scanned: bool = False

        # load actions
        self.connect: Connect = Connect(self)
        self.disconnect: Disconnect = Disconnect(self)
        self.quit: QuitAndDisconnect = QuitAndDisconnect(self)
        self.refresh: Refresh = Refresh(self)
        self.find_archicad: FindArchicad = FindArchicad(self)
        self.open_project: OpenProject = OpenProject(self)
        self.switch_project: SwitchProject = SwitchProject(self)

        self._resolve_primary(port, cli_args)

    @property
    def open_port_headers(self) -> dict[Port, ConnHeader]:
        self._ensure_fleet_scanned()
        return self._open_port_headers

    @open_port_headers.setter
    def open_port_headers(self, value: dict[Port, ConnHeader]) -> None:
        self._open_port_headers = value

    @property
    def pending(self) -> dict[Port, ConnHeader]:
        """Headers currently fetching metadata in background."""
        self._ensure_fleet_scanned()
        return self.get_all_port_headers_with_status(Status.PENDING)

    @property
    def ready(self) -> dict[Port, ConnHeader]:
        """Headers that have finished discovery and are ready for use."""
        self._ensure_fleet_scanned()
        return self.get_all_port_headers_with_status(Status.READY)

    @property
    def active(self) -> dict[Port, ConnHeader]:
        """Headers explicitly queued in MultiConn's batch execution worklist."""
        self._ensure_fleet_scanned()
        return {port: self._open_port_headers[port] for port in self._active_ports if port in self._open_port_headers}

    @property
    def failed(self) -> dict[Port, ConnHeader]:
        """Headers where metadata discovery failed or timed out."""
        self._ensure_fleet_scanned()
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
        if self._primary is None:
            self._set_primary()
        return self._primary

    @primary.setter
    def primary(self, new_value: None | Port | ConnHeader) -> None:
        self._set_primary(new_value)

    @property
    def core(self) -> CoreCommands | type[CoreCommands]:
        return self.primary.core if self.primary else CoreCommands

    @property
    def standard(self) -> StandardConnection | type[StandardConnection]:
        return self.primary.standard if self.primary else StandardConnection

    @property
    def unified(self) -> UnifiedApi | type[UnifiedApi]:
        return self.primary.unified if self.primary else UnifiedApi

    @property
    def supported_tapir_version(self) -> str:
        """Returns the Tapir API version this library was generated against."""
        return SUPPORTED_TAPIR_VERSION

    def __repr__(self) -> str:
        attrs = {
            "pending": self.get_all_port_headers_with_status(Status.PENDING),
            "ready": self.get_all_port_headers_with_status(Status.READY),
            "active": {p: self._open_port_headers[p] for p in self._active_ports if p in self._open_port_headers},
            "failed": self.get_all_port_headers_with_status(Status.FAILED),
            "primary": self._primary,
            "dialog_handler": self.dialog_handler,
        }
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        attrs = {
            "pending": self.get_all_port_headers_with_status(Status.PENDING),
            "ready": self.get_all_port_headers_with_status(Status.READY),
            "active": {p: self._open_port_headers[p] for p in self._active_ports if p in self._open_port_headers},
            "failed": self.get_all_port_headers_with_status(Status.FAILED),
            "primary": self._primary,
            "dialog_handler": self.dialog_handler,
        }
        return f"{self.__class__.__name__}(\n{pformat(attrs, indent=4)})"

    def get_all_port_headers_with_status(self, status: Status) -> dict[Port, ConnHeader]:
        return {
            conn_header.port: conn_header
            for conn_header in self._open_port_headers.values()
            if conn_header.status == status and conn_header.port
        }

    def _scan_ports(self, ports: list[Port]) -> None:
        """Probe ports in parallel, then update connections on the calling thread."""
        results = list(EXECUTOR.map(self._probe_port, ports))
        for port, listening in results:
            self._apply_port_result(port, listening)
        if set(ports) >= set(self._port_range):
            self._fleet_scanned = True

    def _check_port(self, port: Port) -> None:
        self._apply_port_result(*self._probe_port(port))

    def _probe_port(self, port: Port) -> tuple[Port, bool]:
        return port, is_port_listening(self._base_url, port)

    def _apply_port_result(self, port: Port, listening: bool) -> None:
        if listening:
            self.create_or_refresh_connection(port)
        else:
            self.close_if_open(port)

    def create_or_refresh_connection(self, port: Port) -> None:
        header = self._open_port_headers.get(port)
        if header is None:
            self._attach_header(port, ConnHeader(port, initialize=False))
        else:
            header.refresh_metadata()

    def _attach_header(self, port: Port, header: ConnHeader) -> None:
        """Register a header, start its fetch, then notify any selection change."""
        previous = self._open_port_headers.get(port)
        if previous is not None and previous is not header:
            previous.cancel()
        header._bind(events=self.events, ui_mode=self._ui_mode)
        self._open_port_headers[port] = header
        header.refresh_metadata()
        self._replace_primary(previous, header)

    def _remove_header(self, port: Port) -> ConnHeader | None:
        """Remove a managed header while preserving it for the caller."""
        header = self._open_port_headers.pop(port, None)
        self._active_ports.discard(port)
        if header is None:
            return None
        header.cancel()
        self._replace_primary(header, None)
        return header

    def close_if_open(self, port: Port) -> ConnHeader | None:
        if port in self._open_port_headers.keys():
            log.info(f"Removing connection header for inactive/unresponsive port {port}.")
        return self._remove_header(port)

    def _replace_primary(self, previous: ConnHeader | None, replacement: ConnHeader | None) -> None:
        """Follow a selected header's replacement or removal."""
        if previous is not None and self._primary is previous:
            self._commit_primary(replacement)

    def _commit_primary(self, header: ConnHeader | None) -> None:
        """Update selection and publish its change."""
        if header is not None and (header.port is None or self._open_port_headers.get(header.port) is not header):
            raise KeyError(f"Failed to set primary. Port {header.port} is closed.")
        if self._primary is header:
            return
        previous = self._primary
        self._primary = header
        self.events._primary_changed(previous, header)

    def _ensure_primary(self) -> None:
        """Select a known open connection when there is no current selection."""
        if self._primary is None and self._open_port_headers:
            self._set_primary_from_port(min(self._open_port_headers))

    def _set_primary(self, new_value: None | Port | ConnHeader = None) -> None:
        if isinstance(new_value, Port):
            self._set_primary_from_port(new_value)
        elif isinstance(new_value, ConnHeader) and new_value.port in self.open_ports:
            self._set_primary_from_header(new_value)
        elif self.open_ports:
            self._set_primary_from_port(sorted(self.open_ports)[0])
        else:
            self._commit_primary(None)
            log.info("Primary connection cleared")

    def _set_primary_from_port(self, port: Port) -> None:
        if port in self.port_range and port not in self._open_port_headers:
            self._check_port(port)
        if port in self._open_port_headers.keys():
            self._commit_primary(self._open_port_headers[port])
            log.info(f"Primary connection set to Archicad instance on port {port}")
        else:
            raise KeyError(f"Failed to set primary. Port {port} is closed.")

    def _set_primary_from_header(self, header: ConnHeader) -> None:
        if header.port and header.port not in self._open_port_headers:
            self._check_port(header.port)
        if header.port and header.port in self._open_port_headers:
            self._commit_primary(self._open_port_headers[header.port])
            log.info(f"Archicad instance matching the header found on port {header.port}. Setting primary.")
        else:
            raise KeyError(f"Failed to set primary. There is no open port with header: {header}")

    def _resolve_primary(self, port: Port | None, cli_args: Namespace) -> None:
        port = port if port else Port(cli_args.port) if cli_args.port else None
        if port is not None:
            try:
                self._set_primary(port)
            except KeyError:
                if not self._ui_mode:
                    raise
                log.warning("Requested Archicad port %s is unavailable", port)

    def _ensure_fleet_scanned(self) -> None:
        if not self._fleet_scanned:
            self._fleet_scanned = True
            log.info("Triggering on-demand fleet port scan...")
            self.refresh.all_ports()
