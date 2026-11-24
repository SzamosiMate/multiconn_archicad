import importlib
import ast
import json

import pytest
from typeguard import TypeCheckError, check_type

pytestmark = pytest.mark.unit


def test_open_functional_typed_dict_names_are_audited():
    from code_generation.tapir import generation_audit

    tree = ast.parse('Unstable1 = OpenTypedDict("Unstable1", {"value": str}, extra_items=Any)')
    findings = generation_audit.audit_generated_names({generation_audit.tapir_paths.FINAL_TYPED_DICT_TYPES: tree})
    assert any(finding.rule == "unstable-generated-name" for finding in findings)


def test_integrity_collection_includes_backported_typed_dicts():
    from multiconn_archicad.dicts.tapir.types import ModelViewOptions, StairOutlineNotWritable
    from tests.generated.test_model_integrity import _collect_typed_dicts

    collected = {cls for _, cls in _collect_typed_dicts()}
    assert {ModelViewOptions, StairOutlineNotWritable} <= collected


@pytest.mark.parametrize("functional", [False, True])
def test_open_typed_dicts_accept_extras_and_validate_declared_fields_after_split(tmp_path, monkeypatch, functional):
    cleaner = importlib.import_module("code_generation.tapir.model_generators.06_typed_dict_cleaner")
    splitter = importlib.import_module("code_generation.tapir.model_generators.07_split_typed_dicts")
    path = tmp_path / "schema.json"
    path.write_text(
        json.dumps(
            {
                "$defs": {
                    "Open": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "additionalProperties": True,
                    },
                    "Closed": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "additionalProperties": False,
                    },
                    "Empty": {"type": "object"},
                }
            }
        )
    )
    monkeypatch.setattr(cleaner.tapir_paths, "MASTER_SCHEMA_OUTPUT", path)
    declaration = (
        'Open = TypedDict("Open", {"name": str})\n' if functional else "class Open(TypedDict):\n    name: str\n"
    )
    source = declaration + "class Closed(TypedDict):\n    name: str\nclass Empty(TypedDict):\n    pass\n"
    body = cleaner.preserve_open_typed_dicts(source)
    cleaned = cleaner.assemble_final_file(body)
    split = splitter.remove_unused_imports("\n".join(splitter.get_header_lines()) + "\n\n" + body)
    for output in (cleaned, split):
        namespace = {}
        exec(output, namespace)
        check_type({"name": "valid", "custom": [1, {"key": True}]}, namespace["Open"])
        check_type({"custom": 1}, namespace["Empty"])
        with pytest.raises(TypeCheckError):
            check_type({"name": 1}, namespace["Open"])
        with pytest.raises(TypeCheckError):
            check_type({"custom": 1}, namespace["Open"])
        with pytest.raises(TypeCheckError):
            check_type({"name": "valid", "custom": 1}, namespace["Closed"])


def test_unconstrained_empty_pydantic_objects_preserve_data(tmp_path, monkeypatch):
    cleaner = importlib.import_module("code_generation.tapir.model_generators.03_model_cleaner")
    path = tmp_path / "schema.json"
    path.write_text(
        json.dumps(
            {
                "$defs": {
                    "Open": {"type": "object"},
                    "Closed": {"type": "object", "additionalProperties": False},
                }
            }
        )
    )
    monkeypatch.setattr(cleaner.tapir_paths, "MASTER_SCHEMA_OUTPUT", path)
    source = "class Open(APIModel):\n    pass\n\nclass Closed(APIModel):\n    pass\n"
    cleaned = cleaner.assemble_final_file(cleaner.restore_open_object_configs(source))
    namespace = {}
    exec(cleaned, namespace)
    data = {"outline": [{"x": 1.0}], "name": "boundary"}
    assert namespace["Open"].model_validate(data).model_dump() == data
    assert namespace["Closed"].model_validate(data).model_dump() == {}
