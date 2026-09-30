from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from multiconn_archicad.orchestration.conn_header import is_id_initialized

if TYPE_CHECKING:
    from multiconn_archicad.orchestration.conn_header import ConnHeader
    from multiconn_archicad.orchestration.multi_conn import MultiConn
    from multiconn_archicad.orchestration.basic_types import Port

import logging

log = logging.getLogger(__name__)


class ConnectionManager(ABC):
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port) -> list[ConnHeader]:
        return self._execute_action(
            [
                self.multi_conn.open_port_headers[port]
                for port in args
                if port in self.multi_conn.open_port_headers.keys()
            ]
        )

    def from_headers(self, *args: ConnHeader) -> list[ConnHeader]:
        return self._execute_action([*args])

    def all(self) -> list[ConnHeader]:
        return self._execute_action(list(self.multi_conn.open_port_headers.values()))

    @abstractmethod
    def _execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]: ...


class Connect(ConnectionManager):
    def _execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]:
        for conn_header in conn_headers:
            if conn_header.port:
                self.multi_conn._active_ports.add(conn_header.port)
                project_name = (
                    conn_header.archicad_id.projectName if is_id_initialized(conn_header.archicad_id) else "Unknown"
                )
                log.info(f"Added project {project_name} at port {conn_header.port} to active batch worklist")
        return conn_headers

    def failed(self) -> None:
        self._execute_action(list(self.multi_conn.failed.values()))


class Disconnect(ConnectionManager):
    def _execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]:
        for conn_header in conn_headers:
            if conn_header.port:
                self.multi_conn._active_ports.discard(conn_header.port)
                project_name = (
                    conn_header.archicad_id.projectName if is_id_initialized(conn_header.archicad_id) else "Unknown"
                )
                log.info(f"Removed project {project_name} at port {conn_header.port} from active batch worklist")
        return conn_headers