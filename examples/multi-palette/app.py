from nicegui import native, ui, app
from pathlib import Path

from logic.controller import AppState
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
                ui.checkbox(
                    project_name,
                    on_change=lambda e, i=port: app_state.connect_or_disconnect(
                        i, e.value
                    ),
                ).props("dense")
        else:
            no_archicad()


@ui.refreshable
def single_select() -> None:
    with ui.scroll_area().classes("h-200"):
        if app_state.first_port:
            ui.radio(app_state.instance_ids, value=app_state.first_port).bind_value_to(
                app_state.conn, target_name="primary"
            )
        else:
            no_archicad()


def no_archicad() -> None:
    ui.label(
        "Found no running ArchiCAD to connect to. Please start Archicad and hit Refresh"
    )


def set_parameters() -> None:
    with ui.dialog(value=True) as dialog, ui.card().classes('w-[550px] h-[400px] m-0'):
        with ui.card_section().classes('h-full p-0'):
            app_state.script.set_parameters()
        ui.button("Close", on_click=dialog.close).classes('w-full')


def set_global_context() -> None:
    ui.add_head_html(
        "<style>"
        + open(Path(__file__).parent / "assets" / "css" / "global-css.css").read()
        + "</style>"
    )
    ui.colors(
        primary="#28323C", secondary="blue-grey-1", positive="#53B689", accent="#111B1E"
    )
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full gap-3 p-3")

@ui.page("/")
def index():
    set_global_context()
    with ui.card(align_items="stretch").classes("w-full h-full").tight():
        with (
            ui.tabs().classes("w-full")
            .props("active-bg-color=primary active-color=white dense") as tabs
        ):
            single = ui.tab("Single")
            multi = ui.tab("Multiple")
        with ui.tab_panels(tabs, value=single).bind_value(app_state, target_name='run_mode').classes("p-0 gap-0 h-full"):
            with ui.tab_panel(single).classes("p-0"):
                single_select()
            with ui.tab_panel(multi).classes("p-0"):
                multi_select()
        ui.button("Refresh", icon="refresh", on_click=lambda: refresh_options())
    ui.button("Chose File", on_click=lambda: select_script(app_state), icon="folder").classes("w-full")
    (ui.button("Set Parameters", on_click=set_parameters).classes("w-full")
        .bind_enabled_from(app_state, 'parameters'))
    ui.button("Run", on_click=app_state.run).classes("w-full").bind_enabled_from(app_state, 'script')

ui.run(reload=False, native=True, title="Multi-palette", window_size=(300, 600), port=native.find_open_port())

