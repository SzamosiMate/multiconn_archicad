"""Validate parsed query field references against captured metadata."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, Protocol
from uuid import UUID

from .catalogue import FieldCatalogue, QueryFieldCatalogue
from .errors import InvalidFieldTestError, UnsupportedFieldTypeError

if TYPE_CHECKING:
    from .fields import FieldInfo
    from .models import Query, TestModel

_Location: TypeAlias = tuple[str | int, ...]
_IssueCode: TypeAlias = Literal["unknown_field", "unsupported_field", "invalid_test"]


class FieldPredicate[TestT](Protocol):
    """Expose the identity and test needed for field-context validation."""

    @property
    def kind(self) -> str: ...

    @property
    def field_id(self) -> UUID: ...

    @property
    def test(self) -> TestT: ...


@dataclass(frozen=True, slots=True)
class QueryValidationIssue:
    """Describe a field-context problem at one occurrence in the query."""

    location: _Location
    code: _IssueCode
    message: str
    reference: Mapping[str, str]
    name: str | None = None
    group: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference", MappingProxyType(dict(self.reference)))

    @property
    def path(self) -> str:
        """Render the structured location, for example where.items[1].test."""
        path = ""
        for part in self.location:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}" if path else part
        return path

    @property
    def qualified_name(self) -> str | None:
        if self.name is None:
            return None
        return f"{self.group} / {self.name}" if self.group else self.name

    def describe(self) -> dict[str, Any]:
        """Return JSON-friendly location and field context for UI/MCP clients."""
        return {
            "location": list(self.location),
            "path": self.path,
            "code": self.code,
            "message": self.message,
            "reference": dict(self.reference),
            "name": self.name,
            "group": self.group,
            "qualified_name": self.qualified_name,
        }


@dataclass(frozen=True, slots=True)
class QueryValidationResult:
    """Collect context issues without changing or executing the query tree."""

    issues: tuple[QueryValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def raise_for_errors(self) -> None:
        """Raise one exception retaining this complete result when invalid."""
        if self.issues:
            raise QueryValidationError(self)

    def describe(self) -> dict[str, Any]:
        return {"is_valid": self.is_valid, "issues": [issue.describe() for issue in self.issues]}


class QueryValidationError(ValueError):
    """Expose the complete context-validation result to exception-based callers."""

    def __init__(self, result: QueryValidationResult):
        self.result = result
        messages = "\n".join(f"{issue.path}: {issue.message}" for issue in result.issues)
        super().__init__(f"Query context validation failed:\n{messages}")


@dataclass(frozen=True, slots=True)
class FieldCheck[TestT: TestModel]:
    """Check one field predicate at its location in the query tree."""

    predicate: FieldPredicate[TestT]
    location: _Location


def _unknown_field_issue[TestT: TestModel](check: FieldCheck[TestT]) -> QueryValidationIssue:
    """Report a failed lookup at the predicate's identifier."""
    reference = {"kind": check.predicate.kind, "field_id": str(check.predicate.field_id)}
    return QueryValidationIssue(
        location=(*check.location, "field_id"),
        code="unknown_field",
        message=f"Field {reference} is not present in the catalogue",
        reference=reference,
    )


def _check_known_field[TestT: TestModel](
    field: FieldInfo[TestT], check: FieldCheck[TestT]
) -> tuple[QueryValidationIssue, ...]:
    """Check a resolved field's test, preserving unexpected exceptions."""
    code: _IssueCode
    try:
        field.validate(check.predicate.test)
        return ()
    except UnsupportedFieldTypeError as error:
        code, message = "unsupported_field", str(error)
    except InvalidFieldTestError as error:
        code, message = "invalid_test", str(error)

    return (
        QueryValidationIssue(
            location=(*check.location, "test"),
            code=code,
            message=message,
            reference=field.reference,
            name=field.name,
            group=field.group,
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class QueryValidationContext:
    """Supply captured catalogues and common field checks to predicate methods.

    Predicates supply field identity and own tree traversal. This context
    resolves references without traversal, API reads or accumulated issues.
    """

    catalogue: QueryFieldCatalogue

    def __init__(self, catalogues: QueryFieldCatalogue | Sequence[FieldCatalogue[Any, Any]]):
        catalogue = catalogues if isinstance(catalogues, QueryFieldCatalogue) else QueryFieldCatalogue(catalogues)
        object.__setattr__(self, "catalogue", catalogue)

    @property
    def catalogues(self) -> Mapping[str, FieldCatalogue[Any, Any]]:
        return self.catalogue.catalogues

    def check_field[TestT: TestModel](self, check: FieldCheck[TestT]) -> tuple[QueryValidationIssue, ...]:
        """Dispatch a missing reference or a resolved field's test check."""
        predicate = check.predicate
        field = self.catalogue.resolve({"kind": predicate.kind, "field_id": predicate.field_id})
        if field is None:
            return (_unknown_field_issue(check),)
        return _check_known_field(field, check)


def validate_query(
    query: Query,
    catalogues: QueryFieldCatalogue | Sequence[FieldCatalogue[Any, Any]],
) -> QueryValidationResult:
    """Check every branch against supplied metadata, without API or value reads.

    Query construction/parsing must first validate structure. Expected field
    context failures become issues; ambiguous configuration and unexpected errors
    propagate. This function performs no version-compatibility interpretation or
    boolean evaluation, and returns no transformed query representation.
    """
    context = QueryValidationContext(catalogues)
    return QueryValidationResult(issues=query.where.validate_fields(context))

