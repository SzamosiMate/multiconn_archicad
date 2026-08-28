import time
from unittest.mock import patch, MagicMock

from multiconn_archicad.basic_types import Port, ProductInfo, SoloProjectID, ArchicadLocation
from multiconn_archicad.conn_header import ConnHeader
from multiconn_archicad.utilities.ram_monitor import AtomicPeak, RamMonitor


def test_atomic_peak_logic():
    """Verifies that AtomicPeak only updates when a strictly larger value is supplied."""
    peak = AtomicPeak(100)
    assert peak.get() == 100

    peak.update_if_greater(50)
    assert peak.get() == 100

    peak.update_if_greater(200)
    assert peak.get() == 200

    peak.set(300)
    assert peak.get() == 300


def test_peak_bytes_lazy_self_healing_query():
    """
    Verifies that accessing peak_bytes on an unpolled header lazily samples
    the live RSS once and caches it as the initial peak.
    """
    port = Port(19723)
    monitor = RamMonitor(port_getter=lambda: port)

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port", return_value=12345):
        with patch("multiconn_archicad.utilities.ram_monitor.get_process_rss_bytes", return_value=2_147_483_648) as mock_rss:
            # 1. Initially _peak is None, so peak_bytes lazily triggers get_current_rss()
            assert monitor.peak_bytes == 2_147_483_648
            mock_rss.assert_called_once_with(12345)

            # 2. Subsequent reads must use the cached peak without re-querying
            mock_rss.reset_mock()
            assert monitor.peak_bytes == 2_147_483_648
            mock_rss.assert_not_called()


def test_unassigned_header_peak_is_none_not_zero():
    """
    Locks the contract that unassigned/unmeasured headers return None, NOT 0,
    preventing orchestrator OOM scheduling bugs.
    """
    header = ConnHeader(initialize=False)

    assert header.port is None
    assert header.peak_archicad_ram_bytes is None
    assert header.peak_archicad_ram_bytes != 0
    assert header.ram_monitor.current_bytes is None


def test_fetch_worker_auto_seeds_peak_ram_in_background():
    """
    Verifies that ConnHeader._fetch_worker automatically records the initial
    process RSS in the background without requiring manual polling calls.
    """
    header = ConnHeader(port=Port(19723), initialize=False)

    # Mock API fetch calls
    header.get_product_info = MagicMock(return_value=ProductInfo(version=27, buildNumber=3001, languageCode="INT"))
    header.get_archicad_id = MagicMock(return_value=SoloProjectID(projectPath="/path.pln", projectName="Test"))
    header.get_archicad_location = MagicMock(return_value=ArchicadLocation(archicadLocation="/app"))
    header.get_tapir_info = MagicMock()

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port", return_value=12345):
        with patch("multiconn_archicad.utilities.ram_monitor.get_process_rss_bytes", return_value=3_221_225_472):
            # Run fetch worker
            token = object()
            header._fetch_token = token
            header._fetch_worker(token)

            # Assert peak RAM is now auto-seeded
            assert header.peak_archicad_ram_bytes == 3_221_225_472


def test_to_dict_serialization_with_auto_seeded_peak_ram():
    """
    Verifies that to_dict() serializes peakArchicadRamBytes accurately
    when seeded by live process queries.
    """
    header = ConnHeader(port=Port(19723), initialize=False)
    header._product_info = ProductInfo(version=27, buildNumber=3001, languageCode="INT")
    header._archicad_id = SoloProjectID(projectPath="/path/project.pln", projectName="TestProject")
    header._archicad_location = ArchicadLocation(archicadLocation="/path/to/Archicad")

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port", return_value=12345):
        with patch("multiconn_archicad.utilities.ram_monitor.get_process_rss_bytes", return_value=4_294_967_296):
            # to_dict calls peak_archicad_ram_bytes, which lazily samples 4GB
            data = header.to_dict()

            assert data["peakArchicadRamBytes"] == 4_294_967_296
            assert data["archicadId"]["projectName"] == "TestProject"


def test_from_dict_restores_historical_peak_without_process_query():
    """
    Verifies that from_dict restores saved peakArchicadRamBytes without attempting
    to query defunct PIDs or live processes.
    """
    snapshot = {
        "productInfo": {"version": 27, "buildNumber": 3001, "languageCode": "INT"},
        "archicadId": {"project_type": "solo", "projectPath": "/path/project.pln", "projectName": "Snapshot"},
        "archicadLocation": {"archicadLocation": "/path/to/Archicad"},
        "peakArchicadRamBytes": 8_589_934_592,  # 8 GB
    }

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port") as mock_find_pid:
        restored = ConnHeader.from_dict(snapshot)

        assert restored.port is None
        assert restored.peak_archicad_ram_bytes == 8_589_934_592
        # Must not attempt to inspect live OS connections
        mock_find_pid.assert_not_called()


def test_unassign_preserves_peak_ram_and_clears_transport():
    """
    Verifies that unassigning a header clears active port handles and stops polling,
    but strictly preserves historic peak_archicad_ram_bytes.
    """
    header = ConnHeader(port=Port(19723), initialize=False)
    header.peak_archicad_ram_bytes = 1_073_741_824  # 1 GB

    header.unassign()

    assert header.port is None
    assert header.status.value == "unassigned"
    # Preserved profile data
    assert header.peak_archicad_ram_bytes == 1_073_741_824
    # Live RSS is None because no process/port is attached
    assert header.ram_monitor.current_bytes is None


def test_track_context_manager_records_highest_spike():
    """
    Verifies that the track() context manager polls in the background and
    captures the highest observed peak during an operation.
    """
    port = Port(19723)
    monitor = RamMonitor(port_getter=lambda: port)

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port", return_value=12345):
        with patch(
            "multiconn_archicad.utilities.ram_monitor.get_process_rss_bytes",
            side_effect=[1_000_000, 3_000_000, 7_000_000, 4_000_000],
        ):
            with monitor.track(interval_s=0.02):
                assert monitor.is_polling
                time.sleep(0.08)

            assert not monitor.is_polling
            assert monitor.peak_bytes == 7_000_000