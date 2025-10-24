# filename: api_generator/05_generate_command_tests.py

import argparse
import copy
import json
import pathlib
import re
import sys
import textwrap
from typing import Any, Dict, Set

from code_generation.shared.utils import camel_to_snake
from code_generation.tapir.paths import tapir_paths
from code_generation.official.paths import official_paths

KNOWN_RECURSIVE_SCHEMAS = {
    "tapir": {"GetHotlinksResult"},
    "official": {
        "GetNavigatorItemTreeResult",
        "GetAllClassificationsInSystemResult",
        "GetAttributeFolderStructureResult",
    },
}


def patch_recursive_schemas(definitions: dict, model_name_to_test: str, source: str) -> dict:
    patched_defs = copy.deepcopy(definitions)
    if source == "tapir" and model_name_to_test == "GetHotlinksResult":
        if "Hotlink" in patched_defs and "properties" in patched_defs["Hotlink"]:
            patched_defs["Hotlink"]["properties"].pop("children", None)
    if source == "official":
        if model_name_to_test == "GetNavigatorItemTreeResult":
            if "NavigatorItem" in patched_defs and "properties" in patched_defs["NavigatorItem"]:
                patched_defs["NavigatorItem"]["properties"].pop("children", None)
        elif model_name_to_test == "GetAllClassificationsInSystemResult":
            if "ClassificationItemInTree" in patched_defs and "properties" in patched_defs["ClassificationItemInTree"]:
                patched_defs["ClassificationItemInTree"]["properties"].pop("children", None)
        elif model_name_to_test == "GetAttributeFolderStructureResult":
            if "AttributeFolderStructure" in patched_defs and "properties" in patched_defs["AttributeFolderStructure"]:
                patched_defs["AttributeFolderStructure"]["properties"].pop("subfolders", None)
    return patched_defs


def collect_dependencies_recursively(
    name: str, all_definitions: Dict[str, Any], collected_defs: Dict[str, Any], processed: Set[str]
):
    if name in processed:
        return
    processed.add(name)
    if name not in all_definitions:
        return
    definition = all_definitions[name]
    collected_defs[name] = definition
    content_str = json.dumps(definition)
    dependencies = re.findall(r'"#/\$defs/(\w+)"', content_str)
    for dep_name in set(dependencies):
        collect_dependencies_recursively(dep_name, all_definitions, collected_defs, processed)


class TestGenerator:
    def __init__(self, commands_with_code: dict, output_dir: pathlib.Path):
        self._commands_data = commands_with_code
        self._output_dir = output_dir
        self._master_schemas = {}
        self._generated_tests = {"tapir": [], "official": []}
        self._class_imports = {"tapir": set(), "official": set()}

    def generate(self):
        print("--- Starting Unified API Method Test Generation (Stage 5) ---")
        self._load_master_schemas()
        for source, groups in self._commands_data.items():
            for group_name, commands in groups.items():
                for command in commands:
                    try:
                        test_code = self._generate_test_for_command(command)
                        self._generated_tests[source].append(test_code)
                    except Exception as e:
                        print(
                            f"❌ FATAL: Could not generate test for command '{command['name']}'. Error: {e}",
                            file=sys.stderr,
                        )
                        raise
        self._write_test_files()
        print("✅✅✅ Method test generation finished successfully! ✅✅✅")

    def _load_master_schemas(self):
        try:
            with open(tapir_paths.MASTER_SCHEMA_OUTPUT, "r", encoding="utf-8") as f:
                self._master_schemas["tapir"] = json.load(f)
            with open(official_paths.MASTER_SCHEMA_OUTPUT, "r", encoding="utf-8") as f:
                self._master_schemas["official"] = json.load(f)
        except FileNotFoundError as e:
            print(f"❌ Error: Master schema not found at {e.filename}. Run model generation first.", file=sys.stderr)
            sys.exit(1)

    def _get_minimal_schema_for_model(self, model_name: str, source: str) -> str:
        master_schema = self._master_schemas[source]
        all_definitions = master_schema.get("$defs", {})
        if model_name in KNOWN_RECURSIVE_SCHEMAS.get(source, set()):
            all_definitions = patch_recursive_schemas(all_definitions, model_name, source)
        minimal_definitions = {}
        collect_dependencies_recursively(model_name, all_definitions, minimal_definitions, set())
        if not minimal_definitions:
            return "None"
        temp_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$defs": minimal_definitions,
            "$ref": f"#/$defs/{model_name}",
        }
        return repr(json.dumps(temp_schema, separators=(",", ":")))

    def _generate_test_for_command(self, command_details: dict) -> str:
        source = command_details["source"]
        cmd_name = command_details["name"]
        deps = command_details.get("command_model_dependencies", [])
        params_model_name = next((d for d in deps if d.endswith("Parameters")), None)
        result_model_name = next((d for d in deps if d.endswith("Result")), None)
        snake_name = camel_to_snake(cmd_name.removeprefix("API.") if source == "official" else cmd_name)

        given_params, given_args = [], []
        if params_model_name:
            params_schema_str = self._get_minimal_schema_for_model(params_model_name, source)
            if params_schema_str != "None":
                given_params.append(f"input_data=from_schema(json.loads({params_schema_str}))")
                given_args.append("input_data: dict")
        if result_model_name:
            result_schema_str = self._get_minimal_schema_for_model(result_model_name, source)
            if result_schema_str != "None":
                given_params.append(f"mock_response=from_schema(json.loads({result_schema_str}))")
                given_args.append("mock_response: dict")

        decorators = f"@given({', '.join(given_params)})" if given_params else ""
        full_signature = f"def test_{snake_name}_logic({', '.join(given_args)}):"
        class_name, aliased_class_name = self._get_class_names(command_details["group"], source)
        self._class_imports[source].add(
            (self._get_module_name(command_details["group"]), class_name, aliased_class_name)
        )

        has_params = "input_data: dict" in given_args
        has_result = "mock_response: dict" in given_args
        core_method = "post_tapir_command" if source == "tapir" else "post_command"
        alias_prop = command_details.get("alias_property_name")

        body_lines = ["# 1. ARRANGE"]
        body_lines.append(f"command_group = {aliased_class_name}(core=MagicMock())")
        if has_result:
            body_lines.append(f"command_group._core.{core_method}.return_value = mock_response")
        else:
            body_lines.append(f"command_group._core.{core_method}.return_value = {{'success': True}}")

        body_lines.append("\n# 2. ACT")
        body_lines.append(
            "kwargs = {camel_to_snake(k): v for k, v in input_data.items()}" if has_params else "kwargs = {}"
        )
        if snake_name == "rename_navigator_item":
            body_lines.append(
                "if not kwargs.get('new_name') and not kwargs.get('new_id'): kwargs['new_name'] = 'default_name'"
            )
        body_lines.append(f"result = command_group.{snake_name}(**kwargs)")

        body_lines.append("\n# 3. ASSERT")
        if not has_params:
            body_lines.append(f"command_group._core.{core_method}.assert_called_once_with('{cmd_name}')")
        else:
            body_lines.append(f"command_group._core.{core_method}.assert_called_once()")
            body_lines.append(f"args, _ = command_group._core.{core_method}.call_args")
            body_lines.append(f"assert args[0] == '{cmd_name}'")
            if snake_name != "rename_navigator_item":
                body_lines.append("assert set(args[1].keys()) == set(input_data.keys())")

        if has_result:
            if alias_prop:
                # Use the utility function for clean, robust comparison
                body_lines.append(f"assert normalize_for_comparison(result) == mock_response['{alias_prop}']")
            else:
                # Compare model object to model object
                body_lines.append(f"assert result == commands.{result_model_name}.model_validate(mock_response)")
        else:
            body_lines.append("assert result is None")

        unindented_body = "\n".join(body_lines)
        indented_body = textwrap.indent(unindented_body, "    ")
        return f"{decorators}\n{full_signature}\n{indented_body}"

    def _get_module_name(self, group_name: str) -> str:
        name = group_name.lower().replace(" commands", "").strip()
        name = "".join(c if c.isalnum() else "_" for c in name)
        return "_".join(filter(None, name.split("_")))

    def _get_class_names(self, group_name: str, source: str) -> tuple[str, str]:
        clean_name = self._get_module_name(group_name)
        class_name = f"{clean_name.replace('_', ' ').title().replace(' ', '')}Commands"
        aliased_class_name = f"{source.capitalize()}{class_name}"
        return class_name, aliased_class_name

    def _write_test_files(self):
        self._output_dir.mkdir(exist_ok=True, parents=True)
        print(f"\nWriting generated test files to: {self._output_dir}")
        for source in ["tapir", "official"]:
            if not self._generated_tests[source]:
                continue
            import_block = "\n                ".join(
                f"from multiconn_archicad.unified_api.{source}.{module} import {class_name} as {alias}"
                for module, class_name, alias in sorted(self._class_imports[source])
            )
            header = textwrap.dedent(f"""
                # This file is automatically generated by the pipeline. Do not edit directly.
                # Unit tests for all Unified API methods of the '{source}' source.
                import os
                import json
                from enum import Enum
                from unittest.mock import MagicMock
                import pytest
                from pydantic import BaseModel
                from hypothesis import given, settings, HealthCheck
                from hypothesis_jsonschema import from_schema
                from code_generation.shared.utils import camel_to_snake
                from tests.utilities import normalize_for_comparison
                {import_block}
                from multiconn_archicad.models.{source} import commands, types
                NUM_EXAMPLES = int(os.getenv("HYPOTHESIS_NUM_EXAMPLES", 1))
                settings.register_profile("ci", max_examples=NUM_EXAMPLES, suppress_health_check=[HealthCheck.too_slow], deadline=None)
                settings.load_profile("ci")
                pytestmark = pytest.mark.generated_methods
            """)
            all_tests = "\n\n\n".join(sorted(self._generated_tests[source]))
            file_content = header + "\n\n" + all_tests
            output_path = self._output_dir / f"test_generated_{source}_methods.py"
            output_path.write_text(file_content, encoding="utf-8")
            print(f"  - Wrote {len(self._generated_tests[source])} tests to {output_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Stage 5: Generate unit tests for Unified API methods.")
    parser.add_argument(
        "--input-file",
        required=True,
        type=pathlib.Path,
        help="Path to commands JSON with generated code (from Stage 2).",
    )
    parser.add_argument(
        "--output-dir", required=True, type=pathlib.Path, help="Output directory for the generated test files."
    )
    args = parser.parse_args()
    if not args.input_file.is_file():
        print(f"❌ FATAL: Input file not found at: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    with open(args.input_file, "r", encoding="utf-8") as f:
        commands_with_code = json.load(f)
    generator = TestGenerator(commands_with_code, args.output_dir)
    generator.generate()


if __name__ == "__main__":
    main()
