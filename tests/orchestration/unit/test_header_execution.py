from concurrent.futures import Future
from dataclasses import replace
from threading import Thread

import pytest

from multiconn_archicad import MultiConn, Port
from multiconn_archicad.orchestration.basic_types import ProductInfo
from multiconn_archicad.orchestration.conn_header import ConnHeader, Status

pytestmark = pytest.mark.unit


def _install_future(header):
    future = Future()
    header._fetch_task = (header._state.begin_fetch(), future)
    return future


def test_fast_worker_callback_can_read_metadata_before_submit_returns(monkeypatch):
    header = ConnHeader(Port(19723), initialize=False)
    _install_future(header)  # An older request is still waiting.
    metadata = replace(
        header._state.snapshot().metadata,
        product_info=ProductInfo(version=28, buildNumber=4000, languageCode="INT"),
    )
    monkeypatch.setattr(header, "get_product_info", lambda timeout: metadata.product_info)
    monkeypatch.setattr(header, "get_archicad_id", lambda timeout: metadata.archicad_id)
    monkeypatch.setattr(header, "get_archicad_location", lambda timeout: metadata.archicad_location)
    monkeypatch.setattr(header, "get_tapir_info", lambda timeout: metadata.tapir_info)
    monkeypatch.setattr(header.ram_monitor, "get_current_rss", lambda: None)

    def submit_and_finish(worker, token):
        future = Future()

        def run():
            try:
                future.set_result(worker(token))
            except Exception as exc:
                future.set_exception(exc)

        thread = Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=3)
        assert not thread.is_alive(), "A callback waited on its worker or the older fetch"
        return future

    monkeypatch.setattr("multiconn_archicad.orchestration.conn_header.EXECUTOR.submit", submit_and_finish)
    conn = MultiConn()
    seen = []
    conn.events.subscribe_metadata_resolved(lambda current: seen.append((current.status, current.product_info)))
    conn._attach_header(header.port, header)

    header._fetch_task[1].result(timeout=3)
    assert seen == [(Status.READY, metadata.product_info)]


@pytest.mark.parametrize(
    "action, expected",
    [("none", Status.FAILED), ("cancel", Status.PENDING), ("refresh", Status.READY)],
)
def test_unexpected_future_failure_only_changes_its_current_fetch(monkeypatch, action, expected):
    header = ConnHeader(Port(19723), initialize=False)
    future = _install_future(header)
    metadata = replace(
        header._state.snapshot().metadata,
        product_info=ProductInfo(version=28, buildNumber=4000, languageCode="INT"),
    )

    def fail():
        if action == "cancel":
            header.cancel()
        elif action == "refresh":
            header._state.complete(header._state.begin_fetch(), metadata)
        raise RuntimeError("unexpected worker failure")

    monkeypatch.setattr(future, "result", fail)
    assert header.status is expected


def test_old_failed_future_cannot_fail_new_fetch_during_submission(monkeypatch):
    header = ConnHeader(Port(19723), initialize=False, ui_mode=True)
    _install_future(header).set_exception(RuntimeError("older worker failed"))

    def submit(worker, token):
        header._sync_if_needed()
        return Future()

    monkeypatch.setattr("multiconn_archicad.orchestration.conn_header.EXECUTOR.submit", submit)
    header.refresh_metadata()

    assert header.status is Status.PENDING
