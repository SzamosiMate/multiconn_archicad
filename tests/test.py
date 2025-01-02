from multi_conn_ac import MultiConn, Port

def connect_and_run_ac_command():
    conn = MultiConn()
    conn.connect.all()

    elements = {}
    for port, conn_header in conn.active.items():
        elements.update({port: conn_header.archicad.commands.GetAllElements()})
        print(elements)

def connect_and_run_ac_command_oneliner():
    conn = MultiConn()
    conn.connect.all()

    elements = {}
    for port, conn_header in conn.active.items():
        elements.update({port: conn_header.archicad.commands.GetAllElements()})
        print(elements)

    elements = {port: conn_header.archicad.commands.GetAllElements() for port, conn_header in conn.active.items()}

    print(elements)

def connect_and_run_core_command():
    conn = MultiConn()
    conn.connect.all()

    for conn_header in conn.active.values():
        print(conn_header.core.post_tapir_command("GetAddOnVersion"))

def quit_all():
    conn = MultiConn()
    conn.quit.from_headers(conn.open_port_headers[Port(19735)])

def quit_and_refresh():
    conn = MultiConn()
    conn.quit.from_headers(conn.open_port_headers[Port(19724)])
    conn.refresh.all_ports()


def cycle_primary():
    conn = MultiConn()
    for port in conn.open_port_headers.keys():
        conn.primary = port
        print(conn.core.post_tapir_command("GetProjectInfo"))

    for header in conn.open_port_headers.values():
        conn.primary = header
        print(conn.core.post_tapir_command("GetProjectInfo"))


if __name__ == "__main__":
    connect_and_run_ac_command()
    connect_and_run_core_command()
 #  quit_all()
    cycle_primary()
    quit_and_refresh()