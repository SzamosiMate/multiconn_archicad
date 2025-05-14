import asyncio
from enum import Enum
from typing import Self, Any, TypeGuard, Coroutine
from pprint import pformat

from multiconn_archicad.core_commands import CoreCommands
from multiconn_archicad.basic_types import (
    ArchiCadID,
    APIResponseError,
    ProductInfo,
    Port,
    ArchicadLocation,
)
from multiconn_archicad.errors import RequestError, ArchicadAPIError, HeaderUnassignedError
from multiconn_archicad.standard_connection import StandardConnection
from multiconn_archicad.utilities.async_utils import run_sync


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
        self._core: CoreCommands | None = CoreCommands(port)
        self._standard: StandardConnection | None = StandardConnection(port)

        if initialize:
            self.product_info: ProductInfo | APIResponseError = run_sync(self.get_product_info())
            self.archicad_id: ArchiCadID | APIResponseError = run_sync(self.get_archicad_id())
            self.archicad_location: ArchicadLocation | APIResponseError = run_sync(self.get_archicad_location())

    @property
    def status(self) -> Status:
        return self._status

    @property
    def port(self) -> Port | None:
        return self._port

    @port.setter
    def port(self, port: Port | None) -> None:
        self._port = port
        if port:
            self._core = CoreCommands(port)
            self._standard = StandardConnection(port)
            match self.status:
                case Status.ACTIVE:
                    self.connect()
                case Status.UNASSIGNED:
                    self._status = Status.PENDING
                case Status.FAILED:
                    self._status = Status.PENDING
        else:
            self.unassign()

    @property
    def core(self) -> CoreCommands:
        if self._core is None:
            raise HeaderUnassignedError("CoreCommands is not initialized.")
        return self._core

    @property
    def standard(self) -> StandardConnection:
        if self._standard is None:
            raise HeaderUnassignedError("StandardConnection is not initialized.")
        return self._standard

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
            if is_header_fully_initialized(self) and is_header_fully_initialized(other):
                if (
                    self.product_info == other.product_info
                    and self.archicad_id == other.archicad_id
                    and self.archicad_location == other.archicad_location
                ):
                    return True
        return False

    def __repr__(self) -> str:
        attrs = {
            name: getattr(self, name)
            for name in ["port", "_status", "product_info", "archicad_id", "archicad_location"]
        }
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        attrs = {
            name: getattr(self, name)
            for name in ["port", "_status", "product_info", "archicad_id", "archicad_location"]
        }
        return f"{self.__class__.__name__}(\n{pformat(attrs, width=200, indent=4)})"

    @classmethod
    async def async_init(cls, port: Port) -> Self:
        instance = cls(port, initialize=False)

        async def _set(attr: str, coro: Coroutine) -> None:
            setattr(instance, attr, await coro)

        await asyncio.gather(
            _set("product_info", instance.get_product_info()),
            _set("archicad_id", instance.get_archicad_id()),
            _set("archicad_location", instance.get_archicad_location()),
        )
        return instance

    def connect(self) -> None:
        if is_product_info_initialized(self.product_info):
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
        self._core = None
        self._standard = None

    async def get_product_info(self) -> ProductInfo | APIResponseError:
        try:
            result = await self.core.post_command_async(command="API.GetProductInfo", timeout=0.2)
            return ProductInfo.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)

    async def get_archicad_id(self) -> ArchiCadID | APIResponseError:
        try:
            result = await self.core.post_tapir_command_async(command="GetProjectInfo", timeout=0.2)
            return ArchiCadID.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)

    async def get_archicad_location(self) -> ArchicadLocation | APIResponseError:
        try:
            result = await self.core.post_tapir_command_async(command="GetArchicadLocation", timeout=0.2)
            return ArchicadLocation.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)


class ValidatedHeader(ConnHeader):
    product_info: ProductInfo
    archicad_id: ArchiCadID
    archicad_location: ArchicadLocation


def is_header_fully_initialized(header: ConnHeader) -> TypeGuard[ValidatedHeader]:
    return (
        isinstance(header.product_info, ProductInfo)
        and isinstance(header.archicad_id, ArchiCadID)
        and isinstance(header.archicad_location, ArchicadLocation)
    )


def is_product_info_initialized(product_info: ProductInfo | APIResponseError) -> TypeGuard[ProductInfo]:
    return isinstance(product_info, ProductInfo)


def is_id_initialized(archicad_id: ArchiCadID | APIResponseError) -> TypeGuard[ArchiCadID]:
    return isinstance(archicad_id, ArchiCadID)


def is_location_initialized(archicad_location: ArchicadLocation | APIResponseError) -> TypeGuard[ArchicadLocation]:
    return isinstance(archicad_location, ArchicadLocation)
