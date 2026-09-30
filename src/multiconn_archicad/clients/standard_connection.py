from __future__ import annotations
from typing import TYPE_CHECKING

from archicad.versioning import _Versioning
from archicad.connection import create_request
from archicad.releases import Commands, Types, Utilities

if TYPE_CHECKING:
    from multiconn_archicad.orchestration.basic_types import ProductInfo, Port
    from urllib.request import Request


class StandardConnection:
    def __init__(self, port: Port):
        self._request: Request = create_request(int(port))
        self.is_versioned: bool = False
        self.types = Types
        self.commands = Commands
        self.utilities = Utilities

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(_request={self._request.full_url})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(_request={self._request.full_url})"

    def bind(self, product_info: ProductInfo) -> None:
        """Internal binding hook — no public connect() needed."""
        v = _Versioning(product_info.version, product_info.buildNumber, self._request)
        self.commands = v.commands
        self.types = v.types
        self.utilities = v.utilities
        self.is_versioned = True