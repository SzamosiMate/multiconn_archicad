import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from code_generation.official.paths import official_paths


def build_filename_to_group_map(
    menu_items: List[Dict[str, Any]], parent_group: str = "Uncategorized"
) -> Dict[str, str]:
    """
    Recursively traverses the menu tree to create a mapping from a
    command's filename to its group name.
    """
    mapping = {}
    for item in menu_items:
        current_group_name = item.get("name", parent_group)

        # If the item is a command, map its filename to the current group name.
        if filename := item.get("commanddocumentation"):
            mapping[filename] = parent_group

        # If the item is a group with sub-items, recurse into it.
        if sub_items := item.get("menuitems"):
            mapping.update(build_filename_to_group_map(sub_items, parent_group=current_group_name))

    return mapping


def get_command_details_from_file(path: Path) -> Optional[Dict[str, str]]:
    """
    Extracts the command name and description from a single command JSON file.
    The command name is derived from the filename.
    """
    try:
        data = json.loads(path.read_text("utf-8"))
        command_name = path.stem  # e.g., "API.CreateLayout"
        description = data.get("description", "No description available.")

        return {"name": command_name, "description": description}
    except (json.JSONDecodeError, IOError) as e:
        print(f"   ⚠️ Could not process {path.name}: {e}")
        return None


def main():
    """
    Generates a structured JSON file containing details (name, group, description)
    for every official API command.
    """
    print("--- Starting Official API Command Details Generation ---")
    official_paths.create_directories()

    # 1. Load the menu tree to map filenames to group names.
    try:
        # We assume the crawler has downloaded menutree.json into the schema dir
        menutree_path = official_paths.BASE_SCHEMA_DIR / "menutree.json"
        menu_tree = json.loads(menutree_path.read_text("utf-8"))
        filename_to_group = build_filename_to_group_map(menu_tree.get("menuitems", []))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ ERROR: Could not load or parse menutree.json. Please run the crawler first. Details: {e}")
        return

    # 2. Iterate through command files, extract details, and combine with group info.
    all_command_details = []
    command_files = sorted([p for p in official_paths.BASE_SCHEMA_DIR.glob("*.json") if p.name.startswith("API.")])

    if not command_files:
        print("❌ ERROR: No command schema files (API.*.json) found. Did the crawler run successfully?")
        return

    print(f"🔍 Found {len(command_files)} command files to process...")

    for path in command_files:
        details = get_command_details_from_file(path)
        if details:
            group = filename_to_group.get(path.name, "Uncategorized")
            details["group"] = group
            details["version"] = "N/A"  # Official API does not have versioning per command
            all_command_details.append(details)

    # 3. Sort alphabetically by command name for consistent output.
    sorted_details = sorted(all_command_details, key=lambda x: x["name"])

    # 4. Write the structured details to the output file.
    output_path = official_paths.COMMAND_DETAILS_OUTPUT
    print(f"\n💾 Writing {len(sorted_details)} command details to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_details, f, indent=4)

    print("✅ Successfully generated command details file.")


if __name__ == "__main__":
    main()
