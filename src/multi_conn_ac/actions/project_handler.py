from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING, Callable
import subprocess
import time
import psutil

from multi_conn_ac.errors import NotFullyInitializedError, ProjectAlreadyOpenError
from multi_conn_ac.platform_utils import escape_spaces_in_path, is_using_mac
from multi_conn_ac.basic_types import Port, TeamworkCredentials
from multi_conn_ac.conn_header import ConnHeader

if TYPE_CHECKING:
    from multi_conn_ac.multi_conn import MultiConn


class ProjectHandler(ABC):
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_header(self, header: ConnHeader, **kwargs) -> Port | None:
        return self.execute_action(header, **kwargs)

    def execute_action(self, conn_headers:ConnHeader, **kwargs) -> Port | None:
        ...


class FindArchicad(ProjectHandler):

    def execute_action(self, header_to_check: ConnHeader, **kwargs) -> Port | None:
        if header_to_check.is_fully_initialized():
            for port, header in self.multi_conn.open_port_headers.items():
                if header == header_to_check:
                    return port
        return None


class OpenProject(ProjectHandler):

    def __init__(self, multi_conn: MultiConn):
        super().__init__(multi_conn)
        self.process: subprocess.Popen | None = None

    def with_teamwork_credentials(self, header: ConnHeader,
                                  teamwork_credentials: TeamworkCredentials,
                                  dialog_handler: Callable[[subprocess.Popen], None] | None = None) -> Port | None:
        return self.execute_action(header, teamwork_credentials, dialog_handler)

    def execute_action(self, header: ConnHeader,
                       teamwork_credentials: TeamworkCredentials | None = None,
                       dialog_handler: Callable[[subprocess.Popen], None] | None = None) -> Port | None:
        self.check_input(header)
        self.open_project(header, teamwork_credentials)
        print("project open")
        if dialog_handler:
            dialog_handler(self.process)
        print(self.monitor_stdout())
        if dialog_handler:
            dialog_handler(self.process)
        port = Port(self.find_archicad_port())
        self.multi_conn.open_port_headers.update({port: ConnHeader(port)})
        return port

    def check_input(self, header_to_check: ConnHeader) -> None:
        if not header_to_check.is_fully_initialized():
            raise NotFullyInitializedError(f"Cannot open project from partially initializer header {header_to_check}")
        port = self.multi_conn.find_archicad.from_header(header_to_check)
        if port:
            raise ProjectAlreadyOpenError(f"Project is already open at port: {port}")

    def open_project(self, conn_header: ConnHeader, teamwork_credentials: TeamworkCredentials | None = None) -> None:
        self.process = subprocess.Popen(
            f"{escape_spaces_in_path(conn_header.archicad_location.archicadLocation)} "
            f"{escape_spaces_in_path(conn_header.archicad_id.get_project_location(teamwork_credentials))}",
            start_new_session=True,
            shell=is_using_mac(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    def monitor_stdout(self) -> str:
        print("Waiting for output...")
        while True:
            line = self.process.stdout.readline()
            time.sleep(1)
            if not line:
                break
            self.process.stdout.close()
            self.process.stderr.close()
            return line.strip()

    def find_archicad_port(self):
        psutil_process = psutil.Process(self.process.pid)

        while True:
            # Get all network connections for the process
            connections = psutil_process.net_connections(kind="inet")
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN:
                    if  conn.laddr.port in self.multi_conn.port_range:
                        print(f"Detected Archicad listening on port {conn.laddr.port}")
                        return conn.laddr.port
            time.sleep(1)
