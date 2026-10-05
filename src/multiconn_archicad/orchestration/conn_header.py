from __future__ import annotations
from concurrent.futures import Future, CancelledError
import threading
from typing import Self, Any, TypeGuard, Callable, TYPE_CHECKING
from pprint import pformat
import logging
import warnings

from pydantic import GetCoreSchemaHandler, ValidationError
from pydantic_core import core_schema

from multiconn_archicad.clients.core.core_commands import CoreCommands
from multiconn_archicad.orchestration.basic_types import (
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
from multiconn_archicad.clients.standard_connection import StandardConnection
from multiconn_archicad.clients.unified_api.api import UnifiedApi
from multiconn_archicad.orchestration.system.thread_utils import EXECUTOR
from multiconn_archicad.orchestration.system.ram_monitor import RamMonitor
from multiconn_archicad.orchestration.header_state import (
    HeaderMetadata as HeaderMetadata,
    HeaderSnapshot,
    HeaderState,
    Status as Status,
)

if TYPE_CHECKING:
    from multiconn_archicad.orchestration.events import ConnectionEvents


log = logging.getLogger(__name__)


class ConnHeader:
    """Represent an Archicad connection with its metadata and API clients."""

    def __init__(
        self,
        port: Port | None = None,
        initialize: bool = True,
        ui_mode: bool = False,
        initial_peak_ram_bytes: int | None = None,
    ):
        self._port: Port | None = port
        self._state = HeaderState(Status.PENDING if port else Status.UNASSIGNED)
        self._ui_mode: bool = ui_mode
        self._events: ConnectionEvents | None = None
        self._fetch_context = threading.local()

        self._ram_monitor = RamMonitor(
            port_getter=lambda: self._port,
            initial_peak_bytes=initial_peak_ram_bytes,
        )

        self._fetch_task: tuple[object, Future] | None = None
        self._waited_future: Future | None = None

        self._core: CoreCommands | None = CoreCommands(port) if port else None
        self._standard: StandardConnection | None = StandardConnection(port) if port else None
        self._unified: UnifiedApi | None = UnifiedApi(self.core) if self._core else None

        if initialize and port:
            self.refresh_metadata()

    def _bind(self, *, events: ConnectionEvents, ui_mode: bool) -> None:
        """Configure an adopted header before registration and metadata fetching."""
        self._events = events
        self._ui_mode = ui_mode

    def _snapshot(self) -> HeaderSnapshot:
        self._sync_if_needed()
        return self._state.snapshot()

    @property
    def status(self) -> Status:
        return self._snapshot().status

    @property
    def port(self) -> Port | None:
        return self._port

    @port.setter
    def port(self, port: Port | None) -> None:
        if port == self._port:
            return
        if self._port is not None and port is not None:
            raise ValueError(
                f"Cannot reassign ConnHeader from port {self._port} to {port}. "
                f"ConnHeader is bound to a single Archicad instance. Create a new ConnHeader instead."
            )

        self._port = port
        self._ram_monitor.reset_process()

        if port:
            self._core = CoreCommands(port)
            self._standard = StandardConnection(port)
            self._unified = UnifiedApi(self.core)
            self._state.assign()
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
        """Standard Graphisoft connection with JIT self-healing version binding."""
        self._sync_if_needed()
        if self._standard is None:
            raise HeaderUnassignedError("StandardConnection is not initialized.")
        product_info = self._state.snapshot().metadata.product_info
        if not self._standard.is_versioned and is_product_info_initialized(product_info):
            self._standard.bind(product_info)
        return self._standard

    @property
    def unified(self) -> UnifiedApi:
        self._sync_if_needed()
        if self._unified is None:
            raise HeaderUnassignedError("UnifiedApi is not initialized.")
        return self._unified

    @property
    def product_info(self) -> ProductInfo | APIResponseError:
        return self._snapshot().metadata.product_info

    @property
    def archicad_id(self) -> ArchiCadID | APIResponseError:
        return self._snapshot().metadata.archicad_id

    @property
    def archicad_location(self) -> ArchicadLocation | APIResponseError:
        return self._snapshot().metadata.archicad_location

    @property
    def tapir_info(self) -> TapirInfo | APIResponseError:
        return self._snapshot().metadata.tapir_info

    @property
    def latest_metadata(self) -> HeaderMetadata | None:
        """Current fetch result, without historical fallback; None while pending or canceled."""
        return self._snapshot().latest_metadata

    def to_dict(self) -> dict[str, Any]:
        """Serialize connection header. Requires the header to have project identity."""
        snapshot = self._snapshot()
        metadata = snapshot.metadata
        if not _has_project_identity(metadata):
            raise ValueError(
                f"Cannot serialize ConnHeader on port {self.port}: Header is missing project identity "
                f"(status={snapshot.status.value})."
            )
        return {
            "productInfo": metadata.product_info.model_dump(),
            "archicadId": metadata.archicad_id.model_dump(),
            "archicadLocation": metadata.archicad_location.model_dump(),
            "peakArchicadRamBytes": self.peak_archicad_ram_bytes,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Self:
        """Validate and construct a ConnHeader from serialized snapshot data (starts UNASSIGNED)."""
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ValueError(f"Expected {cls.__name__} instance or dict, got {type(data).__name__}")

        instance = cls(initialize=False)
        instance._state = HeaderState(
            Status.UNASSIGNED,
            HeaderMetadata(
                product_info=ProductInfo.model_validate(data["productInfo"]),
                archicad_id=ArchiCadID.model_validate(data["archicadId"]),
                archicad_location=ArchicadLocation.model_validate(data["archicadLocation"]),
                tapir_info=PendingResponse(),
            ),
        )
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
            mine = self._snapshot().metadata
            if not _has_project_identity(mine):
                return False
            theirs = other._snapshot().metadata
            return bool(
                _has_project_identity(theirs)
                and mine.product_info == theirs.product_info
                and mine.archicad_id == theirs.archicad_id
                and mine.archicad_location == theirs.archicad_location
            )
        return False

    def _representation_attributes(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        metadata = snapshot.metadata
        return {
            "port": self.port,
            "_status": snapshot.status,
            "product_info": metadata.product_info,
            "archicad_id": metadata.archicad_id,
            "archicad_location": metadata.archicad_location,
            "tapir_info": metadata.tapir_info,
            "peak_archicad_ram_bytes": self.peak_archicad_ram_bytes,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._representation_attributes()})"

    def __str__(self) -> str:
        attrs = self._representation_attributes()
        return f"{self.__class__.__name__}(\n{pformat(attrs, width=200, indent=4)})"

    def refresh_metadata(self):
        """Starts a new fetch, superseding any currently running fetch."""
        token = self._state.begin_fetch()
        # Keep each future paired with its own token, even while submit is running.
        self._fetch_task = (token, EXECUTOR.submit(self._fetch_worker, token))

    def _resolved_fetch_token(self) -> object | None:
        """Snapshot the current completed fetch without waiting for its future."""
        return self._state.resolved_token()

    def _fetch_worker(self, my_token: object) -> HeaderMetadata | None:
        self._fetch_context.active = True
        try:
            return self._fetch_worker_body(my_token)
        finally:
            self._fetch_context.active = False

    def _fetch_worker_body(self, my_token: object) -> HeaderMetadata | None:
        try:
            self._ram_monitor.get_current_rss()
            metadata = HeaderMetadata(
                product_info=self.get_product_info(timeout=5.0),
                archicad_id=self.get_archicad_id(timeout=5.0),
                archicad_location=self.get_archicad_location(timeout=5.0),
                tapir_info=self.get_tapir_info(timeout=5.0),
            )
        except Exception:
            log.exception("Background metadata fetch failed")
            metadata = None

        if not self._state.complete(my_token, metadata):
            return None
        if self._events is not None:
            self._events._resolved(self, my_token)
        return metadata

    def unassign(self) -> None:
        self._state.unassign()
        self._ram_monitor.reset_process()
        self._port = None
        self._core = None
        self._standard = None
        self._unified = None

    def cancel(self):
        self._state.cancel()

    def _sync_if_needed(self):
        """Wait for metadata while keeping UI and worker reads nonblocking."""
        task = self._fetch_task
        if task is None:
            return
        token, future = task
        if (
            future is self._waited_future
            or threading.current_thread().name.startswith("MultiConnWorker")
            or getattr(self._fetch_context, "active", False)
            or (self._ui_mode and not future.done())
        ):
            return
        try:
            future.result()

        except CancelledError:
            pass
        except Exception as e:
            log.warning(f"Background fetch failed: {e}")
            if task is self._fetch_task:
                self._state.complete(token, None)
        finally:
            self._waited_future = future

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


class SessionReadyHeader(ConnHeader):
    """A fresh command session, including untitled projects, with Tapir polled."""

    port: Port
    product_info: ProductInfo
    archicad_id: ArchiCadID
    tapir_info: TapirInfo
    core: CoreCommands
    standard: StandardConnection
    unified: UnifiedApi


def has_project_identity(header: ConnHeader) -> TypeGuard[ProjectIdentityHeader]:
    """Validates that the header has full project identity data for serialization/launch."""
    return _has_project_identity(header._snapshot().metadata)


def _has_project_identity(metadata: HeaderMetadata) -> bool:
    return bool(
        isinstance(metadata.product_info, ProductInfo)
        and isinstance(metadata.archicad_id, (SoloProjectID, TeamworkProjectID))
        and isinstance(metadata.archicad_location, ArchicadLocation)
    )


def is_session_ready(header: ConnHeader) -> TypeGuard[SessionReadyHeader]:
    """Require fresh product/project metadata and polled Tapir, including untitled projects.

    Tapir installation/version and the executable location are not required.
    """
    return _is_session_ready(header._snapshot(), header.port)


def _is_session_ready(snapshot: HeaderSnapshot, port: Port | None) -> bool:
    metadata = snapshot.latest_metadata
    return bool(
        metadata is not None
        and isinstance(metadata.product_info, ProductInfo)
        and isinstance(metadata.archicad_id, ArchiCadID)
        and port is not None
        and snapshot.status is Status.READY
        and isinstance(metadata.tapir_info, TapirInfo)
    )


def is_tapir_session_ready(header: ConnHeader, min_version: str | None = None) -> TypeGuard[SessionReadyHeader]:
    """Require a ready session (including untitled projects) and a suitable installed Tapir."""
    snapshot = header._snapshot()
    if not _is_session_ready(snapshot, header.port) or snapshot.latest_metadata is None:
        return False
    tapir_info = snapshot.latest_metadata.tapir_info
    if not isinstance(tapir_info, TapirInfo):
        return False
    tapir_meets_requirements = tapir_info.is_at_least(min_version) if min_version else tapir_info.is_supported
    return bool(tapir_info.is_installed and tapir_meets_requirements)


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
