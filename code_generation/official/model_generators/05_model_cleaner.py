import re
from code_generation.official.paths import official_paths


def main():
    """
    Performs a final, surgical cleaning of the Pydantic models generated
    with the --use-annotated flag. This script focuses on structural issues
    that the generator cannot resolve on its own.
    """
    print(f"--- Starting definitive cleaning of {official_paths.RAW_PYDANTIC_MODELS} ---")

    try:
        content = official_paths.RAW_PYDANTIC_MODELS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Raw models file not found at {official_paths.RAW_PYDANTIC_MODELS}. Please generate it first.")
        return

    # Apply a series of cleaning functions in a specific order.
    content = remove_model_rebuild_calls(content)
    content = surgically_fix_rename_navigator_item(content)
    content = surgically_fix_dash_or_line_item(content)
    content = surgically_fix_numbering_style_enum(content)
    content = fix_root_model_unions_to_type_alias(content)
    content = rename_problematic_wrappers(content)
    content = remove_guid_pattern(content)
    content = remove_redundant_model_configs(content)
    content = patch_addon_command(content)
    content = assemble_final_file(content)

    official_paths.CLEANED_PYDANTIC_MODELS.write_text(content, encoding="utf-8")
    print(f"\n✅ Successfully created final, clean models at: {official_paths.CLEANED_PYDANTIC_MODELS}")


### --- Cleaning Logic Functions --- ###


def remove_model_rebuild_calls(content: str) -> str:
    cleaned_content = re.sub(r"^\w+\.model_rebuild\(\)\n?", "", content, flags=re.MULTILINE)
    print("✅ Step 1: Removed all `.model_rebuild()` calls.")
    return cleaned_content


def surgically_fix_rename_navigator_item(content: str) -> str:
    print("⚙️  Step 2: Surgically fixing `RenameNavigatorItemParameters`...")

    current_content = content.replace(
        "RenameNavigatorItemParameters1", "RenameNavigatorItemByName", -1 # Use -1 for global replace within the block
    )
    current_content = current_content.replace(
        "RenameNavigatorItemParameters2", "RenameNavigatorItemById", -1
    )
    current_content = current_content.replace(
        "RenameNavigatorItemParameters3", "RenameNavigatorItemByNameAndId", -1
    )

    print("    - Successfully renamed wrapper classes.")
    return current_content


def surgically_fix_dash_or_line_item(content: str) -> str:
    print("⚙️  Step 3: Surgically fixing `DashOrLineItem`...")
    content = content.replace("class DashOrLineItem1(APIModel):", "class DashItemWrapperItem(APIModel):", 1)
    content = content.replace("class DashOrLineItem2(APIModel):", "class LineItemWrapperItem(APIModel):", 1)

    content = content.replace("DashOrLineItem1", "DashItemWrapperItem", -1)
    content = content.replace("DashOrLineItem2", "LineItemWrapperItem", -1)

    print("    - Renamed wrapper classes to 'DashItemWrapperItem' and 'LineItemWrapperItem'.")
    print("    - Updated all references to use the new names.")
    return content


def surgically_fix_numbering_style_enum(content: str) -> str:
    """Renames the un-pythonic members of the NumberingStyle enum."""
    print("⚙️  Step 4: Surgically fixing `NumberingStyle` enum names...")

    content = content.replace("field_1 = '1'", "Style1 = '1'")
    content = content.replace("field_01 = '01'", "Style01 = '01'")
    content = content.replace("field_001 = '001'", "Style001 = '001'")
    content = content.replace("field_0001 = '0001'", "Style0001 = '0001'")

    return content


def fix_root_model_unions_to_type_alias(content: str) -> str:
    print("⚙️  Step 5: Converting remaining `RootModel` classes to `TypeAlias`...")
    lookahead = r"(?=\n\n\n(class |[A-Z]\w+\s*:\s*TypeAlias)|\Z)"
    pattern = re.compile(
        r"class (\w+)\(RootModel\[(.+?)]\):.*?" + lookahead,
        flags=re.DOTALL
    )
    replacement = r"\1: TypeAlias = \2"

    num_replacements = 0
    while True:
        content, count = pattern.subn(replacement, content, count=1)
        if count == 0:
            break
        num_replacements += 1

    print(f"    - Converted {num_replacements} models.")
    return content


def rename_problematic_wrappers(content: str) -> str:
    """
    Finds all wrapper classes ending in problematic suffixes (e.g., '1', 'OrError1')
    and renames them globally to a consistent '...WrapperItem' convention.
    """
    print("⚙️  Step 6: Renaming all problematic wrapper classes...")

    pattern = re.compile(r"class\s+(?P<full_name>(?P<base_name>\w+?)(?:1|OrError1|OrErrorItem1))\(APIModel\):")
    matches = list(pattern.finditer(content))
    sorted_matches = sorted(matches, key=lambda m: len(m.group("full_name")), reverse=True)

    if not sorted_matches:
        print("    - No problematic wrapper classes found to rename.")
        return content

    for match in sorted_matches:
        old_name = match.group("full_name")
        base_name = match.group("base_name")
        new_name = f"{base_name}WrapperItem"
        content = content.replace(old_name, new_name)
        print(f"    - Renamed {old_name} -> {new_name}")

    return content

def remove_guid_pattern(code: str) -> str:
    """
    Surgically removes the 'pattern=...' argument from any field defined as
    'Annotated[UUID, Field(...)]'. This is necessary because Pydantic V2
    cannot apply a string pattern to a UUID object after validation.
    """
    print("⚙️  Step 8: Removing conflicting 'pattern' from all UUID Fields...")

    pattern = re.compile(
        # --- Group 1: Capture the part BEFORE the pattern argument ---
        r"("
        # Match any field name like 'guid:' or 'stampMainGuid:'
        r"\w+:\s*Annotated\[\s*UUID\s*,\s*Field\("
        # Non-greedily match any characters (including newlines) up to the pattern arg.
        r".*?"
        r")"
        # --- The part to DISCARD ---
        # Match an optional comma, the pattern argument, and its value.
        r'(?:,\s*)?pattern\s*=\s*".*?"'
        # --- Group 2: Capture the part AFTER the pattern argument ---
        r"("
        # Non-greedily match any remaining characters until the end of the annotation.
        r".*?"
        r"\)\s*\]"
        r")",
        flags=re.DOTALL,  # The DOTALL flag makes '.' match newlines, simplifying the regex.
    )

    # The replacement consists of only the two captured groups,
    # effectively deleting the pattern argument from the middle.
    replacement = r"\1\2"

    # We use a loop with subn to replace all occurrences in the file.
    num_replacements = 0
    while True:
        code, count = pattern.subn(replacement, code, count=1)
        if count == 0:
            break
        num_replacements += 1

    if num_replacements > 0:
        print(f"    - Removed {num_replacements} conflicting 'pattern' arguments from UUID fields.")
    else:
        print("    - No conflicting 'pattern' arguments found in UUID fields.")

    return code


def remove_redundant_model_configs(content: str) -> str:
    """
    Finds and removes the boilerplate `model_config` dicts as it is handled by the APIModel base model
    """
    print("    - Removing redundant `model_config` blocks...")

    pattern = re.compile(
        r"\s*model_config = ConfigDict\(\s*extra=\"forbid\",?\s*\)\s*",
        re.MULTILINE
    )

    cleaned_content, num_replacements = pattern.subn("\n    ", content)

    if num_replacements > 0:
        print(f"      - Successfully removed {num_replacements} redundant config blocks.")
    else:
        print("      - Warning: No redundant config blocks were found to remove.")

    return cleaned_content


def patch_addon_command(content: str) -> str:
    """
    Finds specific AddOn command models (Parameters and Result) and inserts
    a ConfigDict to override the inherited 'forbid' behavior, allowing extra fields.
    """
    print("⚙️  Step 9: Patching AddOn command models to allow extra fields...")

    models_to_patch = [
        "ExecuteAddOnCommandParameters",
        "ExecuteAddOnCommandResult",
    ]

    for model_name in models_to_patch:
        pattern = re.compile(rf"(class {model_name}\(APIModel\):)")
        replacement = r'\1\n    model_config = ConfigDict(\n        extra="allow",\n    )'
        new_content, count = pattern.subn(replacement, content, count=1)

        if count > 0:
            print(f"    - Successfully patched '{model_name}' to allow extra fields.")
            content = new_content
        else:
            print(f"    - Warning: '{model_name}' model not found for patching.")

    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, imports, and performs final formatting."""
    print("⚙️  Step 7: Assembling final file...")
    body = re.sub(r"^#.*?\n\n", "", content, flags=re.DOTALL)
    body = re.sub(r"^(from|import).*\n", "", body, flags=re.MULTILINE)
    body = re.sub(r"^OfficialArchicadApiMasterModels\s*:\s*TypeAlias = .*\n", "", body, flags=re.MULTILINE)

    header = [
        "from __future__ import annotations",
        "from typing import List, Literal, TypeAlias, Annotated, Any, Union, TypedDict",
        "from uuid import UUID",
        "from enum import Enum",
        "from pydantic import APIModel, ConfigDict, Field, RootModel",
        "",
        "from multiconn_archicad.models.base import APIModel",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]
    final_header = "\n".join(header)

    full_content = final_header + "\n\n\n" + body.strip()

    full_content = re.sub(r"\n+(?=(class |[A-Z]\w+\s*:\s*TypeAlias))", "\n\n\n", full_content)
    full_content = re.sub(r"\n{4,}", "\n\n\n", full_content)

    return full_content.strip() + "\n"


if __name__ == "__main__":
    main()