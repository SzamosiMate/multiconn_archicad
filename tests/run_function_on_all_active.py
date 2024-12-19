from multi_conn_ac.archicad_connection import ArchiCADConnection
from multi_conn_ac.multi_conn_ac import MultiConn
from time import sleep
import asyncio
from inspect import iscoroutinefunction
from typing import Callable, Any


def add_str_to_id(conn: ArchiCADConnection, str_to_add: str) -> str:
    elements = conn.commands.GetAllElements()
    property_user_id = [conn.types.PropertyUserId(type = "BuiltIn", nonLocalizedName = "General_ElementID")]
    property_id = conn.commands.GetPropertyIds(property_user_id)
    id_wrappers_of_elements = conn.commands.GetPropertyValuesOfElements(elements, property_id)
    ids_of_elements = [old_id_w.propertyValues[0].propertyValue for old_id_w in id_wrappers_of_elements]
    for element_id in ids_of_elements:
        element_id.value = element_id.value + str_to_add
        sleep(1)
        print(element_id.value)
    element_property_values = [conn.types.ElementPropertyValue(element.elementId, property_id[0].propertyId, e_id)
                               for element, e_id in zip(elements, ids_of_elements)]
    return conn.commands.SetPropertyValuesOfElements(element_property_values)

async def call_function(func, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return await asyncio.to_thread(func, *args, **kwargs)


async def run_function_on_all_active_async(conn: MultiConn, fn: Callable[[ArchiCADConnection, Any], Any], *args, **kwargs)-> dict:
    tasks = {
        port: call_function(fn, conn_header.archicad, *args, **kwargs)
        for port, conn_header in conn.active.items()
    }
    results = await asyncio.gather(*tasks.values())
    return {port: result for port, result in zip(tasks.keys(), results)}


def run_function_on_all_active():
    conn = MultiConn()
    conn.connect.all()


    # Run the asyncio event loop
    result = asyncio.run(run_function_on_all_active_async(conn, add_str_to_id, "?"))
    print(result)

if __name__ == "__main__":
    run_function_on_all_active()