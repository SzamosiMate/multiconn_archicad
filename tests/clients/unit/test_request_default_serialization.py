import json
from typing import Literal

from pydantic import Field, TypeAdapter, field_serializer

from multiconn_archicad.models.base import APIModel
from multiconn_archicad.models.tapir.types import NormalNumberPropertyValue


class Record(APIModel):
    kind: Literal["record"] = Field("record", serialization_alias="wireKind")
    success: Literal[False] = False
    value: int
    flag: bool = False
    items: list[int] = []


class Container(APIModel):
    records: list[Record]


def test_nested_default_exclusion_and_aliases():
    obj = Container(records=[Record(value=3), Record(value=4, flag=True, items=[1])])
    expected = {
        "records": [
            {"wireKind": "record", "success": False, "value": 3},
            {"wireKind": "record", "success": False, "value": 4, "flag": True, "items": [1]},
        ]
    }
    assert obj.model_dump(mode="json", exclude_defaults=True) == expected
    assert json.loads(obj.model_dump_json(exclude_defaults=True)) == expected
    assert TypeAdapter(Container).dump_python(obj, mode="json", exclude_defaults=True) == expected
    assert obj.records[0].model_dump(by_alias=False, exclude_defaults=True)["kind"] == "record"
    assert obj.records[0].model_dump()["flag"] is False
    assert NormalNumberPropertyValue(value=3).model_dump(exclude_defaults=True) == {
        "type": "number",
        "status": "normal",
        "value": 3.0,
    }


def test_explicit_filters_and_context():
    class Filtered(APIModel):
        kind: Literal["a"] = "a"
        hidden: Literal["b"] = Field("b", exclude=True)

        @field_serializer("kind")
        def serialize_kind(self, value, info):
            return info.context["prefix"] + value

    obj = Filtered()
    assert obj.model_dump(exclude_defaults=True, context={"prefix": "x"}) == {"kind": "xa"}
    assert obj.model_dump(exclude_defaults=True, exclude={"kind"}, context={"prefix": "x"}) == {}
    assert obj.model_dump(exclude_defaults=True, include={"hidden"}, context={"prefix": "x"}) == {}
    assert obj.model_dump(exclude_defaults=True, exclude_unset=True, context={"prefix": "x"}) == {}


def test_omit_defaults_mixin_in_fresh_process():
    import subprocess
    import sys

    code = """
from typing import Literal
from multiconn_archicad.models.config import configure
from multiconn_archicad.models.mixins import OmitDefaultsMixin
configure(OmitDefaultsMixin)
from multiconn_archicad.models.base import APIModel
class Item(APIModel):
    kind: Literal["x"] = "x"
    flag: bool = False
item = Item()
assert item.model_dump() == {"kind": "x"}
assert item.model_dump(exclude_defaults=False) == {"kind": "x", "flag": False}
assert item.model_dump_json() == '{"kind":"x"}'
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_root_union_preserves_payload_shape():
    from pydantic import RootModel

    class Wrapped(RootModel[Record | str]):
        pass

    value = Wrapped.model_validate({"value": 3})
    assert value.model_dump(mode="json", exclude_defaults=True) == {"wireKind": "record", "success": False, "value": 3}
    assert TypeAdapter(Record | str).dump_python(value.root, mode="json", exclude_defaults=True) == {
        "wireKind": "record",
        "success": False,
        "value": 3,
    }


def test_wrap_serializer_keeps_field_schemas_in_both_modes():
    for mode in ("validation", "serialization"):
        schema = Container.model_json_schema(mode=mode)
        assert schema["properties"]["records"]["items"] == {"$ref": "#/$defs/Record"}
        record = schema["$defs"]["Record"]
        kind = "wireKind" if mode == "serialization" else "kind"
        assert record["properties"][kind]["const"] == "record"
        assert record["properties"]["value"]["type"] == "integer"
        assert record["required"] == ["value"]
