"""
Automated test script for File Organizer.
Creates a mock folder with test files, verifies organization, duplicate detection, and undo.
"""

import os
import shutil
import tempfile
from pathlib import Path
from organizer import FileOrganizer

def run_tests():
    temp_dir = Path(tempfile.mkdtemp(prefix="organizer_test_"))
    print(f"Running tests in temporary directory: {temp_dir}")

    try:
        # 1. Create mock messy files
        test_files = [
            ("invoice.pdf", b"test pdf content 1"),
            ("report.docx", b"test docx content 2"),
            ("photo.jpg", b"image content 3"),
            ("screenshot.png", b"image content 4"),
            ("song.mp3", b"music content 5"),
            ("video.mp4", b"video content 6"),
            ("archive.zip", b"zip content 7"),
            ("installer.exe", b"exe content 8"),
            ("script.py", b"python code 9"),
            ("notes.txt", b"text notes 10"),
            ("duplicate_photo.jpg", b"image content 3"),  # Identical hash to photo.jpg
        ]

        for fname, content in test_files:
            p = temp_dir / fname
            with open(p, "wb") as f:
                f.write(content)

        print(f"Created {len(test_files)} mock files.")

        organizer = FileOrganizer(temp_dir)

        # 2. Test Dry Run
        print("\n--- Test 1: Dry Run ---")
        dry_result = organizer.execute_organization(mode="category", dry_run=True)
        assert dry_result["dry_run"] is True, "Dry run flag should be True"
        assert dry_result["moved"] > 0, "Dry run should report files to move"
        assert (temp_dir / "invoice.pdf").exists(), "Original file should still exist after dry run"
        print("✓ Dry run passed successfully.")

        # 3. Test Actual Organization with Duplicate Detection
        print("\n--- Test 2: Category Organization with Duplicates ---")
        org_result = organizer.execute_organization(
            mode="category",
            detect_duplicates=True,
            conflict_resolution="rename",
        )
        print(f"Moved: {org_result['moved']}, Duplicates: {org_result['duplicates']}")
        assert (temp_dir / "Documents" / "invoice.pdf").exists(), "invoice.pdf should be in Documents/"
        assert (temp_dir / "Documents" / "report.docx").exists(), "report.docx should be in Documents/"
        # Either photo.jpg or duplicate_photo.jpg is in Pictures, and the other is in Duplicates
        pictures_files = [f.name for f in (temp_dir / "Pictures").iterdir()]
        duplicates_files = [f.name for f in (temp_dir / "Duplicates").iterdir()]
        assert ("photo.jpg" in pictures_files or "duplicate_photo.jpg" in pictures_files), "One photo must be in Pictures/"
        assert ("photo.jpg" in duplicates_files or "duplicate_photo.jpg" in duplicates_files), "Duplicate photo must be in Duplicates/"
        assert (temp_dir / "Music" / "song.mp3").exists(), "song.mp3 should be in Music/"
        assert (temp_dir / "Videos" / "video.mp4").exists(), "video.mp4 should be in Videos/"
        assert (temp_dir / "Archives" / "archive.zip").exists(), "archive.zip should be in Archives/"
        assert (temp_dir / "Programs" / "installer.exe").exists(), "installer.exe should be in Programs/"
        assert (temp_dir / "Code" / "script.py").exists(), "script.py should be in Code/"
        assert (temp_dir / "Duplicates").exists(), "Duplicates folder should exist"
        print("✓ Category organization & duplicate detection verified.")

        # 4. Test Undo
        print("\n--- Test 3: Undo Operation ---")
        restored, errors, logs = organizer.undo_last_operation()
        print(f"Restored: {restored}, Errors: {errors}")
        assert errors == 0, f"Undo had errors: {logs}"
        assert restored == len(test_files), f"Expected {len(test_files)} restored, got {restored}"
        assert (temp_dir / "invoice.pdf").exists(), "invoice.pdf should be back in root"
        assert (temp_dir / "photo.jpg").exists(), "photo.jpg should be back in root"
        assert not (temp_dir / "Documents").exists(), "Empty Documents folder should have been cleaned up"
        print("✓ Undo restored all files and cleaned up folders successfully.")

        # 5. Test Date Mode
        print("\n--- Test 4: Date Organization ---")
        date_result = organizer.execute_organization(mode="date")
        assert date_result["moved"] == len(test_files), "All files should be organized by date"
        print(f"Date organization moved {date_result['moved']} files.")
        
        # Test undo again
        restored, errors, _ = organizer.undo_last_operation()
        assert errors == 0 and restored == len(test_files)
        print("✓ Date mode and undo verified.")

        print("\n===============================")
        print("ALL TESTS PASSED WITH 100% SUCCESS!")
        print("===============================")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_tests()
