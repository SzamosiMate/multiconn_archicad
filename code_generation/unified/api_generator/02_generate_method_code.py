import argparse
import inspect
import json
import sys
import textwrap
from types import UnionType
from typing import Any, get_args, get_origin, Union, Annotated

from code_generation.shared.utils import camel_to_snake

from multiconn_archicad.models.official import commands as official_commands
from multiconn_archicad.models.official import types as official_types
from multiconn_archicad.models.tapir import commands as tapir_commands
from multiconn_archicad.models.tapir import types as tapir_types


# --- Data Structures for Model Lookups ---

MODEL_MODULES = {
    "tapir": {"commands": tapir_commands, "types": tapir_types},
    "official": {"commands": official_commands, "types": official_types},
}

# --- Helper Functions (get_model_class, get_clean_type_hint are unchanged) ---


def get_model_class(model_name: str, source: str, dependencies: dict) -> Any | None:
    try:
        model = getattr(MODEL_MODULES[source]["commands"], model_name)
        dependencies["commands"].add(model_name)
        return model
    except AttributeError:
        return None


def get_clean_type_hint(annotation: Any, dependencies: dict) -> str:
    if annotation is type(None):
        return "None"
    origin = get_origin(annotation)
    if origin:
        args = get_args(annotation)
        if origin is Annotated:
            return get_clean_type_hint(args[0], dependencies)
        if origin is UnionType or origin is Union:
            return " | ".join(get_clean_type_hint(arg, dependencies) for arg in args)
        origin_name = getattr(origin, "__name__", str(origin))
        if not args:
            return origin_name
        arg_hints = ", ".join(get_clean_type_hint(arg, dependencies) for arg in args)
        return f"{origin_name}[{arg_hints}]"
    hint = getattr(annotation, "__name__", str(annotation))
    module_name = getattr(annotation, "__module__", "")
    if "multiconn_archicad.models" in module_name:
        if ".types" in module_name:
            dependencies["types"].add(hint)
        elif ".commands" in module_name:
            dependencies["commands"].add(hint)
    return hint


# --- Refactored Method Generation Logic ---


def _build_signature_and_docs(
    snake_name: str, params_model: Any, result_model: Any, dependencies: dict
) -> tuple[str, list[str], str]:
    signature_parts, param_docs = ["self"], []
    if params_model:
        sig = inspect.signature(params_model)
        required_params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
        optional_params = [p for p in sig.parameters.values() if p.default is not inspect.Parameter.empty]
        for param in required_params + optional_params:
            param_name = camel_to_snake(param.name)
            type_hint = get_clean_type_hint(param.annotation, dependencies)
            signature_parts.append(
                f"{param_name}: {type_hint}"
                if param.default is inspect.Parameter.empty
                else f"{param_name}: {type_hint} = {repr(param.default)}"
            )
            doc_line = f"{param_name} ({type_hint})"
            field_info = params_model.model_fields.get(param.name)
            if field_info:
                if field_info.description:
                    doc_line += f": {field_info.description}"
                constraints = []
                if field_info.metadata:
                    for meta_item in field_info.metadata:
                        min_len = getattr(meta_item, "min_length", None)
                        if min_len is not None:
                            constraints.append(f"min_length={min_len}")
                        max_len = getattr(meta_item, "max_length", None)
                        if max_len is not None:
                            constraints.append(f"max_length={max_len}")
                if constraints:
                    doc_line += f" (Constraints: {', '.join(sorted(list(set(constraints))))})"
            param_docs.append(doc_line)

    return_type_hint = "None"
    if result_model:
        return_type_hint = get_clean_type_hint(result_model, dependencies)

    signature = f"def {snake_name}(\n    {',\n    '.join(signature_parts)}\n) -> {return_type_hint}:"
    return signature, param_docs, return_type_hint


def _build_docstring(description: str, param_docs: list[str]) -> str:
    """Assembles the full method docstring, now including a 'Raises' section."""
    docstring = f'"""\n{textwrap.fill(description, width=88)}\n'
    if param_docs:
        docstring += "\nArgs:\n"
        for doc in param_docs:
            wrapped_doc = textwrap.fill(doc, width=88, initial_indent="    ", subsequent_indent=" " * 8)
            docstring += f"{wrapped_doc}\n"

    docstring += "\nRaises:\n"
    docstring += "    ArchicadAPIError: If the API returns an error response.\n"
    docstring += "    RequestError: If there is a network or connection error.\n"

    docstring += '"""'
    return docstring


def _build_body(original_command_name: str, source: str, params_model: Any, return_type_hint: str) -> str:
    """Constructs the implementation body of the method."""
    core_call_method = "post_tapir_command" if source == "tapir" else "post_command"
    body_lines = []

    params_creation_lines = []
    if params_model:
        params_map_lines = ["{"]
        for param in inspect.signature(params_model).parameters.values():
            params_map_lines.append(f"    '{param.name}': {camel_to_snake(param.name)},")
        params_map_lines.append("}")
        params_map = "\n    ".join(params_map_lines)
        params_creation_lines.extend(
            [
                f"params_dict = {params_map}",
                f"validated_params = {params_model.__name__}(**params_dict)",
            ]
        )

    body_lines.extend(params_creation_lines)

    # Build the core API call expression
    call_args = [f'"{original_command_name}"']
    if params_model:
        call_args.append("validated_params.model_dump(by_alias=True, exclude_none=True)")

    call_expression = f"self._core.{core_call_method}(\n    {',\n    '.join(call_args)}\n)"

    if return_type_hint == "None":
        # If we expect no data back, don't assign the result.
        body_lines.append(call_expression)
        body_lines.append("return None")
    else:
        # If we expect data, assign it and then parse it.
        body_lines.append(f"response_dict = {call_expression}")
        body_lines.append(f"return {return_type_hint}.model_validate(response_dict)")

    return "\n".join(body_lines)


def generate_method_code(command_details: dict[str, Any]) -> dict:
    """Orchestrates generation and returns code and dependencies."""
    # This function now correctly handles commands that have no specific result model
    # by checking the 'result_model_name' from the details JSON.
    dependencies = {"commands": set(), "types": set()}
    original_cmd_name = command_details["name"]
    source = command_details["source"]
    command_name = original_cmd_name.removeprefix("API.") if source == "official" else original_cmd_name
    snake_name = camel_to_snake(command_name)
    params_model = get_model_class(f"{command_name}Parameters", source, dependencies)

    # Check if a result model exists. If not, the command returns None.
    result_model = get_model_class(f"{command_name}Result", source, dependencies)

    signature, param_docs, return_type = _build_signature_and_docs(snake_name, params_model, result_model, dependencies)
    docstring = _build_docstring(command_details["description"], param_docs)
    body = _build_body(original_cmd_name, source, params_model, return_type)

    return {
        "method_code": f"{signature}\n{textwrap.indent(docstring, '    ')}\n{textwrap.indent(body, '    ')}",
        "command_model_dependencies": sorted(list(dependencies["commands"])),
        "type_model_dependencies": sorted(list(dependencies["types"])),
    }


def main():
    parser = argparse.ArgumentParser(description="Stage 2: Generate method code strings for API commands.")
    parser.add_argument("--input-file", required=True, help="Path to the organized commands JSON from Stage 1.")
    parser.add_argument("--output-file", required=True, help="Path to save JSON with the new 'method_code' field.")
    args = parser.parse_args()

    print(f"Reading organized command data from: {args.input_file}")
    with open(args.input_file, "r", encoding="utf-8") as f:
        organized_commands = json.load(f)

    print("Generating method code and tracking dependencies for each command...")
    total_commands = 0
    for source, groups in organized_commands.items():
        for commands in groups.values():
            for command in commands:
                total_commands += 1
                try:
                    generated_data = generate_method_code(command)
                    command.update(generated_data)
                except Exception as e:
                    print(
                        f"❌ FATAL: Failed to generate code for command '{command['name']}'. Error: {e}",
                        file=sys.stderr,
                    )
                    raise
    print(f"✅ Successfully generated code for {total_commands} commands.")
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(organized_commands, f, indent=2)
    print(f"Enriched command data saved to: {args.output_file}")


if __name__ == "__main__":
    main()
