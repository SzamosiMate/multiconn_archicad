
from multiconn_archicad import MultiConn, WinDialogHandler, win_int_handler_factory, ConnHeader
import logging
import random

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def connect_and_run_ac_command():
    conn = MultiConn()
    conn.connect.all()

    elements = {}
    for port, conn_header in conn.active.items():
        elements.update({port: conn_header.standard.commands.GetAllElements()})
        log.debug(elements)

def connect_and_run_ac_command_oneliner():
    conn = MultiConn()
    conn.connect.all()

    elements = {port: conn_header.standard.commands.GetAllElements() for port, conn_header in conn.active.items()}

    log.debug(elements)

def connect_and_run_core_command():
    conn = MultiConn()
    conn.connect.all()

    for conn_header in conn.active.values():
        log.debug(conn_header.core.post_tapir_command("GetAddOnVersion"))

def quit_and_reopen_project():
    conn = MultiConn(WinDialogHandler(win_int_handler_factory))
    random_header = random.choice(list(conn.open_port_headers.values()))
    conn.quit.from_headers(random_header)
    port = conn.open_project.from_header(random_header, demo=True)
    assert conn.open_port_headers[port] == random_header
    log.info(f"quit anr reopened project: {random_header.archicad_id.projectName}")

def switch_random_port():
    conn = MultiConn(WinDialogHandler(win_int_handler_factory))
    random_header: ConnHeader = random.choice(list(conn.open_port_headers.values()))
    conn.quit.from_headers(random_header)
    random_port = random.choice(list(conn.open_port_headers.keys()))
    original_header = conn.open_port_headers[random_port]
    conn.switch_project.from_header(original_port=random_port, new_header=random_header)
    assert conn.open_port_headers[random_port] == random_header
    log.info(f"project switched to: {random_header.archicad_id.projectName}")
    conn.open_project.from_header(original_header, demo=True)

def cycle_primary():
    conn = MultiConn()
    for port in conn.open_port_headers.keys():
        conn.primary = port
        log.debug(conn.core.post_tapir_command("GetProjectInfo"))
        log.debug(conn.primary.standard.commands.IsAlive())

    for header in conn.open_port_headers.values():
        conn.primary = header
        log.debug(conn.core.post_tapir_command("GetProjectInfo"))
        log.debug(conn.primary.standard.commands.IsAlive())

def print_test():
    dialog_handler = WinDialogHandler(win_int_handler_factory)
    conn = MultiConn(dialog_handler)

    print(conn)
    print(conn.primary)

if __name__ == "__main__":
    connect_and_run_ac_command()
    connect_and_run_core_command()
    quit_and_reopen_project()
    cycle_primary()
    switch_random_port()
    print_test()