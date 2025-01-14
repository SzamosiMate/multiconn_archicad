from typing import Any
from random import randrange
from nicegui import ui

from multi_conn_ac import ConnHeader

class HighlightWithRandomColor:
    """
    This is a script to demonstrate how the app works. It **does not do anything** *particularly useful.*
    It colors all elements with a random color.
    """
    def __init__(self):
        self.highlightedColors: list[int] = [210, 40, 10, 100]

    def run(self, conn: ConnHeader) -> dict[str, Any]:
        elements = conn.standard.commands.GetAllElements()
        self.randomize_color()
        command_parameters = {
            "elements": [element.to_dict() for element in elements],
            "highlightedColors": [self.highlightedColors for _ in range(len(elements))],
            "wireframe3D": True,
            "nonHighlightedColor": [0, 0, 255, 128],
        }
        response: dict[str, Any] = conn.core.post_tapir_command('HighlightElements', command_parameters)
        return response

    def randomize_color(self):
        self.highlightedColors = [randrange(256), randrange(256), randrange(256), randrange(256)]

class HighlightWithChosenColor:
    """
    This script highlights elements with a **chosen colour**. It does not do anything *particularly useful.*
    It is still just a demonstration script.
    """
    def __init__(self):
        self.highlightedColors: list[int] = [0, 0, 0, 0]

    def run(self, conn: ConnHeader) -> dict[str, Any]:
        elements = conn.standard.commands.GetAllElements()
        command_parameters = {
            "elements": [element.to_dict() for element in elements],
            "highlightedColors": [self.highlightedColors for _ in range(len(elements))],
            "wireframe3D": True,
            "nonHighlightedColor": [0, 0, 255, 128],
        }
        response: dict[str, Any] = conn.core.post_tapir_command('HighlightElements', command_parameters)
        return response

    def set_parameters(self) -> None:
        ui.color_picker(value=True, on_pick=lambda e:self.set_colour(e.color))

    def set_colour(self, colour) -> None:
        print(colour)
        print(type(colour))


