import json
from pathlib import Path
from typing import Any, Dict, List, Set

from code_generation.official.paths import official_paths


def fix_refs_recursively(data: Any) -> Any:
    """Recursively corrects '$ref' paths to point to the new local '$defs'."""
    if isinstance(data, dict):
        if "$ref" in data and isinstance(data["$ref"], str):
            # Transform "APITypes.json#/definitions/Guid" -> "#/$defs/Guid"
            # or "#/definitions/Error" -> "#/$defs/Error"
            ref_path = data["$ref"]
            def_name = ref_path.split("/")[-1]
            data["$ref"] = f"#/$defs/{def_name}"
        return {key: fix_refs_recursively(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [fix_refs_recursively(item) for item in data]
    else:
        return data


def process_type_schema(path: Path, all_defs: Dict[str, Any], base_names: Set[str]):
    """Loads definitions from a type schema file (e.g., APITypes.json)."""
    print(f"   - Processing types from: {path.name}")
    try:
        data = json.loads(path.read_text("utf-8"))
        definitions = data.get("definitions", {})
        for name, definition in definitions.items():
            if name in ["AddOnCommandParameters", "AddOnCommandResponse"]:
                all_defs[name] = definition
                base_names.add(name)
            else:
                all_defs.update({name: definition})
                base_names.add(name)
    except (json.JSONDecodeError, IOError) as e:
        print(f"   ⚠️ Could not process {path.name}: {e}")


def process_command_schema(path: Path, all_defs: Dict[str, Any], command_names: Set[str]):
    """Loads and renames definitions from a command schema file."""
    print(f"   - Processing command: {path.name}")
    try:
        data = json.loads(path.read_text("utf-8"))
        command_name = path.stem.replace("API.", "")  # "API.CreateLayout" -> "CreateLayout"

        definitions = data.get("definitions", {})
        if params := definitions.get("command_parameters"):
            # Only add parameters if they have properties or are a oneOf/anyOf union
            if params.get("properties") or params.get("oneOf") or params.get("anyOf"):
                new_name = f"{command_name}Parameters"
                all_defs[new_name] = params
                command_names.add(new_name)

        if result := definitions.get("response_parameters"):
            # Only add results if they have properties
            if result.get("properties"):
                new_name = f"{command_name}Result"
                all_defs[new_name] = result
                command_names.add(new_name)

    except (json.JSONDecodeError, IOError) as e:
        print(f"   ⚠️ Could not process {path.name}: {e}")


def main():
    """
    Consolidates all downloaded schemas into a single master schema file
    and generates lists of the definition names.
    """
    print("--- Starting Official API Master Schema Generation ---")
    official_paths.create_directories()

    all_definitions: Dict[str, Any] = {}
    base_model_names: Set[str] = set()
    command_model_names: Set[str] = set()

    # 1. Iterate through all downloaded JSON files and process them.
    schema_files = sorted(list(official_paths.BASE_SCHEMA_DIR.glob("*.json")))
    if not schema_files:
        print("❌ ERROR: No schema files found. Did the crawler run successfully?")
        return

    for path in schema_files:
        # Heuristic: command files start with "API.", type files do not.
        if path.name.startswith("API."):
            process_command_schema(path, all_definitions, command_model_names)
        else:
            process_type_schema(path, all_definitions, base_model_names)

    print(f"\n✅ Collected {len(all_definitions)} total definitions.")
    print(f"   ({len(base_model_names)} base types, {len(command_model_names)} command models)")

    # 2. Fix all internal references to point to the new '$defs' structure.
    print("\n🔧 Fixing all $ref pointers...")
    fixed_definitions = fix_refs_recursively(all_definitions)
    print("✅ All references updated.")

    # 3. Assemble the final master schema object.
    master_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "OfficialArchicadApiMasterModels",
        "description": "A consolidated, single-file schema for the official Archicad JSON API.",
        "$defs": fixed_definitions,
    }

    # 4. Write the master schema and helper name lists to disk.
    print(f"\n💾 Writing master schema to: {official_paths.MASTER_SCHEMA_OUTPUT}")
    with open(official_paths.MASTER_SCHEMA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(master_schema, f, indent=2)

    with open(official_paths.BASE_MODEL_NAMES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted(list(base_model_names)), f, indent=2)

    with open(official_paths.COMMAND_MODELS_NAMES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted(list(command_model_names)), f, indent=2)

    print("✅ Successfully generated all schema and name list files.")


if __name__ == "__main__":
    main()
