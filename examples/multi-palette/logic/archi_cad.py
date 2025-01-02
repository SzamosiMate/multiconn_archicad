from ..functions.highlight_elements import HighlightElements
from multi_conn_ac import MultiConn, Port, ConnHeader
from typing import Type, Protocol, Any

class IFunction(Protocol):
    @staticmethod
    def run(conn: MultiConn | ConnHeader) -> dict[str, Any]:
        ...


class AppState:
    def __init__(self):
        self.conn: MultiConn = MultiConn()
        self.instance_ids: dict[Port, str] = self.get_instance_id()
        self.first_port: Port = next(iter(self.instance_ids))
        self.function: Type[IFunction] | None = HighlightElements

    def get_instance_id(self) -> dict[Port, str]:
        return {
            port: str(port) + ": " + header.ArchiCadID.projectName
            for port, header in self.conn.open_port_headers.items()
        }

    def connect_or_disconnect(self, port: Port, do_connect: bool) -> None:
        print(f'setting port {port} to {do_connect}')
        if do_connect:
            self.conn.connect.from_ports(port)
        else:
            self.conn.disconnect.from_ports(port)
        print(f'setting port {port} to {self.conn.open_port_headers[port].status}')

    async def refresh(self) -> None:
        await self.conn.refresh.all_ports()
        self.instance_ids = self.get_instance_id()


