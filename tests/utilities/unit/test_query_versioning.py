"""Enforce numeric major/minor compatibility at the query execution boundary."""

import pytest

from multiconn_archicad.utilities.queries import (
    QUERY_SCHEMA_VERSION,
    Query,
    UnsupportedQueryVersionError,
    validate_query_version,
)
from multiconn_archicad.utilities.queries import versioning

pytestmark = pytest.mark.unit


def test_default_query_version_is_supported():
    query = Query.model_validate({"where": {"kind": "element_type", "types": ["Wall"]}})

    assert query.schema_version == QUERY_SCHEMA_VERSION == "1.0"
    validate_query_version(query.schema_version)


@pytest.mark.parametrize("requested", ["1.0", "1.3", "1.9", "1.10"])
def test_same_major_and_older_or_equal_minor_are_supported(monkeypatch, requested):
    monkeypatch.setattr(versioning, "QUERY_SCHEMA_VERSION", "1.10")

    validate_query_version(requested)


@pytest.mark.parametrize("requested", ["0.9", "1.11", "2.0"])
def test_other_majors_and_future_minors_are_rejected(monkeypatch, requested):
    monkeypatch.setattr(versioning, "QUERY_SCHEMA_VERSION", "1.10")

    with pytest.raises(UnsupportedQueryVersionError) as caught:
        validate_query_version(requested)

    assert caught.value.requested_version == requested
    assert caught.value.supported_version == "1.10"


@pytest.mark.parametrize("requested", ["", "1", "1.0.0", "1.0rc1", " 1.0", "1.0\n", "-1.0", "one.zero"])
def test_malformed_versions_are_rejected(requested):
    with pytest.raises(ValueError, match="expected 'major.minor'"):
        validate_query_version(requested)
