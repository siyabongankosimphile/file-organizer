"""
Live folder monitoring to automatically organize incoming files.
Runs without requiring external packages, with debounce to ensure downloads finish.
"""

import os
import threading
from pathlib import Path
from typing import Callable, Optional, Set
from organizer import FileOrganizer
from config import INCOMPLETE_DOWNLOAD_EXTENSIONS, DEFAULT_IGNORED_FILENAMES


def is_file_ready(
    file_path: Path,
    check_interval: float = 1.0,
    max_attempts: int = 15,
    stop_event: Optional[threading.Event] = None,
) -> bool:
    """
    Ensure the file is completely written (download finished)
    by verifying file size/mtime have stopped changing and it can be accessed.
    Supports 0-byte and read-only files, and exits early if stop_event is set.
    """
    if not file_path.exists():
        return False

    if file_path.suffix.lower() in INCOMPLETE_DOWNLOAD_EXTENSIONS:
        return False

    previous_state = None
    for _ in range(max_attempts):
        if stop_event and stop_event.is_set():
            return False
        if not file_path.exists():
            return False
        try:
            stat_info = file_path.stat()
            current_state = (stat_info.st_size, stat_info.st_mtime_ns)
            if previous_state is not None and current_state == previous_state:
                # Confirm file is readable and not exclusively locked
                with open(file_path, "rb"):
                    pass
                # If writable, also confirm no writer lock holds it exclusively
                if os.access(file_path, os.W_OK):
                    with open(file_path, "r+b"):
                        pass
                return True
            previous_state = current_state
        except (OSError, PermissionError):
            previous_state = None

        if stop_event:
            if stop_event.wait(check_interval):
                return False
        else:
            import time
            time.sleep(check_interval)

    return False


class FolderWatcher:
    def __init__(
        self,
        folder_path: Path,
        mode: str = "category",
        interval: float = 2.0,
        on_event: Optional[Callable[[str], None]] = None,
        conflict_resolution: str = "rename",
        detect_duplicates: bool = False,
        ready_check_interval: float = 1.0,
        ready_max_attempts: int = 15,
    ):
        self.folder_path = Path(folder_path).resolve()
        self.mode = mode
        self.interval = interval
        self.on_event = on_event
        self.conflict_resolution = conflict_resolution
        self.detect_duplicates = detect_duplicates
        self.ready_check_interval = ready_check_interval
        self.ready_max_attempts = ready_max_attempts
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.organizer = FileOrganizer(self.folder_path)

    def _log(self, msg: str):
        if self.on_event:
            self.on_event(msg)
        else:
            print(f"[Watcher] {msg}")

    def _watch_loop(self):
        self._log(f"Started watching: {self.folder_path}")
        known_files: Set[Path] = set()

        # Seed initial existing files so we don't unexpectedly move everything on watch startup
        if self.folder_path.exists():
            for item in self.folder_path.iterdir():
                if item.is_file():
                    known_files.add(item)

        while self._running and not self._stop_event.is_set():
            try:
                if not self.folder_path.exists():
                    self._stop_event.wait(self.interval)
                    continue

                current_files = {item for item in self.folder_path.iterdir() if item.is_file()}
                # Drop deleted/moved entries from known_files without absorbing unready new files
                known_files = {f for f in known_files if f in current_files}

                new_files = sorted(current_files - known_files, key=lambda p: p.name.lower())

                for new_file in new_files:
                    if self._stop_event.is_set():
                        break

                    # Ignore system/app/hidden files permanently for this watch session
                    if new_file.name.lower() in DEFAULT_IGNORED_FILENAMES or new_file.name.startswith("."):
                        known_files.add(new_file)
                        continue

                    # If it's a temp/download extension, skip without marking known so it's checked later
                    if new_file.suffix.lower() in INCOMPLETE_DOWNLOAD_EXTENSIONS:
                        continue

                    # Wait for download/write to complete
                    self._log(f"Detected incoming file: {new_file.name}. Verifying write...")
                    if is_file_ready(
                        new_file,
                        check_interval=self.ready_check_interval,
                        max_attempts=self.ready_max_attempts,
                        stop_event=self._stop_event,
                    ):
                        # Organize ONLY this incoming file so pre-existing files remain untouched
                        result = self.organizer.execute_organization(
                            mode=self.mode,
                            recursive=False,
                            conflict_resolution=self.conflict_resolution,
                            detect_duplicates=self.detect_duplicates,
                            files=[new_file],
                        )
                        moved_or_handled = False
                        for op in result.get("operations", []):
                            if op.action == "moved":
                                self._log(f"Auto-Organized: {op.src.name} -> {op.dest.parent.name}/{op.dest.name}")
                                moved_or_handled = True
                            elif op.action == "duplicate":
                                self._log(f"Duplicate isolated: {op.src.name} -> Duplicates/{op.dest.name}")
                                moved_or_handled = True
                            elif op.action == "skipped":
                                self._log(f"Skipped: {op.src.name} ({op.details})")
                                moved_or_handled = True
                            elif op.action == "error":
                                self._log(f"Error organizing {op.src.name}: {op.details}")
                        if moved_or_handled and new_file.exists():
                            known_files.add(new_file)
                    elif not self._stop_event.is_set():
                        # Do NOT add to known_files so the next cycle retries it
                        self._log(f"File {new_file.name} is still in use or downloading. Will retry...")

            except Exception as e:
                self._log(f"Watcher error: {e}")

            self._stop_event.wait(self.interval)

    def start(self):
        """Start watcher in a background thread."""
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop folder watcher."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._log("Watcher stopped.")
