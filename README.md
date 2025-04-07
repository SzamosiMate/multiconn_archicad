<img src="https://github.com/user-attachments/assets/370ad589-117c-44cb-9a4a-80bfcb734445" width="400px" />

## 

**MultiConn ArchiCAD** is a Python-based connection object for ArchiCAD's JSON API and its Python wrapper. It is designed to manage multiple open instances of Archicad simultaneously, making it easier to execute commands across multiple instances.

[![Latest Release](https://img.shields.io/github/v/release/SzamosiMate/multiconn_archicad)](https://github.com/SzamosiMate/multiconn_archicad/releases/latest) 
![License](https://img.shields.io/github/license/SzamosiMate/multiconn_archicad) 
![Issues](https://img.shields.io/github/issues/SzamosiMate/multiconn_archicad) 
![Forks](https://img.shields.io/github/forks/SzamosiMate/multiconn_archicad) 
![Stars](https://img.shields.io/github/stars/SzamosiMate/multiconn_archicad)

## Features

- **Multi-connection Support**: Connect to one, multiple, or all open instances of Archicad.
- **Seamless Integration**: Utilizes ArchiCAD's official Python package.
- **Tapir Add-On Integration**: Run commands using the Tapir Archicad Add-On framework
- **Efficient I/O Operations**: Handles connection management using concurrent or asynchronous code.
- **Project Management**: Find and open ArchiCAD projects programmatically.

## Installation

You can install the latest version of the package from the following link using `pip`:

```bash
pip install https://github.com/SzamosiMate/multiconn_archicad/releases/latest/download/multiconn_archicad-0.2.0-py3-none-any.whl
```

**Prerequisites: Tapir Add-On is Required**

This package **critically depends** on the [Tapir Archicad Add-On](https://github.com/ENZYME-APD/tapir-archicad-automation?tab=readme-ov-file). You **must** install the Tapir Add-On in your Archicad application for full functionality.

**Specifically, the Tapir Add-On is required for:**
*   All commands executed via the `core.post_tapir_command()` method.
*   Internal commands used by `multiconn_archicad` to identify running Archicad instances and projects (`GetProjectInfo`, `GetArchicadLocation`).

**Without the Tapir Add-On installed, key functionalities like discovering Archicad instances, identifying projects, and running any Tapir-specific commands will fail.** Please install the latest version of Tapir before using this package.

## Usage

**Disclaimer:** The connection object is functional but in the early stages of development. It is not thoroughly tested, and its interfaces may change in future updates.

### Actions - managing the connection
Actions allow you to manage the state of the connection object. You can connect to or disconnect from Archicad instances, quit instances, or refresh ports. All actions can have multiple types of inputs. For each type of input you have to call the corresponding method of the action. To connect to all available ArchiCAD instances, you have to call the .all() method on .connect ( e.g. `conn.connect.all()`). The aim of this method is to provide better autocompletion.

#### Example: Connection Management
```python 
from multiconn_archicad import MultiConn, Port

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

### Project Management

The MultiConn object provides actions to find and open ArchiCAD projects programmatically.

#### Finding ArchiCAD Instances

You can use the `find_archicad` action to locate a specific ArchiCAD instance from a `ConnHeader`.

```python
from multiconn_archicad import MultiConn, ConnHeader

conn = MultiConn()
conn_header = ConnHeader(Port(19723))

# Find the port for a specific connection header
port = conn.find_archicad.from_header(conn_header)
if port:
    print(f"Found ArchiCAD instance at port: {port}")
```

#### Opening Projects

The `open_project` action allows you to programmatically open ArchiCAD projects.

```python
from multiconn_archicad import MultiConn, ConnHeader, TeamworkCredentials

conn = MultiConn()

# Open a project using a connection header
conn_header = ConnHeader.from_dict(saved_header_data)
port = conn.open_project.from_header(conn_header)

# For teamwork projects, you can provide credentials
credentials = TeamworkCredentials("username", "password")
port = conn.open_project.with_teamwork_credentials(conn_header, credentials)
```

### Dialog Handling

MultiConn can automatically handle most dialog windows that appear when opening ArchiCAD projects. This is particularly useful for batch operations and automation scripts.

```python
from multiconn_archicad import MultiConn, WinDialogHandler, win_int_handler_factory

# Create a MultiConn instance with a dialog handler
conn = MultiConn(dialog_handler=WinDialogHandler(win_int_handler_factory))

# Dialog windows will be automatically handled when opening projects
conn.open_project.from_header(conn_header)
```

The current implementation includes:
- `EmptyDialogHandler`: Does nothing (default)
- `WinDialogHandler`: Waits for ArchiCAD to start, and monitors appearing dialogs. If dialog appears, searches for appropriate handler in win_int_handler factory. Only works on windows.
- `win_int_handler_factory`: Provides dialog handleing logic on a dialog by dialog basis for the INT language version. It is an example you should customize for your specific project needs. Even if you end up not modifying it, you should definitely know what it does for what dialog.

### Serialization

The MultiConn package allows you to save and load connection configurations, making it easier to work with specific projects across multiple sessions.

#### Saving Connection Headers

```python
from multiconn_archicad import MultiConn, Port

conn = MultiConn()
conn.connect.all()

# Get a connection header
conn_header = conn.open_port_headers[Port(19723)]

# Convert to dictionary for serialization
header_dict = conn_header.to_dict()

# Save to file using your preferred method
import json
with open('conn_header.json', 'w') as f:
    json.dump(header_dict, f)
```

#### Loading Connection Headers

```python
from multiconn_archicad import ConnHeader, TeamworkCredentials

# Load from file
import json
with open('conn_header.json', 'r') as f:
    header_dict = json.load(f)

# Create a header from the dictionary
conn_header = ConnHeader.from_dict(header_dict)

# For teamwork projects, you need to provide credentials
if isinstance(conn_header.archicad_id, TeamworkProjectID):
    credentials = TeamworkCredentials("username", "password")
    # Use the credentials when opening the project
    port = conn.open_project.with_teamwork_credentials(conn_header, credentials)
```

Note: Passwords are not stored in serialized connection headers for security reasons. You must provide them when loading teamwork projects.

### Running Commands

#### Single Archicad Instance

To run commands on one chosen ArchiCAD instance the `MultiConn` object has a connection called `primary`. Calling a command directly from the MultiConn object will send it to the `primary` instance. The `primary` connection can be changed by assigning any valid `Port`, or `ConnHeader` object to `MultiConn.primary`.

#### Example: Running Commands on a Single Archicad Instance
```python
from multiconn_archicad import MultiConn, Port

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
from multiconn_archicad import MultiConn

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
- **`core`**: A simple JSON-based module that lets users post official Archicad JSON commands and Tapir-specific commands via `core.post_command()` and `core.post_tapir_command()` respectively. **Important:** The `core.post_tapir_command()` method, and internal functions relying on it (like project identification), **absolutely require** the Tapir Add-On to be installed in Archicad. These commands will **fail** if Tapir is not present. This namespace is inspired by Tapir's ["aclib"](https://github.com/ENZYME-APD/tapir-archicad-automation/tree/main/archicad-addon/Examples/aclib).

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

Contributions are welcome! Feel free to submit issues, feature requests, or pull requests to help improve MultiConn ArchiCAD.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
