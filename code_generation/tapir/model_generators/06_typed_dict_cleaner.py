import ast
import json
import re
from code_generation.tapir.paths import tapir_paths


def main():
    print(f"--- Starting definitive cleaning of {tapir_paths.RAW_TYPED_DICTS} ---")

    try:
        content = tapir_paths.RAW_TYPED_DICTS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {tapir_paths.RAW_TYPED_DICTS} not found. Please generate it first.")
        return

    print("Step 1: Reordering forward-referencing TypeAliases...")
    content = fix_forward_reference_aliases(content)
    content = fix_graphic_override_forward_refs(content)
    content = preserve_open_typed_dicts(content)

    print("Step 2: Assembling and formatting the final file...")
    content = assemble_final_file(content)

    tapir_paths.CLEANED_TYPED_DICTS.write_text(content, encoding="utf-8")
    print(f"Created final, clean TypedDict models at: {tapir_paths.CLEANED_TYPED_DICTS}")


def fix_forward_reference_aliases(content: str) -> str:
    """
    Finds patterns like `Alias: TypeAlias = list["Class"]` defined before `class Class(TypedDict)`
    and swaps them to ensure correct definition order. It also strips the quotes from the
    forward-reference, turning it into a solid runtime type to prevent Typeguard NameErrors.
    """
    pattern = re.compile(
        r"^(?P<alias_block>(?P<alias_name>\w+):\s*TypeAlias\s*=\s*list\[[\"'](?P<class_name>\w+)[\"']\](?:\n[ \t]*\"\"\"[^\"]+\"\"\")?)\n+(?P<class_block>class\s+(?P=class_name)\(TypedDict\):(?:\n(?:    .*|))*)",
        re.MULTILINE,
    )

    def replacer(match):
        alias_block = match.group("alias_block").strip()
        class_block = match.group("class_block").strip()
        class_name = match.group("class_name")

        # Changes `Hotlinks: TypeAlias = list["Hotlink"]` to `list[Hotlink]`
        alias_block = re.sub(rf'list\[["\']{class_name}["\']\]', f"list[{class_name}]", alias_block)

        print(
            f"    - Reordered '{match.group('alias_name')}' to be after '{class_name}' and stripped forward-ref quotes."
        )

        return f"{class_block}\n\n\n{alias_block}\n\n\n"

    content, num_replacements = pattern.subn(replacer, content)
    if num_replacements == 0:
        print("    - No forward-reference aliases needed reordering.")
    return content


def fix_graphic_override_forward_refs(content: str) -> str:
    """Defer the two recursive keyword fields, then resolve their runtime types."""
    reference = "NotRequired[list[GraphicOverrideCriterion]]"
    if reference not in content:
        return content
    content = content.replace(reference, 'NotRequired[list["GraphicOverrideCriterion"]]')
    return re.sub(
        r"(?ms)^(GraphicOverrideCriterion = TypedDict\(.*?^\))",
        r"\1\nGraphicOverrideCriterion.__annotations__ = get_type_hints(GraphicOverrideCriterion, include_extras=True)",
        content,
        count=1,
    )


def preserve_open_typed_dicts(content: str) -> str:
    """Express explicit open records and unconstrained objects with PEP 728 extra items."""
    definitions = json.loads(tapir_paths.MASTER_SCHEMA_OUTPUT.read_text(encoding="utf-8"))["$defs"]
    open_names = {
        name
        for name, schema in definitions.items()
        if schema.get("type") == "object"
        and (
            schema.get("additionalProperties") is True
            or (
                not schema.get("properties")
                and schema.get("additionalProperties", True) is True
                and not any(key in schema for key in ("oneOf", "anyOf", "allOf", "$ref"))
            )
        )
    }
    lines = content.splitlines(keepends=True)
    edits = []
    for node in ast.parse(content).body:
        if isinstance(node, ast.ClassDef) and node.name in open_names:
            if any(isinstance(base, ast.Name) and base.id == "TypedDict" for base in node.bases):
                header = lines[node.lineno - 1]
                if any(keyword.arg in {"closed", "extra_items"} for keyword in node.keywords):
                    raise ValueError(f"Review existing TypedDict keywords on {node.name}")
                header = header.replace("(TypedDict", "(OpenTypedDict", 1)
                edits.append((node.lineno - 1, header.replace("):", ", extra_items=Any):", 1)))
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if any(isinstance(target, ast.Name) and target.id in open_names for target in node.targets):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == "TypedDict":
                    if any(keyword.arg == "extra_items" for keyword in call.keywords):
                        raise ValueError("Review existing functional TypedDict extra_items")
                    call.keywords.append(ast.keyword(arg="extra_items", value=ast.Name(id="Any")))
                    call.func = ast.Name(id="OpenTypedDict")
                    replacement = ast.unparse(node) + "\n"
                    edits.append((node.lineno - 1, replacement, node.end_lineno))
    for edit in reversed(edits):
        start, replacement, *end = edit
        lines[start : (end[0] if end else start + 1)] = [replacement]
    return "".join(lines)


def assemble_final_file(content: str) -> str:
    """Adds standard headers and ensures consistent double-blank line separation between definitions."""
    body_lines = [
        line
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith(("#", "from __future__", "from typing", "###"))
    ]

    header = [
        "from __future__ import annotations",
        "",
        "from typing import Any, Literal, TypeAlias, TypedDict, get_type_hints",
        "",
        "from typing_extensions import NotRequired, TypedDict as OpenTypedDict",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]

    final_content = "\n".join(header + [""] + body_lines)

    # Ensure consistent double-blank lines (\n\n\n) between definitions so that
    # the split scripts can identify class boundaries easily.
    final_content = re.sub(r"\n(class |[A-Z]\w+\s*=|[A-Z]\w+\s*:\s*TypeAlias\s*=)", r"\n\n\n\1", final_content)
    final_content = re.sub(r"\n{4,}", "\n\n\n", final_content)

    return final_content.strip() + "\n"


if __name__ == "__main__":
    main()
