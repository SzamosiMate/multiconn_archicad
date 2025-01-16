from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from multi_conn_ac.multi_conn import MultiConn
    from multi_conn_ac.conn_header import ConnHeader
    from multi_conn_ac.basic_types import Port


class CommandRunner(ABC):
    def __init__(self, multi_conn: MultiConn) -> None:
        self.multi_conn: MultiConn = multi_conn

    def active[T, **P](self, command: Callable[P, T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.active, command, *args, **kwargs)

    def pending[T, **P](self, command: Callable[P, T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.pending, command, *args, **kwargs)

    def failed[T, **P](self, command: Callable[P, T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.failed, command, *args, **kwargs)

    def open[T, **P](self, command: Callable[P, T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.open_port_headers, command, *args, **kwargs)

    @abstractmethod
    def execute_command[T, **P](
        self,
        conn_headers: dict[Port, ConnHeader],
        command: Callable[P, T],
        *args: dict[Port, P.args],
        **kwargs: dict[Port, P.kwargs],
    ) -> dict[Port, T]:
        ...
