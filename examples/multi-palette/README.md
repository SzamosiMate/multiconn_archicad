# What is Multi-Palette?

**Multi-Palette** is a simple graphical interface designed to help users select and run their Python scripts. It serves as a replacement for Archicad's built-in Python palette, offering several improvements. This application was developed as an example and test case for the **MultiConnAC** Python package.

# Features
- Run your scripts on a single Archicad instance or multiple instances simultaneously.  
- Define graphical input elements for your scripts, improving user interaction.  
- Utilize **Tapir commands** alongside Graphisoft's standard Python wrapper.  

# Installation
1. Download and unzip the Windows distribution (will provide link later) or clone the repo
2. Download and install the Tapir add-on: [Tapir Archicad Add-On](https://github.com/ENZYME-APD/tapir-archicad-automation?tab=readme-ov-file)
3. Start the Multi-Palette executable or `main.py` from the repository.

# How to create scripts for the palette?
Each script has to be defined as a class, that adheres to a certain template. 

### How to make your script runnable?
There is one mandatory thing - the script's class must implement the `Runnable` protocol. This means, each script must have a methods called "run" with the same parameters, and return types. This method will be called when you click "run" on the UI. The UI supplies the necessary `ConnHeader` and handles looping.  You may provide a docstring to the class. It will appear on the script selection dialog with **Markdown formatting**.

```python
@runtime_checkable
class Runnable(Protocol):
    """
    Put the description of your script here. You can use **markdown** for formatting
    """
    def run(self, conn: ConnHeader) -> dict[str, Any]:
        ...
```

### Setting Parameters via the UI
The "Set Parameters" button will remain disabled until you select a script that implements the `Settable` protocol. When you click the "set Parameters" button the appearing dialog will run the "set_parameters" method of your class. 
When clicked, the "Set Parameters" button opens a dialog that calls the `set_parameters` method of your class. This method can include NiceGUI widgets to set instance parameters, which can then be used in your script.
To create input widgets with complex logic the app injects a reference to the MultiConn object to the .multi_conn parameter of every script.

**Example Implementation:**
```python
import re
from nicegui import ui

class HighlightWithChosenColor:
    def set_parameters(self) -> None:
        color_input = (ui.color_input(
            label="Pick highlight color",
            value="#000000",
            on_change=lambda e: self.set_color(e.value)
        ))
        color_input.picker.q_color.props('format-model=rgba')

    def set_color(self, color) -> None:
        self.highlightedColor = self.convert_color(color)

    def convert_color(self, rgba_str: str) -> list[int]:
        match = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", rgba_str)
        if match:
            return [
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(float(match.group(4))*255),
            ]
        else:
            raise ValueError(f"Invalid rgba string: {rgba_str}")
```
**Note:**  
[**NiceGUI**](https://nicegui.io/) is a Python-based framework for creating web-based user interfaces. You can find more details on its official website.
# Limitations
This project is a work in progress, and there are some known limitations:  
- Currently, it only works on **Windows**.  
- Script dependencies are not downloaded or installed at runtime. You need to:  
  - Manually place the required modules in the `_internal` folder, or  
  - Clone the repository, install the required modules, and rebuild the executable.  
- There is no panel to display the results of running scripts.

# Contributions
There are many features I would love to implement, but I have more ideas I’m excited about than free time to work on them. If you find this project valuable or want to contribute, feel free to reach out! Together, we can make this tool even better.
