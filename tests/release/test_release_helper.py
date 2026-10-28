"""Preparation must preserve version consistency and generated contribution credits."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "release_helper", Path(__file__).resolve().parents[2] / "scripts/release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleasePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(release, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        (self.root / "pyproject.toml").write_text(
            '[project]\nversion="1.2.3"\n[project.urls]\nHomepage="https://github.com/owner/repo"\n', encoding="utf-8"
        )
        (self.root / "uv.lock").write_text("original lock", encoding="utf-8")

    def test_failed_lock_restores_package_and_lock(self):
        original = {p: p.read_bytes() for p in self.root.iterdir()}

        def failed_bump(*args, **kwargs):
            if args[:2] == ("uv", "version"):
                path = self.root / "pyproject.toml"
                path.write_text(path.read_text().replace("1.2.3", "1.2.4"), encoding="utf-8")
            elif args[:2] == ("uv", "lock"):
                self.assertEqual(release.project()["version"], "1.2.4")
                (self.root / "uv.lock").write_text("partial lock", encoding="utf-8")
                raise subprocess.CalledProcessError(1, args)

        with patch.object(release, "run", side_effect=failed_bump), self.assertRaises(subprocess.CalledProcessError):
            release.bump("1.2.4")
        self.assertEqual({p: p.read_bytes() for p in self.root.iterdir()}, original)

    def test_wrong_release_tag_stops_before_commands(self):
        with patch.object(release, "run") as commands:
            with self.assertRaises(ValueError):
                release.check("v1.2.2")
        commands.assert_not_called()

    def test_draft_uses_generated_credits_and_targets_reviewed_commit(self):
        summary = self.root / "summary.md"
        summary.write_text("A descriptive summary.", encoding="utf-8")
        created = []

        def fake_run(*args, **kwargs):
            if args[:3] == ("git", "status", "--porcelain"):
                return ""
            if args[:3] == ("git", "rev-parse", "HEAD") or "/commits/" in " ".join(map(str, args)):
                return "a" * 40
            if "matching-refs" in " ".join(map(str, args)):
                return "[]"
            if args[:3] == ("gh", "release", "create"):
                created.append(args)
                body = Path(args[args.index("--notes-file") + 1]).read_text(encoding="utf-8")
                self.assertEqual(body, "A descriptive summary.")
            return ""

        with patch.object(release, "run", side_effect=fake_run):
            release.draft("v1.2.2", summary)
        self.assertEqual(len(created), 1)
        self.assertIn("--draft", created[0])
        self.assertIn("--generate-notes", created[0])
        self.assertEqual(created[0][created[0].index("--notes-start-tag") + 1], "v1.2.2")
        self.assertEqual(created[0][created[0].index("--target") + 1], "a" * 40)


if __name__ == "__main__":
    unittest.main()
