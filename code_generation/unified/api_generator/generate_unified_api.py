import json
import inspect
import pathlib
import sys
import textwrap
from typing import Any, Dict, get_origin, get_args
from types import UnionType

from code_generation.tapir.paths import tapir_paths
from code_generation.official.paths import official_paths
from code_generation.shared.utils import camel_to_snake

from multiconn_archicad.models.tapir import commands as tapir_commands
from multiconn_archicad.models.tapir import types as tapir_types
from multiconn_archicad.models.official import commands as official_commands
from multiconn_archicad.models.official import types as official_types

# --- Path Setup ---
PROJECT_ROOT = tapir_paths.PROJECT_ROOT
OUTPUT_DIR = PROJECT_ROOT / "src" / "multiconn_archicad" / "unified_api"
OUTPUT_FILE = OUTPUT_DIR / "api.py"

MODEL_MODULES = {
    "tapir": {"commands": tapir_commands, "types": tapir_types},
    "official": {"commands": official_commands, "types": official_types},
}


def get_model_class(model_name: str, source: str) -> Any | None:
    """Safely retrieves a model class from the imported modules by its name."""
    try:
        return getattr(MODEL_MODULES[source]["commands"], model_name)
    except AttributeError:
        return None


def get_clean_type_hint(annotation: Any) -> str:
    """
    Recursively builds a clean, readable type hint string, using the '|'
    operator and 'None' for optional types, optimized for Python 3.12+.
    """
    if annotation is type(None):
        return "None"

    origin = get_origin(annotation)
    if origin:
        args = get_args(annotation)
        if origin is UnionType:
            return " | ".join(get_clean_type_hint(arg) for arg in args)

        origin_name = getattr(origin, "__name__", str(origin))
        if not args:
            return origin_name
        arg_hints = ", ".join(get_clean_type_hint(arg) for arg in args)
        hint = f"{origin_name}[{arg_hints}]"
    else:
        hint = getattr(annotation, "__name__", str(annotation))

    hint = hint.replace("multiconn_archicad.models.tapir.types", "tapir_types")
    hint = hint.replace("multiconn_archicad.models.official.types", "official_types")
    return hint


def generate_method_string(command_details: Dict[str, Any]) -> str:
    """Generates the complete Python method string for a single command."""
    original_command_name = command_details["name"]
    source = command_details["source"]

    command_name = original_command_name
    if source == "official" and original_command_name.startswith("API."):
        command_name = original_command_name.removeprefix("API.")

    snake_name = camel_to_snake(command_name)
    params_model = get_model_class(f"{command_name}Parameters", source)
    result_model = get_model_class(f"{command_name}Result", source)

    required_params = []
    optional_params = []
    if params_model:
        sig = inspect.signature(params_model)
        for param in sig.parameters.values():
            if param.default is inspect.Parameter.empty:
                required_params.append(param)
            else:
                optional_params.append(param)

    sorted_params = required_params + optional_params

    signature_parts = ["self"]
    param_docs = []
    for param in sorted_params:
        param_name = camel_to_snake(param.name)
        type_hint = get_clean_type_hint(param.annotation)

        if param.default is inspect.Parameter.empty:
            signature_parts.append(f"{param_name}: {type_hint}")
        else:
            signature_parts.append(f"{param_name}: {type_hint} = {repr(param.default)}")

        doc_line = f"{param_name} ({type_hint})"
        field_info = params_model.model_fields.get(param.name)
        if field_info and field_info.description:
            doc_line += f": {field_info.description}"
        param_docs.append(doc_line)

    return_type_hint = "None"
    if result_model:
        return_type_hint = f"{source}_commands.{result_model.__name__}"

    signature = f"    def {snake_name}(\n        {',\n        '.join(signature_parts)}\n    ) -> {return_type_hint}:"

    docstring = f'"""\n        {command_details["description"]}\n'
    if param_docs:
        docstring += "\n        Args:\n"
        for doc in param_docs:
            wrapped_doc = textwrap.fill(doc, width=100, initial_indent=" " * 12, subsequent_indent=" " * 16)
            docstring += f"{wrapped_doc.lstrip()}\n"

    # FIX: The "Returns" section is now completely removed. The docstring is always closed here.
    docstring += '        """'

    core_call_method = "post_tapir_command" if source == "tapir" else "post_command"
    api_command_name = original_command_name

    body_lines = []
    if params_model:
        params_map = "{\n"
        for param in inspect.signature(params_model).parameters.values():
            params_map += f"            '{param.name}': {camel_to_snake(param.name)},\n"
        params_map += "        }"
        body_lines.append(f"params_dict = {params_map}")
        body_lines.append(f"validated_params = {source}_commands.{params_model.__name__}(**params_dict)")
        body_lines.append(f"response_dict = self._core.{core_call_method}(")
        body_lines.append(f'    "{api_command_name}",')
        body_lines.append(f"    validated_params.model_dump(by_alias=True, exclude_none=True)")
        body_lines.append(f")")
    else:
        body_lines.append(f'response_dict = self._core.{core_call_method}("{api_command_name}")')

    if result_model:
        body_lines.append(f"return {return_type_hint}.model_validate(response_dict)")
    else:
        body_lines.append("return None")

    body = textwrap.indent("\n".join(body_lines), " " * 8)

    return f"{signature}\n{textwrap.indent(docstring, ' ' * 8)}\n{body}\n"


def generate_api_file():
    """Main function to generate the complete unified_api.py file."""
    print("--- Starting Unified API Generation ---")

    try:
        with open(tapir_paths.COMMAND_DETAILS_OUTPUT, "r", encoding="utf-8") as f:
            tapir_details = json.load(f)
            for cmd in tapir_details:
                cmd["source"] = "tapir"
        print(f"✅ Loaded {len(tapir_details)} Tapir command details.")

        official_details = []
        if official_paths.COMMAND_DETAILS_OUTPUT.exists():
            with open(official_paths.COMMAND_DETAILS_OUTPUT, "r", encoding="utf-8") as f:
                official_details = json.load(f)
                for cmd in official_details:
                    cmd["source"] = "official"
            print(f"✅ Loaded {len(official_details)} Official API command details.")

    except FileNotFoundError as e:
        print(
            f"❌ Error: Command details JSON not found. Please run model generation pipelines first.", file=sys.stderr
        )
        sys.exit(1)

    all_commands = sorted(tapir_details + official_details, key=lambda x: camel_to_snake(x["name"]))

    file_header = textwrap.dedent("""
        # This file is automatically generated by the pipeline. Do not edit directly.
        # It contains a unified, high-level, object-oriented interface for the APIs.

        from __future__ import annotations
        from typing import Any, TYPE_CHECKING

        from multiconn_archicad.models.tapir import commands as tapir_commands
        from multiconn_archicad.models.tapir import types as tapir_types
        from multiconn_archicad.models.official import commands as official_commands
        from multiconn_archicad.models.official import types as official_types

        if TYPE_CHECKING:
            from multiconn_archicad.core.core_commands import CoreCommands


        class UnifiedApi:
            \"\"\"
            A unified, high-level, object-oriented interface for both the Tapir
            and Official Archicad JSON APIs. This class provides type-safe, pythonic
            methods that handle data validation and parsing automatically.
            \"\"\"
            def __init__(self, core: CoreCommands):
                self._core = core
    """).strip()

    file_content = [file_header]
    print(f"\n⚙️  Generating methods for the UnifiedApi class...")

    generated_methods = set()
    for command in all_commands:
        snake_name = camel_to_snake(command["name"].removeprefix("API."))
        if snake_name in generated_methods:
            print(f"⚠️  Skipping duplicate method '{snake_name}' from source '{command['source']}'.")
            continue

        try:
            method_str = generate_method_string(command)
            file_content.append(method_str)
            generated_methods.add(snake_name)
        except Exception as e:
            print(f"❌  Failed to generate method for '{command['name']}': {e}", file=sys.stderr)

    print(f"✅ Generated {len(generated_methods)} unique methods.")
    final_code = "\n".join(file_content)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "__init__.py").touch()
    OUTPUT_FILE.write_text(final_code, encoding="utf-8")
    print(f"\n✅ Successfully generated Unified API file at: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_api_file()