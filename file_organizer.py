"""
Standalone Beginner-Friendly File Organizer Script.
Zero dependencies — uses only Python's built-in pathlib and shutil.
"""

from pathlib import Path
import shutil

# Folder you want to organize (defaults to your Downloads folder)
TARGET_FOLDER = Path.home() / "Downloads"

# Comprehensive category mappings
FILE_TYPES = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".pptx", ".csv", ".rtf", ".epub"],
    "Pictures": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".psd"],
    "Music": [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".flv"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"],
    "Programs": [".exe", ".msi", ".bat", ".apk", ".ps1"],
    "Code": [".py", ".js", ".html", ".css", ".json", ".xml", ".cpp", ".java", ".sql", ".sh"],
}

# Temporary or partial download files to ignore
IGNORE_EXTENSIONS = {".crdownload", ".tmp", ".download", ".part", ".opdownload"}
IGNORE_FILENAMES = {"desktop.ini", "thumbs.db", ".ds_store", "file_organizer.py"}


def organize_files(folder: Path = TARGET_FOLDER):
    print(f"Scanning folder: {folder}")
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Folder '{folder}' does not exist.")
        return

    moved_count = 0
    skipped_count = 0

    for file in folder.iterdir():
        # Skip sub-folders
        if file.is_dir():
            continue

        # Skip system or ignored files
        if file.name.lower() in IGNORE_FILENAMES or file.name.startswith("."):
            continue

        # Skip partial downloads
        if file.suffix.lower() in IGNORE_EXTENSIONS:
            print(f"Skipping active download: {file.name}")
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

        destination_folder.mkdir(exist_ok=True)
        destination_file = destination_folder / file.name

        # If a file with the same name already exists, append a number
        if destination_file.exists():
            counter = 1
            while destination_file.exists():
                destination_file = destination_folder / f"{file.stem} ({counter}){file.suffix}"
                counter += 1

        try:
            shutil.move(str(file), str(destination_file))
            print(f"Moved: {file.name} -> {destination_folder.name}/{destination_file.name}")
            moved_count += 1
        except Exception as e:
            print(f"Error moving {file.name}: {e}")
            skipped_count += 1

    print("\n" + "=" * 40)
    print(f"Finished! Successfully moved {moved_count} files ({skipped_count} skipped/errors).")
    print("=" * 40)


if __name__ == "__main__":
    organize_files()
