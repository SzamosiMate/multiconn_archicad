from abc import ABC, abstractmethod
import subprocess


class DialogHandlerBase(ABC):

    @abstractmethod
    def start_handling_dialogs(self, process: subprocess.Popen) -> None:
        ...