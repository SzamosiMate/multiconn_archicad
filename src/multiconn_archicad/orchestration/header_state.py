"""Metadata state transitions for one connection header."""

from dataclasses import dataclass
from enum import Enum
from threading import Lock

from multiconn_archicad.orchestration.basic_types import (
    APIResponseError,
    ArchiCadID,
    ArchicadLocation,
    PendingResponse,
    ProductInfo,
    TapirInfo,
)


class Status(Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    UNASSIGNED = "unassigned"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(frozen=True)
class HeaderMetadata:
    """Bundle containing all polled metadata from an Archicad instance."""

    product_info: ProductInfo | APIResponseError
    archicad_id: ArchiCadID | APIResponseError
    archicad_location: ArchicadLocation | APIResponseError
    tapir_info: TapirInfo | APIResponseError


@dataclass(frozen=True)
class HeaderSnapshot:
    """One coherent state read; contained metadata models remain mutable."""

    status: Status
    metadata: HeaderMetadata
    latest_metadata: HeaderMetadata | None = None


class HeaderState:
    """Own metadata, status, and fetch validity behind an encapsulated lock.

    Operations never perform HTTP work, wait for futures, or invoke callbacks.
    Metadata bundles are replaced, so captured snapshots retain their values.
    """

    def __init__(self, status: Status, metadata: HeaderMetadata | None = None) -> None:
        self._lock = Lock()
        self._status = status
        if metadata is None:
            metadata = HeaderMetadata(
                product_info=PendingResponse(),
                archicad_id=PendingResponse(),
                archicad_location=PendingResponse(),
                tapir_info=PendingResponse(),
            )
        self._metadata = metadata
        self._latest_metadata: HeaderMetadata | None = None
        self._token: object | None = None

    def begin_fetch(self) -> object:
        """Supersede any fetch while retaining previously collected metadata."""
        with self._lock:
            self._token = token = object()
            self._status = Status.PENDING
            self._latest_metadata = None
            return token

    def complete(self, token: object, metadata: HeaderMetadata | None) -> bool:
        """Commit only a current, uncanceled fetch, including its failure."""
        with self._lock:
            if token is not self._token:
                return False
            self._latest_metadata = metadata
            if metadata is None:
                self._status = Status.FAILED
            else:
                self._metadata = _merge_metadata(self._metadata, metadata)
                self._status = Status.READY if isinstance(metadata.product_info, ProductInfo) else Status.FAILED
            return True

    def cancel(self) -> None:
        """Invalidate an in-flight result without clearing metadata or status."""
        with self._lock:
            self._token = None
            self._latest_metadata = None

    def unassign(self) -> None:
        """Invalidate the fetch and preserve historical project metadata."""
        with self._lock:
            self._token = None
            self._latest_metadata = None
            self._status = Status.UNASSIGNED

    def assign(self) -> None:
        """Mark a newly bound header pending without starting a fetch."""
        with self._lock:
            self._token = None
            self._latest_metadata = None
            self._status = Status.PENDING

    def snapshot(self) -> HeaderSnapshot:
        with self._lock:
            return HeaderSnapshot(self._status, self._metadata, self._latest_metadata)

    def resolved_token(self) -> object | None:
        """Read completion validity without waiting for the worker's future."""
        with self._lock:
            return self._token if self._status in (Status.READY, Status.FAILED) else None


def _merge_metadata(previous: HeaderMetadata, current: HeaderMetadata) -> HeaderMetadata:
    """Retain successful fields when a subsequent refresh cannot fetch them."""
    return HeaderMetadata(
        product_info=_keep_success(previous.product_info, current.product_info),
        archicad_id=_keep_success(previous.archicad_id, current.archicad_id),
        archicad_location=_keep_success(previous.archicad_location, current.archicad_location),
        tapir_info=_keep_success(previous.tapir_info, current.tapir_info),
    )


def _keep_success[T](previous: T | APIResponseError, current: T | APIResponseError) -> T | APIResponseError:
    if isinstance(current, APIResponseError) and not isinstance(previous, APIResponseError):
        return previous
    return current
