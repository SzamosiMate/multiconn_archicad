from threading import Barrier, Event, Thread

import pytest

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.orchestration.basic_types import APIResponseError, PendingResponse, ProductInfo
from multiconn_archicad.orchestration.conn_header import ConnHeader, Status
from multiconn_archicad.orchestration.events import ConnectionEvents


def _events_for(headers, dispatcher=None):
    return ConnectionEvents(dispatcher, get_primary=lambda: None, get_headers=headers.copy)


def _start_fetch(header):
    with header._fetch_lock:
        header._fetch_token = object()
        header._is_cancelled = False
        header._status = Status.PENDING
        return header._fetch_token


def _complete_fetch(header, token=None):
    with header._fetch_lock:
        header._fetch_token = token if token is not None else object()
        header._is_cancelled = False
        header._status = Status.READY
        return header._fetch_token


def test_replay_and_publication_are_ordered_and_cancellable():
    tasks = []
    first, second = ConnHeader(Port(19723), initialize=False), ConnHeader(Port(19724), initialize=False)
    headers = {first.port: first, second.port: second}
    events = _events_for(headers, tasks.append)
    first_token, second_token = _complete_fetch(first), _complete_fetch(second)
    events._resolved(first, first_token)
    events._resolved(second, second_token)

    seen = []
    unsubscribe = events.subscribe_metadata_resolved(seen.append)
    assert len(tasks) == 1
    tasks.pop(0)()
    assert seen == [first, second]

    _start_fetch(first)
    events._resolved(second, second_token)  # duplicate completion
    headers.pop(second.port)
    headers[second.port] = second
    _start_fetch(second)
    assert tasks == []
    unsubscribe()
    unsubscribe()


def test_queued_completion_is_suppressed_by_refresh_removal_and_unsubscribe():
    tasks = []
    header = ConnHeader(Port(19723), initialize=False)
    headers = {header.port: header}
    events = _events_for(headers, tasks.append)
    seen = []
    unsubscribe = events.subscribe_metadata_resolved(seen.append)

    token = _complete_fetch(header)
    events._resolved(header, token)
    _start_fetch(header)
    tasks.pop(0)()
    assert seen == []

    token = _complete_fetch(header)
    events._resolved(header, token)
    headers.pop(header.port)
    tasks.pop(0)()
    assert seen == []

    headers[header.port] = header
    token = _complete_fetch(header)
    events._resolved(header, token)
    unsubscribe()
    tasks.pop(0)()
    assert seen == []


def test_primary_replay_order_noop_and_callback_reentrancy():
    tasks = []
    conn = MultiConn(dispatcher=tasks.append)
    first, second = ConnHeader(Port(19723), initialize=False), ConnHeader(Port(19724), initialize=False)
    conn._open_port_headers = {first.port: first, second.port: second}
    events = conn.events
    seen = []
    unsubscribe = events.subscribe_primary_changed(lambda old, new: seen.append((old, new)))
    conn._commit_primary(first)
    conn._commit_primary(first)
    conn._commit_primary(second)
    conn._commit_primary(None)
    assert len(tasks) == 1
    tasks.pop(0)()
    assert seen == [(None, None), (None, first), (first, second), (second, None)]
    unsubscribe()


def test_dispatcher_and_handler_failures_do_not_block_other_handlers(caplog):
    events = _events_for({}, lambda task: (_ for _ in ()).throw(RuntimeError("schedule")))
    events.subscribe_primary_changed(lambda old, new: None)
    assert "dispatcher failed" in caplog.text

    calls = []
    events = _events_for({})
    events.subscribe_primary_changed(lambda old, new: (_ for _ in ()).throw(RuntimeError("handler")))
    events.subscribe_primary_changed(lambda old, new: calls.append(new))
    events._primary_changed(None, None)
    assert calls == [None]
    assert "callback failed" in caplog.text


def test_multiconn_registration_does_not_scan_and_fetch_reports_success_and_failure(monkeypatch):
    def unexpected_scan(*args):
        raise AssertionError("registration triggered discovery")

    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", unexpected_scan)
    monkeypatch.setattr(ConnHeader, "get_product_info", lambda self, timeout: ProductInfo(version=27, buildNumber=1, languageCode="INT"))
    monkeypatch.setattr(ConnHeader, "get_archicad_id", lambda self, timeout: APIResponseError(message="no project"))
    monkeypatch.setattr(ConnHeader, "get_archicad_location", lambda self, timeout: APIResponseError(message="unknown"))
    monkeypatch.setattr(ConnHeader, "get_tapir_info", lambda self, timeout: APIResponseError(message="missing"))
    monkeypatch.setattr("multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss", lambda self: None)

    tasks = []
    conn = MultiConn(ui_mode=True, dispatcher=tasks.append)
    metadata = []
    primary = []
    conn.events.subscribe_metadata_resolved(metadata.append)
    conn.events.subscribe_primary_changed(lambda old, new: primary.append((old, new)))
    assert conn._open_port_headers == {}
    assert len(tasks) == 1
    tasks.pop(0)()
    assert primary == [(None, None)]

    port = Port(19723)
    conn._attach_header(port, ConnHeader(port, initialize=False, ui_mode=True))
    header = conn._open_port_headers[port]
    header.init_future.result(timeout=3)
    tasks.pop(0)()
    assert metadata == [header]
    assert header.status is Status.READY

    monkeypatch.setattr(ConnHeader, "get_product_info", lambda self, timeout: (_ for _ in ()).throw(RuntimeError("fetch")))
    header.refresh_metadata()
    header.init_future.result(timeout=3)
    tasks.pop(0)()
    assert metadata == [header, header]
    assert header.status is Status.FAILED

    conn.primary = port
    tasks.pop(0)()
    assert primary[-1] == (None, header)
    conn.close_if_open(port)
    tasks.pop(0)()
    assert primary[-1] == (header, None)


def test_registration_racing_completion_receives_result_once():
    for _ in range(30):
        tasks = []
        header = ConnHeader(Port(19723), initialize=False)
        events = _events_for({header.port: header}, tasks.append)
        token = _start_fetch(header)
        rendezvous = Barrier(2)
        seen = []

        def register():
            rendezvous.wait()
            events.subscribe_metadata_resolved(seen.append)

        def resolve():
            rendezvous.wait()
            _complete_fetch(header, token)
            events._resolved(header, token)

        threads = [Thread(target=register), Thread(target=resolve)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
            assert not thread.is_alive()
        for task in tasks:
            task()
        assert seen == [header]


@pytest.mark.parametrize("drain_replay_before_publication", [False, True])
def test_replay_between_metadata_commit_and_publication_receives_result_once(monkeypatch, drain_replay_before_publication):
    entered, release = Event(), Event()
    monkeypatch.setattr(ConnHeader, "get_product_info", lambda self, timeout: ProductInfo(version=27, buildNumber=1, languageCode="INT"))
    monkeypatch.setattr(ConnHeader, "get_archicad_id", lambda self, timeout: APIResponseError(message="no project"))
    monkeypatch.setattr(ConnHeader, "get_archicad_location", lambda self, timeout: APIResponseError(message="unknown"))
    monkeypatch.setattr(ConnHeader, "get_tapir_info", lambda self, timeout: APIResponseError(message="missing"))
    monkeypatch.setattr("multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss", lambda self: None)

    tasks = []
    conn = MultiConn(ui_mode=True, dispatcher=tasks.append)
    publish = conn.events._resolved

    def delayed_publication(header, token):
        entered.set()
        assert release.wait(timeout=3)
        publish(header, token)

    monkeypatch.setattr(conn.events, "_resolved", delayed_publication)
    early, late = [], []
    conn.events.subscribe_metadata_resolved(early.append)
    port = Port(19723)
    conn.create_or_refresh_connection(port)
    header = conn._open_port_headers[port]
    try:
        assert entered.wait(timeout=3)
        assert not header.init_future.done()
        # Metadata has committed, but the worker has not published its event.
        conn.events.subscribe_metadata_resolved(late.append)
        assert len(tasks) == 1
        if drain_replay_before_publication:
            tasks.pop(0)()
            assert late == [header]
    finally:
        release.set()
    header.init_future.result(timeout=3)
    for task in tasks:
        task()
    tasks.clear()
    assert early == [header]
    assert late == [header]
    publish(header, header._resolved_fetch_token())
    assert tasks == []


def test_queued_completion_is_suppressed_by_header_replacement():
    tasks = []
    port = Port(19723)
    original = ConnHeader(port, initialize=False)
    replacement = ConnHeader(port, initialize=False)
    headers = {port: original}
    events = _events_for(headers, tasks.append)
    seen = []
    events.subscribe_metadata_resolved(seen.append)
    old_token = _complete_fetch(original)
    events._resolved(original, old_token)
    headers[port] = replacement
    events._resolved(original, old_token)
    new_token = _complete_fetch(replacement)
    events._resolved(replacement, new_token)

    assert len(tasks) == 1
    tasks.pop(0)()
    assert seen == [replacement]


def test_reentrant_primary_callback_can_remove_replacement(monkeypatch):
    refreshed = []
    monkeypatch.setattr(ConnHeader, "refresh_metadata", lambda self: refreshed.append(self))
    conn = MultiConn()
    port = Port(19723)
    first = ConnHeader(port, initialize=False)
    conn._attach_header(port, first)
    conn._commit_primary(first)
    replacement = ConnHeader(port, initialize=False)
    transitions = []

    def on_primary(previous, current):
        transitions.append((previous, current))
        if current is replacement:
            conn.close_if_open(port)

    conn.events.subscribe_primary_changed(on_primary)
    conn._attach_header(port, replacement)
    assert conn._open_port_headers == {}
    assert conn._primary is None
    assert refreshed == [first, replacement]
    assert transitions[-2:] == [(first, replacement), (replacement, None)]


def test_primary_changes_keep_event_state_canonical_on_calling_thread(monkeypatch):
    monkeypatch.setattr(ConnHeader, "refresh_metadata", lambda self: None)
    conn = MultiConn(dispatcher=lambda task: task())
    first = ConnHeader(Port(19723), initialize=False)
    second = ConnHeader(Port(19724), initialize=False)
    conn._attach_header(first.port, first)
    conn._attach_header(second.port, second)
    selections = []

    def selected(previous, current):
        assert current is conn._primary
        selections.append((previous, current))

    conn.events.subscribe_primary_changed(selected)
    conn.primary = first.port
    conn.primary = second.port
    conn.primary = second.port
    conn.close_if_open(second.port)

    assert selections == [(None, None), (None, first), (first, second), (second, None)]


def test_removal_returns_header_and_finishes_cleanup_before_primary_callback(monkeypatch):
    monkeypatch.setattr(ConnHeader, "refresh_metadata", lambda self: None)
    conn = MultiConn()
    port = Port(19723)
    header = ConnHeader(port, initialize=False)
    conn._attach_header(port, header)
    conn._commit_primary(header)
    conn._active_ports.add(port)
    transitions = []

    def on_primary(previous, current):
        if previous is header and current is None:
            assert port not in conn._open_port_headers
            assert port not in conn._active_ports
            assert header._is_cancelled
            assert conn._primary is None
        transitions.append((previous, current))

    conn.events.subscribe_primary_changed(on_primary)
    removed = conn.close_if_open(port)

    assert removed is header
    assert removed.port == port
    assert transitions == [(None, header), (header, None)]
    assert conn.close_if_open(port) is None
    assert len(transitions) == 2


def test_refresh_supersedes_slow_completion_without_overwriting_new_metadata(monkeypatch):
    entered, release = Event(), Event()
    calls = [0]

    def product_info(self, timeout):
        calls[0] += 1
        if calls[0] == 1:
            entered.set()
            assert release.wait(timeout=3)
            return ProductInfo(version=26, buildNumber=1, languageCode="INT")
        return ProductInfo(version=28, buildNumber=2, languageCode="INT")

    monkeypatch.setattr(ConnHeader, "get_product_info", product_info)
    monkeypatch.setattr(ConnHeader, "get_archicad_id", lambda self, timeout: APIResponseError(message="no project"))
    monkeypatch.setattr(ConnHeader, "get_archicad_location", lambda self, timeout: APIResponseError(message="unknown"))
    monkeypatch.setattr(ConnHeader, "get_tapir_info", lambda self, timeout: APIResponseError(message="missing"))
    monkeypatch.setattr("multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss", lambda self: None)

    conn = MultiConn(ui_mode=True)
    seen = []
    conn.events.subscribe_metadata_resolved(seen.append)
    port = Port(19723)
    header = ConnHeader(port, initialize=False)
    conn._attach_header(port, header)
    assert entered.wait(timeout=3)
    old_future = header.init_future
    try:
        header.refresh_metadata()
        header.init_future.result(timeout=3)
    finally:
        release.set()
    old_future.result(timeout=3)
    assert header.status is Status.READY
    assert header.product_info.version == 28
    assert seen == [header]


def test_unassign_discards_failure_from_cancelled_fetch(monkeypatch):
    entered, release = Event(), Event()

    def failing_product_info(self, timeout):
        entered.set()
        assert release.wait(timeout=3)
        raise RuntimeError("Archicad closed while fetching metadata")

    monkeypatch.setattr(ConnHeader, "get_product_info", failing_product_info)
    monkeypatch.setattr("multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss", lambda self: None)
    header = ConnHeader(Port(19723), ui_mode=True)
    future = header.init_future
    try:
        assert entered.wait(timeout=3)
        header.unassign()
    finally:
        release.set()

    assert future.result(timeout=3) is None
    assert header.status is Status.UNASSIGNED
    assert header.port is None


def test_ui_owner_keeps_default_mode_replacement_nonblocking(monkeypatch):
    entered, release = Event(), Event()

    def product_info(self, timeout):
        entered.set()
        assert release.wait(timeout=3)
        return ProductInfo(version=27, buildNumber=1, languageCode="INT")

    monkeypatch.setattr(ConnHeader, "get_product_info", product_info)
    monkeypatch.setattr(ConnHeader, "get_archicad_id", lambda self, timeout: APIResponseError(message="no project"))
    monkeypatch.setattr(ConnHeader, "get_archicad_location", lambda self, timeout: APIResponseError(message="unknown"))
    monkeypatch.setattr(ConnHeader, "get_tapir_info", lambda self, timeout: APIResponseError(message="missing"))
    monkeypatch.setattr("multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss", lambda self: None)

    conn = MultiConn(ui_mode=True)
    port = Port(19723)
    header = ConnHeader(port, initialize=False)  # Defaults to blocking standalone behavior.
    conn._attach_header(port, header)
    assert entered.wait(timeout=3)
    try:
        observed = []
        reader = Thread(target=lambda: observed.append(header.product_info))
        reader.start()
        reader.join(timeout=0.3)
        assert not reader.is_alive()
        assert isinstance(observed[0], PendingResponse)
    finally:
        release.set()
    header.init_future.result(timeout=3)
