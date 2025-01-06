# MultiConnAC

[![Latest Release](https://img.shields.io/github/v/release/SzamosiMate/MultiConnAC)](https://github.com/SzamosiMate/MultiConnAC/releases/latest) 
![License](https://img.shields.io/github/license/SzamosiMate/MultiConnAC) 
![Issues](https://img.shields.io/github/issues/SzamosiMate/MultiConnAC) 
![Forks](https://img.shields.io/github/forks/SzamosiMate/MultiConnAC) 
![Stars](https://img.shields.io/github/stars/SzamosiMate/MultiConnAC)

## About

**MultiConnAC** is a Python-based connection object for ArchiCAD’s JSON API and its Python wrapper. It is designed to manage multiple open instances of Archicad simultaneously, making it easier to execute commands across multiple instances.

## Features

- **Multi-instance Support**: Connect to one, multiple, or all open instances of Archicad.
- **Seamless Integration**: Utilizes ArchiCAD's official Python package.
- **Tapir Add-On Support**: Run commands from the Tapir Archicad Add-On.
- **Efficient I/O Operations**: Handles connection management using concurrent or asynchronous code.

## Installation

You can install the latest version of the package from the following link using `pip`:

```bash
pip install https://github.com/SzamosiMate/MultiConnAC/releases/latest/download/multi_conn_ac-0.1.2-py3-none-any.whl
```

The package depends on the [Tapir Archicad Add-On](https://github.com/ENZYME-APD/tapir-archicad-automation?tab=readme-ov-file). It is recommended to install the latest version of Tapir to access all features. While some functionality may work without the add-on, all tests have been conducted with it installed.

## Usage

**Disclaimer:** The connection object is functional but in the early stages of development. It is not thoroughly tested, and its interfaces may change in future updates.

### Actions - managing the connection
Actions allow you to manage the state of the connection object. You can connect to or disconnect from Archicad instances, quit instances, or refresh ports. All actions can have multiple types of inputs. For each type of input you have to call the corresponding method of the action. To connect to all available ArchiCAD instances, you have to call the .all() method on .connect ( e.g. `conn.connect.all()`). The aim of this method is to provide better autocompletion.

#### Example: Connection Management
```python 
from multi_conn_ac import MultiConn, Port

conn = MultiConn()

# connect all ArchiCAD instances that were running at instantiation / the last refresh
conn.connect.all()

# disconnect from the instance at port 19723   
conn.disconnect.from_ports(Port(19723))

# refresh all closed ports - ports with no running archicad instance   
conn.refresh.closed_ports()

# close, and remove from the dict of open port headers the archicad instance specified by ConnHeader
conn.quit.from_headers(conn.open_port_headers[Port(19735)])
```
### Running Commands

#### Single Archicad Instance

To run commands on one chosen ArchiCAD instance the `MultiConn` object has a connection called `primary`. Calling a command directly from the MultiConn object will send it to the `primary` instance. The `primary` connection can be changed by assigning any valid `Port`, or `ConnHeader` object to `MultiConn.primary`.

#### Example: Running Commands on a Single Archicad Instance
```python
from multi_conn_ac import MultiConn, Port

# After instantiation the primary connection will be the instance with the lowest port number (probably 19723)
conn = MultiConn()

# Set the primary connection to the instance running on port 19725
conn.primary = Port(19725)

# Prints project info from the instance on port 19725
print(conn.core.post_tapir_command("GetProjectInfo"))
```

#### Multiple Archicad Instances

The MultiConn object stores references to `ConnHeaders` for all open ports (ports, with a running ArchiCAD instance). The references are stored in a dictionary at `.open_port_headers`. This dictionary maps each port to its corresponding connection. Each `ConnHeader` object has its own command objects for each used command namespace. The MultiConn objects has properties to access 3 subsets of open ports based on the status of the `ConnHeaders`: 

- **`active`**: Successfully connected instances.
- **`failed`**: Instances where the connection attempt failed.
- **`pending`**: Instances with no connection attempt made or disconnected.

#### Example: Running Commands on Multiple Archicad Instances

```python
from multi_conn_ac import MultiConn

conn = MultiConn()
conn.connect.all()

# Explicit loop to gather elements from all active connections
elements = {}
for port, conn_header in conn.active.items():
    elements[port] = conn_header.standard.commands.GetAllElements()

# Using dictionary comprehension
elements = {
    port: conn_header.standard.commands.GetAllElements()
    for port, conn_header in conn.active.items()
}
```

### Namespaces

The aim of the module is to incorporate all solutions that let users automate ArchiCAD from python. The different solutions are separated into namespaces, accessed from properties of the connection object. One of the planned features is letting users supply a list of namespaces they want to use when creating the connections. At the moment there are only two namespaces:

- **`standard`**: The official ArchiCAD python wrapper
- **`core`**: A simple JSON based module that lets the users post official and tapir commands based on Tapir's ["aclib"](https://github.com/ENZYME-APD/tapir-archicad-automation/tree/main/archicad-addon/Examples/aclib)

#### Example: Using two namespaces together
```python
def run(conn: MultiConn | ConnHeader) -> dict[str, Any]:
    elements = conn.standard.commands.GetAllElements()
    command_parameters = {
        "elements": [element.to_dict() for element in elements],
        "highlightedColors": [[50, 255, 100, 100] for _ in range(len(elements))],
        "wireframe3D": True,
        "nonHighlightedColor": [0, 0, 255, 128],
    }
    return conn.core.post_tapir_command('HighlightElements', command_parameters)
```

## Contributing

Contributions are welcome! Feel free to submit issues, feature requests, or pull requests to help improve MultiConnAC.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

