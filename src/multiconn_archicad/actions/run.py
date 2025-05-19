from __future__ import annotations
from enum import Enum, auto
import asyncio
import inspect
import logging
from functools import wraps
from typing import Callable, Any, TYPE_CHECKING, Iterable, Generic, TypeVar, Iterator, Mapping, Optional, Concatenate, \
    Coroutine

from multiconn_archicad.utilities.async_utils import run_sync
log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from multiconn_archicad.multi_conn import MultiConn
    from multiconn_archicad.conn_header import ConnHeader
    from multiconn_archicad.basic_types import Port

T = TypeVar("T")

class PerHeader(Generic[T]):
    _data: dict[Port, T | Exception]

    def __init__(self, initial_data: Optional[Mapping[Port, T | Exception]] = None):
        if initial_data:
            self._data = dict(initial_data)
        else:
            self._data = {}

    @property
    def data(self) -> Mapping[Port, T | Exception]:
        """Provides read-only access to the internal data dictionary."""
        return self._data.copy()

    def get(self, port_key: Port, default: Any = None) -> T | Exception | Any:
        return self._data.get(port_key, default)

    def __getitem__(self, port_key: Port) -> T | Exception:
        return self._data[port_key]

    def __setitem__(self, port_key: Port, value: T | Exception) -> None:
        self._data[port_key] = value

    def __contains__(self, port_key: Port) -> bool:
        return port_key in self._data

    def __iter__(self) -> Iterator[Port]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def items(self) -> Iterable[tuple[Port, T | Exception]]:
        return self._data.items()

    def keys(self) -> Iterable[Port]:
        return self._data.keys()

    def values(self) -> Iterable[T | Exception]:
        return self._data.values()

    def successful_results(self) -> dict[Port, T]:
        return {p: r for p, r in self._data.items() if not isinstance(r, Exception)}

    def errors(self) -> dict[Port, Exception]:
        return {p: r for p, r in self._data.items() if isinstance(r, Exception)}

    @classmethod
    def from_scalar(cls, ports: Iterable[Port], scalar_value: T) -> "PerHeader[T]":
        return cls({port: scalar_value for port in ports})

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(data={self._data})"

class RunMode(Enum):
    SINGLE = auto()      # Operates on the primary connection
    MULTI_SYNC = auto()  # Operates on multiple connections, synchronously
    MULTI_ASYNC = auto() # Operates on multiple connections, asynchronously

class RunCommand:
    def __init__(self, multi_conn: MultiConn, default_mode: RunMode = RunMode.SINGLE) -> None:
        self.multi_conn: MultiConn = multi_conn
        self.mode: RunMode = default_mode



    def single[T, **P](self, func: Callable[[ConnHeader, P], T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Runs the function on the primary Archicad connection.
        """
        log.debug(f"RunAction.single: Executing function '{func.__name__}' on primary port {self.multi_conn.primary.port}")
        return func(self.multi_conn.primary, *args, **kwargs)

    def multi_sync[T, **P](self, func: Callable[[ConnHeader, P], T], *args: P.args,
        **kwargs: P.kwargs,
    ) -> dict[Port, T | Exception]:
        """
        Runs the function synchronously on all active Archicad connections.
        Collects results or exceptions for each connection.
        Returns a dictionary mapping each port to its result or the encountered Exception.
        """
        results: dict[Port, T | Exception] = {}

        log.debug(f"RunAction.multi_sync: Executing function '{func.__name__}' on {len(self.multi_conn.active)} headers.")
        for port, header in self.multi_conn.active.items():
            try:
                result = func(header, *args, **kwargs)
                results[port] = result
            except Exception as e:
                log.error(
                    f"RunAction.multi_sync: Error running function '{func.__name__}' on port {port}: {e}", exc_info=True
                )
                results[port] = e
        return results

    @staticmethod
    def _get_value_for_port[T](arg: T | PerHeader[T| Exception], port: Port) -> T | Exception:
        if isinstance(arg, PerHeader):
            if port not in arg:
                return MissingContextualInputError(f"Input for port {port} missing in PerHeader object.")
            return arg[port]
        else:
            return arg

    @staticmethod
    async def _execute_async_on_header(
        self: Any,  # Assuming this is a method of a class, 'self' is conventional
        func: Callable[Concatenate[ConnHeader, P_Call], Coroutine[Any, Any, T_Ret]]
        | Callable[Concatenate[ConnHeader, P_Call], T_Ret],
        header: ConnHeader,
        *args: P_Call.args,
        **kwargs: P_Call.kwargs,
    ) -> T_Ret:  # The function ultimately returns T_Ret, whether it was sync or async
        # Check if func is an async function or a callable object with an async __call__
        is_async_callable = False
        if inspect.iscoroutinefunction(func):
            is_async_callable = True
        elif callable(func) and not inspect.isfunction(func) and hasattr(func, "__call__"):
            # For callable objects, check if their __call__ method is a coroutine function
            if inspect.iscoroutinefunction(getattr(func, "__call__")):
                is_async_callable = True

        if is_async_callable:
            # If func is already async, await it directly.
            # We need to cast `func` here because the Union type doesn't narrow
            # perfectly for the call signature with P_Call.
            # Type checker might see `func` as potentially the sync version.
            async_func = cast(Callable[Concatenate[ConnHeader, P_Call], Coroutine[Any, Any, T_Ret]], func)
            return await async_func(header, *args, **kwargs)
        else:
            # If func is synchronous, run it in a thread.
            # `asyncio.to_thread` correctly infers the return type T_Ret.
            # Cast `func` to its synchronous signature for `to_thread`.
            sync_func = cast(Callable[Concatenate[ConnHeader, P_Call], T_Ret], func)
            return await asyncio.to_thread(sync_func, header, *args, **kwargs)