import importlib

import pytest

cleaner = importlib.import_module("code_generation.tapir.model_generators.03_model_cleaner")
pytestmark = pytest.mark.unit


@pytest.mark.parametrize("union_key", ["oneOf", "anyOf"])
def test_named_object_unions_are_restored_without_losing_sibling_constraints(tmp_path, monkeypatch, union_key):
    import json

    schema = {
        "$defs": {
            "A": {"type": "object"},
            "B": {"type": "object"},
            "Named": {
                "type": "object",
                "description": "Objects",
                union_key: [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
            },
            "Restricted": {
                "type": "object",
                "minProperties": 1,
                union_key: [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
            },
            "Number": {"type": "number"},
            "Mixed": {"type": "object", union_key: [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/Number"}]},
        }
    }
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(schema))
    monkeypatch.setattr(cleaner.tapir_paths, "MASTER_SCHEMA_OUTPUT", path)
    source = "class A: pass\nclass B: pass\n"
    result = cleaner.restore_collapsed_named_unions(source)
    assert "Named: TypeAlias = A | B" in result
    assert "Restricted: TypeAlias" not in result
    assert "Mixed: TypeAlias" not in result

    assert cleaner.restore_collapsed_named_unions(result) == result


def test_mixed_primitive_and_object_union_is_restored_without_weakening_constraints(tmp_path, monkeypatch):
    import json

    from pydantic import BaseModel, TypeAdapter, ValidationError
    from typing import TypeAlias

    schema = {
        "$defs": {
            "OptionalValue": {"type": "object"},
            "FieldValue": {
                "anyOf": [{"type": ["number", "integer", "boolean", "string"]}, {"$ref": "#/$defs/OptionalValue"}]
            },
            "Constrained": {"anyOf": [{"type": "number", "minimum": 1}, {"$ref": "#/$defs/OptionalValue"}]},
        }
    }
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(schema))
    monkeypatch.setattr(cleaner.tapir_paths, "MASTER_SCHEMA_OUTPUT", path)
    source = "class OptionalValue(BaseModel):\n    hasValue: bool\n"
    result = cleaner.restore_collapsed_named_unions(source)
    assert "FieldValue: TypeAlias = float | int | bool | str | OptionalValue" in result
    assert "Constrained: TypeAlias" not in result
    namespace = {"BaseModel": BaseModel, "TypeAlias": TypeAlias}
    exec(result, namespace)
    adapter = TypeAdapter(namespace["FieldValue"])
    for value in [1.5, 2, True, "text"]:
        assert type(adapter.validate_python(value)) is type(value)
    assert adapter.validate_python({"hasValue": False}).hasValue is False
    with pytest.raises(ValidationError):
        adapter.validate_python([1])
