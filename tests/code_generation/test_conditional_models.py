from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types

from datamodel_code_generator import DataModelType, InputFileType, generate
from datamodel_code_generator.format import Formatter
import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from code_generation.shared.conditional_models import (
    CONDITIONAL_OBJECT_MODELS,
    conditional_object_contract,
    prepare_model_schema,
)

cleaner = importlib.import_module("code_generation.tapir.model_generators.03_model_cleaner")
POLICY = {"RoofLevel": CONDITIONAL_OBJECT_MODELS["RoofLevel"]}


def _schema(form):
    common = {
        "type": "object",
        "properties": {
            "levelHeight": {"type": "number"},
            "levelAngle": {"type": "number", "exclusiveMinimum": 0},
            "height": {"type": "number"},
            "angle": {"type": "number", "exclusiveMinimum": 0},
            "note": {"type": ["string", "null"]},
        },
        "additionalProperties": False,
    }
    if form == "inline":
        definition = {
            **common,
            "anyOf": [{"required": ["levelHeight", "levelAngle"]}, {"required": ["height", "angle"]}],
        }
        definitions = {"RoofLevel": definition}
    else:
        definitions = {
            # Deliberately different upstream names and branch ordering.
            "NewHeightRecord": {**deepcopy(common), "required": ["height", "angle"]},
            "NewLevelRecord": {**deepcopy(common), "required": ["levelHeight", "levelAngle"]},
            "RoofLevel": {"anyOf": [{"$ref": "#/$defs/NewHeightRecord"}, {"$ref": "#/$defs/NewLevelRecord"}]},
        }
    return {"$defs": definitions}


def _generate(schema, tmp_path, monkeypatch, policy=POLICY):
    master = tmp_path / "master.json"
    master.write_text(json.dumps(schema), encoding="utf-8")
    monkeypatch.setattr(cleaner.tapir_paths, "MASTER_SCHEMA_OUTPUT", master)
    monkeypatch.setattr(cleaner, "CONDITIONAL_OBJECT_MODELS", policy)
    output = tmp_path / "generated.py"
    generate(
        json.dumps(prepare_model_schema(schema, pydantic=True, policies=policy)),
        input_file_type=InputFileType.JsonSchema,
        output=output,
        output_model_type=DataModelType.PydanticV2BaseModel,
        base_class="multiconn_archicad.models.base.APIModel",
        use_union_operator=True,
        use_double_quotes=True,
        field_constraints=True,
        use_annotated=False,
        collapse_root_models=True,
        skip_root_model=True,
        disable_timestamp=True,
        formatters=[Formatter.BLACK, Formatter.ISORT],
    )
    source = cleaner.configure_conditional_objects(output.read_text(encoding="utf-8"))
    source = cleaner.assemble_final_file(source)
    module = types.ModuleType("test_conditional_generated")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(source, str(output), "exec"), module.__dict__)
    for item in list(module.__dict__.values()):
        if isinstance(item, type) and issubclass(item, BaseModel):
            item.model_rebuild(_types_namespace=module.__dict__)
    return module


@pytest.mark.parametrize("form", ["inline", "references"])
def test_construction_validation_and_schema_survive_upstream_branch_naming(form, tmp_path, monkeypatch):
    source = _schema(form)
    original = deepcopy(source)
    module = _generate(source, tmp_path, monkeypatch)
    assert source == original
    model = module.RoofLevel
    for payload in (
        {"levelHeight": 0, "levelAngle": 0.5},
        {"height": 3, "angle": 0.5},
        {"levelHeight": 3, "levelAngle": 0.5, "height": 4, "angle": 0.7},
    ):
        result = model(**payload)
        assert isinstance(result, model)
        assert type(result) is not model
        assert result.model_dump(exclude_none=True) == payload
    for payload in (
        {},
        {"height": 3},
        {"levelHeight": 3, "angle": 0.5},
        {"height": 3, "angle": 0},
        {"height": 3, "angle": None},
    ):
        with pytest.raises(ValidationError):
            model(**payload)
    assert model(height=3, angle=0.5, note=None).note is None
    from collections import UserDict

    with pytest.raises(ValidationError):
        model.model_validate(UserDict({"height": 3}))

    # Already published helper instances also work inside consuming request fields.
    branch = module.RoofLevelWithHeight(height=3, angle=0.5)
    assert issubclass(module.RoofLevelWithHeight, model)
    assert isinstance(branch, model)
    assert TypeAdapter(model).validate_python(branch) is branch
    branch_schema = module.RoofLevelWithHeight.model_json_schema()
    assert set(branch_schema["required"]) == {"height", "angle"}
    assert "anyOf" not in branch_schema
    with pytest.raises(ValidationError):
        module.RoofLevelWithHeight(height=3)
    with pytest.raises(ValidationError):
        module.RoofLevelWithHeight(levelHeight=3, levelAngle=0.5)
    assert TypeAdapter(list[model]).validate_python([branch])[0].height == 3

    generated_schema = model.model_json_schema()
    assert {branch["$ref"].split("/")[-1] for branch in generated_schema["anyOf"]} == set(POLICY["RoofLevel"])
    height_schema = generated_schema["$defs"]["RoofLevelWithHeight"]
    assert set(height_schema["required"]) == {"height", "angle"}
    assert height_schema["properties"]["angle"]["exclusiveMinimum"] == 0
    assert model(height=3, angle=0.5, levelHeight=None).model_dump() == {"height": 3, "angle": 0.5}

    class Request(BaseModel):
        level: model

    assert isinstance(Request.model_validate({"level": {"height": 3, "angle": 0.5}}).level, module.RoofLevelWithHeight)


def test_adapter_variants_follow_new_schema_alternatives(tmp_path, monkeypatch):
    schema = _schema("inline")
    schema["$defs"]["RoofLevel"]["anyOf"].append({"required": ["height", "levelAngle"]})
    model = _generate(schema, tmp_path, monkeypatch).RoofLevel
    assert model(height=3, levelAngle=0.5).height == 3
    assert len(model.model_json_schema()["anyOf"]) == 3


def test_property_values_keep_common_ids_and_support_both_constructors(tmp_path, monkeypatch):
    schema = {
        "$defs": {
            "ElementPropertyValue": {
                "type": "object",
                "properties": {
                    "elementId": {"type": "string"},
                    "propertyId": {"type": "string"},
                    "propertyValue": {"type": "string"},
                    "valueStatus": {"type": "string", "enum": ["Value", "Default", "UserUndefined"]},
                },
                "required": ["elementId", "propertyId"],
                "anyOf": [{"required": ["propertyValue"]}, {"required": ["valueStatus"]}],
            }
        }
    }
    module = _generate(
        schema, tmp_path, monkeypatch, {"ElementPropertyValue": CONDITIONAL_OBJECT_MODELS["ElementPropertyValue"]}
    )
    model = module.ElementPropertyValue
    assert issubclass(module.ElementPropertyValueWithValue, model)
    assert issubclass(module.ElementPropertyValueWithStatus, model)
    ids = {"elementId": "element", "propertyId": "property"}
    assert model(**ids, propertyValue="text").propertyValue == "text"
    assert model(**ids, valueStatus="Default").valueStatus.value == "Default"
    assert model(**ids, propertyValue="text", valueStatus="Value").propertyValue == "text"
    for payload in (ids, {"propertyValue": "text"}, {**ids, "propertyValue": None}, {**ids, "valueStatus": "invalid"}):
        with pytest.raises(ValidationError):
            model(**payload)
    for branch in model.model_json_schema()["$defs"].values():
        if "properties" in branch and "elementId" in branch["properties"]:
            assert {"elementId", "propertyId"} <= set(branch["required"])


def test_typed_dict_projection_preserves_union_and_published_names():
    schema = _schema("references")
    projected = prepare_model_schema(schema, pydantic=False, policies=POLICY)
    assert projected["$defs"]["RoofLevel"] == schema["$defs"]["RoofLevel"]
    for helper in POLICY["RoofLevel"]:
        assert helper in projected["$defs"]


@pytest.mark.parametrize("change", ["constraints", "oneOf", "helper_conflict"])
def test_incompatible_contract_changes_fail_loudly(change):
    schema = _schema("references")
    if change == "constraints":
        schema["$defs"]["NewHeightRecord"]["properties"]["angle"]["minimum"] = 10
    elif change == "oneOf":
        schema["$defs"]["RoofLevel"]["oneOf"] = schema["$defs"]["RoofLevel"].pop("anyOf")
    else:
        schema["$defs"]["RoofLevelWithHeight"] = {"type": "object"}
    with pytest.raises(ValueError):
        prepare_model_schema(schema, pydantic=True, policies=POLICY)


@pytest.mark.parametrize("filename", ["tapir_master_schema.json", "tapir_unpatched_schema.json"])
def test_both_real_schema_forms_resolve_without_patch_helper_metadata(filename):
    root = Path(__file__).resolve().parents[2]
    schema = json.loads((root / "code_generation/tapir/schema" / filename).read_text(encoding="utf-8"))
    projected = prepare_model_schema(schema, pydantic=True)
    for name in CONDITIONAL_OBJECT_MODELS:
        assert "anyOf" not in projected["$defs"][name]
    contract = conditional_object_contract(schema["$defs"], "ElementPropertyValue")
    assert set(contract.schema["required"]) == {"elementId", "propertyId"}
    assert {frozenset(group) for group in contract.groups} == {frozenset(["propertyValue"]), frozenset(["valueStatus"])}


def test_current_generated_public_constructors_accept_published_helpers():
    from multiconn_archicad.models.tapir.types import (
        ElementId,
        ElementPropertyValue,
        ElementPropertyValueWithValue,
        Level,
        PropertyId,
        PropertyValue,
        RoofLevel,
        RoofLevelWithHeight,
    )

    assert Level is RoofLevel
    assert issubclass(RoofLevel, BaseModel)
    assert issubclass(RoofLevelWithHeight, RoofLevel)
    assert issubclass(ElementPropertyValueWithValue, ElementPropertyValue)
    assert RoofLevel(levelHeight=3, levelAngle=0.5).levelHeight == 3
    legacy_roof = RoofLevelWithHeight(height=3, angle=0.5, levelHeight=None)
    assert TypeAdapter(list[RoofLevel]).validate_python([legacy_roof])[0].height == 3
    ids = {
        "elementId": ElementId(guid="12345678-1234-1234-1234-123456789abc"),
        "propertyId": PropertyId(guid="22345678-1234-1234-1234-123456789abc"),
    }
    ids["propertyValue"] = PropertyValue(value="example")
    legacy_property = ElementPropertyValueWithValue(**ids, valueStatus=None)
    assert (
        TypeAdapter(list[ElementPropertyValue]).validate_python([legacy_property])[0].propertyValue.value == "example"
    )
    ids.pop("propertyValue")
    result = ElementPropertyValue(**ids, valueStatus="Default")
    payload = result.model_dump(mode="json", exclude_defaults=True)
    assert "propertyValue" not in payload
    with pytest.raises(ValidationError):
        ElementPropertyValue(**ids)
    assert ElementPropertyValue(**ids, valueStatus="Default", propertyValue=None).propertyValue is None

    from jsonschema import Draft7Validator

    roof_schema = Draft7Validator(RoofLevel.model_json_schema())
    assert roof_schema.is_valid({"height": 3, "angle": 0.5})
    assert not roof_schema.is_valid({"height": 3})
    assert not roof_schema.is_valid({"height": 3, "angle": None})
    property_schema = Draft7Validator(ElementPropertyValue.model_json_schema())
    assert property_schema.is_valid(payload)
    assert not property_schema.is_valid({key: value for key, value in payload.items() if key != "valueStatus"})


def test_public_variants_satisfy_base_annotations_with_mypy(tmp_path):
    valid = tmp_path / "valid_variants.py"
    valid.write_text(
        """from multiconn_archicad.models.tapir.types import (
    RoofLevel, RoofLevelWithHeight, RoofLevelWithLevelHeight,
    ElementPropertyValue, ElementPropertyValueWithValue, ElementPropertyValueWithStatus,
)

from typing import assert_type

assert_type(RoofLevel(height=3, angle=0.5), RoofLevel)
assert_type(RoofLevelWithHeight(height=3, angle=0.5), RoofLevelWithHeight)

def accept_roof(value: RoofLevel) -> None: pass
def accept_property(value: ElementPropertyValue) -> None: pass

def height_variant(value: RoofLevelWithHeight) -> float:
    accept_roof(value)
    return value.height

def level_variant(value: RoofLevelWithLevelHeight) -> float:
    accept_roof(value)
    return value.levelHeight

def property_variant(value: ElementPropertyValueWithValue) -> str:
    accept_property(value)
    return value.propertyValue.value

def status_variant(value: ElementPropertyValueWithStatus) -> None:
    accept_property(value)
""",
        encoding="utf-8",
    )
    invalid = tmp_path / "invalid_variant.py"
    invalid.write_text(
        """from multiconn_archicad.models.tapir.types import RoofLevel, ElementPropertyValue
def accept_roof(value: RoofLevel) -> None: pass
def wrong(value: ElementPropertyValue) -> None:
    accept_roof(value)
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--follow-imports=silent",
            "--ignore-missing-imports",
            "--no-incremental",
            "--cache-dir",
            str(tmp_path / "mypy-cache"),
            str(valid),
            str(invalid),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=90,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "valid_variants.py:" not in output, output
    assert "invalid_variant.py:" in output and "[arg-type]" in output, output
    assert "Found 1 error" in output, output
