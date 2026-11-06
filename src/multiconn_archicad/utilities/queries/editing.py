"""Represent editable query rows and compile them into an executable query."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PrivateAttr,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from .models import AllOf, AnyOf, Predicate, Query
from .versioning import QUERY_SCHEMA_VERSION, validate_query_version

_Location = tuple[str | int, ...]
_IssueCode = Literal["empty_expression", "unmatched_open", "unmatched_close", "group_in_row", "invalid_predicate"]
_ParenthesisCount = Annotated[int, Field(strict=True, ge=0)]

_predicate_adapter = TypeAdapter[Predicate](Predicate)
_payload_adapter = TypeAdapter[dict[str, JsonValue]](dict[str, JsonValue], config=ConfigDict(allow_inf_nan=False))


class QueryRow(BaseModel):
    """Hold one unfinished predicate and its surrounding expression syntax."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)

    open_parentheses: _ParenthesisCount = 0
    close_parentheses: _ParenthesisCount = 0
    predicate: dict[str, JsonValue]
    join_next: Literal["and", "or"] = "and"

    _row_id: UUID = PrivateAttr(default_factory=uuid4)

    @field_serializer("predicate", when_used="json")
    def serialize_predicate(self, predicate: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Check in-place edits before JSON serialization can replace non-finite values."""
        return _payload_adapter.validate_python(predicate)

    @property
    def row_id(self) -> UUID:
        """Identify the row within the current editor session."""
        return self._row_id

    def duplicate(self) -> QueryRow:
        """Copy the row and its data with a fresh editor identity."""
        return type(self).model_validate(self.model_dump())


class QueryRows(BaseModel):
    """Store a draft in the same schema version as its compiled query."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = QUERY_SCHEMA_VERSION
    rows: list[QueryRow] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def require_explicit_version(cls, data: Any, info: ValidationInfo) -> Any:
        """Use the query's persistence context when loading a saved draft."""
        if (
            isinstance(info.context, Mapping)
            and info.context.get("require_schema_version")
            and isinstance(data, Mapping)
            and "schema_version" not in data
        ):
            raise ValueError("schema_version must be explicitly supplied")
        return data

    @field_validator("schema_version")
    @classmethod
    def check_schema_version(cls, version: str) -> str:
        validate_query_version(version)
        return version


@dataclass(frozen=True, slots=True)
class RowIssue:
    """Describe an expected problem at a location relative to a row."""

    row_id: UUID | None
    location: _Location
    code: _IssueCode
    message: str


@dataclass(frozen=True, slots=True)
class QueryBuildResult:
    """Carry either a complete query with source locations or its input issues."""

    query: Query | None
    issues: tuple[RowIssue, ...] = ()
    row_ids_by_location: Mapping[_Location, UUID] = field(default_factory=dict)

    def __post_init__(self) -> None:
        has_query = self.query is not None
        has_issues = bool(self.issues)
        if has_query == has_issues or (has_issues and self.row_ids_by_location):
            raise ValueError("Expected a complete query or build issues without source locations")
        object.__setattr__(self, "row_ids_by_location", MappingProxyType(dict(self.row_ids_by_location)))

    def row_id_at(self, location: _Location) -> UUID | None:
        """Resolve a predicate path or a location inside that predicate."""
        while location:
            if location in self.row_ids_by_location:
                return self.row_ids_by_location[location]
            location = location[:-1]
        return None


def _payload_location(payload: JsonValue, location: _Location) -> _Location:
    """Remove one union tag per payload object, preserving real keys.

    For example, ("property", "test", "number", "value") becomes
    ("predicate", "test", "value").
    """
    result: list[str | int] = []
    skipped_tag = False
    for part in location:
        if isinstance(payload, dict) and part == payload.get("kind") and not skipped_tag:
            skipped_tag = True
            continue
        result.append(part)
        skipped_tag = False
        if isinstance(payload, dict) and isinstance(part, str):
            payload = payload.get(part)
        elif isinstance(payload, list) and isinstance(part, int) and 0 <= part < len(payload):
            payload = payload[part]
        else:
            payload = None
    return ("predicate", *result)


def _validate_row(row: QueryRow) -> tuple[Predicate | None, tuple[RowIssue, ...]]:
    if row.predicate.get("kind") in ("all", "any"):
        return None, (RowIssue(row.row_id, ("predicate", "kind"),
                        "group_in_row", "A row must contain a single condition, not an AND/OR group. "
                                        "Use parentheses and connectors to group rows."),)

    try:
        predicate = _predicate_adapter.validate_python(row.predicate)
    except ValidationError as error:
        return None, tuple(
            RowIssue(row.row_id, _payload_location(row.predicate, issue["loc"]), "invalid_predicate", issue["msg"])
            for issue in error.errors(include_url=False)
        )
    return predicate, ()


def validate_row(row: QueryRow) -> tuple[RowIssue, ...]:
    """Validate a row's predicate without inspecting adjacent rows or the project."""
    _, issues = _validate_row(row)
    return issues


def _expression_issues(rows: list[QueryRow]) -> list[RowIssue]:
    if not rows:
        return [RowIssue(None, ("rows",), "empty_expression", "Add at least one query row")]

    issues: list[RowIssue] = []
    opens: list[tuple[UUID, int]] = []
    for row in rows:
        if row.open_parentheses:
            opens.append((row.row_id, row.open_parentheses))
        remaining_closes = row.close_parentheses
        while remaining_closes and opens:
            row_id, count = opens.pop()
            if remaining_closes < count:
                opens.append((row_id, count - remaining_closes))
                remaining_closes = 0
            else:
                remaining_closes -= count
        if remaining_closes:
            issues.append(
                RowIssue(
                    row.row_id,
                    ("close_parentheses",),
                    "unmatched_close",
                    f"Unmatched closing parentheses: {remaining_closes}",
                )
            )

    for row_id, count in opens:
        issues.append(
            RowIssue(row_id, ("open_parentheses",), "unmatched_open", f"Unmatched opening parentheses: {count}")
        )
    return issues


@dataclass(slots=True)
class _Group:
    """Collect AND terms between OR connectors at one level of parentheses."""

    and_terms: list[Predicate] = field(default_factory=list)
    or_operands: list[Predicate] = field(default_factory=list)

    def finish_and_term(self) -> None:
        operand = self.and_terms[0] if len(self.and_terms) == 1 else AllOf(items=tuple(self.and_terms))
        self.or_operands.append(operand)
        self.and_terms.clear()

    def finish(self) -> Predicate:
        self.finish_and_term()
        return self.or_operands[0] if len(self.or_operands) == 1 else AnyOf(items=tuple(self.or_operands))


def _compile_expression(rows: list[QueryRow], leaves: list[Predicate]) -> Predicate:
    """Compile nonempty, balanced rows with one validated leaf per row.

    AND binds more tightly than OR within each group.
    """
    groups = [_Group()]
    for index, (row, leaf) in enumerate(zip(rows, leaves, strict=True)):
        groups.extend(_Group() for _ in range(row.open_parentheses))
        groups[-1].and_terms.append(leaf)
        for _ in range(row.close_parentheses):
            group = groups.pop()
            groups[-1].and_terms.append(group.finish())
        if index < len(rows) - 1 and row.join_next == "or":
            groups[-1].finish_and_term()
    return groups[0].finish()


def _source_locations(root: Predicate, rows: list[QueryRow], leaves: list[Predicate]) -> dict[_Location, UUID]:
    row_ids = {id(leaf): row.row_id for row, leaf in zip(rows, leaves, strict=True)}
    pending: list[tuple[_Location, Predicate]] = [(("where",), root)]
    locations: dict[_Location, UUID] = {}
    while pending:
        location, node = pending.pop()
        if isinstance(node, (AllOf, AnyOf)):
            pending.extend(
                ((*location, "items", index), child) for index, child in reversed(tuple(enumerate(node.items)))
            )
        else:
            locations[location] = row_ids[id(node)]
    return locations


def build_query(document: QueryRows) -> QueryBuildResult:
    """Compile a draft offline, collecting expression and predicate issues."""
    issues = _expression_issues(document.rows)
    leaves: list[Predicate] = []
    for row in document.rows:
        predicate, row_issues = _validate_row(row)
        issues.extend(row_issues)
        if predicate is not None:
            leaves.append(predicate)

    if issues:
        return QueryBuildResult(query=None, issues=tuple(issues))

    root = _compile_expression(document.rows, leaves)
    query = Query(schema_version=document.schema_version, where=root)
    return QueryBuildResult(query=query, row_ids_by_location=_source_locations(query.where, document.rows, leaves))
