from abc import ABC, abstractmethod
import subprocess
import threading


class DialogHandlerBase(ABC):

    @abstractmethod
    def start(self, process: subprocess.Popen, stop_event: threading.Event | None = None) -> None:
        ...


class UnhandledDialogError(Exception):
    """Raised when the program could not handle a dialog"""


class EmptyDialogHandler(DialogHandlerBase):

    def start(self, process: subprocess.Popen, stop_event: threading.Event | None = None) -> None:
        pass