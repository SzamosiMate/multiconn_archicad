"""General request-default smoke tests using real generated commands and mocked transport.

Some assertions deliberately fail until the default-serialization plan is
implemented. No test connects to Archicad or performs a model write.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from jsonschema import Draft201909Validator, ValidationError

from multiconn_archicad.clients.unified_api.api import UnifiedApi
from multiconn_archicad.clients.unified_api.official.property import PropertyCommands as OfficialPropertyCommands
from multiconn_archicad.clients.unified_api.tapir.application import ApplicationCommands
from multiconn_archicad.clients.unified_api.tapir.property import PropertyCommands
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir.types import InputConstraint

pytestmark = [pytest.mark.unit, pytest.mark.smoke]

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "request_compatibility" / "property_read_tapir_1_7_3.json"
ELEMENT_ID = UUID(int=1)
PROPERTY_ID = UUID(int=2)


@pytest.fixture
def old_property_read_schema():
    return Draft201909Validator(json.loads(FIXTURE.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "options, expected_extra",
    [
        pytest.param({}, {}, id="omitted-default"),
        pytest.param({"use_si_units": None}, {}, id="explicit-none"),
        pytest.param({"use_si_units": False}, {}, id="explicit-default"),
        pytest.param({"use_si_units": True}, {"useSIUnits": True}, id="explicit-nondefault"),
    ],
)
def test_new_optional_flag_preserves_old_calls_and_forwards_nondefault(
    options, expected_extra, old_property_read_schema
):
    core = MagicMock()
    core.post_tapir_command.return_value = {"propertyValuesForElements": []}

    PropertyCommands(core).get_property_values_of_elements([], [], **options)

    expected = {"elements": [], "properties": [], **expected_extra}
    core.post_tapir_command.assert_called_once_with("GetPropertyValuesOfElements", expected)
    payload = core.post_tapir_command.call_args.args[1]
    if expected_extra:
        # Explicit new capabilities remain unsupported by the old schema.
        with pytest.raises(ValidationError, match="useSIUnits"):
            old_property_read_schema.validate(payload)
    else:
        old_property_read_schema.validate(payload)


@pytest.mark.parametrize("version", ["1.7.2", "1.7.3", "1.8.0", "2.0.0"])
def test_existing_property_utility_keeps_legacy_payload_and_display_values(version, old_property_read_schema):
    core = MagicMock()

    def command(name, parameters=None):
        if name == "GetAddOnVersion":
            return {"version": version}
        assert name == "GetPropertyValuesOfElements"
        return {
            "propertyValuesForElements": [
                {"propertyValues": [{"propertyValue": {"value": "3,13"}, "isAvailable": True}]}
            ]
        }

    core.post_tapir_command.side_effect = command
    api = UnifiedApi(core)

    result = api.utilities.property.get_property_values_per_element_result([ELEMENT_ID], [PROPERTY_ID])

    assert result.rows[0][0].value == "3,13"
    payloads = [
        args[1] for args, _ in core.post_tapir_command.call_args_list if args[0] == "GetPropertyValuesOfElements"
    ]
    assert len(payloads) == 1
    expected = {
        "elements": [{"elementId": {"guid": str(ELEMENT_ID)}}],
        "properties": [{"propertyId": {"guid": str(PROPERTY_ID)}}],
    }
    if version != "1.7.2":
        expected["includeAvailability"] = True
    assert payloads[0] == expected
    old_property_read_schema.validate(payloads[0])


@pytest.mark.parametrize(
    "options, expected",
    [
        pytest.param({}, {}, id="true-and-string-defaults"),
        pytest.param({"show_rubber_line_feedback": False}, {"showRubberLineFeedback": False}, id="nondefault-false"),
    ],
)
def test_true_and_string_defaults_are_omitted_without_losing_nondefault_false(options, expected):
    core = MagicMock()
    core.post_tapir_command.return_value = {"cancelled": True}

    ApplicationCommands(core).get_line_from_user(**options)

    core.post_tapir_command.assert_called_once_with("GetLineFromUser", expected)


@pytest.mark.parametrize("as_model", [False, True], ids=["dictionary", "model"])
@pytest.mark.parametrize("from_last_point", [False, True], ids=["nested-default", "nested-nondefault"])
def test_nested_optional_defaults_follow_the_same_request_policy(as_model, from_last_point):
    core = MagicMock()
    core.post_tapir_command.return_value = {"position": {"x": 0, "y": 0, "z": 0}}
    constraint = {"type": "Angle", "value": 0.1, "fromLastPoint": from_last_point}
    if as_model:
        constraint = InputConstraint(**constraint)

    ApplicationCommands(core).get_point_from_user(constraint=constraint)

    expected = {"type": "Angle", "value": 0.1}
    if from_last_point:
        expected["fromLastPoint"] = True
    core.post_tapir_command.assert_called_once_with("GetPointFromUser", {"constraint": expected})


def test_required_literal_tags_survive_inside_an_official_request_list():
    core = MagicMock()
    core.post_command.return_value = {"executionResults": [{"success": True}]}
    value = official.ElementPropertyValue(
        elementId=official.ElementId(guid=ELEMENT_ID),
        propertyId=official.PropertyId(guid=PROPERTY_ID),
        propertyValue=official.NormalNumberPropertyValue(value=3),
    )

    OfficialPropertyCommands(core).set_property_values_of_elements([value])

    core.post_command.assert_called_once_with(
        "API.SetPropertyValuesOfElements",
        {
            "elementPropertyValues": [
                {
                    "elementId": {"guid": str(ELEMENT_ID)},
                    "propertyId": {"guid": str(PROPERTY_ID)},
                    "propertyValue": {"type": "number", "status": "normal", "value": 3.0},
                }
            ]
        },
    )
