"""Exercise classification discovery, snapshots and assignment grids offline."""

import json
from dataclasses import FrozenInstanceError
from unittest.mock import call
from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.commands import GetClassificationsOfElementsResult
from multiconn_archicad.utilities import ClassificationUtilities
from multiconn_archicad.utilities.identifiers import (
    normalize_classification_item_id,
    normalize_classification_system_id,
    normalize_classification_system_ids,
)
from multiconn_archicad.utilities.queries import (
    ClassificationCatalogue,
    ClassificationInfo,
    ClassificationOperator,
    ClassificationTest,
    FieldCatalogue,
    InvalidClassificationTestError,
)
from tests.utilities.queries.classification_support import (
    CHILD,
    ELEMENT,
    GRANDCHILD,
    LEAF,
    MISSING,
    OTHER_ELEMENT,
    OTHER_SYSTEM,
    ROOT,
    SYSTEM,
    system,
)
from tests.utilities.queries.classification_support import api as api
from tests.utilities.queries.classification_support import tree as tree

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", ["system", "item"])
def test_classification_identifiers_accept_uuid_string_and_both_api_shapes(name):
    prefix = f"Classification{name.title()}Id"
    member = f"classification{name.title()}Id"
    normalize = normalize_classification_system_id if name == "system" else normalize_classification_item_id
    inputs = [SYSTEM, str(SYSTEM)]
    for module in [official, tapir]:
        raw = getattr(module, prefix)(guid=SYSTEM)
        inputs.extend([raw, getattr(module, prefix + "ArrayItem")(**{member: raw})])
    for value in inputs:
        result = normalize(value)
        assert isinstance(result, getattr(tapir, prefix + "ArrayItem"))
        assert getattr(result, member).guid == SYSTEM
    assert normalize(inputs[-1]) is inputs[-1]
    with pytest.raises(ValueError):
        normalize("invalid")
    with pytest.raises(TypeError):
        normalize(1)


def test_system_normalization_preserves_order_and_duplicates():
    assert [
        x.classificationSystemId.guid for x in normalize_classification_system_ids([OTHER_SYSTEM, SYSTEM, SYSTEM])
    ] == [OTHER_SYSTEM, SYSTEM, SYSTEM]


def test_discovery_builds_uniform_ordered_fields_and_reads_each_system_once(api):
    catalogue = api.utilities.classification.discover_query_fields()
    assert isinstance(api.utilities.classification, ClassificationUtilities)
    assert isinstance(catalogue, ClassificationCatalogue)
    assert [f.system_id for f in catalogue] == [SYSTEM, OTHER_SYSTEM]
    field = catalogue[str(SYSTEM)]
    assert field.group == "Classifications"
    assert field.name == "Example"
    assert field.qualified_name == "Classifications / Example"
    assert field.reference == {"kind": "classification", "field_id": str(SYSTEM)}
    assert [i.item_id for i in field.items] == [ROOT, CHILD, GRANDCHILD, LEAF]
    assert field.item(CHILD).code == "Wall"
    assert field.item(CHILD).name == ""
    assert field.item(CHILD).parent_id == ROOT
    assert field.item(ROOT).children == (CHILD, LEAF)
    api.official.classification.get_all_classification_systems.assert_called_once()
    assert api.official.classification.get_all_classifications_in_system.call_args_list == [
        call(official.ClassificationSystemId(guid=SYSTEM)),
        call(official.ClassificationSystemId(guid=OTHER_SYSTEM)),
    ]
    api.tapir.classification.get_classifications_of_elements.assert_not_called()


@pytest.mark.parametrize(
    ("data", "visible", "forbidden"),
    [
        ({}, ("operator",), frozenset()),
        ({"operator": "future operator", "value": str(CHILD)}, ("operator",), frozenset()),
        ({"operator": ["is"]}, ("operator",), frozenset()),
        ({"operator": "is in branch of"}, ("operator", "value"), frozenset()),
        ({"operator": "has value", "value": str(CHILD)}, ("operator",), frozenset({"value"})),
    ],
)
def test_input_description_resolves_active_operands_without_changing_the_draft(api, data, visible, forbidden):
    field = api.utilities.classification.discover_query_fields([SYSTEM])[SYSTEM]
    original = data.copy()

    description = field.describe_test_inputs(current_data=data)

    assert description is not None
    assert tuple(spec.name for spec in description.fields) == visible
    assert all(spec.required for spec in description.fields)
    assert description.forbidden_fields == forbidden
    assert description.definitions["ClassificationOperator"]["enum"] == list(field.operators())
    if "value" in visible:
        assert {"const": str(CHILD), "title": "Wall"} in description.fields[1].schema["oneOf"]
    assert data == original


def test_explicit_discovery_selection_orders_and_deduplicates_tree_reads(api):
    catalogue = api.utilities.classification.discover_query_fields([OTHER_SYSTEM, SYSTEM, OTHER_SYSTEM])
    assert [f.system_id for f in catalogue] == [OTHER_SYSTEM, SYSTEM]
    assert api.official.classification.get_all_classifications_in_system.call_count == 2


def test_missing_system_is_omitted_and_existing_trees_are_loaded(api):
    catalogue = api.utilities.classification.discover_query_fields([MISSING, SYSTEM, MISSING])
    assert [field.system_id for field in catalogue] == [SYSTEM]
    api.official.classification.get_all_classifications_in_system.assert_called_once_with(
        official.ClassificationSystemId(guid=SYSTEM)
    )


def test_empty_discovery_selection_does_not_read_the_api(api):
    assert len(api.utilities.classification.discover_query_fields([])) == 0
    api.official.classification.get_all_classification_systems.assert_not_called()


def test_empty_project_catalogue(api):
    api.official.classification.get_all_classification_systems.return_value = []
    catalogue = api.utilities.classification.discover_query_fields()
    assert catalogue.fields == catalogue.search() == ()
    assert catalogue.get(SYSTEM) is None
    assert catalogue.describe() == {"fields": []}
    api.official.classification.get_all_classifications_in_system.assert_not_called()


def test_snapshot_tree_traversal_and_search_do_not_fetch_or_share_mutable_api_data(api, tree):
    catalogue = api.utilities.classification.discover_query_fields([SYSTEM])
    field = catalogue[SYSTEM]
    tree[0].classificationItem.children.clear()
    api.official.classification.get_all_classification_systems.return_value[0].name = "Changed"
    field.details.name = "Changed copy"
    assert field.name == "Example"
    assert field.descendant_ids(ROOT) == frozenset([CHILD, GRANDCHILD, LEAF])
    assert field.descendant_ids(CHILD, include_self=True) == frozenset([CHILD, GRANDCHILD])
    assert field.descendant_ids(LEAF) == frozenset()
    assert catalogue.search("EXAMPLE", group="Classifications") == (field,)
    assert catalogue.search("Example", group="Other") == ()
    assert catalogue.get(MISSING) is None
    with pytest.raises(KeyError):
        field.descendant_ids(MISSING)
    with pytest.raises(KeyError):
        catalogue[MISSING]
    with pytest.raises(FrozenInstanceError):
        field.item(ROOT).item_id = MISSING
    description = catalogue.describe()
    assert json.loads(json.dumps(description)) == description
    description["fields"][0]["items"].clear()
    assert len(field.items) == 4
    api.official.classification.get_all_classifications_in_system.assert_called_once()


def test_descriptor_exposes_item_choices_and_validates_test_references(api):
    field = api.utilities.classification.discover_query_fields([SYSTEM])[SYSTEM]
    assert field.operators() == tuple(op.value for op in ClassificationOperator)
    schema = field.test_schema()
    assert schema["properties"]["value"]["oneOf"][1] == {"const": str(CHILD), "title": "Wall"}
    test = field.create_test(operator="is in branch of", value=str(CHILD))
    assert isinstance(test, ClassificationTest)
    assert test.operator is ClassificationOperator.IS_IN_BRANCH_OF
    assert ClassificationTest.model_validate_json(test.model_dump_json()) == test
    with pytest.raises(InvalidClassificationTestError, match="not present"):
        field.create_test(operator="is", value=MISSING)
    with pytest.raises(ValidationError):
        field.create_test(operator="contains", value=CHILD)
    with pytest.raises(ValidationError):
        field.create_test(operator="is", value=CHILD, extra=True)


def test_empty_system_retains_metadata_and_has_no_valid_item_choices():
    field = ClassificationInfo(system(), [])
    assert field.items == ()
    assert field.test_schema()["properties"]["value"]["not"] == {}
    with pytest.raises(InvalidClassificationTestError):
        field.create_test(operator="is", value=ROOT)
    assert field.create_test(operator="has no value").value is None


def test_classification_catalogue_uses_shared_filtering_and_duplicate_rules(api):
    catalogue = api.utilities.classification.discover_query_fields()
    assert isinstance(catalogue, FieldCatalogue)
    assert catalogue.supported == catalogue.fields
    assert catalogue.unsupported == ()
    assert catalogue.search("example", supported_only=True) == (catalogue[SYSTEM],)
    assert catalogue.search("", supported_only=True) == catalogue.supported
    with pytest.raises(ValueError, match="Duplicate field GUID"):
        ClassificationCatalogue([catalogue[SYSTEM], catalogue[SYSTEM]])


def assignment(item=CHILD, system_id=SYSTEM):
    value = {"classificationSystemId": {"guid": system_id}}
    if item is not None:
        value["classificationItemId"] = {"guid": item}
    return value


def set_assignments(api, rows):
    response = GetClassificationsOfElementsResult.model_validate({"elementClassifications": rows})
    api.tapir.classification.get_classifications_of_elements.return_value = response.elementClassifications
    return response


def test_assignment_grid_preserves_both_input_axes_duplicates_and_unclassified_values(api):
    set_assignments(
        api,
        [
            {"classificationIds": [assignment(), assignment(None, OTHER_SYSTEM), assignment()]},
            {"classificationIds": [assignment(UUID(int=0)), assignment(LEAF, OTHER_SYSTEM), assignment(UUID(int=0))]},
            {"classificationIds": [assignment(), assignment(None, OTHER_SYSTEM), assignment()]},
        ],
    )
    result = api.utilities.classification.get_classifications_per_element_result(
        [ELEMENT, OTHER_ELEMENT, ELEMENT],
        [SYSTEM, OTHER_SYSTEM, SYSTEM],
    )
    assert result.width == 3
    assert [[s.value for s in row] for row in result.rows] == [
        [CHILD, None, CHILD],
        [None, LEAF, None],
        [CHILD, None, CHILD],
    ]
    elements, systems = api.tapir.classification.get_classifications_of_elements.call_args.args
    assert [e.elementId.guid for e in elements] == [ELEMENT, OTHER_ELEMENT, ELEMENT]
    assert [s.classificationSystemId.guid for s in systems] == [SYSTEM, OTHER_SYSTEM, SYSTEM]
    api.tapir.classification.get_classifications_of_elements.assert_called_once()
    api.official.classification.get_all_classification_systems.assert_not_called()


def test_assignment_errors_retain_cell_and_whole_row_causes(api):
    response = set_assignments(
        api,
        [
            {"classificationIds": [assignment(), {"error": {"code": 7, "message": "Invalid system"}}]},
            {"error": {"code": 8, "message": "Invalid element"}},
        ],
    )
    result = api.utilities.classification.get_classifications_per_element_result(
        [ELEMENT, OTHER_ELEMENT], [SYSTEM, OTHER_SYSTEM]
    )
    assert result.rows[0].slots[0].value == CHILD
    assert result.rows[0].slots[1].error.error is response.elementClassifications[0].classificationIds[1].error
    assert result.rows[1].error.error is response.elementClassifications[1].error
    assert all(s.is_error for s in result.rows[1])
    with pytest.raises(BatchOperationError):
        api.utilities.classification.get_classifications_per_element([ELEMENT, OTHER_ELEMENT], [SYSTEM, OTHER_SYSTEM])


def test_strict_assignment_read_preserves_successful_none(api):
    set_assignments(api, [{"classificationIds": [assignment(None)]}])
    assert api.utilities.classification.get_classifications_per_element([ELEMENT], [SYSTEM]) == [[None]]


def test_empty_elements_return_an_empty_grid_without_calling_tapir(api):
    result = api.utilities.classification.get_classifications_per_element_result([], [SYSTEM, OTHER_SYSTEM])
    assert result.rows == () and result.width == 2
    api.tapir.classification.get_classifications_of_elements.assert_not_called()


def test_missing_system_argument_and_invalid_ids_are_rejected_without_api_reads(api):
    with pytest.raises(ValueError, match="At least one"):
        api.utilities.classification.get_classifications_per_element_result([], [])
    with pytest.raises(ValueError):
        api.utilities.classification.get_classifications_per_element_result([], ["invalid"])
    with pytest.raises(ValueError):
        api.utilities.classification.get_classifications_per_element_result(["invalid"], [SYSTEM])
    api.tapir.classification.get_classifications_of_elements.assert_not_called()


@pytest.mark.parametrize("method", ["get_classifications_per_element", "get_classifications_per_element_result"])
def test_command_failures_propagate_from_both_assignment_methods(api, method):
    failure = RuntimeError("Command failed")
    api.tapir.classification.get_classifications_of_elements.side_effect = failure
    with pytest.raises(RuntimeError) as caught:
        getattr(api.utilities.classification, method)([ELEMENT], [SYSTEM])
    assert caught.value is failure


def test_discovery_failures_propagate(api):
    api.official.classification.get_all_classifications_in_system.side_effect = RuntimeError("Tree failed")
    with pytest.raises(RuntimeError, match="Tree failed"):
        api.utilities.classification.discover_query_fields()
