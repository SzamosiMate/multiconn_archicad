"""Read server versions from an existing header snapshot or a standalone API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from multiconn_archicad.errors import AddOnCommandUnavailable, MulticonnArchicadError
from multiconn_archicad.orchestration.basic_types import APIResponseError

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi
    from multiconn_archicad.orchestration.header_state import HeaderMetadata


def read_archicad_major(api: UnifiedApi, metadata: HeaderMetadata | None) -> int:
    if metadata is None:
        return api.official.basic.get_product_info().version
    product = metadata.product_info
    if isinstance(product, APIResponseError):
        raise MulticonnArchicadError(product.message)
    return product.version


def read_tapir_version(api: UnifiedApi, metadata: HeaderMetadata | None) -> str:
    if metadata is None:
        return api.tapir.application.get_add_on_version()
    tapir = metadata.tapir_info
    if isinstance(tapir, APIResponseError):
        raise MulticonnArchicadError(tapir.message)
    if tapir.version is None:
        raise AddOnCommandUnavailable(message="Tapir is not installed.")
    return tapir.version
