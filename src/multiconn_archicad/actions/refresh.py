from __future__ import annotations
from typing import TYPE_CHECKING
from multiconn_archicad.utilities.async_utils import run_sync

if TYPE_CHECKING:
    from multiconn_archicad.conn_header import ConnHeader
    from multiconn_archicad.multi_conn import MultiConn
    from multiconn_archicad.basic_types import Port

import logging

log = logging.getLogger(__name__)


class Refresh:
    def __init__(self, multi_conn: MultiConn) -> None:
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port) -> None:
        self.execute_action([*args])

    def from_headers(self, *args: ConnHeader) -> None:
        self.execute_action([port for port, header in self.multi_conn.open_port_headers.items() if header in args])

    def all_ports(self) -> None:
        self.execute_action(self.multi_conn.port_range)

    def open_ports(self) -> None:
        self.execute_action(self.multi_conn.open_ports)

    def closed_ports(self) -> None:
        self.execute_action(self.multi_conn.closed_ports)

    def execute_action(self, ports: list[Port]) -> None:
        run_sync(self.multi_conn.scan_ports(ports))
        self.multi_conn.open_port_headers = dict(sorted(self.multi_conn.open_port_headers.items()))
        log.info(
            f"Refreshing - Open ports: {len(self.multi_conn.open_port_headers)}, "
            f"Closed ports: {len(self.multi_conn.closed_ports)}"
        )
