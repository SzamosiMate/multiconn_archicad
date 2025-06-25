import json
import re
import pathlib
import urllib.request
from typing import Any, Dict, List

# --- Configuration ---
COMMAND_DEFS_URL = "https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/main/docs/archicad-addon/command_definitions.js"
COMMON_SCHEMA_URL = "https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/main/docs/archicad-addon/common_schema_definitions.js"

COMMON_SCHEMA_OUTPUT = pathlib.Path("tapir_master_schema.json")


def fetch_file_content(url: str) -> str:
    """Fetches the content of a file from a URL."""
    print(f"Fetching data from {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                return response.read().decode('utf-8')
            else:
                raise ConnectionError(f"Failed to fetch file: HTTP {response.status}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        raise


def parse_js_variable(js_content: str, var_name: str) -> Any:
    """
    Strips the JavaScript variable assignment to extract the raw JSON-like object.
    """
    # Regex to find "var <var_name> = " and remove it, then clean up trailing characters.
    pattern = re.compile(rf"^\s*var\s+{var_name}\s*=\s*", re.MULTILINE)

    # Perform substitution, remove leading/trailing whitespace, and remove trailing semicolon.
    json_str = pattern.sub("", js_content, count=1).strip().rstrip(";")

    if not json_str:
        raise ValueError(f"Could not find or parse variable '{var_name}' in the provided content.")

    return json.loads(json_str)


def fix_refs_recursive(data: Any) -> Any:
    """
    Recursively walks through the schema data and corrects any '$ref' paths.

    A valid ref to a definition in '$defs' must be in the format '#/$defs/MyDefinition'.
    This function corrects paths like '#/MyDefinition'.
    """
    if isinstance(data, dict):
        if "$ref" in data and isinstance(data["$ref"], str):
            ref_path = data["$ref"]
            if ref_path.startswith("#/") and not ref_path.startswith("#/$defs/"):
                # Correct the path
                def_name = ref_path.split("/")[-1]
                data["$ref"] = f"#/$defs/{def_name}"

        return {key: fix_refs_recursive(value) for key, value in data.items()}

    elif isinstance(data, list):
        return [fix_refs_recursive(item) for item in data]

    else:
        return data


def create_master_schema():
    """
    Fetches, parses, and merges Tapir's schema definitions into a single,
    valid JSON Schema file, ready for code generation. This single-file
    approach is more robust than multi-file generation.
    """
    print("--- Starting Master Schema Generation ---")
    common_schema_js = fetch_file_content(COMMON_SCHEMA_URL)
    command_defs_js = fetch_file_content(COMMAND_DEFS_URL)

    print("Parsing JavaScript variable assignments...")
    common_defs: Dict[str, Any] = parse_js_variable(common_schema_js, "gSchemaDefinitions")
    commands_list: List[Dict[str, Any]] = parse_js_variable(command_defs_js, "gCommands")

    command_defs: Dict[str, Any] = {}
    for command_group in commands_list:
        group_name = command_group.get('group', 'UnknownGroup')
        for command in command_group.get("commands", []):
            command_name = command.get("name")
            if not command_name:
                print(f"Warning: Skipping command with no name in group '{group_name}'.")
                continue
            if command.get("inputScheme"):
                def_name = f"{command_name}Parameters"
                command_defs[def_name] = command["inputScheme"]
            if command.get("outputScheme") and command["outputScheme"].get("type") == "object":
                def_name = f"{command_name}Result"
                command_defs[def_name] = command["outputScheme"]

    print(f"Parsed {len(common_defs)} common definitions and {len(command_defs)} command-specific definitions.")

    master_defs = common_defs.copy()
    master_defs.update(command_defs)
    print(f"Total unique definitions after merge: {len(master_defs)}")

    master_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "TapirMasterModels",
        "description": "A consolidated, single-file schema for the Archicad Tapir JSON API. Generated for use with datamodel-code-generator.",
        "$defs": master_defs
    }

    # Recursively fix all '$ref' paths
    master_schema = fix_refs_recursive(master_schema)

    with open(MASTER_SCHEMA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(master_schema, f, indent=2)

    print(f"✅ Successfully generated master schema at: {MASTER_SCHEMA_OUTPUT}")


if __name__ == "__main__":
    create_master_schema()