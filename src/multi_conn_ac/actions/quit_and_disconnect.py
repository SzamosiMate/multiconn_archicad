from __future__ import annotations
from typing import TYPE_CHECKING
from .baseclasses import ConnectionManager

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader


class QuitAndDisconnect(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        for conn_header in conn_headers:
            conn_header.core.post_tapir_command("QuitArchicad")
            self.multi_conn.open_port_headers.pop(conn_header.port)
            conn_header.unassign()