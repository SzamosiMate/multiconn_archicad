import sys
from .dialog_handler_base import UnhandledDialogError, DialogHandlerBase, EmptyDialogHandler

__all__ = [
    "UnhandledDialogError",
    "DialogHandlerBase",
    "EmptyDialogHandler",
]


try:
    from .win_dialog_handler import WinDialogHandler
    from .win_int_handler_factory import win_int_handler_factory

except ImportError:
    if sys.platform == "win32":
        _ERROR_MSG = (
            "The 'dialog-handlers' feature is not installed. "
            "Please install it with: pip install multiconn_archicad[dialog-handlers]"
        )
    else:
        _ERROR_MSG = "WinDialogHandler and win_int_handler_factory are only available on Windows."

    class WinDialogHandler(DialogHandlerBase):
        def __init__(self, *args, **kwargs):
            raise ImportError(_ERROR_MSG)

        def start(self, process) -> None:
            raise ImportError(_ERROR_MSG)

    win_int_handler_factory = {}

__all__.extend([
    "WinDialogHandler",
    "win_int_handler_factory",
])