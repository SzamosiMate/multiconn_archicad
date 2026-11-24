"""Run deep schema tests in isolated processes and verify complete partition coverage."""

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

DEFAULT_PATHS = ["tests/generated", "tests/code_generation"]


def verify_manifests(manifests: list[dict]) -> dict:
    """Reject collection drift, duplicate/missing execution and incomplete workers."""
    collection = manifests[0]["collection"]
    if not collection or len(set(collection)) != len(collection):
        raise ValueError("Collection is empty or contains duplicate node IDs")
    outcomes = Counter()
    for index, manifest in enumerate(manifests):
        if manifest["collection"] != collection:
            raise ValueError(f"Worker {index}: collection differs between processes")
        expected = collection[index :: len(manifests)]
        if manifest["selected"] != expected:
            raise ValueError(f"Worker {index}: incorrect partition")
        reports = manifest["reports"]
        if set(reports) != set(expected):
            raise ValueError(f"Worker {index}: missing or unexpected test reports")
        for node, phases in reports.items():
            if "teardown" not in phases:
                raise ValueError(f"Worker {index}: incomplete test {node}")
            results = [report["outcome"] for report in phases.values()]
            if "failed" in results:
                outcomes["failed"] += 1
            elif "skipped" in results:
                outcomes["skipped"] += 1
            elif phases.get("call", {}).get("outcome") == "passed":
                outcomes["passed"] += 1
            else:
                raise ValueError(f"Worker {index}: missing call result for {node}")
        allowed = (0, 1) if expected else (0, 5)
        if manifest["exit_code"] not in allowed:
            raise ValueError(f"Worker {index}: pytest exited {manifest['exit_code']}")
        if manifest["exit_code"] == 1 and not any(
            report["outcome"] == "failed" for phases in reports.values() for report in phases.values()
        ):
            raise ValueError(f"Worker {index}: pytest failed outside the recorded tests")
    return {
        "collected": len(collection),
        "outcomes": dict(outcomes),
        "collection_counts": dict(Counter(node.split("[", 1)[0] for node in collection)),
        "coverage_verified": True,
    }


def run_worker(index: int, count: int, directory: Path, pytest_args: list[str]) -> int:
    import pytest

    manifest = {"collection": [], "selected": [], "reports": {}}
    with (directory / f"worker-{index}.events").open("w", encoding="utf-8") as events:

        class Partition:
            @pytest.hookimpl(wrapper=True)
            def pytest_collection_modifyitems(self, config, items):
                # Partition after conftest and other selection hooks have run.
                yield
                if config.getoption("schema_tests") != "deep":
                    raise pytest.UsageError("The parallel runner requires --schema-tests=deep")
                if config.option.collectonly:
                    raise pytest.UsageError("Use pytest directly for --collect-only")
                manifest["collection"] = [item.nodeid for item in items]
                selected = items[index::count]
                manifest["selected"] = [item.nodeid for item in selected]
                rejected = [item for position, item in enumerate(items) if position % count != index]
                items[:] = selected
                config.hook.pytest_deselected(items=rejected)

            def pytest_runtest_logreport(self, report):
                manifest["reports"].setdefault(report.nodeid, {})[report.when] = {
                    "outcome": report.outcome,
                    "duration": report.duration,
                }
                if report.failed:
                    events.write(json.dumps({"node": report.nodeid, "phase": report.when}) + "\n")
                    events.flush()

        started = time.monotonic()
        code = int(
            pytest.main(
                ["--schema-tests=deep", "-q", "--tb=short", "--durations=10", *pytest_args], plugins=[Partition()]
            )
        )
        manifest.update(exit_code=code, seconds=round(time.monotonic() - started, 2))
        (directory / f"worker-{index}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # pytest returns NO_TESTS_COLLECTED for a valid empty partition.
        return 0 if code == 5 and manifest["collection"] and not manifest["selected"] else code


def run_parallel(workers: int, directory: Path, pytest_args: list[str]) -> int:
    print(f"Running {workers} deep-test workers. Logs: {directory}", flush=True)
    processes = []
    seen_events = [0] * workers
    finished = set()
    started = time.monotonic()
    with ExitStack() as stack:
        try:
            for index in range(workers):
                log = stack.enter_context((directory / f"worker-{index}.log").open("w", encoding="utf-8"))
                processes.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-u",
                            "-m",
                            "code_generation.run_deep_tests",
                            "--worker",
                            str(index),
                            "--workers",
                            str(workers),
                            "--log-dir",
                            str(directory),
                            "--",
                            *pytest_args,
                        ],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                )
            while len(finished) != workers:
                for index, process in enumerate(processes):
                    event_file = directory / f"worker-{index}.events"
                    if event_file.exists():
                        lines = event_file.read_text(encoding="utf-8").splitlines(keepends=True)
                        for line in lines[seen_events[index] :]:
                            if not line.endswith("\n"):
                                break
                            event = json.loads(line)
                            print(
                                f"FAILED worker {index}: {event['node']} ({event['phase']}); see worker-{index}.log",
                                flush=True,
                            )
                            seen_events[index] += 1
                    if index not in finished and process.poll() is not None:
                        finished.add(index)
                        print(f"Worker {index} finished, exit {process.returncode}", flush=True)
                if len(finished) != workers:
                    time.sleep(0.2)
        finally:
            # Stop only children created by this invocation, including on Ctrl+C.
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    try:
        manifests = [
            json.loads((directory / f"worker-{index}.json").read_text(encoding="utf-8")) for index in range(workers)
        ]
        summary = verify_manifests(manifests)
        # An abnormal process exit must not be hidden by a previously written manifest.
        if any(
            process.returncode != (0 if m["exit_code"] == 5 else m["exit_code"])
            for process, m in zip(processes, manifests)
        ):
            raise ValueError("Worker process exit disagrees with its manifest")
    except (OSError, ValueError, KeyError) as error:
        print(f"Deep-test coverage NOT verified: {error}. Inspect {directory}", flush=True)
        return 1
    summary["seconds"] = round(time.monotonic() - started, 2)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    counts = ", ".join(f"{count} {outcome}" for outcome, count in sorted(summary["outcomes"].items()))
    print(f"Coverage verified: {summary['collected']} unique tests; {counts}; {summary['seconds']}s", flush=True)
    return int(bool(summary["outcomes"].get("failed")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(4, max(1, (os.cpu_count() or 2) // 2)))
    parser.add_argument(
        "--log-dir", type=Path, help="Empty directory for logs and coverage manifests; default: new temp dir"
    )
    parser.add_argument("--worker", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "pytest_args", nargs=argparse.REMAINDER, help="Paths/options after --; defaults to generated + codegen"
    )
    args = parser.parse_args()
    if args.workers < 1 or (args.worker is not None and not 0 <= args.worker < args.workers):
        parser.error("workers must be positive and worker index must be within range")
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    if not pytest_args:
        pytest_args = DEFAULT_PATHS
    elif pytest_args[0].startswith("-"):
        parser.error("After --, start with a test path, then any pytest options")
    if args.worker is not None:
        if args.log_dir is None:
            parser.error("internal worker requires --log-dir")
        return run_worker(args.worker, args.workers, args.log_dir, pytest_args)
    directory = args.log_dir.resolve() if args.log_dir else Path(tempfile.mkdtemp(prefix="multiconn-deep-"))
    if directory.exists() and any(directory.iterdir()):
        parser.error(f"log directory must be empty: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    try:
        return run_parallel(args.workers, directory, pytest_args)
    except KeyboardInterrupt:
        print(f"Interrupted; coverage was not verified. Logs: {directory}", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
