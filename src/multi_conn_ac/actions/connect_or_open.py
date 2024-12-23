from __future__ import annotations
from typing import TYPE_CHECKING
from .baseclasses import ConnectionManager

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader


class ConnectOrOpen(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        pass
