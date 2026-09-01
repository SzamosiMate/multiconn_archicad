import logging

from .multi_conn import MultiConn
from .conn_header import (
    ConnHeader,
    ProjectIdentityHeader,
    SessionReadyHeader,
    ValidatedHeader,
    has_project_identity,
    is_session_ready,
    is_tapir_session_ready,
    is_header_fully_initialized,
    is_id_initialized,
    is_location_initialized,
    is_product_info_initialized,
)
from .basic_types import (
    ArchiCadID,
    TeamworkProjectID,
    SoloProjectID,
    UntitledProjectID,
    TeamworkCredentials,
    ProductInfo,
    ArchicadLocation,
    Port,
    APIResponseError,
    TapirInfo,
)
from .standard_connection import StandardConnection
from .core.core_commands import CoreCommands
from .dialog_handlers import (
    DialogHandlerBase,
    UnhandledDialogError,
    WinDialogHandler,
    win_int_handler_factory,
)
from .errors import (
    MulticonnArchicadError,
    APIErrorBase,
    RequestError,
    APIConnectionError,
    CommandTimeoutError,
    InvalidResponseFormatError,
    ArchicadAPIError,
    StandardAPIError,
    StandardCommandUnavailable,
    TapirCommandError,
    AddOnCommandUnavailable,
    ProjectAlreadyOpenError,
    ProjectNotFoundError,
    NotFullyInitializedError,
)
from .unified_api.api import UnifiedApi


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


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

__all__ = tuple(__all__)