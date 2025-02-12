from abc import ABC, abstractmethod
import subprocess


class DialogHandlerBase(ABC):

    @abstractmethod
    def start(self, process: subprocess.Popen) -> None:
        ...


class UnhandledDialogError(Exception):
    """Raised when the program could not handle a dialog"""


class EmptyDialogHandler(DialogHandlerBase):

    def start(self, process: subprocess.Popen) -> None:
        pass