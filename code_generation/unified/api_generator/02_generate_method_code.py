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


MODEL_MODULES = {
    "tapir": {"commands": tapir_commands, "types": tapir_types},
    "official": {"commands": official_commands, "types": official_types},
}


def main():
    """Main script entry point for Stage 2 of the pipeline."""
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


def generate_method_code(command_details: dict[str, Any]) -> dict:
    """
    Orchestrates the generation of a single API method, handling special cases
    and falling back to a standard generation process.
    """
    dependencies = {"commands": set(), "types": set()}
    original_cmd_name = command_details["name"]
    source = command_details["source"]
    command_name = original_cmd_name.removeprefix("API.") if source == "official" else original_cmd_name
    snake_name = camel_to_snake(command_name)

    if special_case_code := _handle_special_cases(command_name, command_details, dependencies):
        return special_case_code

    params_model = get_model_class(f"{command_name}Parameters", source, dependencies)
    result_model = get_model_class(f"{command_name}Result", source, dependencies)

    _check_for_unhandled_patterns(params_model)

    return _generate_standard_method(command_details, snake_name, params_model, result_model, dependencies)


def _handle_special_cases(command_name: str, command_details: dict[str, Any], dependencies: dict) -> dict | None:
    """Router to delegate generation to special-case handlers. Returns generated data or None."""
    if command_name == "RenameNavigatorItem":
        return _generate_rename_navigator_item_fix(command_details, dependencies)
    return None


def get_model_class(model_name: str, source: str, dependencies: dict) -> Any | None:
    """Safely retrieves a model class by name and tracks it as a dependency."""
    try:
        model = getattr(MODEL_MODULES[source]["commands"], model_name)
        dependencies["commands"].add(model_name)
        return model
    except AttributeError:
        try:
            model = getattr(MODEL_MODULES[source]["types"], model_name)
            dependencies["types"].add(model_name)
            return model
        except AttributeError:
            return None


def get_clean_type_hint(annotation: Any, dependencies: dict) -> str:
    """
    Recursively unwraps type annotations (like Annotated) to get a clean,
    user-facing type hint string and tracks model dependencies.
    """
    if annotation is type(None):
        return "None"
    origin = get_origin(annotation)
    if origin:
        args = get_args(annotation)
        if origin is Annotated:
            return get_clean_type_hint(args[0], dependencies)
        if origin is UnionType or origin is Union:
            return " | ".join(sorted([get_clean_type_hint(arg, dependencies) for arg in args]))

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


def _check_for_unhandled_patterns(params_model: Any) -> None:
    """
    Checks for complex model patterns that the generator isn't equipped to handle automatically.
    Halts the pipeline if an unhandled pattern is found.
    """
    if not params_model or not hasattr(params_model, "model_fields") or "root" not in params_model.model_fields:
        return

    root_field_annotation = params_model.model_fields["root"].annotation
    origin = get_origin(root_field_annotation)
    if origin is Union or origin is UnionType:
        raise NotImplementedError(
            f"Unhandled RootModel[Union[...]] pattern found in '{params_model.__name__}'. "
            "The code generator must be updated to handle this new special case."
        )


def _generate_standard_method(
    command_details: dict[str, Any], snake_name: str, params_model: Any, result_model: Any, dependencies: dict
) -> dict:
    """Generates method code for a standard, straightforward command."""
    final_return_type_hint = "None"
    alias_property_name = None

    if result_model:
        # Check if the result model is just a wrapper for a single field (alias)
        if hasattr(result_model, "model_fields") and len(result_model.model_fields) == 1:
            field_name, field_info = list(result_model.model_fields.items())[0]
            alias_property_name = field_name
            final_return_type_hint = get_clean_type_hint(field_info.annotation, dependencies)
        else:
            final_return_type_hint = get_clean_type_hint(result_model, dependencies)

    signature, param_docs = _build_signature_and_docs(snake_name, params_model, final_return_type_hint, dependencies)
    docstring = _build_docstring(command_details["description"], param_docs)
    body = _build_body(command_details["name"], command_details["source"], params_model, result_model, alias_property_name)

    return {
        "method_code": f"{signature}\n{textwrap.indent(docstring, '    ')}\n{textwrap.indent(body, '    ')}",
        "command_model_dependencies": sorted(list(dependencies["commands"])),
        "type_model_dependencies": sorted(list(dependencies["types"])),
    }


def _build_signature_and_docs(
    snake_name: str, params_model: Any, return_type_hint: str, dependencies: dict
) -> tuple[str, list[str]]:
    """Builds the method signature and the parameter documentation lines."""
    signature_parts, param_docs = ["self"], []
    if params_model:
        sig = inspect.signature(params_model)
        required_params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
        optional_params = [p for p in sig.parameters.values() if p.default is not inspect.Parameter.empty]

        for param in required_params + optional_params:
            param_name_snake = camel_to_snake(param.name)
            type_hint = get_clean_type_hint(param.annotation, dependencies)

            if param.default is inspect.Parameter.empty:
                signature_parts.append(f"{param_name_snake}: {type_hint}")
            else:
                signature_parts.append(f"{param_name_snake}: {type_hint} = {repr(param.default)}")

            doc_line = f"{param_name_snake} ({type_hint})"
            field_info = params_model.model_fields.get(param.name)
            if field_info:
                if field_info.description:
                    doc_line += f": {field_info.description}"
                constraints = [
                    f"{meta_item.alias}={repr(getattr(meta_item, meta_item.alias))}"
                    for meta_item in field_info.metadata
                    if hasattr(meta_item, "alias")
                ]
                if constraints:
                    doc_line += f" (Constraints: {', '.join(sorted(constraints))})"
            param_docs.append(doc_line)

    signature = f"def {snake_name}(\n    {',\n    '.join(signature_parts)}\n) -> {return_type_hint}:"
    return signature, param_docs


def _build_docstring(description: str, param_docs: list[str]) -> str:
    """Assembles the full method docstring, including a standard 'Raises' section."""
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


def _build_body(
    original_command_name: str, source: str, params_model: Any, validation_model: Any, alias_property_name: str | None
) -> str:
    """Constructs the method body, creating the params dict and handling alias returns."""
    core_call_method = "post_tapir_command" if source == "tapir" else "post_command"
    body_lines = []

    if params_model:
        params_map_lines = ["{"]
        for param in inspect.signature(params_model).parameters.values():
            params_map_lines.append(f"    '{param.name}': {camel_to_snake(param.name)},")
        params_map_lines.append("}")
        params_map = "\n    ".join(params_map_lines)
        body_lines.extend(
            [
                f"params_dict = {params_map}",
                f"validated_params = {params_model.__name__}(**params_dict)",
            ]
        )

    call_args = [f'"{original_command_name}"']
    if params_model:
        call_args.append("validated_params.model_dump(by_alias=True, exclude_none=True)")
    call_expression = f"self._core.{core_call_method}(\n    {',\n    '.join(call_args)}\n)"

    if not validation_model:
        body_lines.append(call_expression)
        body_lines.append("return None")
    else:
        body_lines.append(f"response_dict = {call_expression}")
        body_lines.append(f"validated_response = {validation_model.__name__}.model_validate(response_dict)")
        if alias_property_name:
            body_lines.append(f"return validated_response.{alias_property_name}")
        else:
            body_lines.append("return validated_response")

    return "\n".join(body_lines)


def _generate_rename_navigator_item_fix(command_details: dict[str, Any], dependencies: dict) -> dict:
    """Surgical fix to generate a user-friendly method for RenameNavigatorItem."""
    # Manually add all required model dependencies for this command
    dependencies["commands"].update([
        "RenameNavigatorItemParameters",
        "RenameNavigatorItemByName",
        "RenameNavigatorItemById",
        "RenameNavigatorItemByNameAndId",
    ])
    dependencies["types"].add("NavigatorItemId")

    signature = (
        "def rename_navigator_item(\n"
        "    self,\n"
        "    navigator_item_id: NavigatorItemId,\n"
        "    new_name: str | None = None,\n"
        "    new_id: str | None = None\n"
        ") -> None:"
    )

    docstring = _build_docstring(
        command_details["description"],
        [
            "navigator_item_id (NavigatorItemId): The identifier of the navigator item to rename.",
            "new_name (str, optional): The new name for the navigator item.",
            "new_id (str, optional): The new ID for the navigator item.",
        ],
    )

    body = textwrap.dedent("""
        if not new_name and not new_id:
            raise ValueError("Either 'new_name' or 'new_id' (or both) must be provided.")

        if new_name and new_id:
            inner_model = RenameNavigatorItemByNameAndId(navigatorItemId=navigator_item_id, newName=new_name, newId=new_id)
        elif new_name:
            inner_model = RenameNavigatorItemByName(navigatorItemId=navigator_item_id, newName=new_name)
        else:
            inner_model = RenameNavigatorItemById(navigatorItemId=navigator_item_id, newId=new_id)

        validated_params = RenameNavigatorItemParameters(root=inner_model)
        self._core.post_command(
            "API.RenameNavigatorItem", validated_params.model_dump(by_alias=True, exclude_none=True)
        )
        return None
    """).strip()

    return {
        "method_code": f"{signature}\n{textwrap.indent(docstring, '    ')}\n{textwrap.indent(body, '    ')}",
        "command_model_dependencies": sorted(list(dependencies["commands"])),
        "type_model_dependencies": sorted(list(dependencies["types"])),
    }


if __name__ == "__main__":
    main()