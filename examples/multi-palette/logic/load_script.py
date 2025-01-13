from __future__ import annotations
import importlib.util
import inspect

from docutils.nodes import description
from nicegui import ui, app
from typing import Type, Protocol, Any, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from multi_conn_ac import ConnHeader
    from .archi_cad import AppState
    from types import ModuleType

@runtime_checkable
class ScriptRunner(Protocol):
    """
    ScriptRunner is a class template to create scripts that the GUI can run.
    All scripts should provide a docstring describing what the script does,
    a run method that executes, and a set_parameters method that opens a dialog
    where the user can provide the parameters
    """

    def run(self, conn: ConnHeader) -> dict[str, Any]:
        ...

    def set_parameters(self) -> None:
        ...

class ScriptLoader:
    def __init__(self, app_state: AppState, file_paths: tuple[str]) -> None:
        self.app_state: AppState = app_state
        self.protocol: type[ScriptRunner] = ScriptRunner
        self.scripts_runners: list[ScriptRunner]= self.get_scripts_runners_from_files(file_paths)
        self.dialog: ui.dialog = self.script_selector_dialog()

    def script_selector_dialog(self) -> ui.dialog:
        with ui.dialog() as dialog, ui.card().classes('w-[550px] h-[400px] m-0'):
            ui.label(f'Found {len(self.scripts_runners)} scripts:').classes('font-bold text-lg')
            script_names = {i:script.__name__ for i, script in enumerate(self.scripts_runners)}
            selected = ui.select(script_names, value=0)
            script = self.scripts_runners[selected.value]
            print(script)
            with ui.card_section().classes('h-max'):
                description = script.__doc__ if script.__doc__ else "No description"
                ui.markdown(description)
            with ui.row().classes('w-full'):
                ui.button('Cancel', on_click=dialog.close)
                ui.space()
                ui.button('select', on_click=lambda: self.select_script(script))
        return dialog

    def select_script(self, script: ScriptRunner) -> None:
        self.app_state.script= script()
        self.dialog.close()


    def get_scripts_runners_from_files(self, file_paths: tuple[str]) -> list[ScriptRunner]:
        scripts_runners = []
        for file_path in file_paths:
            module = self.import_module(file_path)
            print(module)
            scripts_runners.append(*self.find_classes_implementing_script_protocol(module))
            print(scripts_runners)
        return scripts_runners

    def import_module(self, file_path: str) -> ModuleType:
        module_name = file_path.rsplit("/", 1)[-1].split(".")[0]

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def find_classes_implementing_script_protocol(self, module: ModuleType, ) -> list[Type]:
        matching_classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if the class is defined in the module (avoid imports)
            if obj.__module__ == module.__name__:
                if isinstance(obj, type) and issubclass(obj, self.protocol):
                    matching_classes.append(obj)
        return matching_classes

async def choose_file()-> tuple[str]:
    file_paths = await app.native.main_window.create_file_dialog(allow_multiple=True)
    for file in file_paths:
        ui.notify(file)
    print(file_paths)
    return file_paths

async def select_script(app_state: AppState):
    file_paths = await choose_file()
    dialog = ScriptLoader(app_state, file_paths).dialog
    dialog.open()

