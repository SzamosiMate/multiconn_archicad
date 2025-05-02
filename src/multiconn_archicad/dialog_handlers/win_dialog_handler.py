import contextlib
import io
from pywinauto import Application, WindowSpecification, timings
from pywinauto.controls.uiawrapper import UIAWrapper
import subprocess
import re
import time
from typing import Callable

from multiconn_archicad.dialog_handlers.win_int_handler_factory import win_int_handler_factory
from multiconn_archicad.dialog_handlers.dialog_handler_base import DialogHandlerBase, UnhandledDialogError

import logging

log = logging.getLogger(__name__)


class WinDialogHandler(DialogHandlerBase):
    def __init__(self, handler_factory: dict[str, Callable[[UIAWrapper], None]], retries: int = 2):
        self.application: Application
        self.process: subprocess.Popen
        self.dialog_handlers: dict[str, Callable[[UIAWrapper], None]] = handler_factory
        self.retries: int = retries

    def start(self, process: subprocess.Popen) -> None:
        log.info(f"Starting {self.__class__.__name__} for process {process.pid}.")
        self._get_app_from_pid(process)
        self._wait_and_handle_dialogs()

    def _get_app_from_pid(self, process: subprocess.Popen) -> None:
        self.application = Application(backend="uia").connect(process=process.pid)

    # used for testing
    def _get_app_from_title(self, title: str) -> None:
        self.application = Application(backend="uia").connect(title_re=title)

    def _wait_and_handle_dialogs(self) -> None:
        for retry in range(self.retries + 1):
            log.info(f"Handling dialogs:{self.retries + 1}/{retry + 1} try")
            top_window = self._wait_for_project()
            if self._handle_dialogs(top_window):
                return
            time.sleep(10)
        log.critical(f"Could not handle dialogs after {self.retries + 1} tries.")
        raise UnhandledDialogError("Unable to handle dialogs")

    def _wait_for_project(self) -> WindowSpecification:
        while True:
            time.sleep(1)
            try:
                project_window = self.application.top_window()
                if (
                    "Archicad" in project_window.window_text()
                ):  # catches either the archicad window or Archicad Project Recovery
                    with contextlib.redirect_stdout(io.StringIO()):
                        # Sometimes _is_project_window_ready returns True even when the window is not ready.
                        # .print_control_identifiers() more reliably fails in these cases.
                        project_window.print_control_identifiers()
                    log.info(f"Project window {project_window.window_text()} is ready")
                    break
            except Exception as e:
                # catching a private exception : _ctypes.COMError: (-2147220991, 'An event was unable to invoke any of
                # the subscribers', (None, None, None, 0, None))
                log.warning(f"Caught exception: {e}. Project window is not ready yet. Trying again.")
        time.sleep(1)
        project_window.set_focus()
        log.info("setting focus")
        return project_window

    def _handle_dialogs(self, project_window: WindowSpecification) -> bool:
        if self._is_project_window_ready(project_window):
            # The project window is the ArchiCAD window, and there are no blocking dialogs
            if re.fullmatch(r".*Archicad \d{2}( DEMO)?", project_window.window_text()):
                return True
            # There is a ready window, but it is NOT the ArchiCAD window
            else:
                return self._handle_dialog(project_window)
        else:
            # There is a blocking child window
            for child_window in project_window.children():
                success = self._handle_dialog(child_window)
                if success:
                    return True
        return False

    def _is_project_window_ready(self, project_window: WindowSpecification) -> bool:
        try:
            project_window.wait("exists enabled visible ready active", timeout=1)
            return True
        except timings.TimeoutError:
            return False

    def _handle_dialog(self, dialog) -> bool:
        title = dialog.window_text()
        match = self._match_handler(title)
        if match:
            log.info(f"Handling dialog: {title}")
            self.dialog_handlers[match](dialog)
            self._wait_and_handle_dialogs()
            return True
        else:
            log.warning(f"Could not find a dialog handler for: {title}")
            return False

    def _match_handler(self, title: str) -> str | None:
        for pattern in self.dialog_handlers.keys():
            if re.fullmatch(pattern, title):
                return pattern
        return None


if __name__ == "__main__":
    dialog_handler = WinDialogHandler(win_int_handler_factory)
    dialog_handler._get_app_from_title(".*Archicad.*")
    dialog_handler._wait_and_handle_dialogs()
