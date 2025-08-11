import json
import re
import pathlib
import urllib.request
from typing import Any, Dict, List
from code_generation.tapir.paths import paths

def apply_fixes(content: str) -> str:
    content = content.replace('"type": "double"', '"type": "number"')
    return content


def fetch_file_content(url: str) -> str:
    """Fetches the content of a file from a URL."""
    print(f"Fetching data from {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                return apply_fixes(response.read().decode("utf-8"))
            else:
                raise ConnectionError(f"Failed to fetch file: HTTP {response.status}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        raise


def parse_js_variable(js_content: str, var_name: str) -> Any:
    """Strips the JavaScript variable assignment to extract the raw JSON-like object."""
    pattern = re.compile(rf"^\s*var\s+{var_name}\s*=\s*", re.MULTILINE)
    json_str = pattern.sub("", js_content, count=1).strip().rstrip(";")
    if not json_str:
        raise ValueError(f"Could not find or parse variable '{var_name}' in the provided content.")
    return json.loads(json_str)


def fix_refs_recursive(data: Any) -> Any:
    """Recursively corrects '$ref' paths in the schema to point to '#/$defs/'."""
    if isinstance(data, dict):
        if "$ref" in data and isinstance(data["$ref"], str):
            ref_path = data["$ref"]
            if ref_path.startswith("#/") and not ref_path.startswith("#/$defs/"):
                def_name = ref_path.split("/")[-1]
                data["$ref"] = f"#/$defs/{def_name}"
        return {key: fix_refs_recursive(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [fix_refs_recursive(item) for item in data]
    else:
        return data


def get_command_defs(commands_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extracts schema definitions for command parameters and results."""
    command_defs: Dict[str, Any] = {}
    for command_group in commands_list:
        for command in command_group.get("commands", []):
            command_name = command.get("name")
            if not command_name:
                continue
            if command.get("inputScheme"):
                command_defs[f"{command_name}Parameters"] = command["inputScheme"]
            if command.get("outputScheme") and command["outputScheme"].get("type") == "object":
                command_defs[f"{command_name}Result"] = command["outputScheme"]
    return command_defs


def get_structured_command_details(commands_list: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extracts detailed info (name, group, description, version) for each command,
    preserving the group structure.
    """
    print("Extracting structured command details (group, version, description)...")
    details = []
    for command_group in commands_list:
        group_name = command_group.get("name", "Uncategorized")
        for command in command_group.get("commands", []):
            if name := command.get("name"):
                details.append({
                    "name": name,
                    "group": group_name,
                    "description": command.get("description", ""),
                    "version": command.get("version", "N/A"),
                })
    # Sort alphabetically by command name for consistent output
    return sorted(details, key=lambda x: x['name'])


def generate_literal_commands_file(tapir_commands: List[str], output_path: pathlib.Path):
    """Generates the literal_commands.py file from a static template and a dynamic list."""
    print(f"Generating literal commands file at {output_path}...")

    # Static template for the official Archicad commands, which are not in the schema
    addon_command_template = """
AddonCommandType = Literal[
    "API.ExecuteAddOnCommand",
    "API.IsAddOnCommandAvailable",
    "API.CreateAttributeFolders",
    "API.DeleteAttributeFolders",
    "API.DeleteAttributes",
    "API.GetActivePenTables",
    "API.GetAttributeFolders",
    "API.GetAttributeFolderStructure",
    "API.GetAttributesIndices",
    "API.GetAttributesByType",
    "API.GetBuildingMaterialAttributes",
    "API.GetCompositeAttributes",
    "API.GetFillAttributes",
    "API.GetLayerAttributes",
    "API.GetLayerCombinationAttributes",
    "API.GetLineAttributes",
    "API.GetPenTableAttributes",
    "API.GetProfileAttributes",
    "API.GetProfileAttributePreview",
    "API.GetSurfaceAttributes",
    "API.GetZoneCategoryAttributes",
    "API.MoveAttributesAndFolders",
    "API.RenameAttributeFolders",
    "API.IsAlive",
    "API.GetProductInfo",
    "API.GetAllElements",
    "API.GetSelectedElements",
    "API.GetElementsByType",
    "API.GetTypesOfElements",
    "API.GetElementsByClassification",
    "API.GetAllClassificationSystems",
    "API.GetClassificationSystemIds",
    "API.GetClassificationSystems",
    "API.GetAllClassificationsInSystem",
    "API.GetDetailsOfClassificationItems",
    "API.GetClassificationItemAvailability",
    "API.GetClassificationsOfElements",
    "API.SetClassificationsOfElements",
    "API.GetPropertyIds",
    "API.GetAllPropertyIds",
    "API.GetAllPropertyNames",
    "API.GetDetailsOfProperties",
    "API.GetPropertyDefinitionAvailability",
    "API.GetPropertyGroups",
    "API.GetAllPropertyGroupIds",
    "API.GetPropertyValuesOfElements",
    "API.GetAllPropertyIdsOfElements",
    "API.SetPropertyValuesOfElements",
    "API.GetPublisherSetNames",
    "API.GetNavigatorItemsType",
    "API.GetNavigatorItemTree",
    "API.DeleteNavigatorItems",
    "API.RenameNavigatorItem",
    "API.MoveNavigatorItem",
    "API.GetBuiltInContainerNavigatorItems",
    "API.GetElevationNavigatorItems",
    "API.GetInteriorElevationNavigatorItems",
    "API.GetDetailNavigatorItems",
    "API.GetWorksheetNavigatorItems",
    "API.GetSectionNavigatorItems",
    "API.GetStoryNavigatorItems",
    "API.GetDocument3DNavigatorItems",
    "API.CloneProjectMapItemToViewMap",
    "API.CreateViewMapFolder",
    "API.CreateLayoutSubset",
    "API.GetLayoutSettings",
    "API.CreateLayout",
    "API.SetLayoutSettings",
    "API.Get2DBoundingBoxes",
    "API.Get3DBoundingBoxes",
    "API.GetElementsRelatedToZones",
    "API.GetComponentsOfElements",
    "API.GetPropertyValuesOfElementComponents",
]
"""
    formatted_tapir_commands = ",\n".join(f'    "{name}"' for name in tapir_commands)
    file_content = f"""from typing import Literal
{addon_command_template}

TapirCommandType = Literal[
{formatted_tapir_commands},
]
"""
    output_path.write_text(file_content, encoding="utf-8")


def main():
    """
    Fetches, parses, and merges schema definitions, and generates all
    necessary schema and helper files for the project.
    """
    print("--- Starting Master Schema and Literals Generation ---")
    common_schema_js = fetch_file_content(paths.COMMON_SCHEMA_URL)
    command_defs_js = fetch_file_content(paths.COMMAND_DEFS_URL)

    print("Parsing JavaScript variable assignments...")
    common_defs: Dict[str, Any] = parse_js_variable(common_schema_js, "gSchemaDefinitions")
    commands_list: List[Dict[str, Any]] = parse_js_variable(command_defs_js, "gCommands")

    # --- Generate Schemas and Name Lists ---
    command_defs = get_command_defs(commands_list)
    master_defs = {**common_defs, **command_defs}
    print(f"Total unique definitions for master schema: {len(master_defs)}")

    master_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "TapirMasterModels",
        "description": "A consolidated, single-file schema for the Archicad Tapir JSON API.",
        "$defs": fix_refs_recursive(master_defs),
    }

    with open(paths.MASTER_SCHEMA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(master_schema, f, indent=2)
    print(f"✅ Successfully generated master schema at: {paths.MASTER_SCHEMA_OUTPUT}")

    with open(paths.BASE_MODEL_NAMES_OUTPUT, "w") as f:
        json.dump(list(common_defs.keys()), f)
    with open(paths.COMMAND_MODELS_NAMES_OUTPUT, "w") as f:
        json.dump(list(command_defs.keys()), f)
    print(f"✅ Successfully generated base and command model name lists.")

    structured_command_details = get_structured_command_details(commands_list)
    with open(paths.COMMAND_DETAILS_OUTPUT, "w", encoding="utf-8") as f:
        # Use indent for a human-readable JSON file
        json.dump(structured_command_details, f, indent=4)
    print(f"✅ Successfully generated structured command details at: {paths.COMMAND_DETAILS_OUTPUT}")

    # --- Generate literal_commands.py (deriving names from the new structure) ---
    tapir_command_names = sorted([cmd["name"] for cmd in structured_command_details])
    generate_literal_commands_file(tapir_command_names, paths.FINAL_LITERAL_COMMANDS)
    print(f"✅ Successfully generated literal commands at: {paths.FINAL_LITERAL_COMMANDS}")


if __name__ == "__main__":
    main()
