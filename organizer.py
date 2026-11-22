"""
Core organization engine with support for categories, date sorting,
extensions, conflict resolution, duplicate detection, dry-run, and undo.
"""

import os
import shutil
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple, Any

from config import (
    FILE_CATEGORIES,
    EXTENSION_MAP,
    INCOMPLETE_DOWNLOAD_EXTENSIONS,
    DEFAULT_IGNORED_FILENAMES,
    DEFAULT_IGNORED_DIRNAMES,
)

HISTORY_FILE_NAME = "organizer_history.json"


def calculate_file_hash(file_path: Path, block_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file for duplicate detection."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()


def get_unique_destination_path(target_file: Path) -> Path:
    """Generate a unique file path by appending (1), (2), etc. if file exists."""
    if not target_file.exists():
        return target_file

    stem = target_file.stem
    suffix = target_file.suffix
    parent = target_file.parent
    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class OrganizeOperation:
    def __init__(self, src: Path, dest: Path, category: str, action: str, details: str = ""):
        self.src = src
        self.dest = dest
        self.category = category
        self.action = action  # 'moved', 'skipped', 'duplicate', 'error'
        self.details = details

    def to_dict(self) -> Dict[str, str]:
        return {
            "src": str(self.src),
            "dest": str(self.dest),
            "category": self.category,
            "action": self.action,
            "details": self.details,
        }


class FileOrganizer:
    def __init__(self, target_dir: Path):
        self.target_dir = Path(target_dir).resolve()
        self.history_path = self.target_dir / HISTORY_FILE_NAME

    def get_destination_folder(self, file_path: Path, mode: str = "category") -> Path:
        """Determine destination folder based on organization mode."""
        ext = file_path.suffix.lower()

        if mode == "category":
            category = EXTENSION_MAP.get(ext, "Others")
            return self.target_dir / category

        elif mode == "date":
            # Organize by Year / Month of file modification
            try:
                mtime = file_path.stat().st_mtime
                file_dt = datetime.fromtimestamp(mtime)
                year_folder = file_dt.strftime("%Y")
                month_folder = file_dt.strftime("%m - %B")
                return self.target_dir / year_folder / month_folder
            except Exception:
                return self.target_dir / "Unknown Date"

        elif mode == "extension":
            clean_ext = ext.lstrip(".").upper() if ext else "NO_EXTENSION"
            return self.target_dir / clean_ext

        elif mode == "category_then_extension":
            category = EXTENSION_MAP.get(ext, "Others")
            clean_ext = ext.lstrip(".").upper() if ext else "NO_EXTENSION"
            return self.target_dir / category / clean_ext

        else:
            category = EXTENSION_MAP.get(ext, "Others")
            return self.target_dir / category

    def scan_files(self, recursive: bool = False, include_hidden: bool = False) -> List[Path]:
        """Collect all candidate files in the target directory."""
        if not self.target_dir.exists() or not self.target_dir.is_dir():
            return []

        # Categories that exist as subfolders in target_dir so we don't scan them recursively if not desired
        all_category_names = set(FILE_CATEGORIES.keys()) | {"Others", "Duplicates"}

        files_to_organize: List[Path] = []

        if recursive:
            iterator = self.target_dir.rglob("*")
        else:
            iterator = self.target_dir.iterdir()

        for item in iterator:
            if not item.is_file():
                continue

            # Check if inside an ignored directory
            parts = item.relative_to(self.target_dir).parts
            if any(p.lower() in DEFAULT_IGNORED_DIRNAMES for p in parts[:-1]):
                continue

            # Check if filename is ignored
            name_lower = item.name.lower()
            if name_lower in DEFAULT_IGNORED_FILENAMES:
                continue

            # Ignore hidden files if not included
            if not include_hidden and (item.name.startswith(".") or name_lower.startswith("~$")):
                continue

            # Skip files in the middle of downloading
            if item.suffix.lower() in INCOMPLETE_DOWNLOAD_EXTENSIONS:
                continue

            # If not recursive, do not touch files already inside category folders
            if not recursive and item.parent != self.target_dir:
                continue

            files_to_organize.append(item)

        return sorted(files_to_organize, key=lambda f: f.name.lower())

    def plan_organization(
        self,
        mode: str = "category",
        recursive: bool = False,
        conflict_resolution: str = "rename",
        include_hidden: bool = False,
        detect_duplicates: bool = False,
    ) -> List[OrganizeOperation]:
        """Simulate the organization and return planned operations."""
        files = self.scan_files(recursive=recursive, include_hidden=include_hidden)
        operations: List[OrganizeOperation] = []

        # Track existing file hashes if duplicate detection is enabled
        seen_hashes: Dict[str, Path] = {}

        for file in files:
            dest_folder = self.get_destination_folder(file, mode=mode)
            ext = file.suffix.lower()
            category = EXTENSION_MAP.get(ext, "Others")

            # Check if file is already in its destination folder
            if file.parent.resolve() == dest_folder.resolve():
                operations.append(
                    OrganizeOperation(file, file, category, "skipped", "Already in target category")
                )
                continue

            target_path = dest_folder / file.name

            # Duplicate check
            is_duplicate = False
            if detect_duplicates:
                try:
                    f_hash = calculate_file_hash(file)
                    if f_hash in seen_hashes:
                        # Duplicate found
                        dup_folder = self.target_dir / "Duplicates"
                        dup_dest = get_unique_destination_path(dup_folder / file.name)
                        operations.append(
                            OrganizeOperation(
                                file,
                                dup_dest,
                                "Duplicates",
                                "duplicate",
                                f"Duplicate of {seen_hashes[f_hash].name}",
                            )
                        )
                        is_duplicate = True
                    else:
                        seen_hashes[f_hash] = file
                except Exception as e:
                    pass

            if is_duplicate:
                continue

            # Conflict handling
            if target_path.exists():
                if conflict_resolution == "skip":
                    operations.append(
                        OrganizeOperation(file, target_path, category, "skipped", "Destination already exists")
                    )
                    continue
                elif conflict_resolution == "rename":
                    resolved_path = get_unique_destination_path(target_path)
                    operations.append(
                        OrganizeOperation(
                            file, resolved_path, category, "moved", f"Renamed to avoid conflict: {resolved_path.name}"
                        )
                    )
                    continue
                elif conflict_resolution == "overwrite":
                    operations.append(
                        OrganizeOperation(file, target_path, category, "moved", "Overwrites existing file")
                    )
                    continue

            # Normal move
            operations.append(OrganizeOperation(file, target_path, category, "moved", "Normal move"))

        return operations

    def execute_organization(
        self,
        mode: str = "category",
        recursive: bool = False,
        conflict_resolution: str = "rename",
        include_hidden: bool = False,
        detect_duplicates: bool = False,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
    ) -> Dict[str, Any]:
        """Execute organization process and save history for undo."""
        planned = self.plan_organization(
            mode=mode,
            recursive=recursive,
            conflict_resolution=conflict_resolution,
            include_hidden=include_hidden,
            detect_duplicates=detect_duplicates,
        )

        total_files = len(planned)
        moved_count = 0
        skipped_count = 0
        duplicate_count = 0
        error_count = 0
        actual_moves: List[Dict[str, str]] = []

        for idx, op in enumerate(planned):
            if progress_callback:
                progress_callback(idx + 1, total_files, op.src.name, op.action)

            if dry_run:
                if op.action == "moved":
                    moved_count += 1
                elif op.action == "duplicate":
                    duplicate_count += 1
                elif op.action == "skipped":
                    skipped_count += 1
                continue

            if op.action in ("moved", "duplicate"):
                try:
                    op.dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(op.src), str(op.dest))
                    actual_moves.append(
                        {"src": str(op.src), "dest": str(op.dest), "category": op.category}
                    )
                    if op.action == "duplicate":
                        duplicate_count += 1
                    else:
                        moved_count += 1
                except Exception as ex:
                    error_count += 1
                    op.action = "error"
                    op.details = str(ex)
            elif op.action == "skipped":
                skipped_count += 1

        # Record history if not dry-run and files were moved
        if not dry_run and actual_moves:
            self._save_history(actual_moves, mode)

        return {
            "total": total_files,
            "moved": moved_count,
            "duplicates": duplicate_count,
            "skipped": skipped_count,
            "errors": error_count,
            "operations": planned,
            "dry_run": dry_run,
        }

    def _save_history(self, moves: List[Dict[str, str]], mode: str):
        """Append this operation batch to history file."""
        history = []
        if self.history_path.exists():
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        batch_record = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "moves": moves,
        }
        history.append(batch_record)

        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def undo_last_operation(
        self, progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Reverse the last organization batch.
        Returns: (restored_count, error_count, log_messages)
        """
        if not self.history_path.exists():
            return 0, 0, ["No history found to undo."]

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            return 0, 0, [f"Failed to read history: {e}"]

        if not history:
            return 0, 0, ["History is empty."]

        last_batch = history.pop()
        moves = last_batch.get("moves", [])
        total = len(moves)
        restored = 0
        errors = 0
        logs = []
        folders_to_check = set()

        # Reverse moves in reverse order
        for idx, item in enumerate(reversed(moves)):
            orig_src = Path(item["src"])
            current_dest = Path(item["dest"])

            if progress_callback:
                progress_callback(idx + 1, total, current_dest.name, "restoring")

            if not current_dest.exists():
                logs.append(f"Cannot restore {current_dest.name}: File missing at destination.")
                errors += 1
                continue

            try:
                orig_src.parent.mkdir(parents=True, exist_ok=True)
                dest_path = orig_src
                if dest_path.exists():
                    dest_path = get_unique_destination_path(dest_path)
                shutil.move(str(current_dest), str(dest_path))
                restored += 1
                logs.append(f"Restored: {current_dest.name} -> {dest_path}")
                folders_to_check.add(current_dest.parent)
            except Exception as e:
                errors += 1
                logs.append(f"Error restoring {current_dest.name}: {e}")

        # Clean up empty folders created by organization
        for folder in folders_to_check:
            try:
                if folder.exists() and folder != self.target_dir:
                    # check if folder is empty
                    if not any(folder.iterdir()):
                        folder.rmdir()
                        logs.append(f"Removed empty directory: {folder.name}")
            except Exception:
                pass

        # Save remaining history
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return restored, errors, logs
