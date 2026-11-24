from typing import Literal

from pydantic import BaseModel, Field

from code_generation.shared.default_policy_audit import audit_models, audit_provider


def test_audit_detects_invalid_requiredness_and_aliases():
    class Sample(BaseModel):
        tag: Literal["x"] = Field("x", alias="wireTag")
        success: Literal[False] = False
        count: int = 1
        nullable: Literal["x"] | None = None

    schema = {
        "Sample": {
            "type": "object",
            "properties": {"wireTag": {}, "success": {}, "count": {}, "nullable": {}},
            "required": ["wireTag", "success"],
        }
    }
    assert audit_models("fixture", schema, [Sample]) == []
    schema["Sample"]["required"] = ["success", "count"]
    findings = audit_models("fixture", schema, [Sample])
    assert any("Sample.tag" in f and "optional" in f for f in findings)
    assert any("Sample.count" in f and "wire-required" in f for f in findings)
    del schema["Sample"]["properties"]["wireTag"]
    assert any("Sample.tag" in f and "mapping" in f for f in audit_models("fixture", schema, [Sample]))


def test_reference_and_branch_requiredness():
    class Sample(BaseModel):
        tag: Literal["x"] = "x"

    defs = {
        "Sample": {"allOf": [{"$ref": "#/$defs/Shared"}]},
        "Shared": {"properties": {"tag": {}}, "anyOf": [{"required": ["tag"]}, {"required": ["tag"]}]},
    }
    assert audit_models("fixture", defs, [Sample]) == []
    defs["Shared"]["anyOf"][1] = {}
    assert audit_models("fixture", defs, [Sample])


def test_current_providers():
    assert audit_provider("tapir") == []
    assert audit_provider("official") == []


def test_unified_preflight_precedes_rewrite(monkeypatch, tmp_path):
    import subprocess
    import pytest
    from code_generation.unified.api_generator import run_pipeline

    output = tmp_path / "organized.json"
    output.write_text("original", encoding="utf8")
    monkeypatch.setattr(run_pipeline, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(run_pipeline, "ORGANIZED_COMMANDS_PATH", output)

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(run_pipeline.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        run_pipeline.main()
    assert output.read_text(encoding="utf8") == "original"
