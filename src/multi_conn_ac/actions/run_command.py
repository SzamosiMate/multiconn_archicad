from __future__ import annotations
from .baseclasses import CommandRunner
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from multi_conn_ac.basic_types import Port
    from multi_conn_ac.conn_header import ConnHeader


class RunCommand(CommandRunner):

    def execute_command[T, **P](self, conn_headers: dict[Port, ConnHeader], command: Callable[[P], T],
                                *args: dict[Port, P.args], **kwargs:  dict[Port, P.kwargs]) -> dict[Port, T]:
        pass
