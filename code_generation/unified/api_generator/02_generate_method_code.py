import argparse
import inspect
import json
import sys
import textwrap
from types import UnionType
from typing import Any, get_args, get_origin, Union, Annotated

from code_generation.shared.utils import camel_to_snake
from code_generation.unified.api_generator.shipped_signatures import ShippedMethod, load_shipped_signatures

from multiconn_archicad.models.official import commands as official_commands
from multiconn_archicad.models.official import types as official_types
from multiconn_archicad.models.tapir import commands as tapir_commands
from multiconn_archicad.models.tapir import types as tapir_types


MODEL_MODULES = {
    "tapir": {"commands": tapir_commands, "types": tapir_types},
    "official": {"commands": official_commands, "types": official_types},
}
EXECUTION_RESULT_RETURN = "FailedExecutionResult | SuccessfulExecutionResult"
EXECUTION_RESULTS_RETURN = f"list[{EXECUTION_RESULT_RETURN}]"


def main():
    """Main script entry point for Stage 2 of the pipeline."""
    parser = argparse.ArgumentParser(description="Stage 2: Generate method code strings for API commands.")
    parser.add_argument("--input-file", required=True, help="Path to the organized commands JSON from Stage 1.")
    parser.add_argument("--output-file", required=True, help="Path to save JSON with the new 'method_code' field.")
    args = parser.parse_args()

    print(f"Reading organized command data from: {args.input_file}")
    with open(args.input_file, "r", encoding="utf-8") as f:
        organized_commands = json.load(f)
    shipped_signatures = load_shipped_signatures()

    print("Generating method code and tracking dependencies for each command...")
    total_commands = 0
    for source, groups in organized_commands.items():
        for group_name, commands in groups.items():
            methods = []
            for command in commands:
                total_commands += 1
                try:
                    generated_data = generate_method_code(command, shipped_signatures[source].get(command["name"]))
                    companion = generated_data.pop("dry_run_companion", None)
                    methods.append({**command, **generated_data})
                    if companion:
                        methods.append({**command, **companion})
                except Exception as e:
                    print(
                        f"❌ FATAL: Failed to generate code for command '{command['name']}'. Error: {e}",
                        file=sys.stderr,
                    )
                    raise
            groups[group_name] = methods
    print(f"✅ Successfully generated code for {total_commands} commands.")
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(organized_commands, f, indent=2)
    print(f"Enriched command data saved to: {args.output_file}")


def is_union(obj: Any) -> bool:
    if isinstance(obj, UnionType):
        return True
    origin = get_origin(obj)
    return origin is Union or origin is UnionType


def generate_method_code(
    command_details: dict[str, Any], shipped_methods: dict[str, ShippedMethod] | None = None
) -> dict:
    """
    Orchestrates the generation of a single API method, handling special cases
    and falling back to a standard generation process.
    """
    dependencies = {"commands": set(), "types": set(), "collections_abc": set()}
    original_cmd_name = command_details["name"]
    source = command_details["source"]
    command_name = original_cmd_name.removeprefix("API.") if source == "official" else original_cmd_name
    snake_name = camel_to_snake(command_name)

    if special_case_code := _handle_special_cases(command_name, command_details, dependencies):
        return special_case_code

    params_model = get_model_class(f"{command_name}Parameters", source, dependencies)
    result_model = get_model_class(f"{command_name}Result", source, dependencies)

    _check_for_unhandled_patterns(params_model)

    shipped_methods = shipped_methods or {}
    shipped = shipped_methods.get(snake_name)
    shipped_parameters = shipped["parameters"] if shipped else None
    if (
        source == "tapir"
        and shipped is not None
        and shipped["returns"] in (EXECUTION_RESULT_RETURN, EXECUTION_RESULTS_RETURN)
        and "dry_run" not in shipped["parameters"]
        and "dryRun" in getattr(params_model, "model_fields", {})
        and "dryRun" in getattr(result_model, "model_fields", {})
    ):
        dry_name = f"{snake_name}_dry_run"
        dry_parameters = shipped_methods.get(dry_name, shipped)["parameters"]
        companion = _generate_standard_method(
            command_details, dry_name, params_model, result_model, dependencies, dry_parameters, dry_run=True
        )
        ordinary = _generate_standard_method(
            command_details,
            snake_name,
            params_model,
            result_model,
            dependencies,
            shipped_parameters,
            dry_run=False,
            legacy_return=shipped["returns"],
        )
        ordinary["dry_run_companion"] = companion
        return ordinary

    return _generate_standard_method(
        command_details, snake_name, params_model, result_model, dependencies, shipped_parameters
    )


def _handle_special_cases(command_name: str, command_details: dict[str, Any], dependencies: dict) -> dict | None:
    """Router to delegate generation to special-case handlers. Returns generated data or None."""
    if command_name == "RenameNavigatorItem" and command_details["source"] == "official":
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
    command_details: dict[str, Any],
    snake_name: str,
    params_model: Any,
    result_model: Any,
    dependencies: dict,
    shipped_parameters: list[str] | None,
    *,
    dry_run: bool | None = None,
    legacy_return: str | None = None,
) -> dict:
    """Generates method code for a standard, straightforward command."""
    final_return_type_hint = "None"
    alias_property_name = None
    return_doc_info = None

    command_name = (
        command_details["name"].removeprefix("API.")
        if command_details["source"] == "official"
        else command_details["name"]
    )
    params_model_name = f"{command_name}Parameters" if params_model else None
    result_model_name = f"{command_name}Result" if result_model else None

    if legacy_return:
        final_return_type_hint = legacy_return
        dependencies["types"].update({"ExecutionResult", "FailedExecutionResult", "SuccessfulExecutionResult"})
        if legacy_return == EXECUTION_RESULTS_RETURN:
            alias_property_name = "executionResults"
            field_info = result_model.model_fields[alias_property_name]
            return_doc_info = (legacy_return, field_info.description)
        else:
            return_doc_info = (legacy_return, None)
    elif result_model:
        # Check if the result model is just a wrapper for a single field (alias)
        if inspect.isclass(result_model) and hasattr(result_model, "model_fields") and not result_model.model_fields:
            final_return_type_hint = "None"
        elif (
            inspect.isclass(result_model)
            and hasattr(result_model, "model_fields")
            and len(result_model.model_fields) == 1
        ):
            field_name, field_info = list(result_model.model_fields.items())[0]
            alias_property_name = field_name
            final_return_type_hint = get_clean_type_hint(field_info.annotation, dependencies)
            return_doc_info = (final_return_type_hint, field_info.description)
        else:
            final_return_type_hint = get_clean_type_hint(result_model, dependencies)
            return_doc_info = (final_return_type_hint, None)

    signature, param_docs = _build_signature_and_docs(
        snake_name, params_model, final_return_type_hint, dependencies, shipped_parameters, dry_run
    )
    description = command_details["description"]
    if dry_run is True:
        description = f"Preview this command without applying its changes. {description}"
    docstring = _build_docstring(description, param_docs, return_doc_info)

    body = _build_body(
        command_details["name"],
        command_details["source"],
        params_model,
        params_model_name,
        result_model,
        result_model_name,
        alias_property_name,
        dry_run=dry_run,
        legacy_return=legacy_return,
    )

    generated = {
        "method_code": f"{signature}\n{textwrap.indent(docstring, '    ')}\n{textwrap.indent(body, '    ')}",
        "command_model_dependencies": sorted(list(dependencies["commands"])),
        "type_model_dependencies": sorted(list(dependencies["types"])),
        "alias_property_name": alias_property_name,
    }
    if dependencies["collections_abc"]:
        generated["collections_abc_dependencies"] = sorted(dependencies["collections_abc"])
    if dry_run is not None:
        generated["dry_run"] = dry_run
        generated["python_name"] = snake_name
    return generated


def _order_parameters(
    params: list[inspect.Parameter], shipped_parameters: list[str] | None
) -> tuple[list[inspect.Parameter], list[inspect.Parameter]]:
    if shipped_parameters is None:
        return sorted(params, key=lambda param: param.default is not inspect.Parameter.empty), []

    remaining = {camel_to_snake(param.name): param for param in params}
    boundary = shipped_parameters.index("*") if "*" in shipped_parameters else len(shipped_parameters)
    positional = [remaining.pop(name) for name in shipped_parameters[:boundary] if name in remaining]
    keyword_only = [remaining.pop(name) for name in shipped_parameters[boundary + 1 :] if name in remaining]
    keyword_only.extend(remaining.values())
    # Report incompatible requiredness changes instead of silently reordering positional slots.
    inspect.Signature(
        [param.replace(kind=inspect.Parameter.POSITIONAL_OR_KEYWORD) for param in positional]
        + [param.replace(kind=inspect.Parameter.KEYWORD_ONLY) for param in keyword_only]
    )
    return positional, keyword_only


def _get_parameter_type_hint(annotation: Any, dependencies: dict) -> str:
    property_value_input = getattr(tapir_types, "ElementPropertyValueInput", None)
    if property_value_input is not None and annotation == list[property_value_input]:
        dependencies["collections_abc"].add("Sequence")
        dependencies["types"].add("ElementPropertyValueInput")
        return "Sequence[ElementPropertyValueInput]"
    return get_clean_type_hint(annotation, dependencies)


def _build_signature_and_docs(
    snake_name: str,
    params_model: Any,
    return_type_hint: str,
    dependencies: dict,
    shipped_parameters: list[str] | None = None,
    dry_run: bool | None = None,
) -> tuple[str, list[str]]:
    """Builds the method signature and the parameter documentation lines."""
    if params_model is None:
        return f"def {snake_name}(self) -> {return_type_hint}:", []

    if is_union(params_model):
        args = get_args(params_model)
        type_names = []
        for arg in args:
            name = getattr(arg, "__name__", str(arg).split(".")[-1])
            type_names.append(name)
            module_name = getattr(arg, "__module__", "")
            if "multiconn_archicad.models" in module_name:
                if ".types" in module_name:
                    dependencies["types"].add(name)
                elif ".commands" in module_name:
                    dependencies["commands"].add(name)

        union_str = " | ".join(type_names)
        signature = f"def {snake_name}(\n    self,\n    parameters: {union_str}\n) -> {return_type_hint}:"
        param_docs = [f"parameters ({union_str}): Union model configuration parameters."]
        return signature, param_docs

    signature_parts, param_docs = ["self"], []
    if params_model:
        params = [
            param
            for param in inspect.signature(params_model).parameters.values()
            if dry_run is None or param.name != "dryRun"
        ]
        positional, keyword_only = _order_parameters(params, shipped_parameters)

        for index, param in enumerate(positional + keyword_only):
            if index == len(positional):
                signature_parts.append("*")
            param_name_snake = camel_to_snake(param.name)
            type_hint = _get_parameter_type_hint(param.annotation, dependencies)

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


def _build_docstring(
    description: str, param_docs: list[str], return_doc_info: tuple[str, str | None] | None = None
) -> str:
    """Assembles the full method docstring, including a standard 'Raises' section."""
    docstring = f'"""\n{textwrap.fill(description, width=88)}\n'
    if param_docs:
        docstring += "\nArgs:\n"
        for doc in param_docs:
            wrapped_doc = textwrap.fill(doc, width=88, initial_indent="    ", subsequent_indent=" " * 8)
            docstring += f"{wrapped_doc}\n"

    if return_doc_info:
        return_type, return_desc = return_doc_info
        docstring += "\nReturns:\n"
        # Only add the description part if it's a non-empty string
        return_line = f"{return_type}: {return_desc}" if return_desc else return_type
        wrapped_doc = textwrap.fill(return_line, width=88, initial_indent="    ", subsequent_indent=" " * 8)
        docstring += f"{wrapped_doc}\n"

    docstring += "\nRaises:\n"
    docstring += "    ArchicadAPIError: If the API returns an error response.\n"
    docstring += "    RequestError: If there is a network or connection error.\n"
    docstring += "    pydantic.ValidationError: If the parameters, or the API Response fail validation.\n"
    docstring += '"""'
    return docstring


def _build_body(
    original_command_name: str,
    source: str,
    params_model: Any,
    params_model_name: str | None,
    validation_model: Any,
    validation_model_name: str | None,
    alias_property_name: str | None,
    *,
    dry_run: bool | None = None,
    legacy_return: str | None = None,
) -> str:
    """Constructs the method body, creating the params dict and handling alias returns."""
    core_call_method = "post_tapir_command" if source == "tapir" else "post_command"
    body_lines = []

    if params_model:
        if is_union(params_model):
            body_lines.append(f"validated_params = TypeAdapter({params_model_name}).validate_python(parameters)")
        else:
            params_map_lines = ["{"]
            for param in inspect.signature(params_model).parameters.values():
                if param.name == "dryRun" and dry_run is not None:
                    if dry_run:
                        params_map_lines.append("    'dryRun': True,")
                    continue
                params_map_lines.append(f"    '{param.name}': {camel_to_snake(param.name)},")
            params_map_lines.append("}")
            params_map = "\n    ".join(params_map_lines)
            body_lines.extend(
                [
                    f"params_dict = {params_map}",
                    f"validated_params = {params_model_name}(**params_dict)",
                ]
            )

    call_args = [f'"{original_command_name}"']
    if params_model:
        call_args.append("validated_params.model_dump(mode='json', by_alias=True, exclude_none=True)")
    call_expression = f"self._core.{core_call_method}(\n    {',\n    '.join(call_args)}\n)"

    if not validation_model:
        body_lines.append(call_expression)
        body_lines.append("return None")
    else:
        body_lines.append(f"response_dict = {call_expression}")

        if legacy_return:
            if alias_property_name:
                body_lines.append(
                    f"return TypeAdapter(list[ExecutionResult]).validate_python(response_dict.get({alias_property_name!r}))"
                )
            else:
                body_lines.append("return TypeAdapter(ExecutionResult).validate_python(response_dict)")
            return "\n".join(body_lines)

        if is_union(validation_model):
            body_lines.append(
                f"validated_response = TypeAdapter({validation_model_name}).validate_python(response_dict)"
            )
        else:
            body_lines.append(f"validated_response = {validation_model_name}.model_validate(response_dict)")

        if (
            inspect.isclass(validation_model)
            and hasattr(validation_model, "model_fields")
            and not validation_model.model_fields
        ):
            body_lines.append("return None")
        elif alias_property_name:
            body_lines.append(f"return validated_response.{alias_property_name}")
        else:
            body_lines.append("return validated_response")

    return "\n".join(body_lines)


def _generate_rename_navigator_item_fix(command_details: dict[str, Any], dependencies: dict) -> dict:
    """Surgical fix to generate a user-friendly method for RenameNavigatorItem."""
    # Manually add all required model dependencies for this command
    dependencies["commands"].update(
        [
            "RenameNavigatorItemParameters",
            "RenameNavigatorItemByName",
            "RenameNavigatorItemById",
            "RenameNavigatorItemByNameAndId",
        ]
    )
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
            "API.RenameNavigatorItem", validated_params.model_dump(mode=\'json\', by_alias=True, exclude_none=True)
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
