import contextlib
import io
from pywinauto import Application, WindowSpecification, timings
from pywinauto.controls.uiawrapper import UIAWrapper
import subprocess
import re
import time
from typing import Callable

from .dialog_handler_base import DialogHandlerBase, UnhandledDialogError


class WinDialogHandler(DialogHandlerBase):
    def __init__(self, handler_factory: dict[str, Callable[[UIAWrapper],None]]):
        self.application: Application | None = None
        self.process: subprocess.Popen | None = None
        self.dialog_handlers: dict[str, Callable[[UIAWrapper],None]] = handler_factory

    def start(self, process: subprocess.Popen) -> None:
        self._get_app_from_pid(process)
        self._wait_and_handle_dialogs()

    def _get_app_from_pid(self, process: subprocess.Popen) -> None:
        self.application = Application(backend='uia').connect(process=process.pid)

    # used for testing
    def _get_app_from_title(self, title: str) -> None:
        self.application = Application(backend="uia").connect(title_re=title)

    def _wait_and_handle_dialogs(self) -> None:
        top_window = self._wait_for_project()
        self._handle_dialogs(top_window)

    def _wait_for_project(self) -> WindowSpecification:
        while True:
            try:
                project_window = self.application.top_window()
                if 'Archicad' in project_window.window_text():
                    with contextlib.redirect_stdout(io.StringIO()):
                        project_window.print_control_identifiers()
                    print("Project window loaded.")
                    break
                else:
                    time.sleep(1)
            except Exception as e:
                print(e)
        print('setting focus')
        project_window.set_focus()
        return project_window

    def _handle_dialogs(self, project_window: WindowSpecification) -> bool:
        if self._is_project_window_ready(project_window):
            if re.fullmatch(r".*Archicad \d{2}", project_window.window_text()):
                return True
            else:
                self._handle_dialog(project_window)
        for child_window in project_window.children():
            self._handle_dialog(child_window)
        raise UnhandledDialogError("Unable to handle dialogs")

    def _is_project_window_ready(self, project_window: WindowSpecification) -> bool:
        try:
            project_window.wait('exists enabled visible ready active', timeout=1)
            return True
        except timings.TimeoutError:
            return False

    def _handle_dialog(self, dialog) -> None:
        title = dialog.window_text()
        match = self._match_handler(title)
        if match:
            print(f"Handling dialog: {title}")
            self.dialog_handlers[match](dialog)
            self._wait_and_handle_dialogs()

    def _match_handler(self, title:str) -> str | None:
        for pattern in self.dialog_handlers.keys():
            if re.fullmatch(pattern, title):
                return pattern
        return None

