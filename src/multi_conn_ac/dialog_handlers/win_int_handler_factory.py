import time
from typing import Callable
from pywinauto.controls.uiawrapper import UIAWrapper


win_int_handler_factory: dict[str, Callable[[UIAWrapper], None]] = {}


def handle_changes_dialog(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Receive later" in child.texts():
            child.click()


win_int_handler_factory.update({"Changes": handle_changes_dialog})


def handle_local_data_cleanup(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Cancel" in child.texts():
            child.click()


win_int_handler_factory.update({"Local Data Cleanup": handle_local_data_cleanup})


def handle_editing_conflict(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Edit Anyway" in child.texts():
            child.click()
            time.sleep(2)
    for child in dialog.children():
        if "Discard & Reload" in child.texts():
            child.click()


win_int_handler_factory.update({"Editing Conflict": handle_editing_conflict})


def handle_pla_opening(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Open" in child.texts():
            child.click()


win_int_handler_factory.update({r"^Open .+\.pla$": handle_pla_opening})


def handle_project_recovery(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Cancel" in child.texts():
            child.click()


win_int_handler_factory.update({"Archicad Project Recovery": handle_project_recovery})


def handle_project_is_in_use(dialog: UIAWrapper) -> None:
    for child in dialog.children():
        if "Open with Exclusive Access" in child.texts():
            child.click()


win_int_handler_factory.update({"Information": handle_project_is_in_use})
