from functions.highlight_elements import HighlightElements
from multi_conn_ac import MultiConn, Port, ConnHeader, ArchiCadID, APIResponseError
from typing import Protocol, Any

class IFunction(Protocol):
    @staticmethod
    def run(conn: MultiConn | ConnHeader) -> dict[str, Any]:
        ...


class AppState:
    def __init__(self):
        self.conn: MultiConn = MultiConn()
        self.instance_ids: dict[Port, str] = self.get_instance_id()
        self.first_port: Port | None = self.get_first_port()
        self.script: IFunction | None = HighlightElements()
        self.run_mode: str = 'Single'

    def get_instance_id(self) -> dict[Port, str]:
        instance_ids = {}
        for port, header in self.conn.open_port_headers.items():
            if isinstance(header.archicad_id, ArchiCadID):
                instance_ids.update({port: str(port) + ": " + header.archicad_id.projectName})
            elif isinstance(header.archicad_id, APIResponseError):
                instance_ids.update({port: str(port) + ": " + header.archicad_id.message})
        return instance_ids

    def get_first_port(self) -> Port | None:
        if len(self.instance_ids) > 0:
            port = next(iter(self.instance_ids))
        else:
            port = None
        return port

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
        self.first_port = self.get_first_port()

    def run(self) -> dict[Port, dict[str, Any]]:
        if self.run_mode == 'Single':
            return self.run_single()
        elif self.run_mode == 'Multiple':
            return self.run_multiple()

    def run_single(self) -> dict[Port, dict[str, Any]]:
        return {self.conn.primary.port : self.script.run(self.conn.primary)}

    def run_multiple(self) -> dict[Port, dict[str, Any]]:
        return {port: self.script.run(header) for port, header in self.conn.active.items()}
