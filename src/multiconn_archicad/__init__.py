from __future__ import annotations

from importlib import import_module
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from multiconn_archicad.clients.core.core_commands import CoreCommands
    from multiconn_archicad.clients.standard_connection import StandardConnection
    from multiconn_archicad.clients.unified_api.api import UnifiedApi
    from multiconn_archicad.errors import (
        AddOnCommandUnavailable,
        APIConnectionError,
        APIErrorBase,
        ArchicadAPIError,
        BatchOperationError,
        CommandTimeoutError,
        InvalidResponseFormatError,
        MulticonnArchicadError,
        NotFullyInitializedError,
        ProjectAlreadyOpenError,
        ProjectNotFoundError,
        RequestError,
        StandardAPIError,
        StandardCommandUnavailable,
        TapirCommandError,
    )
    from multiconn_archicad.orchestration.basic_types import (
        APIResponseError,
        ArchicadLocation,
        ArchiCadID,
        Port,
        ProductInfo,
        SoloProjectID,
        TapirInfo,
        TeamworkCredentials,
        TeamworkProjectID,
        UntitledProjectID,
    )
    from multiconn_archicad.orchestration.conn_header import (
        ConnHeader,
        ProjectIdentityHeader,
        SessionReadyHeader,
        ValidatedHeader,
        has_project_identity,
        is_header_fully_initialized,
        is_id_initialized,
        is_location_initialized,
        is_product_info_initialized,
        is_session_ready,
        is_tapir_session_ready,
    )
    from multiconn_archicad.orchestration.dialog_handlers import (
        DialogHandlerBase,
        UnhandledDialogError,
        WinDialogHandler,
        win_int_handler_factory,
    )
    from multiconn_archicad.orchestration.multi_conn import MultiConn


__all__ = [
    "MultiConn",
    "ConnHeader",
    "ArchiCadID",
    "APIResponseError",
    "ProductInfo",
    "Port",
    "TapirInfo",
    "StandardConnection",
    "CoreCommands",
    "TeamworkCredentials",
    "DialogHandlerBase",
    "UnhandledDialogError",
    "WinDialogHandler",
    "win_int_handler_factory",
    "TeamworkProjectID",
    "SoloProjectID",
    "UntitledProjectID",
    "ArchicadLocation",
    "MulticonnArchicadError",
    "APIErrorBase",
    "RequestError",
    "ArchicadAPIError",
    "APIConnectionError",
    "CommandTimeoutError",
    "InvalidResponseFormatError",
    "StandardAPIError",
    "StandardCommandUnavailable",
    "TapirCommandError",
    "AddOnCommandUnavailable",
    "ProjectAlreadyOpenError",
    "ProjectNotFoundError",
    "NotFullyInitializedError",
    "BatchOperationError",
    "ProjectIdentityHeader",
    "SessionReadyHeader",
    "ValidatedHeader",
    "is_location_initialized",
    "is_product_info_initialized",
    "is_id_initialized",
    "has_project_identity",
    "is_session_ready",
    "is_tapir_session_ready",
    "is_header_fully_initialized",
    "UnifiedApi",
]

_LAZY_IMPORTS: dict[str, str] = {
    # .orchestration.multi_conn
    "MultiConn": ".orchestration.multi_conn",
    # .orchestration.conn_header
    "ConnHeader": ".orchestration.conn_header",
    "ProjectIdentityHeader": ".orchestration.conn_header",
    "SessionReadyHeader": ".orchestration.conn_header",
    "ValidatedHeader": ".orchestration.conn_header",
    "has_project_identity": ".orchestration.conn_header",
    "is_session_ready": ".orchestration.conn_header",
    "is_tapir_session_ready": ".orchestration.conn_header",
    "is_header_fully_initialized": ".orchestration.conn_header",
    "is_id_initialized": ".orchestration.conn_header",
    "is_location_initialized": ".orchestration.conn_header",
    "is_product_info_initialized": ".orchestration.conn_header",
    # .orchestration.basic_types
    "ArchiCadID": ".orchestration.basic_types",
    "TeamworkProjectID": ".orchestration.basic_types",
    "SoloProjectID": ".orchestration.basic_types",
    "UntitledProjectID": ".orchestration.basic_types",
    "TeamworkCredentials": ".orchestration.basic_types",
    "ProductInfo": ".orchestration.basic_types",
    "ArchicadLocation": ".orchestration.basic_types",
    "Port": ".orchestration.basic_types",
    "APIResponseError": ".orchestration.basic_types",
    "TapirInfo": ".orchestration.basic_types",
    # .clients.standard_connection
    "StandardConnection": ".clients.standard_connection",
    # .clients.core.core_commands
    "CoreCommands": ".clients.core.core_commands",
    # .orchestration.dialog_handlers
    "DialogHandlerBase": ".orchestration.dialog_handlers",
    "UnhandledDialogError": ".orchestration.dialog_handlers",
    "WinDialogHandler": ".orchestration.dialog_handlers",
    "win_int_handler_factory": ".orchestration.dialog_handlers",
    # .errors
    "MulticonnArchicadError": ".errors",
    "APIErrorBase": ".errors",
    "RequestError": ".errors",
    "APIConnectionError": ".errors",
    "CommandTimeoutError": ".errors",
    "InvalidResponseFormatError": ".errors",
    "ArchicadAPIError": ".errors",
    "StandardAPIError": ".errors",
    "StandardCommandUnavailable": ".errors",
    "TapirCommandError": ".errors",
    "AddOnCommandUnavailable": ".errors",
    "ProjectAlreadyOpenError": ".errors",
    "ProjectNotFoundError": ".errors",
    "NotFullyInitializedError": ".errors",
    "BatchOperationError": ".errors",
    # .clients.unified_api.api
    "UnifiedApi": ".clients.unified_api.api",
}


def __getattr__(name: str) -> Any:
    """Lazily load symbols when accessed on the module."""
    if name in _LAZY_IMPORTS:
        submodule = import_module(_LAZY_IMPORTS[name], __name__)
        attr = getattr(submodule, name)
        # Cache the resolved object in module globals so __getattr__ is bypassed next time
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Ensure dir(multiconn_archicad) and REPL autocomplete show all public exports."""
    return sorted(list(globals().keys()) + __all__)


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)