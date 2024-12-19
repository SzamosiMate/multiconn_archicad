from multi_conn_ac import Port
from multi_conn_ac.multi_conn_ac import MultiConn
from typing import Callable, Any


def build_port_dicts_from_data[T](formula: dict[Port, Any], data: T) -> dict[Port, T]:
    return {port: data for port in formula.keys()}

def print_args_and_kwargs(arg01: int, arg02: str, kwarg01: str, kwarg02: str):
    print(f" This is the instance, the passed args are: {arg01}, {arg02}, {kwarg01}, {kwarg02}")

def active[T, ** P](command: Callable[[P], T], *args: P.args,
                    **kwargs: P.kwargs) -> T:
    return command( *args, **kwargs)

active(print_args_and_kwargs, "wrong type", "arg02", kwarg01=2, kwarg02="right type")

def pending[T, ** P](command: Callable[[P], T], *args: P.args
                     ,
                     **kwargs: list[P.kwargs]) -> None:
    pass

test_dict : dict[Port, str] = {Port(19723) : "_",
             Port(19724) : "_"}

arg01 = build_port_dicts_from_data(test_dict, "arg01")
arg02 = build_port_dicts_from_data(test_dict, "arg02")
kwarg01 = build_port_dicts_from_data(test_dict, "kwarg01")
kwarg02 = build_port_dicts_from_data(test_dict, "kwarg02")

pending(print_args_and_kwargs, arg01, arg02)


def connect_and_run_ac_command():
    conn = MultiConn()
    conn.connect.all()

    elements = {}
    for port, conn_header in conn.active.items():
        elements.update({port : conn_header.archicad.commands.GetAllElements()})
        print(elements)

def connect_and_run_core_command():
    conn = MultiConn()
    conn.connect.all()

    for conn_header in conn.active.values():
        print(conn_header.core.post_tapir_command('GetAddOnVersion'))

def connect_and_run_all_ac_command():
    conn = MultiConn()
    conn.connect.all()
    acc = conn.archicad.commands

    elements = conn.run.active(acc.GetAllElements)
    bb3ds = conn.run.active(acc.Get3DBoundingBoxes)
    print(bb3ds)



def pass_kwargs_with_run():
    conn = MultiConn()
    conn.connect.all()

    class TestClass:
        def __init__(self, number):
            self.number: int = number

        def print_args_and_kwargs(self, arg01:str, arg02:str, kwarg01:str, kwarg02:str):
            print(f" This is the {self.number} instance, the passed args are: {arg01}, {arg02}, {kwarg01}, {kwarg02}")

    conn.test_class = TestClass(0)
    for i, header in enumerate(conn.active.values()):
        header.test_class = TestClass(i)

    conn.test_class = TestClass
    arg01 = build_port_dicts_from_data(conn.active, "arg01")
    arg02 = build_port_dicts_from_data(conn.active, "arg02")
    kwarg01 = build_port_dicts_from_data(conn.active, "kwarg01")
    kwarg02 = build_port_dicts_from_data(conn.active, "kwarg02")


    conn.run.active(conn.test_class.print_args_and_kwargs, arg01, arg02, kwarg01=kwarg01, kwarg02=kwarg02)

if __name__ == "__main__":
    #connect_and_run_ac_command()
    #connect_and_run_core_command()
    #connect_and_run_all_ac_command()
    pass_kwargs_with_run()













