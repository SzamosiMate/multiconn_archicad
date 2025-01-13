from typing import Any
from random import randrange

from multi_conn_ac import ConnHeader

class HighlightElements:
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

    def set_parameters(self) -> None:
        ...

    def randomize_color(self):
        self.highlightedColors = [randrange(256), randrange(256), randrange(256), randrange(256)]


