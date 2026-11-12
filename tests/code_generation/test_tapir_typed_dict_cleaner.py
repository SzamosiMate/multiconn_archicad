import importlib
import sys
import types
import warnings
from typing import get_type_hints

import pytest
from typeguard import TypeCheckError, check_type

cleaner = importlib.import_module("code_generation.tapir.model_generators.06_typed_dict_cleaner")
pytestmark = pytest.mark.unit


@pytest.mark.parametrize("operator", ["and", "or"])
def test_graphic_override_keyword_fields_remain_optional_and_validate_nested_values(monkeypatch, operator):
    source = """from __future__ import annotations
from typing import TypedDict, get_type_hints
from typing_extensions import NotRequired

GraphicOverrideCriterion = TypedDict(
    "GraphicOverrideCriterion",
    {
        "and": NotRequired[list[GraphicOverrideCriterion]],
        "or": NotRequired[list[GraphicOverrideCriterion]],
        "layer": NotRequired[str],
    },
)
"""
    cleaned = cleaner.fix_graphic_override_forward_refs(source)
    module = types.ModuleType("_test_graphic_override_typed_dict")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(cleaned, module.__dict__)
    criterion = module.GraphicOverrideCriterion
    assert criterion.__required_keys__ == frozenset()
    assert criterion.__optional_keys__ == frozenset({"and", "or", "layer"})
    assert get_type_hints(criterion)[operator] == list[criterion]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        check_type({}, criterion)
        check_type({operator: [{"layer": "Walls"}]}, criterion)
        with pytest.raises(TypeCheckError):
            check_type({operator: [{"layer": 1}]}, criterion)
    assert cleaner.fix_graphic_override_forward_refs(cleaned) == cleaned


def test_unrelated_typed_dicts_are_unchanged():
    source = """from typing import TypedDict
class Existing(TypedDict):
    name: str
class Recursive(TypedDict):
    children: list[Recursive]
Item = TypedDict("Item", {"detail": Existing})
"""
    assert cleaner.fix_graphic_override_forward_refs(source) == source
