from __future__ import annotations
from typing import TYPE_CHECKING
from multi_conn_ac.core_commands import sync_or_async
import asyncio

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader
    from multi_conn_ac.multi_conn import MultiConn
    from multi_conn_ac.basic_types import Port


class Refresh:
    def __init__(self, multi_conn: MultiConn) -> None:
        self.multi_conn: MultiConn = multi_conn

    @sync_or_async
    async def from_ports(self, *args: Port) -> None:
        await self.execute_action([*args])

    @sync_or_async
    async def from_headers(self, *args: ConnHeader) -> None:
        await self.execute_action([port for port, header in self.multi_conn.open_port_headers.items() if header in args])

    @sync_or_async
    async def all_ports(self) -> None:
        await self.execute_action(self.multi_conn.all_ports)

    @sync_or_async
    async def open_ports(self) -> None:
        await self.execute_action(self.multi_conn.open_ports)

    @sync_or_async
    async def closed_ports(self) -> None:
        await self.execute_action(self.multi_conn.closed_ports)

    async def execute_action(self, ports: list[Port]) -> None:
        await self.multi_conn.scan_ports(ports)
        self.multi_conn.open_port_headers = dict(sorted(self.multi_conn.open_port_headers.items()))