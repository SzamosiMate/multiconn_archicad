<img src="https://github.com/user-attachments/assets/370ad589-117c-44cb-9a4a-80bfcb734445" width="400px" />

## 

**MultiConn Archicad** is a Python-based connection object for Archicad's JSON API and its Python wrapper. It is designed to manage multiple open instances of Archicad simultaneously, making it easier to execute commands across multiple instances.

[![Latest Release](https://img.shields.io/github/v/release/SzamosiMate/multiconn_archicad)](https://github.com/SzamosiMate/multiconn_archicad/releases/latest) ![License](https://img.shields.io/github/license/SzamosiMate/multiconn_archicad) 
![Issues](https://img.shields.io/github/issues/SzamosiMate/multiconn_archicad) 
![Forks](https://img.shields.io/github/forks/SzamosiMate/multiconn_archicad) 
![Stars](https://img.shields.io/github/stars/SzamosiMate/multiconn_archicad)

## Features

- **Unified High-Level API**: A modern, type-safe, and pythonic interface for both Official and Tapir APIs.
- **Multi-connection Support**: Connect to one, multiple, or all open instances of Archicad.
- **Seamless Integration**: Utilizes Archicad's official Python package.
- **Tapir Add-On Integration**: Run commands using the Tapir Archicad Add-On framework.
- **Efficient I/O Operations**: Handles connection management using concurrent or asynchronous code.
- **Project Management**: Find and open Archicad projects programmatically.

## Installation

You can install the latest version of the package from the following link using `pip`:

```bash
pip install multiconn_archicad
```

**Prerequisites: Tapir Add-On is Required**

This package **critically depends** on the [Tapir Archicad Add-On](https://github.com/ENZYME-APD/tapir-archicad-automation?tab=readme-ov-file). You **must** install the Tapir Add-On in your Archicad application for full functionality.

**Specifically, the Tapir Add-On is required for:**
*   All commands executed via the `core.post_tapir_command()` method.
*   Internal commands used by `multiconn_archicad` to identify running Archicad instances and projects (`GetProjectInfo`, `GetArchicadLocation`).

**Without the Tapir Add-On installed, key functionalities like discovering Archicad instances, identifying projects, and running any Tapir-specific commands will fail.** Please install the latest version of Tapir before using this package.

**Optional dependencies**
```bash
# to enable dialog handleing on windows
pip install multiconn_archicad[dialog-handlers]
```

## Usage

### Running Commands: The API Namespaces

The library provides three distinct namespaces for interacting with Archicad, each suited for different needs. 

*   **`unified`**: A high-level, type-safe and pythonic interface that unifies both the Official and Tapir APIs into a single, easy-to-use framework
*   **`core`**: A low-level interface for sending raw JSON commands.
*   **`standard`**: The official ArchiCAD python wrapper.

By incorporating the 3 namespaces to a common framework it is possible to freely mix them, allowing you to reuse codes of different styles.

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

### 1. The `unified` Namespace (Recommended)

The `unified` namespace is the modern, high-level, and recommended way to execute commands. It provides a type-safe and pythonic interface that unifies both the Official and Tapir APIs into a single, easy-to-use framework.

**Key Benefits:**

*   **Object-Oriented Interface**: A clean, dot-notation structure (`conn.unified.tapir...`) makes the API intuitive and easily discoverable with IDE autocompletion.
*   **Automatic Parameter Validation**: Inputs are validated by Pydantic models *before* a request is sent, preventing common errors and ensuring every API call is correctly formed.
*   **IDE-Native Experience**: Full type hinting provides static error checking and a seamless development experience.
*   **Structured & Validated Responses**: JSON responses are automatically parsed into Pydantic models, giving you reliable, object-oriented data to work with.

#### Example: Using the `unified` API with Pydantic Models

```python
from multiconn_archicad import MultiConn
from multiconn_archicad.models.official import types as official_types

# By default, primary is the first open port in the port range
conn = MultiConn()
assert conn.primary, "No running Archicad instance found."

# Create a shortcut to the official_commands commands for convenience
official_commands = conn.primary.unified.official

# 1. Get identifiers for all elements
elements = official_commands.element_listing.get_all_elements()

# 2. Define the 'Element ID' property using a Pydantic model
property_user_id = [
    official_types.BuiltInPropertyUserId(
        type="BuiltIn", nonLocalizedName="General_ElementID"
    )
]

# 3. Get Archicad's internal ID for that property
property_id = official_commands.property.get_property_ids(property_user_id)

# 4. Fetch the property values for the elements
value_wrappers_of_elements = official_commands.property.get_property_values_of_elements(
    elements, property_id
)

# 5. Extract the actual values using a list comprehension
property_values_for_elements = [
    wrapper.propertyValues[0].propertyValue.value
    for wrapper in value_wrappers_of_elements
]

print(f"Retrieved Element IDs for {len(property_values_for_elements)} elements.")
```

### 2. The `core` Namespace (Low-Level)

The `core` namespace is a low-level interface for sending raw JSON commands. It is useful for advanced scenarios or for accessing commands not yet available in the `unified` API. It requires you to build the request dictionaries manually. It is inspired by Tapir's ["aclib"](https://github.com/ENZYME-APD/tapir-archicad-automation/tree/main/archicad-addon/Examples/aclib).

*   `core.post_command()`: Sends commands to the Official JSON API.
*   `core.post_tapir_command()`: Sends commands to the Tapir Add-On.


#### Enhancing the `core` Namespace with `TypedDicts`

To make the `core` namespace safer and easier to use, the library provides a complete set of `TypedDicts`. These allow your IDE and static type checkers (like MyPy) to validate the structure of your command dictionaries *before* you run your code, catching common mistakes like missing keys or incorrect data types.

#### Example: Using `core` with `TypedDicts` for Static Checking

**Before (Without TypedDicts - Error-Prone):**
```python
# This is a common mistake: the API expects a list of `{"elementId": ...}` wrappers.
# This error would only be caught at runtime.
command_parameters = {
    "elements": [
        {"guid": "GUID_1"},
        {"guid": "GUID_2"}
    ],
}
# This call would fail when sent to the API.
conn.core.post_tapir_command('HighlightElements', command_parameters)
```

**After (With TypedDicts for Static Safety):**
By using a `TypedDict` in a helper function, your tools can validate the dictionary structure instantly.

```python
from multiconn_archicad.tapir.dicts.commands import HighlightElementsParameters

def highlight_elements(conn: MultiConn, params: HighlightElementsParameters):
    """A type-safe wrapper for the HighlightElements command."""
    return conn.core.post_tapir_command('HighlightElements', params)

# --- Incorrect Usage ---
incorrect_params = {
    "elements": [
        {"guid": "GUID_1"}, # Error is here!
        {"guid": "GUID_2"}
    ],
}

# Your IDE and type checker will immediately flag this line with an error,
# preventing a runtime failure.
highlight_elements(conn, incorrect_params) # <-- STATIC ERROR!
```

### 3. The `standard` Namespace (Legacy)

This namespace provides direct access to Archicad's official Python wrapper. It is maintained for backward compatibility with older scripts but is not recommended for new projects, as the `unified` API incorporates all it's features, and covers the Tapir commands as well.

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

### Connection Management

Actions allow you to manage the state of the connection object.

#### Example: Connection Management
```python 
from multiconn_archicad import MultiConn, Port

conn = MultiConn()

# Connect to all running Archicad instances
conn.connect.all()

# Disconnect from a specific instance
conn.disconnect.from_ports(Port(19723))

# Refresh all closed ports - ports with no running archicad instance   
conn.refresh.closed_ports()

# Quit an Archicad instance
conn.quit.from_headers(conn.open_port_headers[Port(19735)])
```

### Project Management

The `MultiConn` object provides actions to find and open Archicad projects programmatically.

#### Finding ArchiCAD Instances

You can use the `find_archicad` action to locate a specific ArchiCAD instance from a `ConnHeader`.

```python
from multiconn_archicad import MultiConn, ConnHeader

conn = MultiConn()
conn_header = ConnHeader(Port(19723))
port = conn.find_archicad.from_header(conn_header)
if port:
    print(f"Found Archicad instance at port: {port}")
```

#### Opening Projects

The `open_project` action allows you to start a new Archicad window an open a project. This is the only way to open teamwork projects. 

```python
from multiconn_archicad import MultiConn, ConnHeader, TeamworkCredentials

conn = MultiConn()

# Open a project using a connection header
conn_header = ConnHeader.from_dict(saved_header_data)
port = conn.open_project.from_header(conn_header)
# Optionally, open in demo mode:
port = conn.open_project.from_header(conn_header, demo=True) 

# For teamwork projects, you can provide credentials
credentials = TeamworkCredentials("username", "password")
port = conn.open_project.with_teamwork_credentials(conn_header, credentials)
```

### Dialog Handling (Windows only)

When you open a project with the `open_project` command different dialogs will likely pop up. The MultiConn library provides DialogHandlers to programmatically handle those dialogs. This is particularly useful for batch operations and automation scripts.

```python
from multiconn_archicad import MultiConn, WinDialogHandler, win_int_handler_factory

# Create a MultiConn instance with a dialog handler
conn = MultiConn(dialog_handler=WinDialogHandler(win_int_handler_factory))

# Dialog windows will be automatically handled when opening projects
conn.open_project.from_header(conn_header)
```


#### Switching Projects (Solo Only)

The `switch_project` action allows you to open a *different* solo project (`.pln`) within an *already running* Archicad instance, without needing to quit and restart. This is useful for quickly changing between solo project files managed by the same Archicad process.
 
```python
from multiconn_archicad import MultiConn, ConnHeader, Port

conn = MultiConn()
# Assume Archicad is running on port 19723 and port 19725

# Get the header for the project you want to switch *to* (e.g., loaded from a file)
target_header = ConnHeader.from_dict(saved_header_data_for_another_project)

# Specify the port of the *running instance* you want to load the new project into
running_instance_port = Port(19723)

# Switch the project on the running instance
# This will close the current project on port 19723 and open the one defined by target_header
new_header_state = conn.switch_project.from_header(original_port=running_instance_port, new_header=target_header)

# Alternatively, switch using a file path directly
new_path = "C:/path/to/another/project.pln"
new_header_state_from_path = conn.switch_project.from_path(original_port=running_instance_port, new_path=new_path)
```
DialogHandlers are platform and language dependent.

The current implementation includes:
- `EmptyDialogHandler`: Does nothing (default)
- `WinDialogHandler`: Waits for ArchiCAD to start, and monitors appearing dialogs. If dialog appears, searches for appropriate handler in win_int_handler factory. Only works on windows.
- `win_int_handler_factory`: Provides dialog handling logic on a dialog by dialog basis for the INT language version. It is an example you should customize for your specific project needs.

### Serialization

You can save and load connection configurations to easily reconnect to specific projects.

#### Saving Connection Headers
```python
import json
from multiconn_archicad import MultiConn, Port

conn = MultiConn()
conn.connect.all()
conn_header = conn.open_port_headers[Port(19723)]
header_dict = conn_header.to_dict()

with open('conn_header.json', 'w') as f:
    json.dump(header_dict, f)
```

#### Loading Connection Headers
Note: Passwords are not stored in serialized connection headers for security reasons. You must provide them when loading teamwork projects.

```python
import json
from multiconn_archicad import ConnHeader

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

### Error Handling

**MultiConn Archicad** uses a structured exception hierarchy for reporting errors. This makes error handling more explicit and robust.

*   All library-specific exceptions inherit from `MulticonnArchicadError`.
*   **API Communication Errors:** Inherit from `APIErrorBase`.
    *   `RequestError`: Problems during the request itself (network, connection, timeout, invalid response).
        *   Examples: `APIConnectionError`, `CommandTimeoutError`, `InvalidResponseFormatError`.
    *   `ArchicadAPIError`: Errors reported *by* Archicad or the Tapir Add-On in the response body.
        *   Examples: `StandardAPIError` (from official API), `TapirCommandError` (from Tapir Add-On).
*   **Other Errors:** Include issues like `ProjectAlreadyOpenError`, `ProjectNotFoundError`, `NotFullyInitializedError`.

You **must** wrap calls to `core.post_command` and `core.post_tapir_command` in `try...except` blocks to handle these potential exceptions gracefully.

#### Example: Handling Core Command Exceptions

```python
from multiconn_archicad.errors import TapirCommandError, RequestError, ArchicadAPIError, APIErrorBase 

try:
    # Attempt to execute a Tapir command
    result = conn.core.post_tapir_command('YourTapirCommandName', command_parameters)
    print(f"Command successful! Result: {result}")

# Handle specific error reported by the Tapir Add-On
except TapirCommandError as e:
    print(f"Tapir command failed: Code={e.code}, Message='{e.message}'")

# Handle broader Archicad API errors (includes StandardAPIError)
except ArchicadAPIError as e:
    print(f"Archicad API error: Code={e.code}, Message='{e.message}'")

# Handle connection/request related errors (timeout, network issues, etc.)
except RequestError as e:
    print(f"Request failed: Message='{e.message}' (Code={e.code})")

# Catch any other potential API-related error (Catches all above errors as well.
# If you do not need to handle failures differently, only catch this!
except APIErrorBase as e:
     print(f"An API error occurred: Code={e.code}, Message='{e.message}'")

```

## Contributing

Contributions are welcome! Feel free to submit issues, feature requests, or pull requests to help improve MultiConn ArchiCAD.

## License

This project is licensed under the MIT License. See the LICENSE file for details.