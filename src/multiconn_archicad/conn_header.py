from enum import Enum
from typing import Self, Any, Awaitable, cast
from pprint import pformat

from multiconn_archicad.core_commands import CoreCommands
from multiconn_archicad.basic_types import (
    ArchiCadID,
    APIResponseError,
    ProductInfo,
    Port,
    ArchicadLocation,
)
from multiconn_archicad.errors import RequestError, ArchicadAPIError
from multiconn_archicad.standard_connection import StandardConnection
from multiconn_archicad.utilities.async_utils import run_in_sync_or_async_context


class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    UNASSIGNED = "unassigned"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __str__(self) -> str:
        return self.__repr__()


class ConnHeader:
    def __init__(self, port: Port, initialize: bool = True):
        self._port: Port | None = port
        self._status: Status = Status.PENDING
        self.core: CoreCommands  | type[CoreCommands]= CoreCommands(port)
        self.standard: StandardConnection  | type[StandardConnection]= StandardConnection(port)

        if initialize:
            self.product_info: ProductInfo | APIResponseError = run_in_sync_or_async_context(self.get_product_info)
            self.archicad_id: ArchiCadID | APIResponseError = run_in_sync_or_async_context(self.get_archicad_id)
            self.archicad_location: ArchicadLocation | APIResponseError = run_in_sync_or_async_context(
                self.get_archicad_location
            )

    @property
    def status(self) -> Status:
        return self._status

    @property
    def port(self) -> Port:
        return self._port

    @port.setter
    def port(self, port: Port | None) -> None:
        self._port = port
        if port:
            self.core = CoreCommands(port)
            self.standard = StandardConnection(port)
            if self.status == Status.ACTIVE:
                self.standard.connect(self.product_info)
        else:
            self.unassign()

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "productInfo": self.product_info.to_dict(),
            "archicadId": self.archicad_id.to_dict(),
            "archicadLocation": self.archicad_location.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        instance = cls(initialize=False, port=Port(data["port"]))
        instance._status = Status.UNASSIGNED
        instance.product_info = ProductInfo.from_dict(data["productInfo"])
        instance.archicad_id = ArchiCadID.from_dict(data["archicadId"])
        instance.archicad_location = ArchicadLocation.from_dict(data["archicadLocation"])
        return instance

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ConnHeader):
            if self.is_fully_initialized() and other.is_fully_initialized():
                if (
                    self.product_info == other.product_info
                    and self.archicad_id == other.archicad_id
                    and self.archicad_location == other.archicad_location
                ):
                    return True
        return False

    def __repr__(self) -> str:
        attrs = {name: getattr(self, name) for name in ["port", "_status", "product_info", "archicad_id", "archicad_location"]}
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        attrs = {name: getattr(self, name) for name in ["port", "_status", "product_info", "archicad_id", "archicad_location"]}
        return f"{self.__class__.__name__}(\n{pformat(attrs, width=200, indent=4)})"

    @classmethod
    async def async_init(cls, port: Port) -> Self:
        instance = cls(port, initialize=False)
        instance.product_info = await instance.get_product_info()
        instance.archicad_id = await instance.get_archicad_id()
        instance.archicad_location = await instance.get_archicad_location()
        return instance

    def connect(self) -> None:
        if self.is_product_info_initialized():
            self.standard.connect(self.product_info)
            self._status = Status.ACTIVE
        else:
            self._status = Status.FAILED

    def disconnect(self) -> None:
        self.standard.disconnect()
        self._status = Status.PENDING

    def unassign(self) -> None:
        self._status = Status.UNASSIGNED
        self._port = None
        self.core = CoreCommands
        self.standard = StandardConnection

    def is_fully_initialized(self) -> bool:
        return (self.is_product_info_initialized()
                and self.is_id_initialized()
                and self.is_location_initialized())

    def is_product_info_initialized(self) -> bool:
        return isinstance(self.product_info, ProductInfo)

    def is_id_initialized(self) -> bool:
        return isinstance(self.archicad_id, ArchiCadID)

    def is_location_initialized(self) -> bool:
        return isinstance(self.archicad_location, ArchicadLocation)

    async def get_product_info(self) -> ProductInfo | APIResponseError:
        try:
            result = await cast(Awaitable[dict[str, Any]], self.core.post_command(command="API.GetProductInfo", timeout=0.2))
            return ProductInfo.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)

    async def get_archicad_id(self) -> ArchiCadID | APIResponseError:
        try:
            result = await cast(Awaitable[dict[str, Any]], self.core.post_tapir_command(command="GetProjectInfo", timeout=0.2))
            return ArchiCadID.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)

    async def get_archicad_location(self) -> ArchicadLocation | APIResponseError:
        try:
            result = await cast(Awaitable[dict[str, Any]], self.core.post_tapir_command(command="GetArchicadLocation", timeout=0.2))
            return ArchicadLocation.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)
