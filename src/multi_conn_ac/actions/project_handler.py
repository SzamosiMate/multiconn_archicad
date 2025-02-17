from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING
import subprocess
import time
import psutil

from multi_conn_ac.errors import NotFullyInitializedError, ProjectAlreadyOpenError
from multi_conn_ac.utilities.platform_utils import escape_spaces_in_path, is_using_mac
from multi_conn_ac.basic_types import Port, TeamworkCredentials
from multi_conn_ac.conn_header import ConnHeader

if TYPE_CHECKING:
    from multi_conn_ac.multi_conn import MultiConn


class ProjectHandler(ABC):
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_header(self, header: ConnHeader, **kwargs) -> Port | None:
        return self._execute_action(header, **kwargs)

    def _execute_action(self, conn_header: ConnHeader, **kwargs) -> Port | None:
        ...


class FindArchicad(ProjectHandler):

    def _execute_action(self, conn_header: ConnHeader, **kwargs) -> Port | None:
        if conn_header.is_fully_initialized():
            for port, header in self.multi_conn.open_port_headers.items():
                if header == conn_header:
                    return port
        return None


class OpenProject(ProjectHandler):

    def __init__(self, multi_conn: MultiConn):
        super().__init__(multi_conn)
        self.process: subprocess.Popen

    def with_teamwork_credentials(self, conn_header: ConnHeader,
                                  teamwork_credentials: TeamworkCredentials) -> Port | None:
        return self._execute_action(conn_header, teamwork_credentials)

    def _execute_action(self, conn_header: ConnHeader,
                        teamwork_credentials: TeamworkCredentials | None = None) -> Port | None:
        self._check_input(conn_header)
        self._open_project(conn_header, teamwork_credentials)
        port = Port(self._find_archicad_port())
        self.multi_conn.open_port_headers.update({port: ConnHeader(port)})
        return port

    def _check_input(self, header_to_check: ConnHeader) -> None:
        if not header_to_check.is_fully_initialized():
            raise NotFullyInitializedError(f"Cannot open project from partially initializer header {header_to_check}")
        port = self.multi_conn.find_archicad.from_header(header_to_check)
        if port:
            raise ProjectAlreadyOpenError(f"Project is already open at port: {port}")

    def _open_project(self, conn_header: ConnHeader, teamwork_credentials: TeamworkCredentials | None = None) -> None:
        self._start_process(conn_header, teamwork_credentials)
        self.multi_conn.dialog_handler.start(self.process)

    def _start_process(self, conn_header: ConnHeader, teamwork_credentials: TeamworkCredentials | None = None) -> None:
        print(f"opening project: {conn_header.archicad_id.projectName}")
        self.process = subprocess.Popen(
            f"{escape_spaces_in_path(conn_header.archicad_location.archicadLocation)} "
            f"{escape_spaces_in_path(conn_header.archicad_id.get_project_location(teamwork_credentials))}",
            start_new_session=True,
            shell=is_using_mac(),
            text=True
        )

    def _find_archicad_port(self):
        psutil_process = psutil.Process(self.process.pid)

        while True:
            connections = psutil_process.net_connections(kind="inet")
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN:
                    if  conn.laddr.port in self.multi_conn.port_range:
                        print(f"Detected Archicad listening on port {conn.laddr.port}")
                        return conn.laddr.port
            time.sleep(1)
