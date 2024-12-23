from __future__ import annotations
from typing import TYPE_CHECKING
from .baseclasses import ConnectionManager

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader


class Disconnect(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        for conn_header in conn_headers:
            conn_header.disconnect()
