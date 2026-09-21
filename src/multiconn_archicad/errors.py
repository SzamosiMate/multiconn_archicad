from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiconn_archicad.utilities.results import BatchResultBase


class MulticonnArchicadError(Exception):
    """Base class for all custom exceptions in the multiconn_archicad package."""


# --- Errors that happen during communication with the API ---


class APIErrorBase(MulticonnArchicadError):
    """
    Base class for errors during API communication or reported by the API.
    Catch this exception for unified handling of all API-related issues.
    """

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code: int | None = code
        self.message: str = message

    def __str__(self):
        return f"error: {{code={self.code}, message='{self.message}}}'"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.code}, message={self.message}>"

    def to_dict(self) -> dict[str, str]:
        return {"code": str(self.code), "message": self.message}


class RequestError(APIErrorBase):
    """Raised for errors originating from Network/HTTP/Parsing"""

    pass


class APIConnectionError(RequestError):
    """Raised for errors establishing a connection to the ArchiCAD API."""

    pass


class HeaderUnassignedError(RequestError, AttributeError):
    """Raised when a command is called on an unassigned ConnHeader"""

    pass


class CommandTimeoutError(RequestError, TimeoutError):
    """Raised when a command request to the ArchiCAD API times out."""

    pass


class InvalidResponseFormatError(RequestError):
    """Raised when the API response cannot be parsed as valid JSON."""

    pass


class ArchicadAPIError(APIErrorBase):
    """Raised when the ArchiCAD API or the Tapir Add-On indicates a failure in the response body."""

    pass


class StandardAPIError(ArchicadAPIError):
    """Raised when the ArchiCAD API indicates a failure in the response body."""

    pass


class StandardCommandUnavailable(StandardAPIError):
    """Raised when the ArchicadAPI receives an unknown command"""

    def __init__(self, message: str):
        super().__init__(message)
        self.code: int = 2002
        self.message: str = message


class AddOnCommandUnavailable(StandardAPIError):
    """Raised when the ArchicadAPI receives an unknown Add-on command"""

    def __init__(self, message: str):
        super().__init__(message)
        self.code: int = 4010
        self.message: str = message


class TapirCommandError(ArchicadAPIError):
    """Raised when a Tapir Add-On command reports a failure in its response."""

    pass


# --- Errors originating from Library Logic ---


class ProjectAlreadyOpenError(MulticonnArchicadError):
    """Raised when attempting to open a project that is already open."""

    pass


class ProjectNotFoundError(MulticonnArchicadError):
    """Raised when a specified project file cannot be found."""

    pass


class NotFullyInitializedError(MulticonnArchicadError):
    """Raised when an operation is attempted on an object not fully initialized."""

    pass


class BatchOperationError(MulticonnArchicadError):
    """Raised by fail-fast utility functions when one or more batch items fail."""

    def __init__(self, operation_name: str, result: BatchResultBase):
        self.result = result
        slots = tuple(slot for _, slot in result.iter_slots())
        self.succeeded_count = sum(slot.is_success for slot in slots)
        self.error_count = sum(slot.is_error for slot in slots)
        self.upstream_failed_count = sum(slot.is_upstream_failed for slot in slots)
        self.filtered_count = sum(slot.is_filtered for slot in slots)
        self._validate_result()
        super().__init__(self._format_message(operation_name))

    def _validate_result(self) -> None:
        if self.error_count == 0:
            raise ValueError(f"{type(self).__name__} requires at least one direct error.")

    def _format_message(self, operation_name: str) -> str:
        outcome = "partially failed" if self.succeeded_count else "failed"
        lines = [
            f"{operation_name} {outcome}.",
            "",
            self._count_line(self.succeeded_count, "item", "items", "succeeded"),
            self._count_line(self.error_count, "item", "items", "failed"),
        ]
        if self.upstream_failed_count:
            lines.append(
                self._count_line(
                    self.upstream_failed_count,
                    "item was",
                    "items were",
                    "skipped because an upstream operation failed",
                )
            )
        if self.filtered_count:
            lines.append(
                self._count_line(
                    self.filtered_count,
                    "item was",
                    "items were",
                    "filtered intentionally",
                )
            )
        lines.extend(self._error_lines("Errors:"))
        return "\n".join(lines)

    def _error_lines(self, heading: str) -> list[str]:
        return [
            "",
            heading,
            *(
                f"  - [{self._format_coordinate(coordinate)}]: {error}"
                for coordinate, error in self.result.iter_errors()
            ),
        ]

    @staticmethod
    def _count_line(count: int, singular: str, plural: str, outcome: str) -> str:
        noun = singular if count == 1 else plural
        return f"{count} {noun} {outcome}."

    @staticmethod
    def _format_coordinate(coordinate: object) -> str:
        if isinstance(coordinate, tuple):
            return ", ".join(map(str, coordinate))
        return str(coordinate)


class BatchNotFullySuccessfulError(BatchOperationError):
    """Raised when an operation requires every batch slot to succeed."""

    def _validate_result(self) -> None:
        if not (self.error_count or self.upstream_failed_count or self.filtered_count):
            raise ValueError("BatchNotFullySuccessfulError requires at least one non-successful slot.")

    def _format_message(self, operation_name: str) -> str:
        lines = [f"{operation_name} requires every item to succeed."]
        counts = (
            (self.error_count, "item contained an error", "items contained errors"),
            (
                self.upstream_failed_count,
                "item was skipped because an upstream operation failed",
                "items were skipped because an upstream operation failed",
            ),
            (self.filtered_count, "item was filtered intentionally", "items were filtered intentionally"),
        )
        lines.extend(
            f"{count} {singular if count == 1 else plural}."
            for count, singular, plural in counts
            if count
        )
        if self.error_count:
            lines.extend(self._error_lines("Errors:"))
        return "\n".join(lines)


class BatchWriteError(BatchOperationError):
    """Raised when a batch write partially or completely fails."""

    @property
    def failed_count(self) -> int:
        return self.error_count

    @property
    def partial_success(self) -> bool:
        return self.succeeded_count > 0

    def _format_message(self, operation_name: str) -> str:
        outcome = "partially failed" if self.partial_success else "failed"
        lines = [
            f"{operation_name} {outcome}.",
            "",
            self._count_line(self.succeeded_count, "value was", "values were", "written successfully"),
            self._count_line(self.failed_count, "value", "values", "failed"),
        ]
        if self.upstream_failed_count:
            lines.append(
                self._count_line(
                    self.upstream_failed_count,
                    "value was",
                    "values were",
                    "skipped because an upstream operation failed",
                )
            )
        if self.filtered_count:
            lines.append(
                self._count_line(
                    self.filtered_count,
                    "value was",
                    "values were",
                    "filtered intentionally",
                )
            )
        if self.partial_success:
            lines.extend(["", "Successful writes were applied and were not rolled back."])

        lines.extend(self._error_lines("Failures:"))
        return "\n".join(lines)
