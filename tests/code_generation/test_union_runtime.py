import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError, field_validator, model_validator
from multiconn_archicad.models.union import UnionModel, bind_variants


def test_validation_context_strict_mode_and_no_double_initialization():
    calls = []

    class Choice(UnionModel):
        x: int | None = None
        y: int | None = None

    class X(Choice):
        x: int

        @field_validator("x")
        @classmethod
        def with_context(cls, value, info):
            return value + (info.context or {}).get("offset", 0)

        @model_validator(mode="after")
        def counted(self):
            calls.append("X")
            return self

    class Y(Choice):
        y: int

    bind_variants(Choice, X | Y)
    assert Choice(x=2).x == 2
    assert calls == ["X"]
    calls.clear()
    assert Choice.model_validate({"x": 2}, context={"offset": 4}).x == 6
    assert calls == ["X"]
    with pytest.raises(ValidationError):
        Choice.model_validate({"x": "2"}, strict=True)
    with pytest.raises(TypeError):
        bind_variants(Choice, X | Y)


def test_bound_parent_schema_preserves_variants_and_metadata_in_both_modes():
    class Choice(UnionModel):
        """Choose either coordinate."""

        x: int | None = None
        y: int | None = None

    class X(Choice):
        x: int

    class Y(Choice):
        y: int

    bind_variants(Choice, X | Y)

    class Request(BaseModel):
        choice: Choice

    for mode in ("validation", "serialization"):
        schema = Choice.model_json_schema(mode=mode)
        assert schema["title"] == "Choice"
        assert schema["description"] == "Choose either coordinate."
        assert schema == TypeAdapter(Choice).json_schema(mode=mode)
        assert len(schema["anyOf"]) == 2
        assert schema["$defs"]["X"]["required"] == ["x"]
        assert schema["$defs"]["Y"]["required"] == ["y"]
        nested = Request.model_json_schema(mode=mode)
        assert nested["properties"]["choice"]["anyOf"]
        assert nested["$defs"]["X"]["properties"]["x"]["type"] == "integer"

    obj = Choice.model_validate_json('{"x":2}')
    assert type(obj) is X
    assert Choice.model_validate(obj) is obj
    assert Request(choice=obj).choice is obj
    assert obj.model_dump_json() == '{"x":2}'
    with pytest.raises(TypeError):
        bind_variants(Choice, int | str)
