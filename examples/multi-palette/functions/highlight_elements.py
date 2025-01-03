from typing import Any

from multi_conn_ac import MultiConn, ConnHeader


class HighlightElements:
    @staticmethod
    def run(conn: MultiConn | ConnHeader) -> dict[str, Any]:
        elements = conn.archicad.commands.GetAllElements()
        command_parameters = {
            "elements": [element.to_dict() for element in elements],
            "highlightedColors": [[50, 255, 100, 100] for _ in range(len(elements))],
            "wireframe3D": True,
            "nonHighlightedColor": [0, 0, 255, 128],
        }
        response = conn.core.post_tapir_command('HighlightElements', command_parameters)
        return response

