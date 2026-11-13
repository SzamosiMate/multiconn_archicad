"""Canonical query reads cross the property utility, generated client and wire payload."""

from unittest.mock import MagicMock

import pytest

from multiconn_archicad.clients.unified_api.api import UnifiedApi
from multiconn_archicad.errors import MulticonnArchicadError
from multiconn_archicad.utilities.queries import NumberTest, PropertyPredicate, Query

from .support import HEIGHT, TALL, element, guids, property_details

pytestmark = pytest.mark.unit


def make_api(*, version="2.0.0", measure="Length", canonical="3.125"):
    core = MagicMock()

    def command(name, parameters=None):
        if name == "GetAddOnVersion":
            return {"version": version}
        if name == "GetAllProperties":
            return {"properties": [property_details(propertyMeasureType=measure).model_dump(mode="json")]}
        if name == "GetAllElements":
            return {"elements": [element(TALL).model_dump(mode="json")]}
        if name == "GetPropertyValuesOfElements":
            value = canonical if parameters.get("useSIUnits") else "3,13"
            return {
                "propertyValuesForElements": [
                    {"propertyValues": [{"propertyValue": {"value": value}, "isAvailable": True}]}
                ]
            }
        raise AssertionError(f"Unexpected command: {name}")

    core.post_tapir_command.side_effect = command
    return UnifiedApi(core), core


def read_payloads(core):
    return [args[1] for args, _ in core.post_tapir_command.call_args_list if args[0] == "GetPropertyValuesOfElements"]


@pytest.mark.parametrize(
    ("measure", "canonical", "operand"),
    [("Length", "0.001", 0.001), ("Area", "1.25", 1.25), ("Volume", "0.125", 0.125), ("Angle", "30", 30)],
    ids=["metres", "square-metres", "cubic-metres", "degrees"],
)
def test_queries_compare_canonical_values_in_si_with_degrees_for_angles(measure, canonical, operand):
    api, core = make_api(measure=measure, canonical=canonical)
    query = Query(where=PropertyPredicate(field_id=HEIGHT, test=NumberTest(operator="is", value=operand)))

    assert guids(api.utilities.element.find_elements(query)) == [TALL]
    (payload,) = read_payloads(core)
    assert payload["useSIUnits"] is True
    assert payload["includeAvailability"] is True


@pytest.mark.parametrize("flag", [None, False, True], ids=["omitted", "explicit-false", "explicit-true"])
def test_generated_client_omits_default_flag_and_forwards_explicit_booleans(flag):
    api, core = make_api()
    kwargs = {} if flag is None else {"use_si_units": flag}

    api.tapir.property.get_property_values_of_elements([element(TALL)], [], **kwargs)

    (payload,) = read_payloads(core)
    if flag is None:
        assert "useSIUnits" not in payload
    else:
        assert payload["useSIUnits"] is flag


@pytest.mark.parametrize("version", ["1.7.2", "1.7.3", "1.8.0", "2.0.0"])
def test_existing_utility_callers_keep_display_values_and_omit_si_flag(version):
    api, core = make_api(version=version)

    result = api.utilities.property.get_property_values_per_element_result([TALL], [HEIGHT])

    assert result.rows[0][0].value == "3,13"
    (payload,) = read_payloads(core)
    assert "useSIUnits" not in payload
    assert payload.get("includeAvailability") is (None if version == "1.7.2" else True)


@pytest.mark.parametrize("version", ["1.7.3", "1.8.0", "2.0.0rc1"])
def test_explicit_si_reads_reject_older_tapir_instead_of_falling_back_to_display_values(version):
    api, core = make_api(version=version)

    with pytest.raises(MulticonnArchicadError, match="require Tapir 2.0.0 or newer"):
        api.utilities.property.get_property_values_per_element_result([TALL], [HEIGHT], use_si_units=True)

    assert read_payloads(core) == []


def test_si_read_keeps_conversion_precision_and_does_not_round_the_angle():
    api, core = make_api(measure="Angle", canonical="29.999999999999996")

    result = api.utilities.property.get_property_values_per_element_result([TALL], [HEIGHT], use_si_units=True)

    assert result.rows[0][0].value == "29.999999999999996"
    assert read_payloads(core)[0]["useSIUnits"] is True
