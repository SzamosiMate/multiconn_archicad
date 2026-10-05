from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, get_ident
from types import SimpleNamespace

import pytest

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.orchestration.basic_types import APIResponseError, ProductInfo
from multiconn_archicad.orchestration.conn_header import ConnHeader, Status


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def ignore_cli_connection_options(monkeypatch):
    monkeypatch.setattr(
        "multiconn_archicad.orchestration.multi_conn.get_cli_args_once",
        lambda: SimpleNamespace(host=None, port=None),
    )


def test_parallel_scan_applies_changes_and_notifications_on_calling_thread(monkeypatch):
    ports = [Port(19723), Port(19724), Port(19725)]
    caller = get_ident()
    rendezvous = Barrier(len(ports))
    probes = []
    refreshes = []
    monkeypatch.setattr(MultiConn, "_port_range", ports)
    monkeypatch.setattr(ConnHeader, "refresh_metadata", lambda header: refreshes.append((header.port, get_ident())))

    conn = MultiConn(ui_mode=True)
    conn.create_or_refresh_connection(ports[0])
    conn.create_or_refresh_connection(ports[2])
    existing = conn._open_port_headers[ports[0]]
    closed = conn._open_port_headers[ports[2]]
    conn.primary = ports[2]
    refreshes.clear()
    notifications = []
    conn.events.subscribe_primary_changed(
        lambda previous, current: notifications.append((previous, current, get_ident()))
    )
    notifications.clear()

    def probe(host, port):
        probes.append((port, get_ident()))
        rendezvous.wait(timeout=5)
        return port != ports[2]

    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", probe)
    with ThreadPoolExecutor(max_workers=len(ports)) as executor:
        monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.EXECUTOR", executor)
        conn.refresh.all_ports()

    assert {port for port, _ in probes} == set(ports)
    assert all(thread != caller for _, thread in probes)
    assert refreshes == [(ports[0], caller), (ports[1], caller)]
    assert set(conn.open_port_headers) == set(ports[:2])
    assert conn.open_port_headers[ports[0]] is existing
    assert conn._primary is existing
    assert notifications == [(closed, None, caller), (None, existing, caller)]


@pytest.mark.parametrize("method", ["all_ports", "from_ports"])
def test_refresh_eagerly_selects_primary_while_metadata_is_pending(monkeypatch, method):
    ports = [Port(19725), Port(19723), Port(19724)]
    listening = ports[:2]
    entered, release = Event(), Event()
    probes = []
    monkeypatch.setattr(MultiConn, "_port_range", ports)

    def probe(host, port):
        probes.append(port)
        return port in listening

    def product_info(self, timeout):
        entered.set()
        assert release.wait(timeout=3)
        return ProductInfo(version=27, buildNumber=1, languageCode="INT")

    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", probe)
    monkeypatch.setattr(ConnHeader, "get_product_info", product_info)
    monkeypatch.setattr(ConnHeader, "get_archicad_id", lambda self, timeout: APIResponseError(message="no project"))
    monkeypatch.setattr(ConnHeader, "get_archicad_location", lambda self, timeout: APIResponseError(message="unknown"))
    monkeypatch.setattr(ConnHeader, "get_tapir_info", lambda self, timeout: APIResponseError(message="missing"))
    monkeypatch.setattr(
        "multiconn_archicad.orchestration.system.ram_monitor.RamMonitor.get_current_rss", lambda self: None
    )
    conn = MultiConn(ui_mode=True)
    selections = []
    conn.events.subscribe_primary_changed(lambda previous, current: selections.append((previous, current)))
    try:
        if method == "all_ports":
            conn.refresh.all_ports()
        else:
            conn.refresh.from_ports(*listening)
        assert entered.wait(timeout=3)
        selected = conn._open_port_headers[min(listening)]
        assert conn._primary is selected  # Selection happened without reading conn.primary.
        assert selected.status is Status.PENDING
        assert selections == [(None, None), (None, selected)]
        assert sorted(probes) == sorted(ports if method == "all_ports" else listening)
    finally:
        release.set()
        for header in conn._open_port_headers.values():
            header._fetch_task[1].result(timeout=3)


def test_refresh_preserves_existing_primary_without_redundant_selection_events(monkeypatch):
    ports = [Port(19723), Port(19724)]
    monkeypatch.setattr(MultiConn, "_port_range", ports)
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", lambda host, port: True)
    monkeypatch.setattr(ConnHeader, "refresh_metadata", lambda self: None)
    conn = MultiConn()
    conn.refresh.all_ports()
    conn.primary = ports[1]
    selected = conn._primary
    selections = []
    conn.events.subscribe_primary_changed(lambda previous, current: selections.append((previous, current)))
    selections.clear()

    conn.refresh.all_ports()

    assert conn._primary is selected
    assert selections == []


def test_refresh_without_connections_keeps_primary_none(monkeypatch):
    monkeypatch.setattr(MultiConn, "_port_range", [Port(19723)])
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", lambda host, port: False)
    conn = MultiConn()
    selections = []
    conn.events.subscribe_primary_changed(lambda previous, current: selections.append((previous, current)))
    conn.refresh.all_ports()

    assert conn._primary is None
    assert selections == [(None, None)]


def test_closed_explicit_port_is_unavailable_in_ui_mode_but_still_errors_in_cli_mode(monkeypatch):
    port = Port(19723)
    monkeypatch.setattr(MultiConn, "_port_range", [port])
    monkeypatch.setattr("multiconn_archicad.orchestration.multi_conn.is_port_listening", lambda host, port: False)
    conn = MultiConn(port=port, ui_mode=True)
    assert conn.primary is None
    with pytest.raises(KeyError):
        MultiConn(port=port)
