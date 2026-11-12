import importlib
from typing import Annotated, TypeAlias

import pytest
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

cleaner = importlib.import_module("code_generation.tapir.model_generators.03_model_cleaner")
pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "annotation, constraint, valid, invalid",
    [
        ("float", "gt=0", 1.0, 0),
        ("int", "ge=0", 0, -1),
        ("str", "min_length=1", "key", ""),
        ("list[int]", "min_length=4, max_length=4", [1, 2, 3, 4], [1]),
    ],
)
def test_collapsed_root_alias_keeps_validation(annotation, constraint, valid, invalid):
    source = f"""class Constrained(RootModel[{annotation}]):
    root: {annotation} = Field(..., description="Value", {constraint})
"""
    cleaned = cleaner.fix_root_model_unions_to_type_alias(source)
    namespace = {"Annotated": Annotated, "TypeAlias": TypeAlias, "Field": Field}
    exec(cleaned, namespace)
    adapter = TypeAdapter(namespace["Constrained"])
    assert adapter.validate_python(valid) == valid
    with pytest.raises(ValidationError):
        adapter.validate_python(invalid)


def test_unconstrained_union_keeps_plain_alias():
    source = """class Result(RootModel[A | B]):
    root: A | B = Field(..., description="Execution result")
"""
    assert cleaner.fix_root_model_unions_to_type_alias(source) == "Result: TypeAlias = A | B"


def test_final_root_collection_keeps_recursive_rebuild_and_length_constraints():
    source = """from __future__ import annotations

class Result(BaseModel):
    children: Results | None = None


class Results(RootModel[list[Result]]):
    root: list[Result] = Field(min_length=1, max_length=2)


Result.model_rebuild(_types_namespace=globals())
"""
    cleaned = cleaner.fix_root_model_unions_to_type_alias(source)
    namespace = {"BaseModel": BaseModel, "Annotated": Annotated, "Field": Field, "TypeAlias": TypeAlias}
    exec(cleaned, namespace)
    assert namespace["Result"].__pydantic_complete__
    adapter = TypeAdapter(namespace["Results"])
    assert adapter.validate_python([{"children": [{}]}])[0].children[0].children is None
    for invalid in ([], [{}, {}, {}]):
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)
