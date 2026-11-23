"""
Comprehensive automated unittest suite for Smart File Organizer.
Covers config invariants, all sorting modes, conflict resolution, intra-batch
collisions, duplicate detection, recursive scans, undo & nested cleanup,
live watcher behavior, CLI flags, and the standalone script.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from config import FILE_CATEGORIES, EXTENSION_MAP
from organizer import FileOrganizer
from watcher import FolderWatcher, is_file_ready
import file_organizer as standalone_script


class TestConfigInvariants(unittest.TestCase):
    def test_no_duplicate_extensions_across_categories(self):
        seen = {}
        for category, extensions in FILE_CATEGORIES.items():
            for ext in extensions:
                lower = ext.lower()
                self.assertNotIn(
                    lower,
                    seen,
                    f"Extension '{lower}' appears in both '{seen.get(lower)}' and '{category}'",
                )
                seen[lower] = category
                self.assertEqual(EXTENSION_MAP[lower], category)


class TestFileOrganizerCore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="organizer_test_"))
        self.organizer = FileOrganizer(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_files(self, files):
        for rel_path, content in files:
            p = self.temp_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)

    def test_dry_run_makes_no_changes(self):
        self._create_files([("invoice.pdf", b"pdf"), ("photo.jpg", b"jpg")])
        res = self.organizer.execute_organization(mode="category", dry_run=True)
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["moved"], 2)
        self.assertTrue((self.temp_dir / "invoice.pdf").exists())
        self.assertFalse((self.temp_dir / "Documents").exists())

    def test_category_mode_and_deterministic_duplicates(self):
        self._create_files([
            ("invoice.pdf", b"pdf 1"),
            ("report.docx", b"docx 2"),
            ("photo.jpg", b"same image"),
            ("duplicate_photo.jpg", b"same image"),
            ("song.mp3", b"music"),
            ("video.mp4", b"video"),
            ("archive.zip", b"zip"),
            ("installer.exe", b"exe"),
            ("main.py", b"user python file"),  # User's own main.py should be organized outside app dir
            ("unknown.xyz", b"mystery"),
        ])

        res = self.organizer.execute_organization(mode="category", detect_duplicates=True)
        self.assertEqual(res["errors"], 0)
        self.assertEqual(res["moved"], 9)
        self.assertEqual(res["duplicates"], 1)

        self.assertTrue((self.temp_dir / "Documents" / "invoice.pdf").exists())
        self.assertTrue((self.temp_dir / "Documents" / "report.docx").exists())
        # Shorter original filename kept in Pictures, duplicate isolated
        self.assertTrue((self.temp_dir / "Pictures" / "photo.jpg").exists())
        self.assertTrue((self.temp_dir / "Duplicates" / "duplicate_photo.jpg").exists())
        self.assertTrue((self.temp_dir / "Code" / "main.py").exists())
        self.assertTrue((self.temp_dir / "Others" / "unknown.xyz").exists())

        # Newly added duplicate of already-organized file is also caught
        (self.temp_dir / "another_copy.jpg").write_bytes(b"same image")
        res2 = self.organizer.execute_organization(mode="category", detect_duplicates=True)
        self.assertEqual(res2["duplicates"], 1)
        self.assertTrue((self.temp_dir / "Duplicates" / "another_copy.jpg").exists())

    def test_extension_and_category_then_extension_modes(self):
        self._create_files([("a.pdf", b"1"), ("b.JPG", b"2"), ("README", b"3")])

        res_ext = self.organizer.execute_organization(mode="extension")
        self.assertEqual(res_ext["moved"], 3)
        self.assertTrue((self.temp_dir / "PDF" / "a.pdf").exists())
        self.assertTrue((self.temp_dir / "JPG" / "b.JPG").exists())
        self.assertTrue((self.temp_dir / "NO_EXTENSION" / "README").exists())

        restored, errors, _ = self.organizer.undo_last_operation()
        self.assertEqual((restored, errors), (3, 0))
        self.assertFalse((self.temp_dir / "PDF").exists())

        res_nested = self.organizer.execute_organization(mode="category_then_extension")
        self.assertEqual(res_nested["moved"], 3)
        self.assertTrue((self.temp_dir / "Documents" / "PDF" / "a.pdf").exists())
        self.assertTrue((self.temp_dir / "Pictures" / "JPG" / "b.JPG").exists())
        self.assertTrue((self.temp_dir / "Others" / "NO_EXTENSION" / "README").exists())

        # Undo must remove nested empty parent folders (Documents/PDF AND Documents/)
        restored, errors, _ = self.organizer.undo_last_operation()
        self.assertEqual((restored, errors), (3, 0))
        self.assertFalse((self.temp_dir / "Documents").exists())
        self.assertFalse((self.temp_dir / "Pictures").exists())
        self.assertFalse((self.temp_dir / "Others").exists())

    def test_date_mode_and_nested_year_folder_cleanup(self):
        self._create_files([("notes.txt", b"hello")])
        res = self.organizer.execute_organization(mode="date")
        self.assertEqual(res["moved"], 1)

        year_dirs = [p for p in self.temp_dir.iterdir() if p.is_dir()]
        self.assertEqual(len(year_dirs), 1)
        year_dir = year_dirs[0]

        restored, errors, _ = self.organizer.undo_last_operation()
        self.assertEqual((restored, errors), (1, 0))
        self.assertTrue((self.temp_dir / "notes.txt").exists())
        self.assertFalse(year_dir.exists(), "Empty year folder should be cleaned up on undo")

    def test_conflict_resolution_modes(self):
        # Pre-existing destination file
        self._create_files([("Documents/doc.pdf", b"existing"), ("doc.pdf", b"new")])

        # Skip
        res_skip = self.organizer.execute_organization(mode="category", conflict_resolution="skip")
        self.assertEqual(res_skip["skipped"], 1)
        self.assertTrue((self.temp_dir / "doc.pdf").exists())
        self.assertEqual((self.temp_dir / "Documents" / "doc.pdf").read_bytes(), b"existing")

        # Rename
        res_rename = self.organizer.execute_organization(mode="category", conflict_resolution="rename")
        self.assertEqual(res_rename["moved"], 1)
        self.assertEqual((self.temp_dir / "Documents" / "doc.pdf").read_bytes(), b"existing")
        self.assertEqual((self.temp_dir / "Documents" / "doc (1).pdf").read_bytes(), b"new")

        # Overwrite
        (self.temp_dir / "doc.pdf").write_bytes(b"overwrite_payload")
        res_overwrite = self.organizer.execute_organization(mode="category", conflict_resolution="overwrite")
        self.assertEqual(res_overwrite["moved"], 1)
        self.assertEqual((self.temp_dir / "Documents" / "doc.pdf").read_bytes(), b"overwrite_payload")

    def test_recursive_intra_batch_collisions_and_duplicates_quarantine(self):
        self._create_files([
            ("sub1/report.pdf", b"version A"),
            ("sub2/report.pdf", b"version B"),
            ("sub1/dup.jpg", b"same image bytes"),
            ("sub2/dup.jpg", b"same image bytes"),
            ("sub3/dup.jpg", b"same image bytes"),
            (".git/config", b"git internal"),
            ("node_modules/pkg.js", b"ignored js"),
        ])

        skip_plan = self.organizer.plan_organization(mode="category", recursive=True, conflict_resolution="skip")
        report_ops = [op for op in skip_plan if op.src.name == "report.pdf"]
        self.assertEqual(sorted(op.action for op in report_ops), ["moved", "skipped"])

        res = self.organizer.execute_organization(
            mode="category",
            recursive=True,
            conflict_resolution="rename",
            detect_duplicates=True,
        )
        self.assertEqual(res["errors"], 0)
        self.assertEqual(sorted(f.name for f in (self.temp_dir / "Documents").iterdir()), ["report (1).pdf", "report.pdf"])
        self.assertEqual(sorted(f.read_bytes() for f in (self.temp_dir / "Documents").iterdir()), [b"version A", b"version B"])
        self.assertEqual(sorted(f.name for f in (self.temp_dir / "Pictures").iterdir()), ["dup.jpg"])
        self.assertEqual(sorted(f.name for f in (self.temp_dir / "Duplicates").iterdir()), ["dup (1).jpg", "dup.jpg"])
        # Ignored dirs untouched
        self.assertTrue((self.temp_dir / ".git" / "config").exists())
        self.assertTrue((self.temp_dir / "node_modules" / "pkg.js").exists())

        # Running recursive again WITHOUT detect_duplicates must NOT pull files back out of Duplicates/
        res_again = self.organizer.execute_organization(mode="category", recursive=True, detect_duplicates=False)
        self.assertEqual(res_again["moved"], 0)
        self.assertEqual(sorted(f.name for f in (self.temp_dir / "Duplicates").iterdir()), ["dup (1).jpg", "dup.jpg"])

    def test_ignored_hidden_and_partial_downloads(self):
        self._create_files([
            (".hidden.txt", b"secret"),
            ("~$temp.docx", b"office lock"),
            ("movie.mp4.crdownload", b"partial"),
            ("file.part", b"partial"),
            ("desktop.ini", b"sys"),
            ("real.txt", b"ok"),
        ])

        res = self.organizer.execute_organization(mode="category", include_hidden=False)
        self.assertEqual(res["moved"], 1)
        self.assertTrue((self.temp_dir / "Documents" / "real.txt").exists())
        self.assertTrue((self.temp_dir / ".hidden.txt").exists())
        self.assertTrue((self.temp_dir / "~$temp.docx").exists())
        self.assertTrue((self.temp_dir / "movie.mp4.crdownload").exists())
        self.assertTrue((self.temp_dir / "file.part").exists())
        self.assertTrue((self.temp_dir / "desktop.ini").exists())

    def test_undo_preserves_failed_items_and_handles_corrupt_history(self):
        self._create_files([("a.pdf", b"1"), ("b.pdf", b"2")])
        self.organizer.execute_organization(mode="category")

        # Delete b.pdf at destination so one restore fails
        (self.temp_dir / "Documents" / "b.pdf").unlink()
        restored, errors, logs = self.organizer.undo_last_operation()
        self.assertEqual(restored, 1)
        self.assertEqual(errors, 1)
        self.assertTrue((self.temp_dir / "a.pdf").exists())
        self.assertTrue(any("Cannot restore" in line for line in logs))

        # Failed item should remain in history for retry
        remaining = json.loads((self.temp_dir / "organizer_history.json").read_text(encoding="utf-8"))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(len(remaining[0]["moves"]), 1)

        # Corrupt history should fail gracefully
        (self.temp_dir / "organizer_history.json").write_text("{not valid json", encoding="utf-8")
        restored, errors, logs = self.organizer.undo_last_operation()
        self.assertEqual((restored, errors), (0, 0))
        self.assertTrue(any("Failed to read history" in line for line in logs))


class TestFolderWatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="watcher_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_readiness_for_zero_byte_and_readonly_files(self):
        empty_file = self.temp_dir / "empty.txt"
        empty_file.write_bytes(b"")
        self.assertTrue(is_file_ready(empty_file, check_interval=0.05, max_attempts=5))

        ro_file = self.temp_dir / "readonly.txt"
        ro_file.write_bytes(b"read only")
        os.chmod(ro_file, stat.S_IREAD)
        try:
            self.assertTrue(is_file_ready(ro_file, check_interval=0.05, max_attempts=5))
        finally:
            os.chmod(ro_file, stat.S_IWRITE | stat.S_IREAD)

    def test_watcher_preserves_existing_retries_and_stops_promptly(self):
        existing = self.temp_dir / "existing.pdf"
        existing.write_bytes(b"pre-existing")

        readiness_calls = {"count": 0}
        real_is_file_ready = is_file_ready

        def flaky_ready(path, *args, **kwargs):
            readiness_calls["count"] += 1
            if readiness_calls["count"] == 1:
                return False
            return real_is_file_ready(path, *args, **kwargs)

        events = []
        watcher = FolderWatcher(
            self.temp_dir,
            mode="category",
            interval=0.1,
            on_event=events.append,
            ready_check_interval=0.05,
            ready_max_attempts=5,
        )

        with patch("watcher.is_file_ready", side_effect=flaky_ready):
            watcher.start()
            time.sleep(0.2)
            (self.temp_dir / "incoming.pdf").write_bytes(b"new download")

            deadline = time.time() + 3.0
            while time.time() < deadline and not (self.temp_dir / "Documents" / "incoming.pdf").exists():
                time.sleep(0.1)

            t0 = time.time()
            watcher.stop()
            stop_elapsed = time.time() - t0

        self.assertTrue((self.temp_dir / "Documents" / "incoming.pdf").exists(), f"Events: {events}")
        self.assertGreaterEqual(readiness_calls["count"], 2)
        self.assertTrue(existing.exists())
        self.assertFalse((self.temp_dir / "Documents" / "existing.pdf").exists())
        self.assertLess(stop_elapsed, 1.5)


class TestCLIAndStandalone(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="cli_test_"))
        self.project_dir = Path(__file__).resolve().parent

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_organize_and_undo(self):
        (self.temp_dir / "sample.pdf").write_bytes(b"cli pdf")

        dry = subprocess.run(
            [sys.executable, str(self.project_dir / "main.py"), "--path", str(self.temp_dir), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertTrue((self.temp_dir / "sample.pdf").exists())

        org = subprocess.run(
            [sys.executable, str(self.project_dir / "main.py"), "--path", str(self.temp_dir), "--quiet"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(org.returncode, 0, org.stderr)
        self.assertTrue((self.temp_dir / "Documents" / "sample.pdf").exists())

        undo = subprocess.run(
            [sys.executable, str(self.project_dir / "main.py"), "--path", str(self.temp_dir), "--undo"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(undo.returncode, 0, undo.stderr)
        self.assertTrue((self.temp_dir / "sample.pdf").exists())

    def test_cli_invalid_path_exits_nonzero(self):
        bad = subprocess.run(
            [sys.executable, str(self.project_dir / "main.py"), "--path", str(self.temp_dir / "does_not_exist")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(bad.returncode, 1)

    def test_standalone_script_dry_run_and_move(self):
        (self.temp_dir / "pic.png").write_bytes(b"png")
        (self.temp_dir / "active.crdownload").write_bytes(b"partial")

        dry_res = standalone_script.organize_files(self.temp_dir, dry_run=True)
        self.assertEqual(dry_res["moved"], 1)
        self.assertEqual(dry_res["skipped"], 1)
        self.assertTrue((self.temp_dir / "pic.png").exists())

        real_res = standalone_script.organize_files(self.temp_dir, dry_run=False)
        self.assertEqual(real_res["moved"], 1)
        self.assertEqual(real_res["errors"], 0)
        self.assertTrue((self.temp_dir / "Pictures" / "pic.png").exists())
        self.assertTrue((self.temp_dir / "active.crdownload").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
