from code_generation.shared.schema_match import match_definitions


def test_match_inline_schema_and_report_annotations_and_reference_sites():
    source = {
        "Guid": {"type": "string"},
        "GetParameters": {
            "properties": {
                "element/id": {
                    "description": "Original description",
                    "properties": {"guid": {"$ref": "#/$defs/Guid"}},
                    "type": "object",
                },
            },
        },
    }
    target = {
        "Guid": {"type": "string"},
        "ElementId": {
            "type": "object",
            "properties": {"guid": {"$ref": "#/Guid"}},
            "description": "Shared description",
        },
        "GetParameters": {"properties": {"element/id": {"$ref": "#/$defs/ElementId"}}},
    }

    report = match_definitions(source, target, "GetParameters", "/properties/element~1id")

    [match] = [item for item in report["matches"] if item["definition"] == "ElementId"]
    assert match["structural_differences"] == []
    assert match["annotation_differences"] == [
        {
            "path": "/$defs/GetParameters/properties/element~1id",
            "before": {"description": "Original description"},
            "after": {"description": "Shared description"},
        },
    ]
    assert match["reference_sites"] == ["/$defs/GetParameters/properties/element~1id/$ref"]


def test_reference_constraints_remain_structural_and_sibling_descriptions_are_separate():
    definitions = {
        "Text": {"type": "string"},
        "Named": {"$ref": "#/$defs/Text", "description": "Any length"},
        "Short": {"$ref": "#/$defs/Text", "maxLength": 8, "description": "Limited length"},
    }

    report = match_definitions(definitions, definitions, "Named", candidate="Short")

    [comparison] = report["matches"]
    assert comparison["structural_differences"]
    assert any("$ref siblings" in path for path in comparison["structural_differences"])
    assert comparison["annotation_differences"] == [
        {
            "path": "/$defs/Named/$ref annotations",
            "before": [{"description": "Any length"}],
            "after": [{"description": "Limited length"}],
        },
    ]
