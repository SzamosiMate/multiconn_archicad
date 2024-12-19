from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable
from multi_conn_ac.conn_header import *

if TYPE_CHECKING:
    from multi_conn_ac.multi_conn_ac import MultiConn
    from multi_conn_ac import Port


class ConnectionManager(ABC):
    def __init__(self, multi_conn):
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port) -> None:
        self.execute_action(
            [self.multi_conn.open_port_headers[port] for port in args if port in self.multi_conn.open_port_headers.keys()])

    def from_headers(self, *args: ConnHeader) -> None:
        self.execute_action([*args])

    def all(self) -> None:
        self.execute_action(list(self.multi_conn.open_port_headers.values()))

    @abstractmethod
    def execute_action(self, conn_headers: list[ConnHeader]) -> None:
        ...

class CommandRunner(ABC):
    def __init__(self, multi_conn):
        self.multi_conn: MultiConn = multi_conn

    def active[T, **P](self, command: Callable[[P], T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.active, command, *args, **kwargs)

    def pending[T, **P](self, command: Callable[[P], T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.pending, command, *args, **kwargs)

    def failed[T, **P](self, command: Callable[[P], T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.failed, command, *args, **kwargs)

    def open[T, **P](self, command: Callable[[P], T], *args: dict[Port, P.args],
                       **kwargs: dict[Port, P.kwargs]) -> dict[Port, T]:
        return self.execute_command(self.multi_conn.open_port_headers, command, *args, **kwargs)

    def execute_command[T, **P](self, conn_headers: dict[Port, ConnHeader], command: Callable[[P], T],
                                *args: dict[Port, P.args], **kwargs:  dict[Port, P.kwargs]) -> dict[Port, T]:
        ...
