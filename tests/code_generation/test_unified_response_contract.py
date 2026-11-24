"""Unified returns describe post-core responses, while models retain the wire contract."""

import ast
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
from typing import get_args
from unittest.mock import MagicMock

from jsonschema import Draft7Validator
from pydantic import TypeAdapter, ValidationError
import pytest

from code_generation.shared.utils import camel_to_snake
from code_generation.tapir.paths import tapir_paths
from code_generation.unified.api_generator.response_contract import reachable_response_schema, reachable_response_type
from code_generation.unified.api_generator.shipped_signatures import load_shipped_signatures
from multiconn_archicad.clients.core.core_commands import CoreCommands
from multiconn_archicad.errors import TapirCommandError
from multiconn_archicad.models.tapir import commands, types


generator = import_module("code_generation.unified.api_generator.02_generate_method_code")
test_generator = import_module("code_generation.unified.api_generator.05_generate_command_tests")


def generate(command_name):
    return generator.generate_method_code(
        {"name": command_name, "source": "tapir", "description": "Example command."},
        load_shipped_signatures()["tapir"].get(command_name),
    )


def build_method(generated):
    namespace = {**vars(types), **vars(commands), "TypeAdapter": TypeAdapter}
    exec(generated["method_code"], namespace)
    return namespace[ast.parse(generated["method_code"]).body[0].name]


@pytest.mark.parametrize(
    "command_name, expected",
    [
        ("CloseProject", "SuccessfulExecutionResult"),
        ("ShowScriptUI", "ScriptUIShown"),
        ("GetAllElements", "ElementsWithExecutionResults"),
        ("GetAttributesByType", "AttributeHeadersWrapper"),
        ("GetZoneBoundaries", "ZoneBoundariesOfZonesWrapper | ZoneBoundariesWrapper"),
        ("DeleteSelectedElements", "SuccessfulExecutionResult"),
    ],
)
def test_generator_narrows_root_errors_and_validates_reachable_types(command_name, expected):
    generated = generate(command_name)
    method = ast.parse(generated["method_code"]).body[0]
    assert ast.unparse(method.returns) == expected
    assert expected in ast.get_docstring(method)
    assert "ErrorItem" not in generated["type_model_dependencies"]
    assert "FailedExecutionResult" not in generated["type_model_dependencies"]
    assert generated["result_model_name"] == f"{command_name}Result"
    assert f"TypeAdapter({expected})" in generated["method_code"]


@pytest.mark.parametrize(
    "payload",
    [{"error": {"code": 7, "message": "Failure"}}, {"success": False, "error": {"code": 7, "message": "Failure"}}],
)
def test_generated_method_propagates_real_core_errors(payload):
    core = CoreCommands.__new__(CoreCommands)
    core._post_command = MagicMock(return_value={"succeeded": True, "result": {"addOnCommandResponse": payload}})
    with pytest.raises(TapirCommandError) as caught:
        build_method(generate("CloseProject"))(SimpleNamespace(_core=core))
    assert caught.value.code == 7
    assert caught.value.message == "Failure"


def test_narrowed_validation_rejects_unreachable_failed_execution_from_mock_core():
    core = MagicMock()
    core.post_tapir_command.return_value = {"success": False, "error": {"code": 7, "message": "Failure"}}
    with pytest.raises(ValidationError):
        build_method(generate("CloseProject"))(SimpleNamespace(_core=core))


def test_successful_wrapper_keeps_shape_and_nested_database_failures():
    core = MagicMock()
    core.post_tapir_command.return_value = {
        "elements": [],
        "executionResultForDatabases": [{"success": False, "error": {"code": 7, "message": "Failure"}}],
    }
    result = build_method(generate("GetAllElements"))(SimpleNamespace(_core=core))
    assert isinstance(result, types.ElementsWithExecutionResults)
    assert isinstance(result.executionResultForDatabases[0], types.FailedExecutionResult)

    core.post_tapir_command.return_value = {"attributes": []}
    result = build_method(generate("GetAttributesByType"))(SimpleNamespace(_core=core), attribute_type="Layer")
    assert isinstance(result, types.AttributeHeadersWrapper)


def test_legacy_scalar_and_batch_dry_run_contracts():
    scalar = generate("DeleteSelectedElements")
    assert ast.unparse(ast.parse(scalar["method_code"]).body[0].returns) == "SuccessfulExecutionResult"
    assert "DeleteSelectedElementsResult" in scalar["dry_run_companion"]["method_code"]
    batch = generate("SetPropertyValuesOfElements")
    assert ast.unparse(ast.parse(batch["method_code"]).body[0].returns) == generator.EXECUTION_RESULTS_RETURN
    core = MagicMock()
    core.post_tapir_command.return_value = {
        "executionResults": [{"success": False, "error": {"code": 7, "message": "Failure"}}]
    }
    result = build_method(batch)(SimpleNamespace(_core=core), element_property_values=[])
    assert isinstance(result[0], types.FailedExecutionResult)
    core.post_tapir_command.return_value = {"dryRun": True, "success": True, "wouldDelete": True, "elements": []}
    preview = build_method(scalar["dry_run_companion"])(SimpleNamespace(_core=core))
    assert isinstance(preview, commands.DeleteSelectedElementsResult)
    assert preview.wouldDelete


def test_dry_run_split_survives_a_shipped_snapshot_with_narrowed_scalar_returns():
    shipped = deepcopy(load_shipped_signatures()["tapir"]["DeleteSelectedElements"])
    shipped["delete_selected_elements"]["returns"] = "SuccessfulExecutionResult"
    generated = generator.generate_method_code(
        {"name": "DeleteSelectedElements", "source": "tapir", "description": "Delete selected elements."}, shipped
    )
    assert ast.unparse(ast.parse(generated["method_code"]).body[0].returns) == "SuccessfulExecutionResult"
    assert "DeleteSelectedElementsResult" in generated["dry_run_companion"]["method_code"]
    assert generated["dry_run"] is False
    assert generated["dry_run_companion"]["dry_run"] is True


def test_type_projection_leaves_official_and_nested_errors_unchanged():
    wire = types.SuccessfulExecutionResult | types.FailedExecutionResult
    assert reachable_response_type(wire, "official") is wire
    assert reachable_response_type(list[wire], "tapir") == list[wire]
    assert reachable_response_type(types.ElementsWithExecutionResults, "tapir") is types.ElementsWithExecutionResults
    assert types.ErrorItem in get_args(commands.GetAllElementsResult)
    assert types.FailedExecutionResult in get_args(commands.CloseProjectResult)


@pytest.fixture(scope="module")
def master_schema():
    return json.loads(tapir_paths.MASTER_SCHEMA_OUTPUT.read_text(encoding="utf-8"))


@pytest.mark.parametrize("command_name", ["GetAllElements", "CloseProject", "DeleteSelectedElements"])
def test_method_response_schemas_exclude_root_errors_without_mutating_wire_schema(
    master_schema, command_name, tmp_path
):
    original = deepcopy(master_schema)
    tests = test_generator.TestGenerator({}, tmp_path)
    tests._master_schemas["tapir"] = master_schema
    name = f"{command_name}Result"
    schema = json.loads(ast.literal_eval(tests._get_minimal_schema_for_model(name, "tapir", core_response=True)))
    validator = Draft7Validator(schema)
    assert validator.is_valid({"elements": []} if command_name == "GetAllElements" else {"success": True})
    assert not validator.is_valid({"error": {"code": 7, "message": "Failure"}, "success": False})
    assert master_schema == original

    # Stage 5 must still find wire models removed from generated runtime imports.
    details = {"name": command_name, "source": "tapir", "group": "Example Commands", **generate(command_name)}
    code = tests._generate_test_for_command(details)
    assert "mock_response: dict" in code
    assert f"test_{camel_to_snake(command_name)}_logic" in code


def test_response_schema_keeps_nested_error_variants(master_schema):
    definitions = master_schema["$defs"]
    wire = definitions["GetAllElementsResult"]
    projected = reachable_response_schema(wire, definitions, "tapir")
    validator = Draft7Validator({"$defs": definitions, **projected})
    assert validator.is_valid(
        {
            "elements": [],
            "executionResultForDatabases": [{"success": False, "error": {"code": 7, "message": "Failure"}}],
        }
    )
    assert reachable_response_schema(wire, definitions, "official") == wire


@pytest.mark.parametrize("input_data", [{}, {"method": "General"}, {"method": None}])
def test_generated_payload_expectation_applies_method_defaults(tmp_path, master_schema, input_data):
    from inspect import signature
    from multiconn_archicad.clients.unified_api.tapir.application import ApplicationCommands as TapirApplicationCommands

    tests = test_generator.TestGenerator({}, tmp_path)
    tests._master_schemas["tapir"] = master_schema
    details = {
        "name": "GetPolygonFromUser",
        "source": "tapir",
        "group": "Application Commands",
        **generate("GetPolygonFromUser"),
    }
    code = tests._generate_test_for_command(details)
    function = ast.parse(code).body[0]
    function.decorator_list.clear()
    namespace = {
        "TapirApplicationCommands": TapirApplicationCommands,
        "MagicMock": MagicMock,
        "camel_to_snake": camel_to_snake,
        "commands": commands,
        "signature": signature,
    }
    exec(ast.unparse(function), namespace)
    namespace[function.name](input_data, {"cancelled": False})
