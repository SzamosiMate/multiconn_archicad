"""Check the major/minor query schema contract before execution."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from packaging.version import Version

from multiconn_archicad.errors import AddOnCommandUnavailable, MulticonnArchicadError
from multiconn_archicad.utilities.server_versions import read_tapir_version
from .errors import UnsupportedQueryVersionError

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi
    from multiconn_archicad.orchestration.header_state import HeaderMetadata

QUERY_SCHEMA_VERSION = "1.0"
MIN_QUERY_TAPIR_VERSION = "2.0.0"


def require_query_tapir_version(api: UnifiedApi, metadata: HeaderMetadata | None) -> None:
    try:
        installed = read_tapir_version(api, metadata)
    except AddOnCommandUnavailable as error:
        raise MulticonnArchicadError(
            f"Element queries require Tapir {MIN_QUERY_TAPIR_VERSION} or newer. Tapir is unavailable."
        ) from error
    if Version(installed) < Version(MIN_QUERY_TAPIR_VERSION):
        raise MulticonnArchicadError(
            f"Element queries require Tapir {MIN_QUERY_TAPIR_VERSION} or newer. Installed version: {installed}."
        )


def validate_query_version(version: str) -> None:
    """Accept the same major and an equal or older minor than this executor.

    Parsing a Query retains its version string for inspection. Execution calls
    this helper before metadata reads, listing, or empty-population shortcuts.
    No migration or query transformation takes place.
    """
    # Version accepts the wider PEP 440 syntax; query schemas use major.minor.
    if re.fullmatch(r"[0-9]+\.[0-9]+", version) is None:
        raise ValueError(f"Invalid query schema version {version!r}; expected 'major.minor'")
    requested = Version(version)
    supported = Version(QUERY_SCHEMA_VERSION)
    if requested.major != supported.major or requested > supported:
        raise UnsupportedQueryVersionError(version, QUERY_SCHEMA_VERSION)
