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


@pytest.mark.parametrize("helper", HELPERS[:2])
def test_extraction_rejects_existing_definition_without_overwriting_it(helper):
    inline = {"type": "string", "enum": ["first", "second"]}
    definitions = {"Command": {"properties": {"field": inline}}, "NamedDefinition": deepcopy(inline)}
    original = deepcopy(definitions)

    with pytest.raises(ValueError, match="NamedDefinition.*already exists"):
        helper(definitions, "Command", ["field"], "NamedDefinition")

    assert definitions == original


def test_enum_extraction_requires_an_enum():
    definitions = {"Command": {"properties": {"field": {"type": "string"}}}}
    original = deepcopy(definitions)

    with pytest.raises(ValueError, match="Expected enum"):
        schema_patching.extract_inline_enum(definitions, "Command", ["field"], "NamedDefinition")

    assert definitions == original


def test_required_variants_reject_existing_names_before_mutating_schema():
    definitions = {
        "Command": {"properties": {"name": {"type": "string"}}, "oneOf": [{"required": ["name"]}, {"required": []}]},
        "Second": {"type": "string"},
    }
    original = deepcopy(definitions)

    with pytest.raises(ValueError, match="Second.*already exists"):
        schema_patching.name_required_variants(definitions, "Command", [], ["First", "Second"])

    assert definitions == original


@pytest.mark.parametrize("union_key", ["oneOf", "anyOf"])
def test_extract_union_variant_preserves_other_branches_and_constraints(union_key):
    branch = {"type": "object", "properties": {"value": {}}, "required": ["value"], "additionalProperties": False}
    definitions = {"Command": {"type": "object", union_key: [deepcopy(branch), {"$ref": "#/$defs/ErrorItem"}]}}

    schema_patching.extract_union_variant(definitions, "Command", [], 0, "NamedVariant")

    assert definitions["NamedVariant"] == branch
    assert definitions["Command"] == {
        "type": "object",
        union_key: [{"$ref": "#/$defs/NamedVariant"}, {"$ref": "#/$defs/ErrorItem"}],
    }
    original = deepcopy(definitions)
    with pytest.raises(ValueError, match="already references"):
        schema_patching.extract_union_variant(definitions, "Command", [], 0, "NamedVariant")
    assert definitions == original


@pytest.mark.parametrize("target", [{}, {"oneOf": []}, {"oneOf": [None]}, {"oneOf": [], "anyOf": []}])
def test_union_extraction_rejects_changed_shape_without_mutating_schema(target):
    definitions = {"Command": target}
    original = deepcopy(definitions)

    with pytest.raises(ValueError):
        schema_patching.extract_union_variant(definitions, "Command", [], 0, "NamedVariant")

    assert definitions == original


def test_union_extraction_rejects_existing_definition():
    definitions = {"Command": {"oneOf": [{"type": "string"}]}, "NamedVariant": {"type": "integer"}}
    original = deepcopy(definitions)

    with pytest.raises(ValueError, match="NamedVariant.*already exists"):
        schema_patching.extract_union_variant(definitions, "Command", [], 0, "NamedVariant")

    assert definitions == original
