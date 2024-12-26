from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader
    from multi_conn_ac.multi_conn import MultiConn
    from multi_conn_ac.basic_types import Port


class Refresh:
    def __init__(self, multi_conn):
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port) -> None:
        self.execute_action([*args])

    def from_headers(self, *args: ConnHeader) -> None:
        self.execute_action([port for port, header in self.multi_conn.open_port_headers.items() if header in args])

    def all_ports(self) -> None:
        self.execute_action(self.multi_conn.all_ports)

    def open_ports(self) -> None:
        self.execute_action(self.multi_conn.open_ports)

    def closed_ports(self) -> None:
        self.execute_action(self.multi_conn.closed_ports)

    def execute_action(self, ports: list[Port]) -> None:
        asyncio.run(self.multi_conn.scan_ports(ports))