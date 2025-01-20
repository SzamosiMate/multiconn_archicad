from __future__ import annotations
from typing import TYPE_CHECKING
from multi_conn_ac.core_commands import callable_from_sync_or_async_context
import asyncio

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader
    from multi_conn_ac.multi_conn import MultiConn
    from multi_conn_ac.basic_types import Port


class Refresh:
    def __init__(self, multi_conn: MultiConn) -> None:
        self.multi_conn: MultiConn = multi_conn

    @callable_from_sync_or_async_context
    async def from_ports(self, *args: Port) -> None:
        await self.execute_action([*args])

    @callable_from_sync_or_async_context
    async def from_headers(self, *args: ConnHeader) -> None:
        await self.execute_action([port for port, header in self.multi_conn.open_port_headers.items() if header in args])

    @callable_from_sync_or_async_context
    async def all_ports(self) -> None:
        await self.execute_action(self.multi_conn.port_range)

    @callable_from_sync_or_async_context
    async def open_ports(self) -> None:
        await self.execute_action(self.multi_conn.open_ports)

    @callable_from_sync_or_async_context
    async def closed_ports(self) -> None:
        await self.execute_action(self.multi_conn.closed_ports)

    async def execute_action(self, ports: list[Port]) -> None:
        await self.multi_conn.scan_ports(ports)
        self.multi_conn.open_port_headers = dict(sorted(self.multi_conn.open_port_headers.items()))