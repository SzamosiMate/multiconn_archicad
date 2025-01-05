from __future__ import annotations
from typing import TYPE_CHECKING
from .baseclasses import ConnectionManager

if TYPE_CHECKING:
    from multi_conn_ac.conn_header import ConnHeader


class Connect(ConnectionManager):

    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        for conn_header in conn_headers:
            print(f'connecting {conn_header.product_info}')
            conn_header.connect()

    def failed(self) -> None:
        self.execute_action(list(self.multi_conn.failed.values()))
