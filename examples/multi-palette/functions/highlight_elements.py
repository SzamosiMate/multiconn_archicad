from typing import Any
from random import randrange
from nicegui import ui
import re

from multiconn_archicad import ConnHeader, MultiConn


class HighlightWithRandomColor:
    """
    This is a script to demonstrate how the app works. It **does not do anything** *particularly useful.*
    It colors all elements with a random color.
    """
    def __init__(self):
        self.multi_conn: MultiConn | None = None
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
    This script highlights elements with a **chosen color**. It does not do anything *particularly useful.*
    It is still just a demonstration script.
    """
    def __init__(self):
        self.multi_conn: MultiConn | None = None
        self.highlightedColor: list[int] = [0, 0, 0, 0]

    def run(self, conn: ConnHeader) -> dict[str, Any]:
        elements = conn.standard.commands.GetAllElements()
        command_parameters = {
            "elements": [element.to_dict() for element in elements],
            "highlightedColors": [self.highlightedColor for _ in range(len(elements))],
            "wireframe3D": True,
            "nonHighlightedColor": [0, 0, 255, 128],
        }
        response: dict[str, Any] = conn.core.post_tapir_command('HighlightElements', command_parameters)
        return response

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



