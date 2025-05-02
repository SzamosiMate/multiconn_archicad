from __future__ import annotations
from typing import TYPE_CHECKING
import subprocess
import time
import psutil
import os
from dataclasses import dataclass

from multiconn_archicad.errors import (
    NotFullyInitializedError,
    ProjectAlreadyOpenError,
    ProjectNotFoundError,
    StandardAPIError,
)
from multiconn_archicad.utilities.platform_utils import escape_spaces_in_path, is_using_mac
from multiconn_archicad.utilities.exception_logging import auto_decorate_methods, log_exceptions
from multiconn_archicad.basic_types import Port, TeamworkCredentials, TeamworkProjectID, SoloProjectID
from multiconn_archicad.conn_header import ConnHeader, is_header_fully_initialized, ValidatedHeader

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
        if is_header_fully_initialized(conn_header):
            for port, header in self.multi_conn.open_port_headers.items():
                if header == conn_header:
                    return port
        return None


@dataclass
class ProjectParams:
    conn_header: ValidatedHeader
    teamwork_credentials: TeamworkCredentials | None
    demo: bool


@auto_decorate_methods(log_exceptions)
class SwitchProject:
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_header(self, original_port: Port, new_header: ConnHeader) -> ConnHeader:
        if not isinstance(new_header.archicad_id, SoloProjectID):
            raise ProjectNotFoundError("Can only open solo projects in an open Archicad window")
        return self._execute_action(original_port, os.fspath(new_header.archicad_id))

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
                return header.core.post_command("API.IsAlive").get("isAlive")
            except StandardAPIError:
                pass


@auto_decorate_methods(log_exceptions)
class OpenProject:
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn
        self.process: subprocess.Popen

    def from_header(self, conn_header: ConnHeader, demo: bool = False) -> Port | None:
        if is_header_fully_initialized(conn_header):
            project_params = ProjectParams(conn_header, None, demo)
        else:
            raise NotFullyInitializedError(f"Cannot open project from partially initializer header {conn_header}")
        return self._execute_action(project_params)

    def with_teamwork_credentials(
        self, conn_header: ConnHeader, teamwork_credentials: TeamworkCredentials, demo: bool = False
    ) -> Port | None:
        if is_header_fully_initialized(conn_header):
            project_params = ProjectParams(conn_header, teamwork_credentials, demo)
        else:
            raise NotFullyInitializedError(f"Cannot open project from partially initializer header {conn_header}")
        return self._execute_action(project_params)

    def _execute_action(self, project_params: ProjectParams) -> Port | None:
        self._check_input(project_params)
        self._open_project(project_params)
        port = Port(self._find_archicad_port())
        self.multi_conn.open_port_headers.update({port: ConnHeader(port)})
        log.info(
            f"Successfully opened project '{project_params.conn_header.archicad_id.projectName}' "
            f"on port {port} (Process PID: {self.process.pid})"
        )
        return port

    def _check_input(self, project_params: ProjectParams) -> None:
        if isinstance(project_params.conn_header.archicad_id, TeamworkProjectID):
            if project_params.teamwork_credentials:
                assert project_params.teamwork_credentials.password, "You must supply a valid password!"
            else:
                assert project_params.conn_header.archicad_id.teamworkCredentials.password, (
                    "You must supply a valid password!"
                )
        port = self.multi_conn.find_archicad.from_header(project_params.conn_header)
        if port:
            raise ProjectAlreadyOpenError(f"Project is already open at port: {port}")

    def _open_project(self, project_params: ProjectParams) -> None:
        self._start_process(project_params)
        self.multi_conn.dialog_handler.start(self.process)

    def _start_process(self, project_params: ProjectParams) -> None:
        log.info(f"opening project: {project_params.conn_header.archicad_id.projectName}")
        demo_flag = " -demo" if project_params.demo else ""
        self.process = subprocess.Popen(
            f"{escape_spaces_in_path(project_params.conn_header.archicad_location.archicadLocation)} "
            f"{escape_spaces_in_path(project_params.conn_header.archicad_id.get_project_location(project_params.teamwork_credentials))}"
            + demo_flag,
            start_new_session=True,
            shell=is_using_mac(),
            text=True,
        )

    def _find_archicad_port(self):
        psutil_process = psutil.Process(self.process.pid)

        while True:
            connections = psutil_process.net_connections(kind="inet")
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN:
                    if conn.laddr.port in self.multi_conn.port_range:
                        log.debug(f"Detected Archicad listening on port {conn.laddr.port}")
                        return conn.laddr.port
            time.sleep(1)
