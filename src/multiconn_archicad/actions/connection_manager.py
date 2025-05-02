from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from multiconn_archicad.errors import RequestError, ArchicadAPIError
from multiconn_archicad.conn_header import is_id_initialized

if TYPE_CHECKING:
    from multiconn_archicad.conn_header import ConnHeader
    from multiconn_archicad.multi_conn import MultiConn
    from multiconn_archicad.basic_types import Port

import logging

log = logging.getLogger(__name__)


class ConnectionManager(ABC):
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port) -> list[ConnHeader]:
        return self.execute_action(
            [
                self.multi_conn.open_port_headers[port]
                for port in args
                if port in self.multi_conn.open_port_headers.keys()
            ]
        )

    def from_headers(self, *args: ConnHeader) -> list[ConnHeader]:
        return self.execute_action([*args])

    def all(self) -> list[ConnHeader]:
        return self.execute_action(list(self.multi_conn.open_port_headers.values()))

    @abstractmethod
    def execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]: ...


class Connect(ConnectionManager):
    def execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]:
        for conn_header in conn_headers:
            project_name = (
                conn_header.archicad_id.projectName if is_id_initialized(conn_header.archicad_id) else "Unknown"
            )
            log.info(f"Connecting to project {project_name} at port {conn_header.port}")
            conn_header.connect()
        return conn_headers

    def failed(self) -> None:
        self.execute_action(list(self.multi_conn.failed.values()))


class Disconnect(ConnectionManager):
    def execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]:
        for conn_header in conn_headers:
            project_name = (
                conn_header.archicad_id.projectName if is_id_initialized(conn_header.archicad_id) else "Unknown"
            )
            log.info(f"Disconnecting from project {project_name} at port {conn_header.port}")
            conn_header.disconnect()
        return conn_headers


class QuitAndDisconnect(ConnectionManager):
    def execute_action(self, conn_headers: list[ConnHeader]) -> list[ConnHeader]:
        for conn_header in conn_headers:
            if conn_header.port:
                log.info(f"Sending Quit command to Archicad on port {conn_header.port} and unassigning header.")
                try:
                    conn_header.core.post_tapir_command("QuitArchicad")
                except (RequestError, ArchicadAPIError) as e:
                    log.error(f"Failed to quit archicad: error: {e}")
                    raise
                self.multi_conn.open_port_headers.pop(conn_header.port)
            conn_header.unassign()
        return conn_headers
