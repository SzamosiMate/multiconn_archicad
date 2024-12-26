from multi_conn_ac import MultiConn

def connect_and_run_ac_command():
    conn = MultiConn()
    conn.connect.all()

    elements = {}
    for port, conn_header in conn.active.items():
        elements.update({port: conn_header.archicad.commands.GetAllElements()})
        print(elements)


def connect_and_run_core_command():
    conn = MultiConn()
    conn.connect.all()

    for conn_header in conn.active.values():
        print(conn_header.core.post_tapir_command("GetAddOnVersion"))


def quit_all():
    conn = MultiConn()
    conn.quit.all()


if __name__ == "__main__":
    connect_and_run_ac_command()
    connect_and_run_core_command()
    quit_all()



