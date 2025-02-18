from enum import Enum
from typing import Self, Any, Awaitable, cast

from multi_conn_ac.core_commands import  CoreCommands
from multi_conn_ac.basic_types import ArchiCadID, APIResponseError, ProductInfo, Port, create_object_or_error_from_response, \
    ArchicadLocation
from multi_conn_ac.standard_connection import StandardConnection
from multi_conn_ac.utilities.async_utils import run_in_sync_or_async_context

class Status(Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    FAILED=  'failed'
    UNASSIGNED = 'unassigned'

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __str__(self) -> str:
        return self.__repr__()


class ConnHeader:

    def __init__(self, port: Port, initialize: bool = True):
        self.port: Port | None = port
        self.status: Status = Status.PENDING
        self.core: CoreCommands = CoreCommands(self.port)
        self.standard: StandardConnection = StandardConnection(self.port)

        if initialize:
            self.product_info: ProductInfo | APIResponseError = run_in_sync_or_async_context(self.get_product_info)
            self.archicad_id: ArchiCadID | APIResponseError = run_in_sync_or_async_context(self.get_archicad_id)
            self.archicad_location: ArchicadLocation | APIResponseError = run_in_sync_or_async_context(self.get_archicad_location)

    def to_dict(self) -> dict[str, Any]:
        return {
            'port': self.port,
            'productInfo': self.product_info.to_dict(),
            'archicadId': self.archicad_id.to_dict(),
            'archicadLocation': self.archicad_location.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        instance = cls(initialize=False, port=Port(data['port']))
        instance.status = Status.UNASSIGNED
        instance.product_info = ProductInfo.from_dict(data['productInfo'])
        instance.archicad_id = ArchiCadID.from_dict(data['archicadId'])
        instance.archicad_location = ArchicadLocation.from_dict(data['archicadLocation'])
        return instance

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ConnHeader):
            if self.is_fully_initialized() and other.is_fully_initialized():
                if (self.product_info == other.product_info and
                    self.archicad_id == other.archicad_id and
                    self.archicad_location == other.archicad_location):
                    return True
        return False

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        return self.__repr__()

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
            self.status = Status.ACTIVE
        else:
            self.status = Status.FAILED

    def disconnect(self) -> None:
        self.standard.disconnect()
        self.status = Status.PENDING

    def unassign(self) -> None:
        self.standard.disconnect()
        self.status = Status.UNASSIGNED
        self.port = None

    def is_fully_initialized(self) -> bool:
        return self.is_product_info_initialized() and self.is_id_and_location_initialized()

    def is_product_info_initialized(self) -> bool:
        return isinstance(self.product_info, ProductInfo)

    def is_id_and_location_initialized(self) -> bool:
        return isinstance(self.archicad_id, ArchiCadID) and isinstance(self.archicad_location, ArchicadLocation)

    async def get_product_info(self) -> ProductInfo | APIResponseError:
        result = await cast(Awaitable[dict[str, Any]], self.core.post_command(command="API.GetProductInfo"))
        return await create_object_or_error_from_response(result, ProductInfo)

    async def get_archicad_id(self) -> ArchiCadID | APIResponseError:
        result = await cast(Awaitable[dict[str, Any]], self.core.post_tapir_command(command='GetProjectInfo'))
        return await create_object_or_error_from_response(result, ArchiCadID)

    async def get_archicad_location(self) -> ArchicadLocation | APIResponseError:
        result = await cast(Awaitable[dict[str, Any]], self.core.post_tapir_command(command='GetArchicadLocation'))
        return await create_object_or_error_from_response(result, ArchicadLocation)

