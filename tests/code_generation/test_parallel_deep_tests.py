import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from code_generation.run_deep_tests import verify_manifests


def _run_suite(tmp_path, source, workers):
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (suite / "conftest.py").write_text(
        'def pytest_addoption(parser):\n    parser.addoption("--schema-tests", default="routine")\n', encoding="utf-8"
    )
    (suite / "test_example.py").write_text(source, encoding="utf-8")
    logs = tmp_path / "logs"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "code_generation.run_deep_tests",
            "--workers",
            str(workers),
            "--log-dir",
            str(logs),
            "--",
            str(suite),
            "-c",
            str(suite / "pytest.ini"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result, logs


def test_parallel_execution_covers_each_node_and_handles_empty_worker_and_skip(tmp_path):
    result, logs = _run_suite(
        tmp_path,
        """
import pytest
def test_pass():
    pass
@pytest.mark.skip(reason="Intentional coverage check")
def test_skip():
    pass
""",
        workers=3,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((logs / "summary.json").read_text())
    assert summary["coverage_verified"]
    assert summary["collected"] == 2
    assert summary["outcomes"] == {"passed": 1, "skipped": 1}
    manifests = [json.loads(path.read_text()) for path in sorted(logs.glob("worker-*.json"))]
    assert len(manifests) == 3
    assert len({node for manifest in manifests for node in manifest["reports"]}) == 2
    assert sum(len(manifest["reports"]) for manifest in manifests) == 2


def test_call_setup_and_teardown_failures_are_reported_and_fail_the_command(tmp_path):
    result, logs = _run_suite(
        tmp_path,
        """
import pytest
@pytest.fixture
def bad_setup():
    raise RuntimeError("setup failure")
@pytest.fixture
def bad_teardown():
    yield
    raise RuntimeError("teardown failure")
def test_setup(bad_setup):
    pass
def test_teardown(bad_teardown):
    pass
def test_call():
    assert False
""",
        workers=2,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads((logs / "summary.json").read_text())
    assert summary["collected"] == 3
    assert summary["outcomes"] == {"failed": 3}
    for phase in ("setup", "call", "teardown"):
        assert f"({phase})" in result.stdout


def _successful_manifests():
    phases = {phase: {"outcome": "passed", "duration": 0.01} for phase in ("setup", "call", "teardown")}
    return [
        {"collection": ["a", "b"], "selected": [node], "reports": {node: copy.deepcopy(phases)}, "exit_code": 0}
        for node in ("a", "b")
    ]


@pytest.mark.parametrize("corruption", ["collection", "partition", "report", "teardown", "process_exit"])
def test_rejects_incomplete_or_inconsistent_worker_evidence(corruption):
    manifests = _successful_manifests()
    if corruption == "collection":
        manifests[1]["collection"] = ["b", "a"]
    elif corruption == "partition":
        manifests[1]["selected"] = ["a"]
    elif corruption == "report":
        manifests[1]["reports"].clear()
    elif corruption == "teardown":
        del manifests[1]["reports"]["b"]["teardown"]
    else:
        manifests[1]["exit_code"] = 3
    with pytest.raises(ValueError):
        verify_manifests(manifests)
