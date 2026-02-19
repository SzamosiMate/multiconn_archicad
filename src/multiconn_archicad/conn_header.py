import asyncio
import concurrent.futures
from enum import Enum
from typing import Self, Any, TypeGuard
from pprint import pformat

from multiconn_archicad.core.core_commands import CoreCommands
from multiconn_archicad.basic_types import (
    ArchiCadID,
    APIResponseError,
    PendingResponse,
    ProductInfo,
    Port,
    ArchicadLocation
)
from multiconn_archicad.errors import RequestError, ArchicadAPIError, HeaderUnassignedError
from multiconn_archicad.standard_connection import StandardConnection
from multiconn_archicad.utilities.async_utils import start_background_task, wait_for_handle, AsyncHandle
from multiconn_archicad.unified_api.api import UnifiedApi


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
    def __init__(self, port: Port, initialize: bool = True, ui_mode: bool = False):
        self._port: Port | None = port
        self._status: Status = Status.PENDING
        self._ui_mode = ui_mode

        self._core: CoreCommands | None = CoreCommands(port)
        self._standard: StandardConnection | None = StandardConnection(port)
        self._unified: UnifiedApi | None = UnifiedApi(self.core)

        self._product_info: ProductInfo | APIResponseError = PendingResponse()
        self._archicad_id: ArchiCadID | APIResponseError = PendingResponse()
        self._archicad_location: ArchicadLocation | APIResponseError = PendingResponse()

        self._init_handle: AsyncHandle | None = None
        if initialize and port:
            self._init_handle = start_background_task(self.refresh_metadata())

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
            self._unified = UnifiedApi(self.core)
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

    @property
    def unified(self) -> UnifiedApi:
        if self._unified is None:
            raise HeaderUnassignedError("UnifiedApi is not initialized.")
        return self._unified

    @property
    def product_info(self) -> ProductInfo | APIResponseError:
        self._sync_if_needed()
        return self._product_info

    @property
    def archicad_id(self) -> ArchiCadID | APIResponseError:
        self._sync_if_needed()
        return self._archicad_id

    @property
    def archicad_location(self) -> ArchicadLocation | APIResponseError:
        self._sync_if_needed()
        return self._archicad_location

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
        instance._product_info = ProductInfo.from_dict(data["productInfo"])
        instance._archicad_id = ArchiCadID.from_dict(data["archicadId"])
        instance._archicad_location = ArchicadLocation.from_dict(data["archicadLocation"])
        return instance

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
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

    async def refresh_metadata(self):
        await self.cancel_init_handle()
        metadata = await asyncio.gather(
            self.get_product_info(timeout=3.0),
            self.get_archicad_id(timeout=3.0),
            self.get_archicad_location(timeout=3.0),
        )
        self._assign_metadata(*metadata)

    async def cancel_init_handle(self) -> None:
        if self._init_handle and not self._init_handle.done():
            self._init_handle.cancel()
            try:
                await self._init_handle
            except (asyncio.CancelledError, Exception):
                pass

    def _assign_metadata(self,
                        product_info: ProductInfo | APIResponseError,
                        archicad_id: ArchiCadID | APIResponseError,
                        archicad_location: ArchicadLocation| APIResponseError) -> None:
        if isinstance(self._product_info, APIResponseError) or isinstance(product_info, ProductInfo):
            self._product_info = product_info
        if isinstance(self._archicad_id, APIResponseError) or isinstance(archicad_id, ArchiCadID):
            self._archicad_id = archicad_id
        if isinstance(self._archicad_location, APIResponseError) or isinstance(archicad_location, ArchicadLocation):
            self._archicad_location = archicad_location

    def connect(self) -> None:
        if is_product_info_initialized(self.product_info):
            self.standard.connect(self.product_info)
            self._status = Status.ACTIVE
        elif isinstance(self.product_info, PendingResponse):
            self._status = Status.PENDING
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
        self._unified = None

    def _sync_if_needed(self):
        if self._ui_mode:
            return
        try:
            wait_for_handle(self._init_handle)
        except (concurrent.futures.CancelledError, asyncio.CancelledError):
            pass

    async def get_product_info(self, timeout: float) -> ProductInfo | APIResponseError:
        try:
            result = await self.core.post_command_async(command="API.GetProductInfo", timeout=timeout)
            return ProductInfo.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)

    async def get_archicad_id(self, timeout: float) -> ArchiCadID | APIResponseError:
        try:
            result = await self.core.post_tapir_command_async(command="GetProjectInfo", timeout=timeout)
            return ArchiCadID.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)

    async def get_archicad_location(self, timeout: float) -> ArchicadLocation | APIResponseError:
        try:
            result = await self.core.post_tapir_command_async(command="GetArchicadLocation", timeout=timeout)
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
