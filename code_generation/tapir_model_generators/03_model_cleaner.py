import re
from code_generation.paths import paths

def main():
    """
    Performs a final, surgical cleaning of the generated Pydantic models.
    This script is simplified to handle only the remaining artifacts from the
    improved datamodel-codegen process.
    """
    print(f"--- Starting SIMPLIFIED cleaning of {paths.RAW_PYDANTIC_MODELS} ---")

    try:
        content = paths.RAW_PYDANTIC_MODELS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {paths.RAW_PYDANTIC_MODELS} not found. Please generate it first.")
        return

    print("Step 1: Replacing 'constr' with 'str'...")
    content = replace_constr_with_str(content)

    print("Step 2: Removing known incomplete duplicate classes...")
    content = remove_specific_duplicates(content)

    print("Step 3: Resolving wrapper model name collisions...")
    content = fix_wrapper_models_and_alias(content)

    print("Step 4: Consolidating suffixed classes (e.g., 'Hole1' -> 'Hole')...")
    content = promote_suffixed_classes(content)

    print("Step 5: Reordering self-referencing models...")
    content = fix_forward_reference_models(content)

    print("Step 6: Assembling and formatting the final file...")
    content = assemble_final_file(content)

    paths.CLEANED_PYDANTIC_MODELS.write_text(content, encoding="utf-8")
    print(f"✅ Successfully created final, clean models at: {paths.CLEANED_PYDANTIC_MODELS}")


### Cleaning Logic Functions (in execution order) ###


def replace_constr_with_str(content: str) -> str:
    """Replaces all instances of `constr(...)` with `str`."""
    content = re.sub(r"constr\(.*?\)", "str", content)
    print("    - All 'constr' types replaced with 'str'.")
    return content


def remove_specific_duplicates(content: str) -> str:
    """Removes known, less-complete class definitions before renaming."""
    # This pattern is still needed as the generator creates a less-complete
    # 'DocumentRevision' before creating the correct 'DocumentRevision1'.
    duplicate_doc_rev_pattern = re.compile(
        r"class DocumentRevision\(BaseModel\):\s*\n(?:    .+\n)+?    revisionId: DocumentRevisionId\s*\n", re.MULTILINE
    )
    content, count = duplicate_doc_rev_pattern.subn("", content)
    if count > 0:
        print("    - Removed incomplete 'DocumentRevision' class.")

    # This pattern is still needed to remove the 'Hole' that uses 'polygonOutline'
    # so we can promote the 'Hole1' that correctly uses 'polygonCoordinates'.
    original_hole_pattern = re.compile(
        r"class Hole\(BaseModel\):\s*\n    polygonOutline: .+\n(?:    .+\n)*", re.MULTILINE
    )
    content, count = original_hole_pattern.subn("", content)
    if count > 0:
        print("    - Removed 'Hole' class with incorrect 'polygonOutline' field.")

    return content


def fix_wrapper_models_and_alias(content: str) -> str:
    """
    Identifies classes that wrap another class (e.g., `class A: a: A1`),
    renames them to avoid collisions (e.g., `A` -> `AWrapper`, `A1` -> `A`),
    and adds a `title` to the wrapper's `ConfigDict` to ensure the
    generated schema title remains the original name.
    """
    print("    - Searching for wrapper/data class pairs...")
    blocks = re.split(r"\n\n\n", content)
    wrappers = {}  # Maps original wrapper name to its info
    all_class_names = {m.group(1) for m in re.finditer(r"class\s+(\w+)\(BaseModel\):", content)}

    for block in blocks:
        class_name_match = re.search(r"class\s+(\w+)\(BaseModel\):", block)
        if not class_name_match:
            continue
        class_name = class_name_match.group(1)

        # A wrapper class has exactly one attribute (field).
        field_lines = [line for line in block.split("\n") if re.match(r"^\s{4}\w+\s*:", line)]
        if len(field_lines) != 1:
            continue

        # Extract field name and its type.
        field_match = re.match(r"^\s{4}(\w+)\s*:\s*([\w\d]+)", field_lines[0])
        if not field_match:
            continue

        field_name, field_type = field_match.groups()

        # The field's type must be another known class.
        if field_type not in all_class_names:
            continue

        # Heuristic for wrapper pattern:
        # 1. The field name is the camelCase version of the type's base name.
        # 2. The wrapper's base name is the same as the type's base name.
        type_base_name = re.sub(r"\d*$", "", field_type)
        class_base_name = re.sub(r"\d*$", "", class_name)
        expected_field_name = f"{type_base_name[0].lower()}{type_base_name[1:]}"

        if field_name == expected_field_name and type_base_name == class_base_name:
            wrappers[class_name] = {
                "data_name": field_type,
                "base_name": type_base_name,
            }

    if not wrappers:
        print("    - No wrapper model patterns found to fix.")
        return content

    print(f"    - Found {len(wrappers)} wrapper pattern(s) to resolve.")

    # Phase 1: Rename all original wrapper classes to NewNameWrapper.
    # This must be done first to free up the base name.
    # Sort by length descending to prevent partial replacements (e.g., `Class` in `ClassDetail`).
    sorted_wrapper_names = sorted(wrappers.keys(), key=len, reverse=True)
    for wrapper_name in sorted_wrapper_names:
        info = wrappers[wrapper_name]
        new_wrapper_name = f"{info['base_name']}Wrapper"
        print(f"      - Renaming wrapper '{wrapper_name}' -> '{new_wrapper_name}'")
        content = re.sub(r"\b" + re.escape(wrapper_name) + r"\b", new_wrapper_name, content)
        info["new_wrapper_name"] = new_wrapper_name  # Store for phase 3

    # Phase 2: Rename all data classes to the clean base name.
    data_renames = {
        info["data_name"]: info["base_name"] for info in wrappers.values() if info["data_name"] != info["base_name"]
    }
    sorted_data_names = sorted(data_renames.keys(), key=len, reverse=True)
    for data_name in sorted_data_names:
        base_name = data_renames[data_name]
        print(f"      - Renaming data class '{data_name}' -> '{base_name}'")
        content = re.sub(r"\b" + re.escape(data_name) + r"\b", base_name, content)

    # Phase 3: Add `title` alias to the new wrapper class's ConfigDict.
    for wrapper_name in sorted_wrapper_names:
        info = wrappers[wrapper_name]
        base_name = info["base_name"]
        new_wrapper_name = info["new_wrapper_name"]

        # Regex to find the start of the ConfigDict for the renamed wrapper.
        config_pattern = re.compile(
            r"(class\s+" + re.escape(new_wrapper_name) + r"\(BaseModel\):\s*\n"
            r"\s*model_config\s*=\s*ConfigDict\()"
        )

        # The replacement string injects the title.
        replacement = r"\1\n        title='" + base_name + "',"

        # Perform the substitution.
        content, count = config_pattern.subn(replacement, content, count=1)
        if count > 0:
            print(f"      - Aliasing '{new_wrapper_name}' with `title='{base_name}'`.")
        else:
            print(f"    - WARNING: Could not find ConfigDict for '{new_wrapper_name}' to add title alias.")

    return content


def promote_suffixed_classes(content: str) -> str:
    """
    Finds class definitions ending with any number (e.g., "Hole1", "Story1")
    and renames all occurrences of those names to their base name.
    """
    # This regex finds class names ending in one or more digits.
    suffixed_class_pattern = re.compile(r"class\s+(\w+\d+)\s*\(")
    suffixed_class_names = sorted(list(set(suffixed_class_pattern.findall(content))), key=len, reverse=True)

    if not suffixed_class_names:
        print("    - No suffixed classes found to consolidate.")
        return content

    print(f"    - Found suffixed classes to consolidate: {', '.join(suffixed_class_names)}")

    for suffixed_name in suffixed_class_names:
        # Remove any trailing digits from the name.
        base_name = re.sub(r"\d+$", "", suffixed_name)
        print(f"    - Renaming all instances of '{suffixed_name}' to '{base_name}'...")
        # Use word boundaries (\b) to ensure we replace the whole word only.
        content = re.sub(r"\b" + re.escape(suffixed_name) + r"\b", base_name, content)

    return content


def fix_forward_reference_models(content: str) -> str:
    """
    Finds models that self-reference in a list (e.g., Hotlink) and ensures
    the model is defined before its update_forward_refs() call if it exists.
    This also handles reordering for clarity if no forward ref is used.
    """

    hotlink_model_pattern = re.compile(r"(class Hotlink\(BaseModel\):\s*\n(?:(?:    .*\n)+))", re.MULTILINE)
    hotlink_match = hotlink_model_pattern.search(content)

    if hotlink_match:
        hotlink_model_block = hotlink_match.group(1)
        # In case there's an `update_forward_refs` call, remove it
        content = re.sub(r"Hotlink\.update_forward_refs\(.*\)\s*\n", "", content)
        # Ensure the model definition appears before its use in GetHotlinksResult
        get_hotlinks_result_pattern = re.compile(
            r"(class GetHotlinksResult\(BaseModel\):[\s\S]*?hotlinks: List\[Hotlink\].*)"
        )
        get_hotlinks_match = get_hotlinks_result_pattern.search(content)
        if get_hotlinks_match:
            print("    - Moving 'Hotlink' model definition to ensure correct order.")
            # Remove the original hotlink model block
            content = hotlink_model_pattern.sub("", content)
            # Insert it before the class that uses it
            content = get_hotlinks_result_pattern.sub(
                f"{hotlink_model_block}\n\n{get_hotlinks_match.group(1)}", content, count=1
            )
    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, imports, and performs final formatting."""
    # Remove the placeholder `TapirMasterModels` which isn't needed.
    master_model_pattern = re.compile(r"class TapirMasterModels\(RootModel\[Any\]\):(?:\n.+)+")
    content = master_model_pattern.sub("", content)

    # Define the new, correct header.
    header = [
        "from __future__ import annotations",
        "from typing import Any, List, Literal, Union, TypeAlias",
        "from uuid import UUID",
        "from enum import Enum",
        "",
        "from pydantic import BaseModel, ConfigDict, Field, RootModel",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]

    # Get the body, filtering out all old import lines.
    body_lines = [
        line for line in content.splitlines() if line.strip() and not line.startswith(("from ", "# generated"))
    ]

    final_content = "\n".join(header + [""] + body_lines)

    # Standardize spacing between definitions for readability.
    final_content = re.sub(r"\n(class |[A-Z]\w+\s*=)", r"\n\n\n\1", final_content)
    # Clean up any excessive newlines from the regex substitutions.
    final_content = final_content.replace("\n\n\n\n", "\n\n\n")

    return final_content.strip() + "\n"


if __name__ == "__main__":
    main()
