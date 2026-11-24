from typing import Any

from .base import APIModel

class UnionModel(APIModel): ...

def bind_variants(model: type[UnionModel], variants: Any) -> None: ...
