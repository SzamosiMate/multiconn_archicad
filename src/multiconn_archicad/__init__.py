from .multi_conn import MultiConn
from .conn_header import (
    ConnHeader,
    ValidatedHeader,
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
    FromAPIResponse,
)
from .standard_connection import StandardConnection
from .core_commands import CoreCommands
from .dialog_handlers import (
    DialogHandlerBase,
    WinDialogHandler,
    win_int_handler_factory,
    UnhandledDialogError,
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
    TapirCommandError,
    ProjectAlreadyOpenError,
    ProjectNotFoundError,
    NotFullyInitializedError,
)

import logging

__all__: tuple[str, ...] = (
    "MultiConn",
    "ConnHeader",
    "ArchiCadID",
    "APIResponseError",
    "FromAPIResponse",
    "ProductInfo",
    "Port",
    "StandardConnection",
    "CoreCommands",
    "TeamworkCredentials",
    "DialogHandlerBase",
    "WinDialogHandler",
    "win_int_handler_factory",
    "UnhandledDialogError",
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
    "TapirCommandError",
    "ProjectAlreadyOpenError",
    "ProjectNotFoundError",
    "NotFullyInitializedError",
    "ValidatedHeader",
    "is_location_initialized",
    "is_product_info_initialized",
    "is_id_initialized",
    "is_header_fully_initialized",
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
