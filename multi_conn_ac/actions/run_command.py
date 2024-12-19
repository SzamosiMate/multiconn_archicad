from .baseclasses import *
from multi_conn_ac.method_binders import bind_method_to_instance_of_origin_class_in_attributes
from .. import Port


class RunCommand(CommandRunner):

    def execute_command[T, **P](self, conn_headers: dict[Port, ConnHeader], command: Callable[[P], T],
                                *args: dict[Port, P.args], **kwargs:  dict[Port, P.kwargs]) -> dict[Port, T]:
        command_results = {}
        for port, conn_header in conn_headers.items():
            bound_command = bind_method_to_instance_of_origin_class_in_attributes(command, conn_header)
            print(args)
            port_args = [arg[port] for arg in args]
            port_kwargs = {key:kwarg[port] for key, kwarg in kwargs.items()}
            print(args)
            command_results.update({port: bound_command(*port_args, **port_kwargs)})
        print(f'Final command result:{command_results}')
        return command_results