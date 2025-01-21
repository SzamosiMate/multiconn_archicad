from pywinauto import Application, WindowSpecification, timings
from pywinauto.controls.uiawrapper import UIAWrapper
import time
import subprocess
import re


class UnhandledDialogError(Exception):
    """Raised when the program could not handle a dialog"""


def handle_changes_dialog(dialog: UIAWrapper) -> None:
    print("Handling 'Changes' dialog...")
    for child in dialog.children():
        if "Receive later" in child.texts():
            child.click()


def handle_local_data_cleanup(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Cancel" in child.texts():
            child.click()


def handle_editing_conflict(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Edit Anyway" in child.texts():
            child.click()
            wait_and_handle_dialogs(app)
    for child in dialog.children():
        if "Discard & Reload" in child.texts():
            child.click()
            wait_and_handle_dialogs(app)


def handle_pla_opening(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Open" in child.texts():
            child.click()
            wait_and_handle_dialogs(app)


# Map dialog titles to handling functions
dialog_handlers = {
    "Changes": handle_changes_dialog,
    "Local Data Cleanup": handle_local_data_cleanup,
    "Editing Conflict": handle_editing_conflict,
    r"^Open .+\.pla$": handle_pla_opening,
}

app: Application | None = None


def match_handler(title: str) -> str | None:
    for pattern in dialog_handlers.keys():
        if re.fullmatch(pattern, title):
            return pattern
    return None


def handle_dialog(dialog) -> None:
    title = dialog.window_text()
    match = match_handler(title)
    if match:
        print(f"Handling dialog: {title}")
        dialog_handlers[match](dialog)


def wait_for_project(application: Application) -> WindowSpecification:
    while True:
        try:
            project_window = application.top_window()

            project_window.print_control_identifiers()
            print("Project window loaded.")
            break
        except Exception as e:
            print(e)
            time.sleep(1)

    print("setting focus")
    project_window.set_focus()
    return project_window


def is_project_window_ready(project_window: WindowSpecification) -> bool:
    try:
        project_window.wait("exists enabled visible ready", timeout=1)
        return True
    except timings.TimeoutError:
        return False


def handle_dialogs(project_window: WindowSpecification) -> bool:
    for child_window in project_window.children():
        if is_project_window_ready(project_window):
            return True
        else:
            handle_dialog(child_window)
    raise UnhandledDialogError("Unable to handle dialogs")


def get_app_from_pid(process: subprocess.Popen) -> Application:
    global app
    app = Application(backend="uia").connect(process=process.pid)
    return app


def get_app_from_title(title: str) -> Application:
    global app
    app = Application(backend="uia").connect(title_re=title)
    return app


def wait_and_handle_dialogs(application: Application) -> None:
    top_window = wait_for_project(application)
    handle_dialogs(top_window)


def start_handling_dialogs(process: subprocess.Popen) -> None:
    wait_and_handle_dialogs(get_app_from_pid(process))
