from dataclasses import replace
from threading import Event, Thread

import pytest

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.orchestration.basic_types import APIResponseError, PendingResponse, ProductInfo
from multiconn_archicad.orchestration.conn_header import ConnHeader, HeaderMetadata, Status
from multiconn_archicad.orchestration.events import ConnectionEvents


@pytest.fixture
def metadata_api(monkeypatch):
    """Successful product info with unavailable optional metadata."""
    error = APIResponseError(message="unavailable")
    metadata = HeaderMetadata(
        ProductInfo(version=27, buildNumber=1, languageCode="INT"),
        error, error, error,
    )
    for field in ("product_info", "archicad_id", "archicad_location", "tapir_info"):
        monkeypatch.setattr(
            ConnHeader, f"get_{field}",
            lambda self, timeout, result=getattr(metadata, field): result,
        )
    monkeypatch.setattr(
        "multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss",
        lambda self: None,
    )


def _events_for(headers, dispatcher=None):
    return ConnectionEvents(dispatcher, get_primary=lambda: None, get_headers=headers.copy)


def _complete_fetch(header, token=None):
    token = token if token is not None else header._state.begin_fetch()
    metadata = replace(
        header._state.snapshot().metadata,
        product_info=ProductInfo(version=27, buildNumber=1, languageCode="INT"),
    )
    header._state.complete(token, metadata)
    return token


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

    events._resolved(second, second_token)  # Already delivered through replay.
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
    header._state.begin_fetch()
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


def test_primary_replay_and_changes_are_delivered_in_order():
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
    calls.clear()
    header = ConnHeader(initialize=False)
    events._primary_changed(None, header)
    assert calls == [header]
    assert "callback failed" in caplog.text


def test_multiconn_registration_does_not_scan_and_fetch_reports_success_and_failure(monkeypatch, metadata_api):
    def unexpected_scan(*args):
        raise AssertionError("registration triggered discovery")

    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", unexpected_scan)

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
    header._fetch_task[1].result(timeout=3)
    tasks.pop(0)()
    assert metadata == [header]
    assert header.status is Status.READY

    monkeypatch.setattr(ConnHeader, "get_product_info", lambda self, timeout: (_ for _ in ()).throw(RuntimeError("fetch")))
    header.refresh_metadata()
    header._fetch_task[1].result(timeout=3)
    tasks.pop(0)()
    assert metadata == [header, header]
    assert header.status is Status.FAILED

    conn.primary = port
    tasks.pop(0)()
    assert primary[-1] == (None, header)
    conn.close_if_open(port)
    tasks.pop(0)()
    assert primary[-1] == (header, None)


@pytest.mark.parametrize("drain_replay_before_publication", [False, True])
def test_replay_between_metadata_commit_and_publication_receives_result_once(monkeypatch, metadata_api, drain_replay_before_publication):
    entered, release = Event(), Event()

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
        # Metadata has committed, but the worker has not published its event.
        conn.events.subscribe_metadata_resolved(late.append)
        if drain_replay_before_publication:
            tasks.pop(0)()
    finally:
        release.set()
    header._fetch_task[1].result(timeout=3)
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


def test_removal_returns_header_and_finishes_cleanup_before_primary_callback(monkeypatch):
    monkeypatch.setattr(ConnHeader, "refresh_metadata", lambda self: None)
    conn = MultiConn()
    port = Port(19723)
    header = ConnHeader(port, initialize=False)
    conn._attach_header(port, header)
    _complete_fetch(header)
    conn._commit_primary(header)
    conn._active_ports.add(port)
    transitions = []

    def on_primary(previous, current):
        if previous is header and current is None:
            assert port not in conn._open_port_headers
            assert port not in conn._active_ports
            assert header._resolved_fetch_token() is None
            assert conn._primary is None
        transitions.append((previous, current))

    conn.events.subscribe_primary_changed(on_primary)
    removed = conn.close_if_open(port)

    assert removed is header
    assert removed.port == port
    assert transitions == [(None, header), (header, None)]
    assert conn.close_if_open(port) is None


def test_refresh_supersedes_slow_completion_without_overwriting_new_metadata(monkeypatch, metadata_api):
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

    conn = MultiConn(ui_mode=True)
    seen = []
    conn.events.subscribe_metadata_resolved(seen.append)
    port = Port(19723)
    header = ConnHeader(port, initialize=False)
    conn._attach_header(port, header)
    assert entered.wait(timeout=3)
    old_future = header._fetch_task[1]
    try:
        header.refresh_metadata()
        header._fetch_task[1].result(timeout=3)
    finally:
        release.set()
    old_future.result(timeout=3)
    assert header.status is Status.READY
    assert header.product_info.version == 28
    assert seen == [header]


def test_unassign_discards_failure_from_cancelled_fetch(monkeypatch, metadata_api):
    entered, release = Event(), Event()

    def failing_product_info(self, timeout):
        entered.set()
        assert release.wait(timeout=3)
        raise RuntimeError("Archicad closed while fetching metadata")

    monkeypatch.setattr(ConnHeader, "get_product_info", failing_product_info)
    header = ConnHeader(Port(19723), ui_mode=True)
    future = header._fetch_task[1]
    try:
        assert entered.wait(timeout=3)
        header.unassign()
    finally:
        release.set()

    future.result(timeout=3)
    assert header.status is Status.UNASSIGNED
    assert header.port is None


def test_ui_owner_keeps_default_mode_replacement_nonblocking(monkeypatch, metadata_api):
    entered, release = Event(), Event()

    def product_info(self, timeout):
        entered.set()
        assert release.wait(timeout=3)
        return ProductInfo(version=27, buildNumber=1, languageCode="INT")

    monkeypatch.setattr(ConnHeader, "get_product_info", product_info)

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
    header._fetch_task[1].result(timeout=3)
