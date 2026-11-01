"""Validate parsed query field references against captured metadata."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Literal, TypeAlias, assert_never

from .discovery import ClassificationCatalogue, PropertyCatalogue
from .fields import FieldInfo
from .errors import InvalidFieldTestError, UnsupportedFieldTypeError
from .models import (
    AllOf,
    AnyOf,
    ClassificationPredicate,
    ElementTypePredicate,
    Predicate,
    PropertyPredicate,
    Query,
    TestModel,
)

_Location: TypeAlias = tuple[str | int, ...]
_IssueCode: TypeAlias = Literal["unknown_field", "unsupported_field", "invalid_test"]


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


def validate_query(
    query: Query,
    catalogue: PropertyCatalogue | None = None,
    *,
    classifications: ClassificationCatalogue | None = None,
) -> QueryValidationResult:
    """Check every branch against supplied metadata, without API or value reads.

    Query construction/parsing must first validate structure. Expected field
    context failures become issues; ambiguous configuration and unexpected errors
    propagate. This function performs no version-compatibility interpretation or
    boolean evaluation, and returns no transformed query representation.
    """
    issues: list[QueryValidationIssue] = []

    def check_field[TestT: TestModel](
        field: FieldInfo[TestT] | None,
        test: TestT,
        reference: Mapping[str, str],
        id_field: str,
        location: _Location,
    ) -> None:
        if field is None:
            issues.append(
                QueryValidationIssue(
                    location=(*location, id_field),
                    code="unknown_field",
                    message=f"Field {dict(reference)} is not present in the catalogue",
                    reference=reference,
                )
            )
            return
        code: _IssueCode
        try:
            field.validate(test)
        except UnsupportedFieldTypeError as error:
            code, message = "unsupported_field", str(error)
        except InvalidFieldTestError as error:
            code, message = "invalid_test", str(error)
        else:
            return
        issues.append(
            QueryValidationIssue(
                location=(*location, "test"),
                code=code,
                message=message,
                reference=field.reference,
                name=field.name,
                group=field.group,
            )
        )

    def visit(node: Predicate, location: _Location) -> None:
        if isinstance(node, PropertyPredicate):
            check_field(
                catalogue.get(node.property_id) if catalogue is not None else None,
                node.test,
                {"kind": "property", "property_id": str(node.property_id)},
                "property_id",
                location,
            )
        elif isinstance(node, ClassificationPredicate):
            check_field(
                classifications.get(node.system_id) if classifications is not None else None,
                node.test,
                {"kind": "classification", "system_id": str(node.system_id)},
                "system_id",
                location,
            )
        elif isinstance(node, (AllOf, AnyOf)):
            for index, item in enumerate(node.items):
                visit(item, (*location, "items", index))
        elif isinstance(node, ElementTypePredicate):
            # The enum choices were checked during structure validation.
            return
        else:
            assert_never(node)

    visit(query.where, ("where",))
    return QueryValidationResult(issues=tuple(issues))
