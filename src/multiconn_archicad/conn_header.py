from __future__ import annotations
from concurrent.futures import Future, CancelledError
import threading
from enum import Enum
from typing import Self, Any, TypeGuard
from pprint import pformat
import logging

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
from multiconn_archicad.unified_api.api import UnifiedApi
from multiconn_archicad.utilities.thread_utils import EXECUTOR


log = logging.getLogger(__name__)


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
        self._ui_mode: bool = ui_mode
        self._is_cancelled: bool = False

        self._fetch_token: object | None = None
        self.init_future: Future | None = None

        self._core: CoreCommands | None = CoreCommands(port)
        self._standard: StandardConnection | None = StandardConnection(port)
        self._unified: UnifiedApi | None = UnifiedApi(self.core)

        self._product_info: ProductInfo | APIResponseError = PendingResponse()
        self._archicad_id: ArchiCadID | APIResponseError  = PendingResponse()
        self._archicad_location: ArchicadLocation | APIResponseError  = PendingResponse()
        if initialize and port:
            self.refresh_metadata()

    @property
    def status(self) -> Status:
        self._sync_if_needed()
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
        self._sync_if_needed()
        if self._core is None:
            raise HeaderUnassignedError("CoreCommands is not initialized.")
        return self._core

    @property
    def standard(self) -> StandardConnection:
        self._sync_if_needed()
        if self._standard is None:
            raise HeaderUnassignedError("StandardConnection is not initialized.")
        return self._standard

    @property
    def unified(self) -> UnifiedApi:
        self._sync_if_needed()
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

    def refresh_metadata(self):
        """Starts a new fetch, superseding any currently running fetch."""
        self._is_cancelled = False
        self._fetch_token = object()
        self.init_future = EXECUTOR.submit(self._fetch_worker, self._fetch_token)

    def _fetch_worker(self,  my_token: object) -> None | tuple[
        ProductInfo | APIResponseError,
        ArchiCadID | APIResponseError,
        ArchicadLocation | APIResponseError
    ]:
        product_info = self.get_product_info(timeout=5.0)
        archicad_id = self.get_archicad_id(timeout=5.0)
        archicad_location = self.get_archicad_location(timeout=5.0)

        if self._fetch_token is not my_token or self._is_cancelled:
            return None

        self._assign_metadata(product_info, archicad_id, archicad_location)
        return product_info, archicad_id, archicad_location

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
        self._sync_if_needed()
        info = self._product_info

        if is_product_info_initialized(info):
            self.standard.connect(info)
            self._status = Status.ACTIVE
        else:
            self._status = Status.FAILED

    def disconnect(self) -> None:
        self.standard.disconnect()
        self._status = Status.PENDING

    def unassign(self) -> None:
        self.cancel()
        self._status = Status.UNASSIGNED
        self._port = None
        self._core = None
        self._standard = None
        self._unified = None

    def cancel(self):
        self._is_cancelled = True

    def sync_from_master_future(self, master_future: Future) -> None:
        """Chains this header to a master future to synchronize metadata and connect once the master fetch completes."""
        self.init_future = Future()

        def _callback(completed_master: Future):
            if self.init_future is None:
                return
            if self._is_cancelled:
                self.init_future.cancel()
                return

            try:
                res = completed_master.result()
                if res:
                    self._assign_metadata(*res)
                    self.connect()
                self.init_future.set_result(res)

            except CancelledError:
                self.init_future.cancel()
            except Exception as e:
                self.init_future.set_exception(e)

        master_future.add_done_callback(_callback)

    def _sync_if_needed(self):
        """Safely blocks the thread if not in UI mode."""
        if self._ui_mode or not self.init_future:
            return
        if threading.current_thread().name.startswith("MultiConnWorker"):
            return
        if not self.init_future.done():
            try:
                self.init_future.result()
            except CancelledError:
                pass
            except Exception as e:
                log.warning(f"Background fetch failed: {e}")

    def get_product_info(self, timeout: float) -> ProductInfo | APIResponseError:
        try:
            result = self.core.post_command(command="API.GetProductInfo", timeout=timeout)
            return ProductInfo.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)
        except (KeyError, TypeError) as e:
            return APIResponseError(code=None, message=f"Malformed API response: missing key {e}")

    def get_archicad_id(self, timeout: float) -> ArchiCadID | APIResponseError:
        try:
            result = self.core.post_tapir_command(command="GetProjectInfo", timeout=timeout)
            return ArchiCadID.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)
        except (KeyError, TypeError) as e:
            return APIResponseError(code=None, message=f"Malformed API response: missing key {e}")

    def get_archicad_location(self, timeout: float) -> ArchicadLocation | APIResponseError:
        try:
            result = self.core.post_tapir_command(command="GetArchicadLocation", timeout=timeout)
            return ArchicadLocation.from_api_response(result)
        except (RequestError, ArchicadAPIError) as e:
            return APIResponseError.from_exception(e)
        except (KeyError, TypeError) as e:
            return APIResponseError(code=None, message=f"Malformed API response: missing key {e}")


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
