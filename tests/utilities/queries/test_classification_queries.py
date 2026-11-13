"""Classification comparisons and query integration from classifications.md."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    BooleanTest,
    ClassificationCatalogue,
    ClassificationInfo,
    ClassificationOperator,
    ClassificationPredicate,
    ClassificationTest,
    ElementTypePredicate,
    ElementTypeTest,
    PropertyPredicate,
    Query,
    QueryValidationError,
    validate_query,
)

from .classification_support import (
    CHILD,
    ELEMENT,
    GRANDCHILD,
    LEAF,
    MISSING,
    OTHER_ELEMENT,
    OTHER_SYSTEM,
    ROOT,
    SYSTEM,
    node,
    system,
)
from .classification_support import api as api
from .classification_support import tree as tree

pytestmark = pytest.mark.unit

DEEP_DESCENDANT = UUID(int=1000)

CLASSIFICATION_EXPECTATIONS = {
    # Ancestor / selected item / direct child / deeper descendant / other branch / unclassified.
    "is": (False, True, False, False, False, False),
    "is not": (True, False, True, True, True, True),
    "has value": (True, True, True, True, True, False),
    "has no value": (False, False, False, False, False, True),
    "is in branch of": (False, True, True, True, False, False),
    "is not in branch of": (True, False, False, False, True, True),
    "is direct child of": (False, False, True, False, False, False),
    "is not direct child of": (True, True, False, True, True, True),
}


@pytest.mark.parametrize("operator", list(ClassificationOperator))
def test_operator_operand_contract_round_trips_and_is_advertised_in_schema(operator):
    from jsonschema import Draft202012Validator

    data = {"kind": "classification", "operator": operator.value}
    if operator.value not in {"has value", "has no value"}:
        data["value"] = str(CHILD)
    test = ClassificationTest.model_validate(data)
    assert test.model_dump(mode="json") == data
    assert ClassificationTest.model_validate_json(test.model_dump_json()) == test
    validator = Draft202012Validator(ClassificationTest.model_json_schema())
    assert validator.is_valid(data)
    invalid = {"kind": "classification", "operator": operator.value}
    if operator.value in {"has value", "has no value"}:
        invalid["value"] = str(CHILD)
    with pytest.raises(ValidationError):
        ClassificationTest.model_validate(invalid)
    assert not validator.is_valid(invalid)
    with pytest.raises(ValidationError):
        ClassificationTest(operator=operator, value=None)


@pytest.mark.parametrize(
    ("operator", "assignment", "expected"),
    [
        pytest.param(operator, assignment, expected, id=f"{operator}-{relationship}")
        for operator, decisions in CLASSIFICATION_EXPECTATIONS.items()
        for relationship, assignment, expected in zip(
            ("ancestor", "selected", "direct-child", "deeper-descendant", "other-branch", "unclassified"),
            (ROOT, CHILD, GRANDCHILD, DEEP_DESCENDANT, LEAF, None),
            decisions,
            strict=True,
        )
    ],
)
def test_classification_comparisons_follow_the_documented_operator_table(tree, operator, assignment, expected):
    grandchild = tree[0].classificationItem.children[0].classificationItem.children[0].classificationItem
    grandchild.children = [official.ClassificationItemArrayItem.model_validate(node(DEEP_DESCENDANT, "Deep partition"))]
    field = ClassificationInfo(system(), tree)
    data = {"operator": operator}
    if operator not in {"has value", "has no value"}:
        data["value"] = CHILD
    result = field.create_test(**data).evaluate(assignment, field)
    assert result.is_success
    assert result.value is expected


def predicate(operator="is in branch of", value=CHILD, system_id=SYSTEM):
    data = {"operator": operator}
    if operator not in {"has value", "has no value"}:
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
    yield SimpleNamespace(api=api, ids=ids, cell=cell, row_error=row_error)
    api.tapir.element.change_selection_of_elements.assert_not_called()


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
