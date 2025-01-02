from typing import Any
from multi_conn_ac import MultiConn, ConnHeader


class HighlightElements:
    @staticmethod
    def run(conn: MultiConn | ConnHeader) -> dict[str, Any]:
        elements = conn.archicad.commands.GetAllElements()
        command_parameters = {
            "elements": elements.to_dict(),
            "highlightedColors": [
                [(i * 30) % 255, 50, 50, 255]
                for i in range(len(elements))
            ],
            "wireframe3D": True,
            "nonHighlightedColor": [0, 0, 255, 128],
        }
        response = conn.core.RunTapirCommand('HighlightElements', command_parameters)
        return response


