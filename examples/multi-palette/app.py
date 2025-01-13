from nicegui import native, ui, app
from pathlib import Path

from logic.archi_cad import AppState
from logic.load_script import select_script

app.add_static_files("/assets", "assets")
app_state = AppState()



async def refresh_options() -> None:
    await app_state.refresh()
    single_select.refresh()
    multi_select.refresh()


@ui.refreshable
def multi_select() -> None:
    with ui.scroll_area().classes("h-200"):
        if app_state.first_port:
            for port, project_name in app_state.instance_ids.items():
                ui.checkbox(project_name, on_change=lambda e, i=port: app_state.connect_or_disconnect(i, e.value)).props("dense")
        else:
            no_archicad()

@ui.refreshable
def single_select() -> None:
    with ui.scroll_area().classes("h-200"):
        if app_state.first_port:
            ui.radio(
                app_state.instance_ids, value=app_state.first_port
            ).bind_value_to(app_state.conn, target_name="primary")
        else:
            no_archicad()

def no_archicad() -> None:
    ui.label(
        "Found no running ArchiCAD to connect to. Please start Archicad and hit Refresh"
    )


@ui.page("/")
def index():
    ui.colors(
        primary="#28323C", secondary="blue-grey-1", positive="#53B689", accent="#111B1E"
    )
    ui.add_head_html(
        "<style>"
        + open(Path(__file__).parent / "assets" / "css" / "global-css.css").read()
        + "</style>"
    )

    with ui.card(align_items="stretch").classes("w-full").tight():
        with (
            ui.tabs()
            .classes("w-full")
            .props("active-bg-color=primary active-color=white dense") as tabs
        ):
            single = ui.tab("Single")
            multi = ui.tab("Multiple")
        with ui.tab_panels(tabs, value=single).bind_value(app_state, target_name='run_mode').classes("p-0 gap-0"):
            with ui.tab_panel(single).classes("p-0"):
                single_select()
            with ui.tab_panel(multi).classes("p-0"):
                multi_select()
        ui.button("Refresh", icon="refresh", on_click=lambda: refresh_options())
    ui.button("Chose File", on_click=lambda: select_script(app_state), icon="folder").classes("w-full")
    ui.button("Set Parameters", on_click=lambda: ui.notify("This does nothing!")).classes("w-full")
    ui.button("Run", on_click=app_state.run).classes("w-full")


ui.run(reload=False, native=True, window_size=(300, 600), port=native.find_open_port())
