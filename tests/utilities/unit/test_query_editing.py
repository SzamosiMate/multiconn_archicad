"""Verify row persistence, expression compilation, and diagnostic locations."""

from uuid import UUID

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    QUERY_SCHEMA_VERSION,
    AllOf,
    AnyOf,
    ElementTypePredicate,
    ElementTypeTest,
)
from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query, validate_row

pytestmark = pytest.mark.unit


def _type_row(element_type: str, **syntax) -> QueryRow:
    return QueryRow(
        predicate={"kind": "element_type", "test": {"kind": "element_type", "types": [element_type]}}, **syntax
    )


def test_compiles_and_before_or_and_ignores_the_last_connector():
    wall = _type_row("Wall", join_next="or")
    slab = _type_row("Slab")
    beam = _type_row("Beam", join_next="or")

    result = build_query(QueryRows(rows=[wall, slab, beam]))

    assert not result.issues
    assert result.query is not None
    assert result.query.schema_version == QUERY_SCHEMA_VERSION
    assert result.query.where == AnyOf(
        items=(
            ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))),
            AllOf(
                items=(
                    ElementTypePredicate(test=ElementTypeTest(types=(ElementType.SLAB,))),
                    ElementTypePredicate(test=ElementTypeTest(types=(ElementType.BEAM,))),
                )
            ),
        )
    )
    assert result.row_id_at(("where", "items", 1, "items", 0, "test", "types", 0)) == slab.row_id
    assert result.row_id_at(("where",)) is None
    assert beam.join_next == "or"


def test_parentheses_close_before_the_outgoing_connector_and_preserve_nested_groups():
    wall = _type_row("Wall", open_parentheses=2, join_next="or")
    slab = _type_row("Slab", close_parentheses=1)
    beam = _type_row("Beam", close_parentheses=1, join_next="or")
    column = _type_row("Column")

    result = build_query(QueryRows(rows=[wall, slab, beam, column]))

    assert result.query is not None
    assert result.query.where == AnyOf(
        items=(
            AllOf(
                items=(
                    AnyOf(
                        items=(
                            ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))),
                            ElementTypePredicate(test=ElementTypeTest(types=(ElementType.SLAB,))),
                        )
                    ),
                    ElementTypePredicate(test=ElementTypeTest(types=(ElementType.BEAM,))),
                )
            ),
            ElementTypePredicate(test=ElementTypeTest(types=(ElementType.COLUMN,))),
        )
    )
    assert result.row_id_at(("where", "items", 0, "items", 0, "items", 1)) == slab.row_id


def test_collects_expression_and_predicate_errors_without_returning_a_query():
    extra_close = _type_row("Wall", close_parentheses=1)
    incomplete = QueryRow(
        open_parentheses=1,
        predicate={
            "kind": "property",
            "field_id": str(UUID(int=1)),
            "test": {"kind": "number", "operator": "is greater than"},
        },
    )

    result = build_query(QueryRows(rows=[extra_close, incomplete]))

    assert result.query is None
    assert not result.row_ids_by_location
    assert [(issue.row_id, issue.location, issue.code) for issue in result.issues] == [
        (extra_close.row_id, ("close_parentheses",), "unmatched_close"),
        (incomplete.row_id, ("open_parentheses",), "unmatched_open"),
        (incomplete.row_id, ("predicate", "test", "value"), "invalid_predicate"),
    ]
    assert validate_row(incomplete) == result.issues[-1:]


def test_rejects_hidden_group_nodes_and_empty_expressions():
    group = QueryRow(predicate={"kind": "all", "items": []})
    assert validate_row(group)[0].code == "group_in_row"

    result = build_query(QueryRows())
    assert result.query is None
    assert result.issues[0].code == "empty_expression"


def test_saved_draft_regenerates_runtime_ids_and_keeps_incomplete_input():
    row = QueryRow(predicate={"kind": "property", "test": {"kind": "number"}}, join_next="or")
    document = QueryRows(rows=[row])

    payload = document.model_dump()
    assert "row_id" not in payload["rows"][0]
    restored = QueryRows.model_validate_json(document.model_dump_json(), context={"require_schema_version": True})
    assert restored.model_dump() == payload
    assert restored.rows[0].row_id != row.row_id
    assert document.model_copy(deep=True).rows[0].row_id == row.row_id

    duplicate = row.duplicate()
    assert duplicate.row_id != row.row_id
    duplicate.predicate["test"] = {"kind": "number", "value": 1}
    assert row.predicate["test"] == {"kind": "number"}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")], ids=["nan", "inf", "-inf"])
def test_rejects_nonfinite_values_on_load_and_after_in_place_edits(value):
    with pytest.raises(ValidationError, match="finite number"):
        QueryRow(predicate={"test": {"value": [value]}})

    row = QueryRow(predicate={"test": {"value": [0]}})
    document = QueryRows(rows=[row])
    row.predicate["test"] = {"value": [value]}

    with pytest.raises(PydanticSerializationError, match="finite number"):
        document.model_dump_json()


def test_saved_document_requires_supported_version_and_nonnullable_connectors():
    context = {"require_schema_version": True}
    with pytest.raises(ValidationError, match="schema_version must be explicitly supplied"):
        QueryRows.model_validate({"rows": []}, context=context)
    with pytest.raises(ValidationError, match="Unsupported query schema version"):
        QueryRows.model_validate({"schema_version": "999.0", "rows": []}, context=context)
    with pytest.raises(ValidationError, match="join_next"):
        QueryRow.model_validate({"predicate": {}, "join_next": None})
