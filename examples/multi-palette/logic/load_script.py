from __future__ import annotations
import importlib.util
import inspect

from nicegui import ui, app
from typing import Type, Protocol, Any, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from multiconn_archicad import ConnHeader
    from .controller import AppState
    from types import ModuleType

@runtime_checkable
class Runnable(Protocol):
    def run(self, conn: ConnHeader) -> dict[str, Any]:
        ...

@runtime_checkable
class Settable(Protocol):
    def set_parameters(self) -> None:
        ...

class ScriptLoader:
    def __init__(self, app_state: AppState, file_paths: tuple[str]) -> None:
        self.app_state: AppState = app_state
        self.scripts_runners: list[type[Runnable]] = self.get_scripts_runners_from_files(file_paths)
        self.script_index: int = 0
        self.dialog: ui.dialog = self.script_selector_dialog()


    def script_selector_dialog(self) -> ui.dialog:
        with (ui.dialog() as dialog, ui.card().classes('w-[550px] h-[400px] m-0')):
            ui.label(f'Found {len(self.scripts_runners)} scripts:').classes('font-bold text-lg')
            script_names = {i:script.__name__ for i, script in enumerate(self.scripts_runners)}
            ui.select(script_names, value=0).classes('w-full').props('dense').bind_value(self, 'script_index')
            with ui.card_section().classes('h-full p-0'):
                ui.markdown(self.get_description()
                            ).bind_content_from(self, 'script_index', backward=lambda i:self.get_description())
            with ui.row().classes('w-full'):
                ui.button('Cancel', on_click=dialog.close)
                ui.space()
                ui.button('select', on_click=self.set_selected_script)
        return dialog

    def get_description(self) -> str:
        description = self.scripts_runners[self.script_index].__doc__
        return description if description else "No description"


    def set_selected_script(self) -> None:
        script = self.scripts_runners[self.script_index]
        self.app_state.script = script()
        self.app_state.script.multi_conn = self.app_state.conn
        self.app_state.parameters = issubclass(script, Settable)
        self.dialog.close()


    def get_scripts_runners_from_files(self, file_paths: tuple[str]) -> list[Type[Runnable]]:
        scripts_runners = []
        for file_path in file_paths:
            module = self.import_module(file_path)
            scripts_runners.extend(self.find_runnable_classes(module))
        return scripts_runners

    @staticmethod
    def import_module(file_path: str) -> ModuleType:
        module_name = file_path.rsplit("/", 1)[-1].split(".")[0]

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def find_runnable_classes(module: ModuleType, ) -> list[Type[Runnable]]:
        matching_classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if the class is defined in the module (avoid imports)
            if obj.__module__ == module.__name__:
                if isinstance(obj, type) and issubclass(obj, Runnable):
                    matching_classes.append(obj)
        return matching_classes

async def choose_file()-> tuple[str]:
    file_paths = await app.native.main_window.create_file_dialog(allow_multiple=True)
    for file in file_paths:
        ui.notify(file)
    return file_paths

async def select_script(app_state: AppState):
    file_paths = await choose_file()
    dialog = ScriptLoader(app_state, file_paths).dialog
    dialog.open()

