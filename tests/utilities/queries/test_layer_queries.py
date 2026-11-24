"""Exercise layer identity, name selection, combination visibility and batching."""

from unittest.mock import call, patch
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from multiconn_archicad.errors import BatchOperationError, RequestError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    ContextBuilder,
    LayerAttribute,
    LayerInfo,
    LayerNameInfo,
    LayerCombinationInfo,
    LayerCombinationNameInfo,
    LayerPredicate,
    LayerNamePredicate,
    LayerCombinationPredicate,
    LayerCombinationNamePredicate,
    LayerTest,
    LayerCombinationTest,
    Query,
    QueryFieldCatalogue,
    QueryValidationError,
    InvalidFieldTestError,
    TextTest,
    validate_query,
)
from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query
from multiconn_archicad.utilities.queries.sources import ELEMENT_LAYER_INDICES, LAYER_COMBINATIONS

from .support import BAD, SHORT, SLAB, TALL, UNAVAILABLE, UNDEFINED, element, guids

pytestmark = pytest.mark.unit

LAYERS = tuple(
    LayerAttribute(UUID(int=100 + i), i, name)
    for i, name in enumerate(("Archicad Layer", "A-Walls", "A-Slabs", "Z-Hidden"), start=1)
)
COMBINATIONS = tuple(
    LayerAttribute(UUID(int=200 + i), i, name)
    for i, name in enumerate(("Structural", "Documentation", "Empty"), start=1)
)
ASSIGNMENTS = {TALL: 2, SLAB: 3, SHORT: 2, BAD: 4, UNDEFINED: 1, UNAVAILABLE: 3}
LAYER_INDEX_PROPERTY = UUID("a74b66a1-629a-4807-83ac-5fff0553a3ac")
VISIBLE = {COMBINATIONS[0].guid: {1, 2}, COMBINATIONS[1].guid: {1, 3}, COMBINATIONS[2].guid: set()}


def headers(attributes):
    return tapir.AttributeHeadersWrapper(
        attributes=[
            tapir.AttributeHeader(
                attributeId=tapir.AttributeId(guid=item.guid),
                index=item.index,
                name=item.name,
                modificationTime=0,
            )
            for item in attributes
        ]
    )


@pytest.fixture
def layer_project(project):
    api = project.api
    api.tapir.attribute.get_attributes_by_type.side_effect = lambda kind: headers(
        LAYERS if kind == tapir.AttributeType.LAYER else COMBINATIONS
    )

    def combinations(attributes):
        selected = {item.attributeId.guid for item in attributes}
        return [
            tapir.LayerCombinationAttribute(
                layerCombination=tapir.LayerCombinationAttributeDetails(
                    attributeId=tapir.AttributeId(guid=combo.guid),
                    attributeIndex=combo.index,
                    name=combo.name,
                    layers=[
                        tapir.LayersOfLayerCombinationItem(
                            attributeId=tapir.AttributeId(guid=layer.guid),
                            isHidden=layer.index not in VISIBLE[combo.guid],
                            isLocked=True,
                            isWireframe=True,
                            intersectionGroupNr=7,
                        )
                        for layer in LAYERS
                    ],
                )
            )
            for combo in COMBINATIONS
            if combo.guid in selected
        ]

    for guid, index in ASSIGNMENTS.items():
        project.values[guid][LAYER_INDEX_PROPERTY] = str(index)

    def filter_elements(elements, *, layer_indices=None, element_types=None):
        return [
            item
            for item in elements
            if (layer_indices is None or ASSIGNMENTS[item.elementId.guid] in layer_indices)
            and (element_types is None or project.types[item.elementId.guid] in element_types)
        ]

    api.tapir.attribute.get_layer_combinations.side_effect = combinations
    api.tapir.element.filter_elements.side_effect = filter_elements
    return project


def layer(index=2, operator="is"):
    return LayerPredicate(test=LayerTest(operator=operator, value=LAYERS[index - 1].guid))


def combination(index=1, operator="is"):
    return LayerCombinationPredicate(test=LayerCombinationTest(operator=operator, value=COMBINATIONS[index - 1].guid))


@pytest.mark.parametrize(
    ("predicate", "expected"),
    [
        (layer(), [TALL, SHORT]),
        (layer(operator="is not"), [SLAB, BAD, UNDEFINED, UNAVAILABLE]),
        (LayerNamePredicate(test=TextTest(operator="starts with", value="a-")), [TALL, SLAB, SHORT, UNAVAILABLE]),
        (LayerNamePredicate(test=TextTest(operator="does not contain", value="a-")), [BAD, UNDEFINED]),
        (combination(), [TALL, SHORT, UNDEFINED]),
        (combination(operator="is not"), [SLAB, BAD, UNAVAILABLE]),
        (
            LayerCombinationNamePredicate(test=TextTest(operator="contains", value="t")),
            [TALL, SLAB, SHORT, UNDEFINED, UNAVAILABLE],
        ),
        (
            LayerCombinationNamePredicate(test=TextTest(operator="does not contain", value="structural")),
            [SLAB, UNDEFINED, UNAVAILABLE],
        ),
        (LayerNamePredicate(test=TextTest(operator="is", value="missing")), []),
        (LayerCombinationNamePredicate(test=TextTest(operator="is", value="missing")), []),
        (
            LayerCombinationNamePredicate(test=TextTest(operator="is not", value="Structural")),
            [SLAB, UNDEFINED, UNAVAILABLE],
        ),
        (combination(3), []),
        (combination(3, "is not"), list(ASSIGNMENTS)),
    ],
)
def test_membership_semantics(layer_project, predicate, expected):
    api = layer_project.api
    assert guids(api.utilities.element.find_elements(Query(where=predicate))) == expected
    api.tapir.element.get_details_of_elements.assert_not_called()
    api.official.attribute.get_attributes_indices.assert_not_called()
    api.tapir.element.filter_elements.assert_not_called()
    api.tapir.property.get_property_values_of_elements.assert_called_once()


@pytest.mark.parametrize(
    ("predicate", "field"),
    [
        (layer(), LayerInfo(LAYERS)),
        (LayerNamePredicate(test=TextTest(operator="contains", value="a-")), LayerNameInfo(LAYERS)),
        (combination(), LayerCombinationInfo(COMBINATIONS)),
        (
            LayerCombinationNamePredicate(test=TextTest(operator="ends with", value="tion")),
            LayerCombinationNameInfo(COMBINATIONS),
        ),
    ],
)
def test_serialization_schema_editor_and_offline_validation(predicate, field):
    query = Query(where=predicate)
    saved = query.model_dump_json()
    restored = Query.model_validate_json(saved, context={"require_schema_version": True})
    assert restored == query
    assert "field_id" not in query.model_dump()["where"]
    Draft202012Validator(Query.model_json_schema()).validate(query.model_dump(mode="json"))
    catalogue = QueryFieldCatalogue(fields=[field])
    assert validate_query(query, catalogue).is_valid
    row = QueryRow(predicate={**field.reference, "test": predicate.test.model_dump(mode="json")})
    draft = QueryRows.model_validate_json(QueryRows(rows=[row]).model_dump_json())
    assert build_query(draft).query == query
    assert field.group_path == ("Layer",)
    assert field.create_test(**predicate.test.model_dump()) == predicate.test


@pytest.mark.parametrize("field", [LayerInfo(LAYERS), LayerCombinationInfo(COMBINATIONS)])
def test_dropdown_choices_save_guid_and_display_name(field):
    inputs = field.describe_test_inputs({})
    operator, value = inputs.fields
    assert operator.required and value.required
    choices = value.schema["oneOf"]
    assert choices == [{"const": str(item.guid), "title": item.name} for item in field.attributes]
    chosen = choices[0]
    assert field.create_test(operator="is", value=chosen["const"]).value == field.attributes[0].guid
    value.schema.clear()
    assert field.describe_test_inputs({}).fields[1].schema["oneOf"]


def test_browse_reads_each_attribute_type_once_and_scoped_refresh_avoids_unrelated_reads(layer_project):
    api = layer_project.api
    api.official.basic.get_product_info.return_value.version = 29
    api.official.classification.get_all_classification_systems.return_value = []
    catalogue = api.utilities.element.discover_query_fields()
    assert [entry.field.name for entry in catalogue.browse_fields() if entry.group_path == ("Layer",)] == [
        "Layer",
        "Layer Name",
        "Layer Combination",
        "Layer Combination Name",
    ]
    assert api.tapir.attribute.get_attributes_by_type.call_args_list == [
        call(tapir.AttributeType.LAYER),
        call(tapir.AttributeType.LAYER_COMBINATION),
    ]
    api.reset_mock()
    rows = [QueryRow(predicate={"kind": kind}) for kind in ("layer", "layer_name")]
    scoped = api.utilities.element.discover_query_fields(rows)
    assert scoped.resolve({"kind": "layer"}).attributes == LAYERS
    api.tapir.attribute.get_attributes_by_type.assert_called_once_with(tapir.AttributeType.LAYER)
    api.tapir.property.get_all_properties.assert_not_called()
    api.official.classification.get_all_classification_systems.assert_not_called()


def test_mixed_nested_query_shares_raw_data_reads(layer_project):
    predicate = AnyOf(
        items=(
            layer(),
            layer(operator="is not"),
            LayerNamePredicate(test=TextTest(operator="is", value="a-walls")),
            combination(),
            combination(2),
            combination(operator="is not"),
            LayerCombinationNamePredicate(test=TextTest(operator="is", value="Structural")),
        )
    )
    api = layer_project.api
    assert guids(api.utilities.element.find_elements(Query(where=predicate))) == list(ASSIGNMENTS)
    api.tapir.property.get_property_values_of_elements.assert_called_once()
    api.tapir.attribute.get_layer_combinations.assert_called_once()
    assert len(api.tapir.attribute.get_layer_combinations.call_args.args[0]) == len(COMBINATIONS)
    api.tapir.attribute.get_layers.assert_not_called()
    api.tapir.element.filter_elements.assert_not_called()


@pytest.mark.parametrize("predicate", [layer(), combination()])
def test_missing_saved_guid_is_invalid_even_for_empty_population(layer_project, predicate):
    predicate = predicate.model_copy(update={"test": predicate.test.model_copy(update={"value": UUID(int=999)})})
    api = layer_project.api
    with pytest.raises(QueryValidationError) as caught:
        api.utilities.element.filter_elements_by_query_result([], Query(where=predicate))
    (issue,) = caught.value.result.issues
    assert issue.code == "invalid_test" and issue.path == "where.test"
    api.tapir.element.filter_elements.assert_not_called()
    api.tapir.attribute.get_layer_combinations.assert_not_called()


def test_empty_population_validates_without_visibility_or_element_reads(layer_project):
    api = layer_project.api
    assert api.utilities.element.filter_elements_by_query([], Query(where=combination())) == []
    api.tapir.attribute.get_attributes_by_type.assert_called_once()
    api.tapir.attribute.get_layer_combinations.assert_not_called()
    api.tapir.attribute.get_layers.assert_not_called()
    api.tapir.element.filter_elements.assert_not_called()
    api.tapir.property.get_property_values_of_elements.assert_not_called()


def test_no_matching_combination_names_are_decided_during_evaluation(layer_project):
    api = layer_project.api
    query = Query(where=LayerCombinationNamePredicate(test=TextTest(operator="contains", value="absent")))
    assert api.utilities.element.find_elements(query) == []
    api.tapir.attribute.get_layer_combinations.assert_called_once()
    api.tapir.element.filter_elements.assert_not_called()


def test_combination_read_errors_are_query_wide_failures(layer_project):
    api = layer_project.api
    error = tapir.ErrorItem(error=tapir.Error(code=7, message="Cannot read combination"))
    api.tapir.attribute.get_layer_combinations.side_effect = lambda attributes: [error] * len(attributes)
    with pytest.raises(BatchOperationError, match="Cannot read"):
        api.utilities.element.find_elements(Query(where=combination(operator="is not")))


def test_property_read_failure_is_query_wide(layer_project):
    api = layer_project.api
    api.tapir.property.get_property_values_of_elements.side_effect = RequestError("Layer read failed")
    with pytest.raises(RequestError, match="Layer read failed"):
        api.utilities.element.find_elements(Query(where=layer(operator="is not")))


@pytest.mark.parametrize(
    "predicate",
    [
        layer(operator="is not"),
        LayerNamePredicate(test=TextTest(operator="does not contain", value="Hidden")),
        combination(operator="is not"),
        LayerCombinationNamePredicate(test=TextTest(operator="is not", value="Empty")),
    ],
)
@pytest.mark.parametrize("error_location", ["row", "cell"])
def test_element_read_errors_are_preserved_in_negative_tests(layer_project, predicate, error_location):
    error = tapir.Error(code=7, message="Cannot read element")
    if error_location == "row":
        layer_project.row_errors[TALL] = tapir.ErrorItem(error=error)
    else:
        layer_project.values[TALL][LAYER_INDEX_PROPERTY] = tapir.PropertyValueErrorItem(error=error)
    result = layer_project.api.utilities.element.filter_elements_by_query_result([TALL, SLAB], Query(where=predicate))
    assert result.slots[0].is_error
    assert "Cannot read element" in result.slots[0].error.message
    assert "where.test" in result.slots[0].error.message
    assert all(item.elementId.guid != TALL for item in result.successes)


def test_unknown_layer_index_is_an_element_error(layer_project):
    layer_project.values[TALL][LAYER_INDEX_PROPERTY] = "999"
    result = layer_project.api.utilities.element.filter_elements_by_query_result(
        [TALL], Query(where=layer(operator="is not"))
    )
    assert result.slots[0].is_error
    assert "Layer index 999" in result.slots[0].error.message


def test_offline_metadata_reports_missing_field_and_rejects_wrong_test_family():
    result = validate_query(Query(where=layer()), [])
    (issue,) = result.issues
    assert (issue.code, issue.path, dict(issue.reference)) == ("unknown_field", "where.kind", {"kind": "layer"})

    with pytest.raises(InvalidFieldTestError, match="requires LayerTest"):
        LayerInfo(LAYERS).validate(TextTest(operator="is", value="A-Walls"))


def test_empty_dropdown_metadata_has_a_valid_schema_and_no_accepted_operand():
    field = LayerInfo([])
    schema = field.test_schema()
    Draft202012Validator.check_schema(schema)
    assert not Draft202012Validator(schema).is_valid(layer().test.model_dump(mode="json"))


def test_supplied_population_order_duplicates_and_nested_groups(layer_project):
    query = Query(
        where=AllOf(
            items=(
                LayerNamePredicate(test=TextTest(operator="starts with", value="a-")),
                AnyOf(items=(combination(), layer(3))),
            )
        )
    )
    inputs = [SLAB, BAD, TALL, SLAB]
    assert guids(layer_project.api.utilities.element.filter_elements_by_query(inputs, query)) == [SLAB, TALL, SLAB]


def test_prepare_without_catalogue_discovers_requested_metadata_once(layer_project):
    predicate = AnyOf(items=(layer(), LayerNamePredicate(test=TextTest(operator="is", value="A-Walls"))))
    builder = ContextBuilder()
    predicate.prepare(builder)
    context = builder.build(layer_project.api, [element(TALL), element(BAD)])
    assert predicate.evaluate(context, TALL).value
    assert not predicate.evaluate(context, BAD).value
    layer_project.api.tapir.attribute.get_attributes_by_type.assert_called_once_with(tapir.AttributeType.LAYER)
    layer_project.api.tapir.property.get_property_values_of_elements.assert_called_once()


def test_text_comparison_runs_only_in_predicate_evaluation(layer_project):
    predicate = LayerNamePredicate(test=TextTest(operator="contains", value="Walls"))
    builder = ContextBuilder()
    with patch.object(TextTest, "evaluate", autospec=True, side_effect=TextTest.evaluate) as compare:
        predicate.prepare(builder)
        context = builder.build(layer_project.api, [element(TALL), element(BAD)])
        compare.assert_not_called()
        assert predicate.evaluate(context, TALL).value
        compare.assert_called_once_with(predicate.test, "A-Walls")


def test_combination_name_comparison_runs_only_in_predicate_evaluation(layer_project):
    predicate = LayerCombinationNamePredicate(test=TextTest(operator="is", value="Structural"))
    builder = ContextBuilder()
    with patch.object(TextTest, "evaluate", autospec=True, side_effect=TextTest.evaluate) as compare:
        predicate.prepare(builder)
        context = builder.build(layer_project.api, [element(TALL), element(BAD)])
        compare.assert_not_called()
        assert predicate.evaluate(context, TALL).value
        compare.assert_called_once_with(predicate.test, "Structural")
        assert not predicate.evaluate(context, BAD).value


def test_combination_prepare_without_catalogue_shares_raw_reads(layer_project):
    predicate = AnyOf(
        items=(
            combination(),
            LayerCombinationNamePredicate(test=TextTest(operator="is", value="Structural")),
        )
    )
    builder = ContextBuilder()
    predicate.prepare(builder)
    context = builder.build(layer_project.api, [element(TALL), element(BAD)])
    assert predicate.evaluate(context, TALL).value
    assert not predicate.evaluate(context, BAD).value
    api = layer_project.api
    api.tapir.property.get_property_values_of_elements.assert_called_once()
    api.tapir.attribute.get_layer_combinations.assert_called_once()
    api.tapir.attribute.get_layers.assert_not_called()
    api.tapir.element.filter_elements.assert_not_called()


def test_layer_source_uses_builtin_property_and_preserves_read_errors(layer_project):
    layer_project.row_errors[TALL] = tapir.ErrorItem(error=tapir.Error(code=7, message="Cannot read element"))
    values = ELEMENT_LAYER_INDICES.load(layer_project.api, [element(TALL), element(SLAB)], [None])[None]
    assert values[TALL].is_error
    assert values[SLAB].value == 3
    api = layer_project.api
    args, kwargs = api.tapir.property.get_property_values_of_elements.call_args
    assert [item.propertyId.guid for item in args[1]] == [LAYER_INDEX_PROPERTY]
    assert kwargs == {"include_availability": True, "use_si_units": True}
    api.tapir.element.get_details_of_elements.assert_not_called()
    api.tapir.element._core.post_tapir_command.assert_not_called()


@pytest.mark.parametrize("raw", ["", "33.0", "3,0", "nan"])
def test_malformed_layer_index_is_an_element_error(layer_project, raw):
    layer_project.values[TALL][LAYER_INDEX_PROPERTY] = raw
    result = layer_project.api.utilities.element.filter_elements_by_query_result(
        [TALL], Query(where=layer(operator="is not"))
    )
    assert result.slots[0].is_error
    assert "Cannot interpret layer index" in result.slots[0].error.message


@pytest.mark.parametrize(
    "raw",
    [
        "<Undefined>",
        tapir.PropertyValueErrorItem(
            error=tapir.Error(code=7, message="Not available or not evaluated property"), isAvailable=False
        ),
    ],
)
def test_unavailable_or_undefined_layer_property_remains_an_error(layer_project, raw):
    layer_project.values[TALL][LAYER_INDEX_PROPERTY] = raw
    result = layer_project.api.utilities.element.filter_elements_by_query_result(
        [TALL], Query(where=layer(operator="is not"))
    )
    assert result.slots[0].is_error


def test_raw_combination_source_handles_empty_project(layer_project):
    layer_project.api.tapir.attribute.get_attributes_by_type.return_value = headers([])
    layer_project.api.tapir.attribute.get_attributes_by_type.side_effect = None
    assert LAYER_COMBINATIONS.load(layer_project.api, [element(TALL)], [None]) == {None: {}}
    layer_project.api.tapir.attribute.get_layer_combinations.assert_not_called()


@pytest.mark.parametrize("model", [LayerTest, LayerCombinationTest])
@pytest.mark.parametrize(
    "data",
    [
        {"operator": "contains", "value": str(LAYERS[0].guid)},
        {"operator": "is", "value": 2},
        {"operator": "is", "value": "not-a-guid"},
        {"operator": "is"},
        {"operator": "is", "value": str(LAYERS[0].guid), "name": "stale"},
    ],
)
def test_identity_test_rejects_invalid_operands(model, data):
    with pytest.raises(ValidationError):
        model.model_validate(data)
