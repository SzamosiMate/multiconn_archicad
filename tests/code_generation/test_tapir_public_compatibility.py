"""Public names and wire keys that must survive model regeneration."""

import pytest
from typeguard import TypeCheckError, check_type

from multiconn_archicad.dicts.tapir import types as wire
from multiconn_archicad.models.tapir import types as models

pytestmark = pytest.mark.unit


def test_library_scripts_preserve_numeric_wire_keys():
    payload = {"2d": "LINE2 0, 0, 1, 1", "3d": "BLOCK 1, 1, 1"}
    assert models.LibraryPartScripts.model_validate(payload).model_dump() == payload
    check_type(payload, wire.LibraryPartScripts)
    assert {"2d", "3d"} <= wire.LibraryPartScripts.__optional_keys__
    with pytest.raises(TypeCheckError):
        check_type({"2d": 42}, wire.LibraryPartScripts)


def test_released_names_retain_existing_imports():
    assert models.GraphicOverrideRuleDetails is models.GraphicOverrideRule
    assert models.MarkerGDLParameterDetails is models.StoredGDLParameter
    assert wire.GraphicOverrideRuleDetails is wire.GraphicOverrideRule
    assert wire.MarkerGDLParameterDetails is wire.StoredGDLParameter
    assert models.Level is models.RoofLevel
