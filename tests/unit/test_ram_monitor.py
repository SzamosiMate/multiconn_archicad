import time
from unittest.mock import patch
from multiconn_archicad.basic_types import Port, ProductInfo, SoloProjectID, ArchicadLocation
from multiconn_archicad.conn_header import ConnHeader
from multiconn_archicad.utilities.ram_monitor import AtomicPeak, RamMonitor


def test_atomic_peak():
    peak = AtomicPeak(100)
    assert peak.get() == 100

    peak.update_if_greater(50)
    assert peak.get() == 100

    peak.update_if_greater(200)
    assert peak.get() == 200

    peak.set(300)
    assert peak.get() == 300


def test_ram_monitor_live_query():
    port = Port(19723)
    monitor = RamMonitor(port_getter=lambda: port)

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port", return_value=12345):
        with patch("multiconn_archicad.utilities.ram_monitor.get_process_rss_bytes", side_effect=[1000, 2500, 1500]):
            assert monitor.current_bytes == 1000
            assert monitor.peak_bytes == 1000

            assert monitor.current_bytes == 2500
            assert monitor.peak_bytes == 2500

            assert monitor.current_bytes == 1500
            assert monitor.peak_bytes == 2500  # Peak stays at 2500


def test_ram_monitor_track_context_manager():
    port = Port(19723)
    monitor = RamMonitor(port_getter=lambda: port)

    with patch("multiconn_archicad.utilities.ram_monitor.find_pid_by_port", return_value=12345):
        with patch("multiconn_archicad.utilities.ram_monitor.get_process_rss_bytes", side_effect=[500, 1500, 3000, 2000]):
            with monitor.track_peak_ram(interval_s=0.05):
                assert monitor.is_polling
                time.sleep(0.15)

            assert not monitor.is_polling
            assert monitor.peak_bytes == 3000


def test_header_serialization_with_peak_ram():
    header = ConnHeader(initialize=False)
    header._product_info = ProductInfo(version=27, buildNumber=3001, languageCode="INT")
    header._archicad_id = SoloProjectID(projectPath="/path/to/project.pln", projectName="TestProject")
    header._archicad_location = ArchicadLocation(archicadLocation="/path/to/Archicad")
    header.peak_archicad_ram_bytes = 4_294_967_296  # 4 GB

    serialized = header.to_dict()
    assert serialized["peakArchicadRamBytes"] == 4_294_967_296

    restored = ConnHeader.from_dict(serialized)
    assert restored.peak_archicad_ram_bytes == 4_294_967_296
    assert restored.product_info.version == 27
    assert restored.archicad_id.projectName == "TestProject"


def test_header_unassign_preserves_peak_ram():
    header = ConnHeader(port=Port(19723), initialize=False)
    header.peak_archicad_ram_bytes = 1024

    header.unassign()
    assert header.port is None
    assert header.peak_archicad_ram_bytes == 1024
    assert header.ram_monitor.current_bytes is None