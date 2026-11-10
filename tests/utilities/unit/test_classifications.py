"""Exercise classification discovery, snapshots and assignment grids offline."""

import json
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, call
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.commands import GetClassificationsOfElementsResult
from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.utilities import ClassificationUtilities, Utilities
from multiconn_archicad.utilities.identifiers import (
    normalize_classification_item_id,
    normalize_classification_system_id,
    normalize_classification_system_ids,
)
from multiconn_archicad.utilities.queries import (
    ClassificationCatalogue,
    FieldCatalogue,
    ClassificationInfo,
    ClassificationOperator,
    ClassificationTest,
    ClassificationPredicate,
    AllOf,
    AnyOf,
    ElementTypePredicate,
    ElementTypeTest,
    Query,
    QueryValidationError,
    validate_query,
    BooleanTest,
    PropertyPredicate,
    InvalidClassificationTestError,
)

pytestmark = pytest.mark.unit
SYSTEM, OTHER_SYSTEM, ROOT, CHILD, GRANDCHILD, LEAF, ELEMENT, OTHER_ELEMENT, MISSING = [
    UUID(int=i) for i in range(1, 10)
]


def system(guid=SYSTEM, name="Example"):
    return official.ClassificationSystem.model_validate(
        {
            "classificationSystemId": {"guid": guid},
            "name": name,
            "description": "Description",
            "source": "Example",
            "version": "1",
            "date": "2026-11-01",
        }
    )


def node(guid, code, children=None, name=""):
    return {
        "classificationItem": {
            "classificationItemId": {"guid": guid},
            "id": code,
            "name": name,
            "description": "Item description",
            "children": children,
        }
    }


@pytest.fixture
def tree():
    return [
        official.ClassificationItemArrayItem.model_validate(
            node(
                ROOT,
                "Elements",
                [
                    node(CHILD, "Wall", [node(GRANDCHILD, "Partition")]),
                    node(LEAF, "Slab", name="Slabs"),
                ],
            )
        )
    ]


@pytest.fixture
def api(tree):
    api = MagicMock()
    api.utilities = Utilities(api)
    api.official.classification.get_all_classification_systems.return_value = [system(), system(OTHER_SYSTEM, "Other")]
    api.official.classification.get_all_classifications_in_system.return_value = tree
    return api


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


@pytest.mark.parametrize("operator", list(ClassificationOperator))
def test_operator_operand_contract_round_trips_and_is_advertised_in_schema(operator):
    from jsonschema import Draft202012Validator

    data = {"kind": "classification", "operator": operator.value}
    if operator.requires_value:
        data["value"] = str(CHILD)
    test = ClassificationTest.model_validate(data)
    assert test.model_dump(mode="json") == data
    assert ClassificationTest.model_validate_json(test.model_dump_json()) == test
    validator = Draft202012Validator(ClassificationTest.model_json_schema())
    assert validator.is_valid(data)
    invalid = {"kind": "classification", "operator": operator.value}
    if not operator.requires_value:
        invalid["value"] = str(CHILD)
    with pytest.raises(ValidationError):
        ClassificationTest.model_validate(invalid)
    assert not validator.is_valid(invalid)
    with pytest.raises(ValidationError):
        ClassificationTest(operator=operator, value=None)


CLASSIFICATION_EXPECTATIONS = {
    "is": (False, True, False, False, False),
    "is not": (True, False, True, True, True),
    "has value": (True, True, True, True, False),
    "has no value": (False, False, False, False, True),
    "is in branch of": (False, True, True, False, False),
    "is not in branch of": (True, False, False, True, True),
    "is direct child of": (False, False, True, False, False),
    "is not direct child of": (True, True, False, True, True),
}


@pytest.mark.parametrize("operator", CLASSIFICATION_EXPECTATIONS)
@pytest.mark.parametrize(("assignment", "index"), [(ROOT, 0), (CHILD, 1), (GRANDCHILD, 2), (LEAF, 3), (None, 4)])
def test_all_classification_operations_follow_archicad_semantics(tree, operator, assignment, index):
    field = ClassificationInfo(system(), tree)
    data = {"operator": operator}
    if ClassificationOperator(operator).requires_value:
        data["value"] = CHILD
    result = field.create_test(**data).evaluate(assignment, field)
    assert result.is_success
    assert result.value is CLASSIFICATION_EXPECTATIONS[operator][index]


def predicate(operator="is in branch of", value=CHILD, system_id=SYSTEM):
    data = {"operator": operator}
    if ClassificationOperator(operator).requires_value:
        data["value"] = value
    return ClassificationPredicate(field_id=system_id, test=ClassificationTest.model_validate(data))


def test_query_json_and_field_schema_publish_presence_and_item_tests(api):
    from jsonschema import Draft202012Validator

    field = api.utilities.classification.discover_query_fields([SYSTEM])[SYSTEM]
    for operator in ClassificationOperator:
        node = predicate(operator.value)
        query = Query(where=node)
        assert Query.model_validate_json(query.model_dump_json()) == query
        payload = node.test.model_dump(mode="json")
        assert Draft202012Validator(field.test_schema()).is_valid(payload)
    empty = ClassificationInfo(system(), [])
    assert Draft202012Validator(empty.test_schema()).is_valid({"operator": "has no value"})


@pytest.fixture
def query_project(api):
    ids = [ELEMENT, OTHER_ELEMENT, UUID(int=100), UUID(int=101), UUID(int=102), UUID(int=103), UUID(int=104)]
    assignments = dict(zip(ids, [CHILD, GRANDCHILD, ROOT, LEAF, None, None, None]))
    cell = tapir.ErrorItem(error=tapir.Error(code=71, message="Classification cell failed"))
    row_error = tapir.ErrorItem(error=tapir.Error(code=72, message="Classification row failed"))
    types = {guid: tapir.ElementType.SLAB if index == 3 else tapir.ElementType.WALL for index, guid in enumerate(ids)}

    def listing(*args, **kwargs):
        kind = args[0] if args else None
        return tapir.ElementsWithExecutionResults(
            elements=[
                tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=guid))
                for guid in ids
                if kind is None or types[guid] == kind
            ]
        )

    def reads(elements, systems):
        rows = []
        for element in elements:
            guid = element.elementId.guid
            if guid == ids[-1]:
                rows.append(row_error)
            else:
                values = [
                    cell
                    if guid == ids[-2]
                    else tapir.ClassificationId(
                        classificationSystemId=system.classificationSystemId,
                        classificationItemId=tapir.ClassificationItemId(guid=assignments[guid])
                        if assignments[guid]
                        else None,
                    )
                    for system in systems
                ]
                rows.append(tapir.ElementClassificationItemArray(classificationIds=values))
        return rows

    api.tapir.element.get_all_elements.side_effect = listing
    api.tapir.element.get_elements_by_type.side_effect = listing
    api.tapir.element.filter_elements.side_effect = lambda elements, *, element_types: [
        e for e in elements if types[e.elementId.guid] in element_types
    ]
    api.tapir.classification.get_classifications_of_elements.side_effect = reads
    property_id = UUID(int=500)
    api.read_header_metadata.return_value = None
    api.tapir.application.get_add_on_version.return_value = "2.0.0"
    api.tapir.property.get_all_properties.return_value = GetAllPropertiesResult.model_validate(
        {
            "properties": [
                {
                    "propertyId": {"guid": property_id},
                    "propertyType": "Custom",
                    "propertyGroupName": "Example",
                    "propertyName": "Eligible",
                    "propertyCollectionType": "Single",
                    "propertyValueType": "Boolean",
                    "propertyMeasureType": "Default",
                    "propertyIsEditable": True,
                    "isExpressionBased": False,
                }
            ]
        }
    )
    api.tapir.property.get_property_values_of_elements.side_effect = lambda elements, properties, **kwargs: [
        tapir.PropertyValuesArrayItem(
            propertyValues=[
                tapir.PropertyValueArrayItem(
                    propertyValue=tapir.PropertyValue(value="True" if element.elementId.guid == ELEMENT else "False"),
                )
            ]
        )
        for element in elements
    ]
    return SimpleNamespace(api=api, ids=ids, cell=cell, row_error=row_error)


def test_classification_search_batches_systems_and_reuses_validation_metadata(query_project):
    project = query_project
    query = Query(where=AllOf(items=(predicate(), predicate("has value", system_id=OTHER_SYSTEM), predicate())))
    result = project.api.utilities.element.find_elements_result(query)
    assert [e.elementId.guid for e in result.candidates] == project.ids
    assert [e.elementId.guid for e in result.outcomes.successes] == project.ids[:2]
    assert result.outcomes.slots[-2].error.causes[0].causes[0].error is project.cell.error
    assert result.outcomes.slots[-1].error.causes[0].causes[0].error is project.row_error.error
    assert result.outcomes.slots[-1].is_error
    assert "where.items[0].test" in result.outcomes.slots[-2].error.message
    project.api.tapir.classification.get_classifications_of_elements.assert_called_once()
    _, systems = project.api.tapir.classification.get_classifications_of_elements.call_args.args
    assert [s.classificationSystemId.guid for s in systems] == [SYSTEM, OTHER_SYSTEM]
    project.api.official.classification.get_all_classification_systems.assert_called_once()
    assert project.api.official.classification.get_all_classifications_in_system.call_count == 2
    project.api.tapir.property.get_all_properties.assert_not_called()
    project.api.tapir.property.get_property_values_of_elements.assert_not_called()


def test_classification_filter_preserves_duplicates_and_unclassified_negative_matches(query_project):
    project = query_project
    result = project.api.utilities.element.filter_elements_by_query_result(
        [project.ids[4], ELEMENT, ELEMENT, project.ids[-1]],
        Query(where=predicate("is not")),
    )
    assert [e.elementId.guid for e in result.successes] == [project.ids[4]]
    project.api.official.classification.get_all_classifications_in_system.assert_called_once_with(
        official.ClassificationSystemId(guid=SYSTEM)
    )
    assert result.slots[-1].is_error
    assert result.slots[1].is_filtered and result.slots[2].is_filtered
    read_elements = project.api.tapir.classification.get_classifications_of_elements.call_args.args[0]
    assert [e.elementId.guid for e in read_elements] == [project.ids[4], ELEMENT, project.ids[-1]]
    with pytest.raises(BatchOperationError):
        project.api.utilities.element.filter_elements_by_query([project.ids[-1]], Query(where=predicate()))


def test_classification_errors_survive_decisive_boolean_siblings(query_project):
    project = query_project
    query = Query(
        where=AnyOf(
            items=(
                ElementTypePredicate(test=ElementTypeTest(types=(tapir.ElementType.WALL,))),
                predicate("has no value"),
            )
        )
    )
    result = project.api.utilities.element.filter_elements_by_query_result([project.ids[-2]], query)
    assert result.slots[0].is_error
    assert "where.items[1].test" in result.slots[0].error.message


@pytest.mark.parametrize("missing_system", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_unknown_classification_references_validate_before_listing_or_empty_return(
    query_project, missing_system, empty
):
    project = query_project
    query = Query(
        where=AllOf(
            items=(
                ElementTypePredicate(test=ElementTypeTest(types=(tapir.ElementType.WALL,))),
                ElementTypePredicate(test=ElementTypeTest(types=(tapir.ElementType.SLAB,))),
                predicate(system_id=MISSING) if missing_system else predicate(value=MISSING),
            )
        )
    )
    with pytest.raises(QueryValidationError) as caught:
        if empty:
            project.api.utilities.element.filter_elements_by_query_result([], query)
        else:
            project.api.utilities.element.find_elements_result(query)
    issue = caught.value.result.issues[0]
    assert issue.code == ("unknown_field" if missing_system else "invalid_test")
    assert issue.reference["kind"] == "classification"
    assert issue.path == ("where.items[2].field_id" if missing_system else "where.items[2].test")
    project.api.tapir.element.get_all_elements.assert_not_called()
    project.api.tapir.element.get_elements_by_type.assert_not_called()
    project.api.tapir.classification.get_classifications_of_elements.assert_not_called()


def test_offline_validation_checks_every_classification_reference_without_io(api):
    catalogue = api.utilities.classification.discover_query_fields([SYSTEM])
    query = Query(where=AnyOf(items=(predicate(value=MISSING), predicate(system_id=MISSING))))
    result = validate_query(query, [catalogue])
    assert [i.code for i in result.issues] == ["invalid_test", "unknown_field"]
    api.tapir.classification.get_classifications_of_elements.assert_not_called()


def test_property_and_classification_fields_with_the_same_guid_remain_distinct(query_project, tree):
    shared_id = UUID(int=500)
    properties = query_project.api.utilities.property.discover_query_fields()
    classifications = ClassificationCatalogue([ClassificationInfo(system(guid=shared_id), tree)])
    query = Query(
        where=AllOf(
            items=(
                PropertyPredicate(field_id=shared_id, test=BooleanTest(operator="is", value=True)),
                ClassificationPredicate(field_id=shared_id, test=ClassificationTest(operator="has value")),
            )
        )
    )

    assert properties.get_field(shared_id) is properties[shared_id]
    assert classifications.get_field(shared_id) is classifications[shared_id]
    assert validate_query(query, [classifications, properties]).is_valid


def test_classification_and_property_predicates_share_the_same_query_pipeline(query_project):
    project = query_project
    query = Query(
        where=AllOf(
            items=(
                predicate(),
                PropertyPredicate(field_id=UUID(int=500), test=BooleanTest(operator="is", value=True)),
            )
        )
    )
    result = project.api.utilities.element.find_elements_result(query)
    assert [e.elementId.guid for e in result.outcomes.successes] == [ELEMENT]
    assert result.outcomes.slots[-1].is_error
    project.api.tapir.property.get_all_properties.assert_called_once()
    project.api.official.classification.get_all_classification_systems.assert_called_once()
    project.api.tapir.property.get_property_values_of_elements.assert_called_once()
    project.api.tapir.classification.get_classifications_of_elements.assert_called_once()


def test_mixed_query_validation_collects_property_and_classification_issues(query_project):
    project = query_project
    query = Query(
        where=AnyOf(
            items=(
                PropertyPredicate(field_id=MISSING, test=BooleanTest(operator="is", value=True)),
                predicate(value=MISSING),
                predicate(system_id=MISSING),
            )
        )
    )
    with pytest.raises(QueryValidationError) as caught:
        project.api.utilities.element.find_elements(query)
    assert [i.code for i in caught.value.result.issues] == ["unknown_field", "invalid_test", "unknown_field"]
    assert [i.reference["kind"] for i in caught.value.result.issues] == ["property", "classification", "classification"]
    project.api.tapir.classification.get_classifications_of_elements.assert_not_called()


def test_type_bounds_narrow_before_classification_assignment_reads(query_project):
    project = query_project
    query = Query(
        where=AllOf(items=(ElementTypePredicate(test=ElementTypeTest(types=(tapir.ElementType.WALL,))), predicate()))
    )
    result = project.api.utilities.element.filter_elements_by_query_result(project.ids, query)
    assert result.slots[3].is_filtered
    elements = project.api.tapir.classification.get_classifications_of_elements.call_args.args[0]
    assert [e.elementId.guid for e in elements] == [guid for index, guid in enumerate(project.ids) if index != 3]


@pytest.mark.parametrize(
    "entry", ["find_elements", "find_elements_result", "filter_elements_by_query", "filter_elements_by_query_result"]
)
def test_classification_whole_command_failure_raises_from_every_query_entrypoint(query_project, entry):
    project = query_project
    failure = RuntimeError("Assignment command failed")
    project.api.tapir.classification.get_classifications_of_elements.side_effect = failure
    with pytest.raises(RuntimeError) as caught:
        fn = getattr(project.api.utilities.element, entry)
        query = Query(where=predicate())
        fn(query) if entry.startswith("find") else fn([ELEMENT], query)
    assert caught.value is failure


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
