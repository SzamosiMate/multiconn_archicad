"""Validate a parsed query against an existing property metadata snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias, assert_never
from uuid import UUID

from .discovery import PropertyCatalogue
from .errors import InvalidPropertyTestError
from .models import AllOf, AnyOf, ElementTypePredicate, Negate, Predicate, PropertyPredicate, Query
from . import UnsupportedPropertyTypeError

_Location: TypeAlias = tuple[str | int, ...]
_IssueCode: TypeAlias = Literal["unknown_property", "unsupported_property", "invalid_test"]


@dataclass(frozen=True, slots=True)
class QueryValidationIssue:
    """Describe a property-context problem at one occurrence in the query."""

    location: _Location
    code: _IssueCode
    message: str
    property_id: UUID
    name: str | None = None
    group: str | None = None

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
            "reference": {"kind": "property", "property_id": str(self.property_id)},
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


def validate_query(query: Query, catalogue: PropertyCatalogue) -> QueryValidationResult:
    """Check every branch against supplied metadata, without API or value reads.

    Query construction/parsing must first validate structure. Expected property
    context failures become issues; ambiguous configuration and unexpected errors
    propagate. This function performs no version-compatibility interpretation or
    boolean evaluation, and returns no transformed query representation.
    """
    issues: list[QueryValidationIssue] = []

    def visit(node: Predicate, location: _Location) -> None:
        if isinstance(node, PropertyPredicate):
            field = catalogue.get(node.property_id)
            if field is None:
                issues.append(
                    QueryValidationIssue(
                        location=(*location, "property_id"),
                        code="unknown_property",
                        message=f"Property {node.property_id} is not present in the catalogue",
                        property_id=node.property_id,
                    )
                )
                return
            code: _IssueCode
            try:
                field.validate(node.test)
            except UnsupportedPropertyTypeError as error:
                code = "unsupported_property"
                message = str(error)
            except InvalidPropertyTestError as error:
                code = "invalid_test"
                message = str(error)
            else:
                return
            issues.append(
                QueryValidationIssue(
                    location=(*location, "test"),
                    code=code,
                    message=message,
                    property_id=node.property_id,
                    name=field.name,
                    group=field.group,
                )
            )
        elif isinstance(node, (AllOf, AnyOf)):
            for index, item in enumerate(node.items):
                visit(item, (*location, "items", index))
        elif isinstance(node, Negate):
            visit(node.item, (*location, "item"))
        elif isinstance(node, ElementTypePredicate):
            # The enum choices were checked during structure validation.
            return
        else:
            assert_never(node)

    visit(query.where, ("where",))
    return QueryValidationResult(issues=tuple(issues))
