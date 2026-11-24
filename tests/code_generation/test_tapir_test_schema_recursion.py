import ast
import importlib
import json

import pytest
from hypothesis import given, settings
from hypothesis_jsonschema import from_schema


@pytest.mark.parametrize("name", ["GetGraphicOverrideRulesResult", "GetGraphicOverrideRulesByNameResult"])
def test_shared_recursive_criterion_is_bounded_for_readback_consumers(tmp_path, monkeypatch, name):
    generator = importlib.import_module("code_generation.tapir.model_generators.08_generate_model_tests")
    criterion = {
        "type": "object",
        "properties": {
            "elementType": {"type": "string"},
            "and": {"type": "array", "items": {"$ref": "#/$defs/GraphicOverrideCriterion"}},
            "or": {"type": "array", "items": {"$ref": "#/$defs/GraphicOverrideCriterion"}},
        },
        "additionalProperties": False,
    }
    schema = {
        "$defs": {
            "GraphicOverrideCriterion": criterion,
            name: {"type": "object", "properties": {"criterion": {"$ref": "#/$defs/GraphicOverrideCriterion"}}},
        }
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema))
    names_path = tmp_path / "names.json"
    names_path.write_text(json.dumps([name]))
    output = tmp_path / "generated.py"
    monkeypatch.setattr(generator.tapir_paths, "MASTER_SCHEMA_OUTPUT", schema_path)
    monkeypatch.setattr(generator.tapir_paths, "COMMAND_MODELS_NAMES_OUTPUT", names_path)
    monkeypatch.setattr(generator.tapir_paths, "GENERATED_TESTS_OUTPUT", output)

    generator.main()
    function = next(node for node in ast.parse(output.read_text()).body if isinstance(node, ast.FunctionDef))
    strategy = function.decorator_list[-1].keywords[0].value
    generated = json.loads(ast.literal_eval(strategy.args[0]))
    definitions = generated["$defs"]
    assert definitions["GraphicOverrideCriterion"]["properties"]["and"]["items"] == {
        "$ref": "#/$defs/GraphicOverrideCriterionLeafForTests"
    }
    assert not {"and", "or"} & definitions["GraphicOverrideCriterionLeafForTests"]["properties"].keys()
    assert json.loads(schema_path.read_text()) == schema

    # Strategy construction is lazy: draw examples to prove recursion resolves.
    @settings(max_examples=3, deadline=None)
    @given(from_schema(generated))
    def draw_example(data):
        assert isinstance(data, dict)

    draw_example()
