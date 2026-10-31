"""Collect source requests and retain their data for one query execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar, cast

from multiconn_archicad.models.tapir import types as tapir

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


# Keep both parameters invariant: provide(source, key, value) must enforce the
# source's exact types rather than widening Value to accommodate a wrong value.
Key = TypeVar("Key", bound=Hashable)
Value = TypeVar("Value")


class ContextSource(ABC, Generic[Key, Value]):
    """Load a batch of requested keys; source objects also identify their data.

    Reuse the same source instance in preparation and evaluation. Each source
    defines its own key and value types, with no central source-kind registry.
    """

    @abstractmethod
    def load(
        self,
        api: UnifiedApi,
        elements: Sequence[tapir.ElementIdArrayItem],
        keys: Sequence[Key],
    ) -> Mapping[Key, Value]:
        """Retrieve all requested keys for the supplied candidate population."""
        ...


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """Share completed source data across every element in one execution.

    ContextBuilder constructs this heterogeneous store through typed requests.
    Evaluation only reads it; source payloads retain their original batch slots.
    """

    _data: Mapping[object, object] = field(default_factory=dict)

    def data[Key: Hashable, Value](self, source: ContextSource[Key, Value]) -> Mapping[Key, Value]:
        """Recover the payload type associated with this exact source instance."""
        # The builder stores source.load() under that same source object. The
        # heterogeneous dictionary cannot express this relationship to mypy.
        return cast(Mapping[Key, Value], self._data[source])


class _LoadRequest(Protocol):
    """Erase individual source types only while storing/executing requests."""

    def load(self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem]) -> object: ...


@dataclass(slots=True)
class _SourceRequest[Key: Hashable, Value]:
    """Track requested keys and already supplied answers for one source batch."""

    source: ContextSource[Key, Value]
    # An ordered set of keys requested by predicates.
    keys: dict[Key, None] = field(default_factory=dict)
    # Completed answers supplied by an earlier execution step, before loading.
    provided: dict[Key, Value] = field(default_factory=dict)

    def load(self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem]) -> Mapping[Key, Value]:
        missing = tuple(key for key in self.keys if key not in self.provided)
        loaded = self.source.load(api, elements, missing) if missing and elements else {}
        return {**self.provided, **loaded}


class ContextBuilder:
    """Collect predicate requirements, deduplicate keys, then load each source."""

    def __init__(self) -> None:
        self._requests: dict[object, _LoadRequest] = {}

    def _request[Key: Hashable, Value](self, source: ContextSource[Key, Value]) -> _SourceRequest[Key, Value]:
        if source not in self._requests:
            self._requests[source] = _SourceRequest(source)
        # Every entry was created from its key's source. Reusing that source
        # preserves its Key/Value types across calls to require/provide.
        return cast(_SourceRequest[Key, Value], self._requests[source])

    def require[Key: Hashable, Value](self, source: ContextSource[Key, Value], key: Key) -> None:
        """Request a key once, preserving first-request order within its source."""
        self._request(source).keys.setdefault(key, None)

    def requires[Key: Hashable, Value](self, source: ContextSource[Key, Value]) -> bool:
        """Report whether preparation has registered this source."""
        return source in self._requests

    def provide[Key: Hashable, Value](self, source: ContextSource[Key, Value], key: Key, value: Value) -> None:
        """Reuse an already completed value instead of requesting it again."""
        self._request(source).provided[key] = value

    def build(self, api: UnifiedApi, elements: Sequence[tapir.ElementIdArrayItem]) -> EvaluationContext:
        """Load requested data for this population; never issue reads for no elements."""
        return EvaluationContext({source: request.load(api, elements) for source, request in self._requests.items()})
