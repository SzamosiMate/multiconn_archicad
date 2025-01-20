from pywinauto import Application, WindowSpecification, timings
import time
from multi_conn_ac import MultiConn
import subprocess


class UnhandledDialogError(Exception):
    """Raised when the program could not handle a dialog"""


# Define actions for specific dialog titles
def handle_changes_dialog(dialog: WindowSpecification):
    print("Handling 'Changes' dialog...")
    for child in dialog.children():
        if "Receive later" in child.texts():
            child.click()

# Map dialog titles to handling functions
dialog_handlers = {
    "Changes": handle_changes_dialog,
    # Add other dialogs here
}


def handle_dialog(dialog):
    title = dialog.window_text()
    if title in dialog_handlers:
        print(f"Handling dialog: {title}")
        dialog_handlers[title](dialog)


def wait_for_project(app: Application) -> WindowSpecification:
    while True:
        try:
            project_window = app.top_window()

            project_window.print_control_identifiers()
            print("Project window loaded.")
            break
        except Exception as e:
            print(e)
            time.sleep(1)

    print('setting focus')
    project_window.set_focus()
    return project_window

def is_project_window_ready(project_window: WindowSpecification) -> bool:
    try:
        project_window.wait('exists enabled visible ready', timeout=1)
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


def dialog_handler(process: subprocess.Popen):
    app = Application(backend='uia').connect(process=process.pid)
    top_window = wait_for_project(app)

    handle_dialogs(top_window)


