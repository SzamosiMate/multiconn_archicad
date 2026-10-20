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
