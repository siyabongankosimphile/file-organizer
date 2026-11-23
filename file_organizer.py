"""
Standalone Beginner-Friendly File Organizer Script.
Zero dependencies — uses only Python's built-in pathlib, shutil, and argparse.
"""

import argparse
from pathlib import Path
import shutil

# Folder you want to organize (defaults to your Downloads folder)
TARGET_FOLDER = Path.home() / "Downloads"

# Comprehensive category mappings (kept in sync with config.py)
FILE_TYPES = {
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages", ".tex",
        ".csv", ".tsv", ".xls", ".xlsx", ".xlsm", ".ods",
        ".ppt", ".pptx", ".odp", ".key", ".epub", ".mobi",
    ],
    "Pictures": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
        ".tiff", ".tif", ".ico", ".raw", ".cr2", ".nef", ".arw",
        ".psd", ".ai", ".heic", ".heif",
    ],
    "Music": [
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma",
        ".opus", ".mid", ".midi", ".alac", ".aiff",
    ],
    "Videos": [
        ".mp4", ".mkv", ".flv", ".avi", ".mov", ".wmv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp", ".m2ts", ".vob",
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".iso", ".tgz", ".7zip", ".cab",
    ],
    "Programs": [
        ".exe", ".msi", ".bat", ".cmd", ".ps1", ".apk", ".dmg",
        ".appx", ".msix",
    ],
    "Code": [
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm",
        ".css", ".scss", ".sass", ".json", ".xml", ".yaml", ".yml",
        ".c", ".cpp", ".h", ".hpp", ".cs", ".java", ".go", ".rs",
        ".php", ".rb", ".sh", ".sql", ".lua", ".swift", ".kt",
    ],
    "3D Models & CAD": [
        ".obj", ".fbx", ".stl", ".blend", ".3ds", ".step", ".stp",
        ".dwg", ".dxf", ".dae",
    ],
    "Fonts": [
        ".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon",
    ],
    "Torrents & Links": [
        ".torrent", ".url", ".lnk",
    ],
}

# Temporary or partial download files to ignore
IGNORE_EXTENSIONS = {".crdownload", ".tmp", ".download", ".part", ".opdownload"}
IGNORE_FILENAMES = {"desktop.ini", "thumbs.db", ".ds_store", "file_organizer.py"}


def organize_files(folder: Path = TARGET_FOLDER, dry_run: bool = False):
    folder = Path(folder)
    print(f"Scanning folder: {folder}")
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Folder '{folder}' does not exist.")
        return {"moved": 0, "skipped": 0, "errors": 1}

    moved_count = 0
    skipped_count = 0
    error_count = 0

    for file in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        # Skip sub-folders and symlinks
        if file.is_dir() or file.is_symlink():
            continue

        # Skip system or ignored files
        if file.name.lower() in IGNORE_FILENAMES or file.name.startswith("."):
            skipped_count += 1
            continue

        # Skip partial downloads
        if file.suffix.lower() in IGNORE_EXTENSIONS:
            print(f"Skipping active download: {file.name}")
            skipped_count += 1
            continue

        extension = file.suffix.lower()
        destination_folder = None

        # Determine which folder the file belongs to
        for category, extensions in FILE_TYPES.items():
            if extension in extensions:
                destination_folder = folder / category
                break

        # If extension is not in list, put it into 'Others'
        if not destination_folder:
            destination_folder = folder / "Others"

        destination_file = destination_folder / file.name

        # If a file with the same name already exists, append a number
        if destination_file.exists():
            counter = 1
            while destination_file.exists():
                destination_file = destination_folder / f"{file.stem} ({counter}){file.suffix}"
                counter += 1

        if dry_run:
            print(f"[DRY RUN] Would move: {file.name} -> {destination_folder.name}/{destination_file.name}")
            moved_count += 1
            continue

        try:
            destination_folder.mkdir(exist_ok=True)
            shutil.move(str(file), str(destination_file))
            print(f"Moved: {file.name} -> {destination_folder.name}/{destination_file.name}")
            moved_count += 1
        except Exception as e:
            print(f"Error moving {file.name}: {e}")
            error_count += 1

    print("\n" + "=" * 40)
    prefix = "Dry run finished! Would move" if dry_run else "Finished! Successfully moved"
    print(f"{prefix} {moved_count} files ({skipped_count} skipped, {error_count} errors).")
    print("=" * 40)
    return {"moved": moved_count, "skipped": skipped_count, "errors": error_count}


def main():
    parser = argparse.ArgumentParser(description="Standalone Beginner-Friendly File Organizer.")
    parser.add_argument(
        "-p", "--path",
        default=str(TARGET_FOLDER),
        help="Folder to organize (defaults to your Downloads folder).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without modifying any files.",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt.",
    )
    args = parser.parse_args()
    target = Path(args.path).expanduser().resolve()

    if not args.dry_run and not args.yes:
        reply = input(f"Organize files in '{target}'? (This script has no undo) [y/N]: ").strip().lower()
        if reply not in ("y", "yes"):
            print("Cancelled.")
            return

    organize_files(target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
