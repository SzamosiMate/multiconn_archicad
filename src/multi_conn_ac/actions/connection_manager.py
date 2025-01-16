from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader
    from multi_conn_ac.multi_conn import MultiConn
    from multi_conn_ac.basic_types import Port


class ConnectionManager(ABC):
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port) -> None:
        self.execute_action(
            [self.multi_conn.open_port_headers[port] for port in args if port in self.multi_conn.open_port_headers.keys()])

    def from_headers(self, *args: ConnHeader) -> None:
        self.execute_action([*args])

    def all(self) -> None:
        self.execute_action(list(self.multi_conn.open_port_headers.values()))


    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        ...


class Connect(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        for conn_header in conn_headers:
            print(f'connecting {conn_header.product_info}')
            conn_header.connect()

    def failed(self) -> None:
        self.execute_action(list(self.multi_conn.failed.values()))


class Disconnect(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        for conn_header in conn_headers:
            conn_header.disconnect()


class QuitAndDisconnect(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        for conn_header in conn_headers:
            conn_header.core.post_tapir_command("QuitArchicad")
            self.multi_conn.open_port_headers.pop(conn_header.port)
            conn_header.unassign()

