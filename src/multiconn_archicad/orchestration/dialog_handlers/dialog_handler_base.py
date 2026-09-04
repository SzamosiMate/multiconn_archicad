from abc import ABC, abstractmethod
import subprocess


class DialogHandlerBase(ABC):
    @abstractmethod
    def start(self, process: subprocess.Popen) -> None: ...

    def __repr__(self) -> str:
        return self.__class__.__name__

    def __str__(self) -> str:
        return self.__class__.__name__


class UnhandledDialogError(Exception):
    """Raised when the program could not handle a dialog"""


class EmptyDialogHandler(DialogHandlerBase):
    def start(self, process: subprocess.Popen) -> None:
        pass
