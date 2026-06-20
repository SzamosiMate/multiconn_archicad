from typing import Any, Optional


def _get_target_from_path(defs: dict[str, Any], parent_name: str, path: list[str]) -> tuple[
    Optional[dict], Optional[dict], str]:
    """
    Navigates the schema dict. Returns (parent_of_target, target_schema, last_key_used).
    Automatically assumes segments are properties unless the segment is 'items'.
    """
    if parent_name not in defs:
        return None, None, ""

    current = defs[parent_name]

    # We need to keep track of the container to perform the $ref swap at the end
    parent_of_target = None
    last_key = ""

    for segment in path:
        parent_of_target = current
        last_key = segment

        if segment == "items":
            current = current.get("items")
        else:
            # Assume it is a property
            current = current.get("properties", {}).get(segment)

        if not isinstance(current, dict):
            return None, None, ""

    return parent_of_target, current, last_key


def extract_inline_schema(defs: dict[str, Any], parent_name: str, path: list[str], new_def_name: str):
    """
    Helper to extract an inline schema definition into a named $ref.
    Path is simplified: ['surveyPoint', 'position'] instead of ['properties', 'surveyPoint', 'properties', 'position']
    """
    container, target_schema, key = _get_target_from_path(defs, parent_name, path)

    if not target_schema or "$ref" in target_schema:
        return

    print(f"  -> Extracting Model {parent_name} / {path} to {new_def_name}")

    # 1. Store the target in top-level defs
    defs[new_def_name] = target_schema

    # 2. Replace the original location with a $ref
    if container:
        if key == "items":
            container["items"] = {"$ref": f"#/$defs/{new_def_name}"}
        else:
            container["properties"][key] = {"$ref": f"#/$defs/{new_def_name}"}


def extract_inline_enum(defs: dict[str, Any], parent_name: str, path: list[str], new_def_name: str):
    """
    Helper to extract an inline enum definition into a named $ref.
    """
    container, target_schema, key = _get_target_from_path(defs, parent_name, path)

    if not target_schema or "$ref" in target_schema:
        return

    if "enum" not in target_schema:
        print(f"  -> Warning: Expected enum at {parent_name} / {path}, but found none.")
        return

    print(f"  -> Extracting Enum {parent_name} / {path} to {new_def_name}")

    defs[new_def_name] = target_schema
    if container:
        if key == "items":
            container["items"] = {"$ref": f"#/$defs/{new_def_name}"}
        else:
            container["properties"][key] = {"$ref": f"#/$defs/{new_def_name}"}


def replace_inline_schema_with_ref(
    defs: dict[str, Any], parent_name: str, path: list[str], ref_name: str, preserve_description: bool = False
):
    """
    Replaces an inline schema at the given path with a $ref.
    Optionally preserves the original 'description' as a sibling keyword (valid in Draft 2019-09).
    """
    container, target_schema, key = _get_target_from_path(defs, parent_name, path)

    if not target_schema or "$ref" in target_schema:
        return

    print(f"  -> Replacing inline Model {parent_name} / {path} with {ref_name}")

    new_schema = {"$ref": f"#/$defs/{ref_name}"}

    if preserve_description and "description" in target_schema:
        new_schema["description"] = target_schema["description"]

    if container:
        if key == "items":
            container["items"] = new_schema
        else:
            container["properties"][key] = new_schema


def apply_permanent_patches(master_defs: dict[str, Any]):
    """
    Patches that are required permanently due to limitations in code generators
    or conscious design choices in our Python client (e.g., forcing better names).
    """
    print("Applying permanent schema patches...")

    # --- 1. Fix array element names (e.g., ZonesDatum -> ZoneData) ---
    creation_data_types = {
        "CreateColumnsParameters": ("columnsData", "ColumnData"),
        "CreateSlabsParameters": ("slabsData", "SlabData"),
        "CreatePolylinesParameters": ("polylinesData", "PolylineData"),
        "CreateObjectsParameters": ("objectsData", "ObjectData"),
        "CreateMeshesParameters": ("meshesData", "MeshData"),
        "CreateZonesParameters": ("zonesData", "ZoneData"),
        "CreateBeamsParameters": ("beamsData", "BeamData"),
        "CreateWallsParameters": ("wallsData", "WallData"),
        "CreateLabelsParameters": ("labelsData", "LabelData"),
        "CreateDetailsParameters": ("detailsData", "DetailData"),
        "CreateWorksheetsParameters": ("worksheetsData", "WorksheetData"),
        "CreateLayoutsParameters": ("layoutsData", "LayoutData"),
        "CreateSubsetsParameters": ("subsetsData", "SubsetData"),
        "CreateDrawingsParameters": ("drawingsData", "DrawingData"),
        "CreateWindowsParameters": ("windowsData", "WindowData"),
        "CreateDoorsParameters": ("doorsData", "DoorData"),
        "CreateMorphsParameters": ("morphsData", "MorphData"),
        "CreateRoofsParameters": ("roofsData", "RoofData"),
        "CreateOpeningsParameters": ("openingsData", "OpeningData"),
        "CreateAssociativeDimensionsParameters": ("dimensionsData", "AssociativeDimensionData"),
        "CreateAssociativeDimensionsOnSectionParameters": ("dimensionsData", "AssociativeDimensionOnSectionData"),
        "CreateWallThicknessDimensionsParameters": ("dimensionsData", "WallThicknessDimensionData"),
        "CreateSectionsParameters": ("sectionsData", "SectionData"),
        "CreateStairsParameters": ("stairsData", "SectionData"),
        "CreateLampsParameters": ("lampsData", "LampData"),
        "CreateTextsParameters": ("textsData", "TextData"),
    }

    for parent_model, (field_name, new_model_name) in creation_data_types.items():
        extract_inline_schema(master_defs, parent_model, [field_name, "items"], new_model_name)

    element_modification_datatypes = {
        "ModifyWallsParameters": ("wallsWithDetails", "WallWithDetails"),
        "ModifyBeamsParameters": ("beamsWithDetails", "BeamWithDetails"),
        "ModifySlabsParameters": ("slabsWithDetails", "SlabWithDetails"),
        "ModifyColumnsParameters": ("columnsWithDetails", "ColumnWithDetails"),
        "ModifyWindowsParameters": ("windowsWithDetails", "WindowWithDetails"),
        "ModifyDoorsParameters": ("doorsWithDetails", "DoorWithDetails"),
        "ModifyMorphsParameters": ("morphsWithDetails", "MorphWithDetails"),
        "ModifyRoofsParameters": ("roofsWithDetails", "RoofWithDetails"),
    }

    for parent_model, (field_name, new_model_name) in element_modification_datatypes.items():
        extract_inline_schema(master_defs, parent_model, [field_name, "items"], new_model_name)


def apply_temporary_patches(master_defs: dict[str, Any]):
    """
    Patches that we expect to be fixed on the Tapir side eventually.
    Once the upstream schema is fixed, these can be deleted.
    """
    print("Applying temporary schema patches (pending upstream fixes)...")

    # --- Extract specific inline Enums ---
    extract_inline_enum(master_defs, "WallDetails", ["structureType"], "WallStructureType")
    extract_inline_enum(master_defs, "WallData", ["structureType"], "WallStructureType")
    extract_inline_enum(master_defs, "WallWithDetails", ["structureType"], "WallStructureType")
    extract_inline_enum(master_defs, "SlabDetails", ["structureType"], "SlabStructureType")
    extract_inline_enum(master_defs, "SlabWithDetails", ["structureType"], "SlabStructureType")
    extract_inline_enum(master_defs, "RoofData", ["structureType"], "RoofStructureType")
    extract_inline_enum(master_defs, "RoofWithDetails", ["structureType"], "RoofStructureType")

    # --- Replace inline Coordinate2D properties in RotateElementsParameters ---
    replace_inline_schema_with_ref(master_defs, "RotateElementsParameters", ["elementsWithRotations", "items", "rotation", "beginPoint"], "Coordinate2D", preserve_description=True)
    replace_inline_schema_with_ref(master_defs, "RotateElementsParameters", ["elementsWithRotations", "items", "rotation", "endPoint"], "Coordinate2D", preserve_description=True)
    replace_inline_schema_with_ref(master_defs, "RotateElementsParameters", ["elementsWithRotations", "items", "rotation", "origin"], "Coordinate2D", preserve_description=True)

    # --- Extract conflicting inline Schemas ---
    extract_inline_schema(master_defs, "DimensionData", ["witnessPoints", "items"], "CoordinateWitnessPoint")
    extract_inline_schema(master_defs, "AssociativeDimensionData", ["witnessPoints", "items"], "AssociativeWitnessPoint")
    extract_inline_schema(
        master_defs, "CreateProjectInfoFieldsParameters", ["projectInfoFields", "items"], "ProjectInfoFieldData"
    )
    extract_inline_schema(master_defs, "CreateDesignOptionsParameters", ["designOptions", "items"], "DesignOptionData")
    extract_inline_schema(
        master_defs,
        "GetDesignOptionCombinationsResult",
        ["designOptionCombinations", "items"],
        "DesignOptionCombinationDetails",
    )
    extract_inline_schema(
        master_defs,
        "CreateDesignOptionCombinationsParameters",
        ["designOptionCombinations", "items"],
        "DesignOptionCombinationData",
    )

    # --- Unify GeoLocation schemas ---
    extract_inline_schema(master_defs, "GetGeoLocationResult", ["projectLocation"], "ProjectLocation")
    extract_inline_schema(master_defs, "GetGeoLocationResult", ["surveyPoint", "position"], "SurveyPointPosition")
    extract_inline_schema(master_defs, "GetGeoLocationResult", ["surveyPoint", "geoReferencingParameters"],
                          "GeoReferencingParameters")
    extract_inline_schema(master_defs, "GetGeoLocationResult", ["surveyPoint"], "SurveyPoint")

    # Fix the bad inline schema by pointing it to the existing ArrayItem definition
    if "GetElementsOfDesignOptionsParameters" in master_defs:
        params = master_defs["GetElementsOfDesignOptionsParameters"].get("properties", {})
        if "designOptions" in params:
            params["designOptions"]["items"] = {"$ref": "#/$defs/DesignOptionIdArrayItem"}

    # Fix broken #ref in GetElementsOfDesignOptionsResult
    if "GetElementsOfDesignOptionsResult" in master_defs:
        res_props = master_defs["GetElementsOfDesignOptionsResult"].get("properties", {})
        if "elementsOfDesignOptions" in res_props:
            res_props["elementsOfDesignOptions"]["items"] = {
                "$ref": "#/$defs/ElementsOfDesignOptionOrError"
            }

    if "SetGeoLocationParameters" in master_defs:
        params = master_defs["SetGeoLocationParameters"]["properties"]
        if "projectLocation" in params:
            params["projectLocation"] = {"$ref": "#/$defs/ProjectLocation"}
        if "surveyPoint" in params:
            params["surveyPoint"] = {"$ref": "#/$defs/SurveyPoint"}

    nav_window = master_defs.get("NavigatorItemIdOrDatabaseIdAndWindowType")
    if nav_window and "oneOf" in nav_window and len(nav_window["oneOf"]) > 1:
        # Extract the second union element (the inline object) to a new definition
        master_defs["DatabaseIdAndWindowType"] = nav_window["oneOf"][1]
        # Replace the inline object with a $ref
        nav_window["oneOf"][1] = {"$ref": "#/$defs/DatabaseIdAndWindowType"}

    # --- Unify Zoom schemas ---
    extract_inline_schema(master_defs, "ViewTransformations", ["zoom"], "Zoom")

    if "ViewSettings" in master_defs:
        params = master_defs["ViewSettings"]["properties"]
        if "zoom" in params:
            params["zoom"] = {"$ref": "#/$defs/Zoom"}

    # --- remove malformed Export Favorites result ---
        master_defs.pop("ExportFavoritesResult", None)
