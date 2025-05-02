from __future__ import annotations
from typing import TYPE_CHECKING
import subprocess
import time
import psutil
from dataclasses import dataclass

from multiconn_archicad.errors import NotFullyInitializedError, ProjectAlreadyOpenError
from multiconn_archicad.utilities.platform_utils import escape_spaces_in_path, is_using_mac
from multiconn_archicad.basic_types import Port, TeamworkCredentials, TeamworkProjectID
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
