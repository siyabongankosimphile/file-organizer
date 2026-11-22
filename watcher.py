"""
Live folder monitoring to automatically organize incoming files.
Runs without requiring external packages, with debounce to ensure downloads finish.
"""

import time
import threading
from pathlib import Path
from typing import Callable, Optional, Set
from organizer import FileOrganizer
from config import INCOMPLETE_DOWNLOAD_EXTENSIONS, DEFAULT_IGNORED_FILENAMES


def is_file_ready(file_path: Path, check_interval: float = 1.0, max_attempts: int = 15) -> bool:
    """
    Ensure the file is completely written (download finished)
    by verifying file size has stopped changing and it's not locked.
    """
    if not file_path.exists():
        return False

    if file_path.suffix.lower() in INCOMPLETE_DOWNLOAD_EXTENSIONS:
        return False

    previous_size = -1
    for _ in range(max_attempts):
        if not file_path.exists():
            return False
        try:
            current_size = file_path.stat().st_size
            if current_size == previous_size and current_size > 0:
                # Try opening in append mode to confirm no lock
                with open(file_path, "ab"):
                    return True
            previous_size = current_size
        except (OSError, PermissionError):
            pass
        time.sleep(check_interval)

    return False


class FolderWatcher:
    def __init__(
        self,
        folder_path: Path,
        mode: str = "category",
        interval: float = 2.0,
        on_event: Optional[Callable[[str], None]] = None,
    ):
        self.folder_path = Path(folder_path).resolve()
        self.mode = mode
        self.interval = interval
        self.on_event = on_event
        self._running = False
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
        for item in self.folder_path.iterdir():
            if item.is_file():
                known_files.add(item)

        while self._running:
            try:
                if not self.folder_path.exists():
                    time.sleep(self.interval)
                    continue

                current_files = set()
                for item in self.folder_path.iterdir():
                    if item.is_file():
                        current_files.add(item)

                new_files = current_files - known_files

                for new_file in new_files:
                    # Ignore system/app files
                    if new_file.name.lower() in DEFAULT_IGNORED_FILENAMES or new_file.name.startswith("."):
                        continue

                    # If it's a temp/download extension, skip until next check
                    if new_file.suffix.lower() in INCOMPLETE_DOWNLOAD_EXTENSIONS:
                        continue

                    # Wait for download/write to complete
                    self._log(f"Detected incoming file: {new_file.name}. Verifying write...")
                    if is_file_ready(new_file):
                        result = self.organizer.execute_organization(
                            mode=self.mode,
                            recursive=False,
                            conflict_resolution="rename",
                        )
                        for op in result.get("operations", []):
                            if op.action == "moved":
                                self._log(f"Auto-Organized: {op.src.name} -> {op.dest.parent.name}/{op.dest.name}")
                    else:
                        self._log(f"File {new_file.name} is still in use or downloading. Will retry...")

                # Update known files (excluding deleted/moved ones)
                known_files = {f for f in current_files if f.exists()}

            except Exception as e:
                self._log(f"Watcher error: {e}")

            time.sleep(self.interval)

    def start(self):
        """Start watcher in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop folder watcher."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._log("Watcher stopped.")
