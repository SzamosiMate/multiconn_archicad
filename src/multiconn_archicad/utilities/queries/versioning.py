"""Check the major/minor query schema contract before execution."""

import re

from packaging.version import Version

from .errors import UnsupportedQueryVersionError

QUERY_SCHEMA_VERSION = "1.0"


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
