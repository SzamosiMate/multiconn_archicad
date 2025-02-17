from __future__ import annotations
from typing import TYPE_CHECKING

from archicad.versioning import _Versioning
from archicad.connection import create_request
from archicad.releases import Commands, Types, Utilities

if TYPE_CHECKING:
    from multi_conn_ac.basic_types import ProductInfo, Port
    from urllib.request import Request


class StandardConnection:
    types = Types
    commands = Commands
    utilities = Utilities

    def __init__(self, port: Port):
        self._request: Request = create_request(int(port))

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(port={self._request.full_url})"

    def connect(self, product_info: ProductInfo) -> None:
        v = _Versioning(product_info.version, product_info.build, self._request)
        self.commands = v.commands
        self.types = v.types
        self.utilities = v.utilities

    def disconnect(self) -> None:
        self.types = Types
        self.commands = Commands
        self.utilities = Utilities