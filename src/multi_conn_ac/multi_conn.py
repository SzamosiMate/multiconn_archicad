import asyncio
import aiohttp

from multi_conn_ac.core_commands import CoreCommands
from multi_conn_ac.archicad_connection import ArchiCADConnection
from multi_conn_ac.conn_header import ConnHeader, Status
from multi_conn_ac.basic_types import Port, APIResponseError
from multi_conn_ac.actions import Connect, Disconnect, Refresh, QuitAndDisconnect


class MultiConn:
    _base_url: str = "http://127.0.0.1"
    _port_range: list[Port] = [Port(port) for port in range(19723, 19744)]

    def __init__(self):
        self.open_port_headers: dict[Port, ConnHeader] = {}
        self._primary: ConnHeader | None = None

        # command namespaces of new_value
        self.core: CoreCommands | type(CoreCommands) = CoreCommands
        self.archicad: ArchiCADConnection | type(ArchiCADConnection) = ArchiCADConnection

        # load actions
        self.connect: Connect = Connect(self)
        self.disconnect: Disconnect = Disconnect(self)
        self.quit: QuitAndDisconnect = QuitAndDisconnect(self)
        self.refresh: Refresh = Refresh(self)

        self.refresh.all_ports()
        self.set_primary()


    @property
    def pending(self) -> dict[Port, ConnHeader]:
        return self.get_all_port_headers_with_status(Status.PENDING)

    @property
    def active(self) -> dict[Port, ConnHeader]:
        return self.get_all_port_headers_with_status(Status.ACTIVE)

    @property
    def failed(self) -> dict[Port, ConnHeader]:
        return self.get_all_port_headers_with_status(Status.FAILED)

    @property
    def open_ports(self) -> list[Port]:
        return list(self.open_port_headers.keys())

    @property
    def closed_ports(self) -> list[Port]:
        return [port for port in self._port_range if port not in self.open_port_headers.keys()]

    @property
    def all_ports(self) -> list[Port]:
        return self._port_range

    def get_all_port_headers_with_status(self, status: Status) -> dict[Port, ConnHeader]:
        return {conn_header.port: conn_header
                for conn_header in self.open_port_headers.values()
                if conn_header.status == status}

    async def scan_ports(self, ports: list[Port]) -> None:
        async with aiohttp.ClientSession() as session:
            tasks = [self.check_port(session, port) for port in ports]
            await asyncio.gather(*tasks)

    async def check_port(self, session: aiohttp.ClientSession, port: Port) -> None:
        url = f"{self._base_url}:{port}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=1)) as response:
                if response.status == 200:
                    await self.create_or_refresh_connection(port)
                else:
                    await self.close_if_open(port)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            await self.close_if_open(port)
            print(f"Port {port} is raises exception")

    async def create_or_refresh_connection(self, port: Port) -> None:
        if port not in self.open_port_headers.keys():
            self.open_port_headers[port] = await ConnHeader.async_init(port)
        else:
            if isinstance(self.open_port_headers[port].ProductInfo, APIResponseError):
                await self.open_port_headers[port].get_product_info()
            if isinstance(self.open_port_headers[port].ArchiCadID, APIResponseError):
                await self.open_port_headers[port].get_archicad_id()

    async def close_if_open(self, port: Port) -> None:
        if port in self.open_port_headers.keys():
            self.open_port_headers.pop(port)
            if self._primary.port == port:
                self.set_primary()

    @property
    def primary(self) -> ConnHeader | None:
        return self._primary

    @primary.setter
    def primary(self, new_value: Port | ConnHeader) -> None:
        self.set_primary(new_value)

    def set_primary(self, new_value: None | Port | ConnHeader = None) -> None:
        if isinstance(new_value, Port):
            self._set_primary_from_port(new_value)
        elif isinstance(new_value, ConnHeader):
            self._set_primary_from_header(new_value)
        else:
            self._set_primary_from_none()

    def _set_primary_from_port(self, port: Port) -> None:
        if port in self.open_port_headers.keys():
            self._set_primary_namespaces(port)
        else:
            raise KeyError(f"Failed to set primary. Port {port} is closed.")

    def _set_primary_from_header(self, header: ConnHeader) -> None:
        if header in self.open_port_headers.values():
            self._set_primary_namespaces(header.port)
        else:
            raise KeyError(f"Failed to set primary. There is no open port with header: {header}")

    def _set_primary_from_none(self) -> None:
        for port in self._port_range:
            if port in self.open_port_headers.keys():
                self._set_primary_namespaces(port)
                return
        self._clear_primary_namespaces()

    def _set_primary_namespaces(self, port: Port) -> None:
        self._primary = self.open_port_headers[port]
        self.core = self._primary.core
        self.archicad = self._primary.archicad

    def _clear_primary_namespaces(self) -> None:
        self._primary = None
        self.core = CoreCommands
        self.archicad = ArchiCADConnection
