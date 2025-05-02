import time

from multiconn_archicad import MultiConn, Port, WinDialogHandler, win_int_handler_factory
import logging

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

def quit_port():
    conn = MultiConn()
    conn.quit.from_headers(conn.open_port_headers[Port(19723)])
    time.sleep(1)


def quit_and_refresh():

    conn = MultiConn()
    conn.quit.from_headers(conn.open_port_headers[Port(19725)])
    conn.refresh.all_ports()


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
    quit_port()
    cycle_primary()
    quit_and_refresh()
    print_test()