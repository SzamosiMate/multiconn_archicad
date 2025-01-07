import asyncio
from enum import Enum
from typing import Self

from multi_conn_ac.core_commands import  CoreCommands, sync_or_async
from multi_conn_ac.basic_types import ArchiCadID, APIResponseError, ProductInfo, Port, create_object_or_error_from_response
from multi_conn_ac.standard_connection import StandardConnection
from multi_conn_ac.async_utils import run_or_add_to_loop

class Status(Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    FAILED=  'failed'
    UNASSIGNED = 'unassigned'

class ConnHeader:

    def __init__(self, port: Port, initialize: bool = True):
        self.port: Port = port
        self.status: Status = Status.PENDING
        self.core: CoreCommands = CoreCommands(self.port)
        self.standard: StandardConnection = StandardConnection(self.port)

        if initialize:
            self.product_info: ProductInfo | APIResponseError = asyncio.run(self.get_product_info())
            self.archicad_id: ArchiCadID | APIResponseError = asyncio.run(self.get_archicad_id())

    @classmethod
    async def async_init(cls, port: Port) -> Self:
        instance = cls(port, initialize=False)
        instance.product_info = await instance.get_product_info()
        instance.archicad_id = await instance.get_archicad_id()
        return instance

    def connect(self) -> None:
        if isinstance(self.product_info, APIResponseError):
            self.product_info = asyncio.run(self.get_product_info())
        if isinstance(self.product_info, ProductInfo):
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

    async def get_product_info(self) -> ProductInfo | APIResponseError:
        result = await self.core.post_command(command="API.GetProductInfo")
        return await create_object_or_error_from_response(result, ProductInfo)

    async def get_archicad_id(self) -> ArchiCadID | APIResponseError:
        result = await self.core.post_tapir_command(command='GetProjectInfo')
        return await create_object_or_error_from_response(result, ArchiCadID)

