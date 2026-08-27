from __future__ import annotations
from concurrent.futures import Future, CancelledError
import threading
from enum import Enum
from typing import Self, Any, TypeGuard, Callable
from pprint import pformat
import logging
import warnings
from dataclasses import dataclass
from pydantic import GetCoreSchemaHandler, ValidationError
from pydantic_core import core_schema

from multiconn_archicad.core.core_commands import CoreCommands
from multiconn_archicad.basic_types import (
    ArchiCadID,
    APIResponseError,
    PendingResponse,
    ProductInfo,
    Port,
    ArchicadLocation,
    TapirInfo,
    SoloProjectID,
    TeamworkProjectID,
)
from multiconn_archicad.errors import RequestError, ArchicadAPIError, HeaderUnassignedError, AddOnCommandUnavailable
from multiconn_archicad.standard_connection import StandardConnection
from multiconn_archicad.unified_api.api import UnifiedApi
from multiconn_archicad.utilities.thread_utils import EXECUTOR
from multiconn_archicad.utilities.ram_monitor import RamMonitor


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


@dataclass(frozen=True)
class HeaderMetadata:
    """Bundle containing all polled metadata from an Archicad instance."""
    product_info: ProductInfo | APIResponseError
    archicad_id: ArchiCadID | APIResponseError
    archicad_location: ArchicadLocation | APIResponseError
    tapir_info: TapirInfo | APIResponseError


class ConnHeader:
    def __init__(
        self,
        port: Port | None = None,
        initialize: bool = True,
        ui_mode: bool = False,
        initial_peak_ram_bytes: int | None = None,
    ):
        self._port: Port | None = port
        self._status: Status = Status.PENDING if port else Status.UNASSIGNED
        self._ui_mode: bool = ui_mode
        self._is_cancelled: bool = False

        self._ram_monitor = RamMonitor(
            port_getter=lambda: self._port,
            initial_peak_bytes=initial_peak_ram_bytes,
        )

        self._fetch_token: object | None = None
        self.init_future: Future | None = None
        self._unpacked_future: Future | None = None
        self._auto_connect: bool = False

        self._core: CoreCommands | None = CoreCommands(port) if port else None
        self._standard: StandardConnection | None = StandardConnection(port) if port else None
        self._unified: UnifiedApi | None = UnifiedApi(self.core) if self._core else None

        self._product_info: ProductInfo | APIResponseError = PendingResponse()
        self._archicad_id: ArchiCadID | APIResponseError = PendingResponse()
        self._archicad_location: ArchicadLocation | APIResponseError = PendingResponse()
        self._tapir_info: TapirInfo | APIResponseError = PendingResponse()

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
        self._ram_monitor.reset_process()
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
    def ram_monitor(self) -> RamMonitor:
        """Process RAM telemetry and background tracking controller."""
        return self._ram_monitor

    @property
    def peak_archicad_ram_bytes(self) -> int | None:
        """The maximum observed RSS memory usage in bytes for this project."""
        return self._ram_monitor.peak_bytes

    @peak_archicad_ram_bytes.setter
    def peak_archicad_ram_bytes(self, value: int | None) -> None:
        self._ram_monitor.peak_bytes = value

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

    @property
    def tapir_info(self) -> TapirInfo | APIResponseError:
        self._sync_if_needed()
        return self._tapir_info

    def to_dict(self) -> dict[str, Any]:
        """Serialize connection header. Requires the header to be fully initialized."""
        if not has_project_identity(self):
            raise ValueError(
                f"Cannot serialize ConnHeader on port {self.port}: Header is not fully initialized "
                f"(status={self._status.value})."
            )
        return {
            "productInfo": self._product_info.model_dump(),
            "archicadId": self._archicad_id.model_dump(),
            "archicadLocation": self._archicad_location.model_dump(),
            "peakArchicadRamBytes": self.peak_archicad_ram_bytes,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Self:
        """Validate and construct a ConnHeader from serialized snapshot data."""
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ValueError(f"Expected {cls.__name__} instance or dict, got {type(data).__name__}")

        instance = cls(initialize=False)
        instance._product_info = ProductInfo.model_validate(data["productInfo"])
        instance._archicad_id = ArchiCadID.model_validate(data["archicadId"])
        instance._archicad_location = ArchicadLocation.model_validate(data["archicadLocation"])
        instance.peak_archicad_ram_bytes = data.get("peakArchicadRamBytes")
        return instance

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Enables Pydantic V2 to serialize/deserialize ConnHeader controllers."""
        return core_schema.json_or_python_schema(
            json_schema=core_schema.chain_schema([
                core_schema.dict_schema(),
                core_schema.no_info_plain_validator_function(cls.from_dict),
            ]),
            python_schema=core_schema.chain_schema([
                core_schema.no_info_plain_validator_function(cls.from_dict),
                core_schema.is_instance_schema(cls),
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance.to_dict(),
                when_used="always",
            ),
        )

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if isinstance(other, ConnHeader):
            if has_project_identity(self) and has_project_identity(other):
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
            for name in [
                "port",
                "_status",
                "product_info",
                "archicad_id",
                "archicad_location",
                "tapir_info",
                "peak_archicad_ram_bytes",
            ]
        }
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        attrs = {
            name: getattr(self, name)
            for name in [
                "port",
                "_status",
                "product_info",
                "archicad_id",
                "archicad_location",
                "tapir_info",
                "peak_archicad_ram_bytes",
            ]
        }
        return f"{self.__class__.__name__}(\n{pformat(attrs, width=200, indent=4)})"

    def refresh_metadata(self):
        """Starts a new fetch, superseding any currently running fetch."""
        self._is_cancelled = False
        self._fetch_token = object()
        self.init_future = EXECUTOR.submit(self._fetch_worker, self._fetch_token)

    def _fetch_worker(self, my_token: object) -> HeaderMetadata | None:
        metadata = HeaderMetadata(
            product_info=self.get_product_info(timeout=5.0),
            archicad_id=self.get_archicad_id(timeout=5.0),
            archicad_location=self.get_archicad_location(timeout=5.0),
            tapir_info=self.get_tapir_info(timeout=5.0),
        )

        if self._fetch_token is not my_token or self._is_cancelled:
            return None

        self._assign_metadata(metadata)
        return metadata

    def _assign_metadata(self, metadata: HeaderMetadata) -> None:
        if isinstance(self._product_info, APIResponseError) or isinstance(metadata.product_info, ProductInfo):
            self._product_info = metadata.product_info
        if isinstance(self._archicad_id, APIResponseError) or isinstance(metadata.archicad_id, ArchiCadID):
            self._archicad_id = metadata.archicad_id
        if isinstance(self._archicad_location, APIResponseError) or isinstance(metadata.archicad_location, ArchicadLocation):
            self._archicad_location = metadata.archicad_location
        if isinstance(self._tapir_info, APIResponseError) or isinstance(metadata.tapir_info, TapirInfo):
            self._tapir_info = metadata.tapir_info

    def connect(self) -> None:
        """Public method to wait for metadata and establish standard API connection."""
        self._sync_if_needed()
        self._resolve_connection_state()

    def disconnect(self) -> None:
        self.standard.disconnect()
        self._status = Status.PENDING

    def unassign(self) -> None:
        self.cancel()
        self._ram_monitor.reset_process()
        self._status = Status.UNASSIGNED
        self._port = None
        self._core = None
        self._standard = None
        self._unified = None

    def cancel(self):
        self._is_cancelled = True

    def sync_from_master_future(self, master_future: Future) -> None:
        """Links this header to a master future."""
        self.init_future = master_future
        self._auto_connect = True

    def _sync_if_needed(self):
        """Safely unpacks the future when data is needed or ready."""
        if (
            not self.init_future
            or self.init_future is self._unpacked_future
            or threading.current_thread().name.startswith("MultiConnWorker")
        ):
            return

        if self._ui_mode:  # UI Mode: Only unpack if background thread is done
            if self.init_future.done():
                self._unpack_future()
        else:  # Standard Mode: Safely block and wait for data
            self._unpack_future()

    def _unpack_future(self) -> None:
        """Helper to resolve the future and mutate state."""
        try:
            res = self.init_future.result()
            if res and self.init_future is not self._unpacked_future:
                self._assign_metadata(res)
                self._unpacked_future = self.init_future

                if self._auto_connect and self._status == Status.PENDING:
                    self._resolve_connection_state()

        except CancelledError:
            pass
        except Exception as e:
            log.warning(f"Background fetch failed: {e}")
            self._status = Status.FAILED
            self._unpacked_future = self.init_future

    def _resolve_connection_state(self) -> None:
        """Configures standard connection and updates header status based on product info."""
        info = self._product_info
        if is_product_info_initialized(info):
            if self._standard is None:
                raise HeaderUnassignedError("StandardConnection is not initialized.")
            self._standard.connect(info)
            self._status = Status.ACTIVE
        else:
            self._status = Status.FAILED

    def _execute_api_fetch[T](
        self,
        command_fn: Callable[[], Any],
        validator_fn: Callable[[Any], T],
        fallbacks: dict[type[Exception], Callable[[], T]] | None = None,
    ) -> T | APIResponseError:
        """Centralized executor handling timeouts, API errors, and validation errors."""
        try:
            raw_result = command_fn()
            return validator_fn(raw_result)
        except Exception as e:
            if fallbacks:
                for exc_type, fallback_factory in fallbacks.items():
                    if isinstance(e, exc_type):
                        return fallback_factory()
            if isinstance(e, (RequestError, ArchicadAPIError)):
                return APIResponseError.from_exception(e)
            if isinstance(e, (KeyError, TypeError, ValidationError)):
                return APIResponseError(code=None, message=f"Malformed API response: {e}")
            raise

    def get_product_info(self, timeout: float) -> ProductInfo | APIResponseError:
        return self._execute_api_fetch(
            lambda: self.core.post_command("API.GetProductInfo", timeout=timeout),
            ProductInfo.model_validate,
        )

    def get_archicad_id(self, timeout: float) -> ArchiCadID | APIResponseError:
        return self._execute_api_fetch(
            lambda: self.core.post_tapir_command("GetProjectInfo", timeout=timeout),
            ArchiCadID.model_validate,
        )

    def get_archicad_location(self, timeout: float) -> ArchicadLocation | APIResponseError:
        return self._execute_api_fetch(
            lambda: self.core.post_tapir_command("GetArchicadLocation", timeout=timeout),
            ArchicadLocation.model_validate,
        )

    def get_tapir_info(self, timeout: float) -> TapirInfo | APIResponseError:
        return self._execute_api_fetch(
            lambda: self.core.post_tapir_command("GetAddOnVersion", timeout=timeout),
            TapirInfo.model_validate,
            fallbacks={AddOnCommandUnavailable: TapirInfo.not_installed},
        )


class ProjectIdentityHeader(ConnHeader):
    """Guaranteed to have all metadata that is required to reopen a project"""
    product_info: ProductInfo
    archicad_id: SoloProjectID | TeamworkProjectID
    archicad_location: ArchicadLocation


# Deprecation Alias
ValidatedHeader = ProjectIdentityHeader


class SessionReadyHeader(ProjectIdentityHeader):
    """Guaranteed to be active, connected to a port, with Tapir polled."""
    port: Port
    tapir_info: TapirInfo
    core: CoreCommands
    standard: StandardConnection
    unified: UnifiedApi


def has_project_identity(header: ConnHeader) -> TypeGuard[ProjectIdentityHeader]:
    """Validates that the header has full project identity data for serialization/launch."""
    return bool(
        isinstance(header.product_info, ProductInfo)
        and isinstance(header.archicad_id, (SoloProjectID, TeamworkProjectID))
        and isinstance(header.archicad_location, ArchicadLocation)
    )


def is_session_ready(header: ConnHeader) -> TypeGuard[SessionReadyHeader]:
    """Validates that Archicad is live on a port and all background tasks have finished."""
    return bool(
        has_project_identity(header)
        and header.port is not None
        and header.status == Status.ACTIVE
        and isinstance(header.tapir_info, TapirInfo)
    )


def is_tapir_session_ready(header: ConnHeader) -> TypeGuard[SessionReadyHeader]:
    """Validates that Archicad is live on a port and the Tapir API version meets requirements"""
    return bool(
        is_session_ready(header)
        and header.tapir_info.is_installed
        and header.tapir_info.is_supported
    )


def is_product_info_initialized(product_info: ProductInfo | APIResponseError) -> TypeGuard[ProductInfo]:
    return isinstance(product_info, ProductInfo)


def is_id_initialized(archicad_id: ArchiCadID | APIResponseError) -> TypeGuard[ArchiCadID]:
    return isinstance(archicad_id, ArchiCadID)


def is_location_initialized(archicad_location: ArchicadLocation | APIResponseError) -> TypeGuard[ArchicadLocation]:
    return isinstance(archicad_location, ArchicadLocation)


def is_tapir_info_initialized(tapir_info: TapirInfo | APIResponseError) -> TypeGuard[TapirInfo]:
    return isinstance(tapir_info, TapirInfo)


def is_header_fully_initialized(header: ConnHeader) -> TypeGuard[ValidatedHeader]:
    """Deprecated: Use has_project_identity instead."""
    warnings.warn(
        "is_header_fully_initialized is deprecated and will be removed in a future release. "
        "Use has_project_identity instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return has_project_identity(header)