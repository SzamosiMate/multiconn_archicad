from __future__ import annotations
from typing import TYPE_CHECKING
import subprocess
import time
import os
import psutil
from dataclasses import dataclass

from multiconn_archicad.errors import (
    NotFullyInitializedError,
    ProjectAlreadyOpenError,
    ProjectNotFoundError,
    StandardAPIError,
)
from multiconn_archicad.utilities.platform_utils import is_using_mac
from multiconn_archicad.utilities.exception_logging import auto_decorate_methods, log_exceptions
from multiconn_archicad.utilities.process_utils import find_port_by_pid
from multiconn_archicad.basic_types import Port, TeamworkCredentials, TeamworkProjectID, SoloProjectID
from multiconn_archicad.conn_header import ConnHeader, has_project_identity, ProjectIdentityHeader

if TYPE_CHECKING:
    from multiconn_archicad.multi_conn import MultiConn

import logging

log = logging.getLogger(__name__)


class FindArchicad:
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_header(self, header: ConnHeader) -> Port | None:
        return self._execute_action(header)

    def _execute_action(self, conn_header: ConnHeader) -> Port | None:
        if has_project_identity(conn_header):
            for port, header in self.multi_conn.open_port_headers.items():
                if header == conn_header:
                    return port
        return None


@auto_decorate_methods(log_exceptions)
class SwitchProject:
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_header(self, original_port: Port, new_header: ConnHeader) -> ConnHeader:
        if not isinstance(new_header.archicad_id, SoloProjectID):
            raise ProjectNotFoundError("Can only open solo projects in an open Archicad window")
        return self._execute_action(original_port, os.fspath(new_header.archicad_id.get_project_location()))

    def from_path(self, original_port: Port, new_path: str | os.PathLike[str]) -> ConnHeader:
        return self._execute_action(original_port, os.fspath(new_path))

    def _execute_action(self, original_port: Port, new_path: str) -> ConnHeader:
        if original_port not in self.multi_conn.open_ports:
            raise ProjectNotFoundError(f"No open project an port: {original_port}")
        if duplicate_port := self._find_duplicate_path(new_path):
            raise ProjectAlreadyOpenError(f"Project is already open at port: {duplicate_port}")
        original_header = self.multi_conn.open_port_headers[original_port]
        original_header.core.post_tapir_command("OpenProject", {"projectFilePath": new_path})
        self._wait_until_alive(original_header)
        self.multi_conn.open_port_headers[original_port] = ConnHeader(original_port)
        return self.multi_conn.open_port_headers[original_port]

    def _find_duplicate_path(self, new_path: str) -> Port | None:
        for port, header in self.multi_conn.open_port_headers.items():
            if isinstance(header.archicad_id, SoloProjectID) and header.archicad_id.projectPath == new_path:
                return port
        return None

    @staticmethod
    def _wait_until_alive(header: ConnHeader) -> bool:
        while True:
            time.sleep(0.5)
            try:
                return header.core.post_command("API.IsAlive").get("isAlive", False)
            except StandardAPIError:
                pass


@dataclass
class ProjectParams:
    conn_header: ConnHeader
    teamwork_credentials: TeamworkCredentials | None
    demo: bool


@dataclass
class ProjectIdentityParams:
    conn_header: ProjectIdentityHeader
    teamwork_credentials: TeamworkCredentials | None
    demo: bool


@auto_decorate_methods(log_exceptions)
class OpenProject:
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn
        self.process: subprocess.Popen

    def from_header(self, conn_header: ConnHeader, demo: bool = False) -> Port | None:
        project_params = ProjectParams(conn_header, None, demo)
        return self._execute_action(project_params)

    def with_teamwork_credentials(
        self, conn_header: ConnHeader, teamwork_credentials: TeamworkCredentials, demo: bool = False
    ) -> Port | None:
        project_params = ProjectParams(conn_header, teamwork_credentials, demo)
        return self._execute_action(project_params)

    def _execute_action(self, project_params: ProjectParams) -> Port | None:
        identity_params = self._check_input(project_params)
        self._check_ram_advisory(identity_params)
        self._open_project(identity_params)
        port = self._activate_and_attach_header(identity_params.conn_header)
        log.info(
            f"Successfully opened project '{identity_params.conn_header.archicad_id.projectName}' "
            f"on port {port} (Process PID: {self.process.pid})"
        )
        return port

    def _check_input(self, project_params: ProjectParams) -> ProjectIdentityParams:
        header = project_params.conn_header
        if not has_project_identity(header):
            raise NotFullyInitializedError(f"Cannot open project from partially initializer header {header}")
        if isinstance(header.archicad_id, TeamworkProjectID):
            if project_params.teamwork_credentials:
                assert project_params.teamwork_credentials.password, "You must supply a valid password!"
            else:
                assert header.archicad_id.teamworkCredentials.password, (
                    "You must supply a valid password!"
                )
        port = self.multi_conn.find_archicad.from_header(header)
        if port:
            raise ProjectAlreadyOpenError(f"Project is already open at port: {port}")
        return ProjectIdentityParams(header, project_params.teamwork_credentials, project_params.demo)

    def _check_ram_advisory(self, project_params: ProjectIdentityParams) -> None:
        """Non-blocking diagnostic warning for capacity visibility."""
        historical_peak = project_params.conn_header.peak_archicad_ram_bytes
        if historical_peak is not None:
            try:
                available_ram = psutil.virtual_memory().available
                if historical_peak > available_ram:
                    log.warning(
                        f"Opening project '{project_params.conn_header.archicad_id.projectName}' with historical "
                        f"peak RAM of {historical_peak / (1024**3):.2f} GB, but system currently has only "
                        f"{available_ram / (1024**3):.2f} GB available."
                    )
            except Exception as e:
                log.debug(f"Failed to check available system RAM: {e}")

    def _open_project(self, project_params: ProjectIdentityParams) -> None:
        self._start_process(project_params)
        self.multi_conn.dialog_handler.start(self.process)

    def _start_process(self, project_params: ProjectIdentityParams) -> None:
        log.info(f"opening project: {project_params.conn_header.archicad_id.projectName}")
        command = [
            os.fspath(project_params.conn_header.archicad_location.archicadLocation),
            os.fspath(project_params.conn_header.archicad_id.get_project_location(project_params.teamwork_credentials)),
        ]
        if project_params.demo:
            command.append("-demo")
        kwargs = {}
        if is_using_mac():
            kwargs["start_new_session"] = True
        else:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

        self.process = subprocess.Popen(command, **kwargs)

    def _activate_and_attach_header(self, header: ConnHeader) -> Port:
        port = Port(self._find_archicad_port())
        header.port = port
        header.refresh_metadata()
        self.multi_conn.open_port_headers[port] = header
        return port

    def _find_archicad_port(self) -> int:
        port = find_port_by_pid(self.process.pid, self.multi_conn.port_range, timeout=None, poll_interval=1.0)
        if port is None:
            raise RuntimeError(f"Archicad process (PID {self.process.pid}) terminated without opening a port.")
        return port
