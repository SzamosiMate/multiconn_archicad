from copy import deepcopy

import pytest

from code_generation.shared import schema_patching

pytestmark = pytest.mark.unit

HELPERS = [
    schema_patching.extract_inline_schema,
    schema_patching.extract_inline_enum,
    schema_patching.replace_inline_schema_with_ref,
]


@pytest.mark.parametrize("helper", HELPERS)
@pytest.mark.parametrize("is_array", [False, True])
def test_inline_target_is_replaced_and_extractions_preserve_schema(helper, is_array):
    inline = {"type": "string", "enum": ["first", "second"], "description": "Context"}
    field = {"type": "array", "items": deepcopy(inline)} if is_array else deepcopy(inline)
    definitions = {"Command": {"type": "object", "properties": {"field": field}}}
    path = ["field", "items"] if is_array else ["field"]

    helper(definitions, "Command", path, "NamedDefinition")

    actual = definitions["Command"]["properties"]["field"]
    if is_array:
        actual = actual["items"]
    assert actual == {"$ref": "#/$defs/NamedDefinition"}
    if helper is schema_patching.replace_inline_schema_with_ref:
        assert "NamedDefinition" not in definitions
    else:
        assert definitions["NamedDefinition"] == inline


def test_replacement_preserves_contextual_description_when_requested():
    definitions = {
        "Command": {"properties": {"field": {"type": "string", "description": "Context"}}},
        "NamedDefinition": {"type": "string"},
    }

    schema_patching.replace_inline_schema_with_ref(
        definitions, "Command", ["field"], "NamedDefinition", preserve_description=True
    )

    assert definitions["Command"]["properties"]["field"] == {
        "$ref": "#/$defs/NamedDefinition",
        "description": "Context",
    }


@pytest.mark.parametrize("helper", HELPERS)
@pytest.mark.parametrize("missing_parent", [False, True])
def test_missing_target_fails_without_modifying_schema(helper, missing_parent):
    definitions = {} if missing_parent else {"Command": {"properties": {}}}
    original = deepcopy(definitions)

    with pytest.raises(KeyError) as error:
        helper(definitions, "Command", ["field"], "NamedDefinition")

    assert "Command" in str(error.value)
    assert "not found" in str(error.value) if missing_parent else "does not resolve" in str(error.value)
    assert definitions == original


@pytest.mark.parametrize("helper", HELPERS)
@pytest.mark.parametrize("reference", ["#/$defs/NamedDefinition", "#/$defs/UnexpectedDefinition"])
def test_existing_reference_requires_review_even_when_name_matches(helper, reference):
    definitions = {"Command": {"properties": {"field": {"type": "array", "items": {"$ref": reference}}}}}
    original = deepcopy(definitions)
    path = ["field", "items"]

    with pytest.raises(ValueError) as error:
        helper(definitions, "Command", path, "NamedDefinition")

    message = str(error.value)
    assert "Command" in message
    assert str(path) in message
    assert reference in message
    assert "Review the upstream definition" in message
    assert definitions == original
