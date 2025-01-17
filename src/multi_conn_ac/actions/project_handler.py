from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING
import subprocess

from multi_conn_ac.errors import NotFullyInitializedError, ProjectAlreadyOpenError
from multi_conn_ac.platform_utils import escape_spaces_in_path, is_using_mac

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader
    from multi_conn_ac.multi_conn import MultiConn
    from multi_conn_ac.basic_types import Port


class ProjectHandler(ABC):
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_header(self, header: ConnHeader) -> Port | None:
        return self.execute_action(header)

    def execute_action(self, conn_headers:ConnHeader) -> Port | None:
        ...


class FindArchicad(ProjectHandler):

    def execute_action(self, header_to_check: ConnHeader) -> Port | None:
        if header_to_check.is_fully_initialized():
            for port, header in self.multi_conn.open_port_headers.items():
                return port if header == header_to_check else None


class OpenProject(ProjectHandler):

    def __init__(self, multi_conn: MultiConn):
        super().__init__(multi_conn)
        self.process: subprocess.Popen | None = None

    def execute_action(self, header: ConnHeader, timeout: int = 0) -> Port | None:
        self.check_input(header)
        self.open_project(header)
        pass

    def open_project(self, conn_header: ConnHeader) -> None:
        self.process = subprocess.Popen(
            f"{escape_spaces_in_path(conn_header.archicad_location.archicadLocation)} "
            f"{escape_spaces_in_path(conn_header.archicad_id.projectLocation)}",
            start_new_session=True,
            shell=is_using_mac(),
        )

    def check_input(self, header_to_check: ConnHeader) -> None:
        if not header_to_check.is_fully_initialized():
            raise NotFullyInitializedError(f"Cannot open project from partially initializer header {header_to_check}")
        port = self.multi_conn.find_archicad.from_header(header_to_check)
        if port:
            raise ProjectAlreadyOpenError(f"Project is already open at port: {port}")