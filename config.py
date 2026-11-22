"""
Configuration and file category mappings for File Organizer.
"""

from pathlib import Path

# Mapping of Category Name -> List of extensions (lowercase with leading dot)
FILE_CATEGORIES = {
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages", ".tex",
        ".csv", ".tsv", ".xls", ".xlsx", ".xlsm", ".ods",
        ".ppt", ".pptx", ".odp", ".key", ".epub", ".mobi"
    ],
    "Pictures": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
        ".tiff", ".tif", ".ico", ".raw", ".cr2", ".nef", ".arw",
        ".psd", ".ai", ".heic", ".heif"
    ],
    "Music": [
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma",
        ".opus", ".mid", ".midi", ".alac", ".aiff"
    ],
    "Videos": [
        ".mp4", ".mkv", ".flv", ".avi", ".mov", ".wmv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp", ".ts", ".vob"
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".iso", ".tgz", ".7zip", ".cab"
    ],
    "Programs": [
        ".exe", ".msi", ".bat", ".cmd", ".ps1", ".apk", ".dmg",
        ".appx", ".msix"
    ],
    "Code": [
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm",
        ".css", ".scss", ".sass", ".json", ".xml", ".yaml", ".yml",
        ".c", ".cpp", ".h", ".hpp", ".cs", ".java", ".go", ".rs",
        ".php", ".rb", ".sh", ".sql", ".lua", ".swift", ".kt"
    ],
    "3D Models & CAD": [
        ".obj", ".fbx", ".stl", ".blend", ".3ds", ".step", ".stp",
        ".dwg", ".dxf", ".dae"
    ],
    "Fonts": [
        ".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon"
    ],
    "Torrents & Links": [
        ".torrent", ".url", ".lnk"
    ]
}

# Reverse lookup dictionary for O(1) extension category lookup
EXTENSION_MAP = {}
for category, extensions in FILE_CATEGORIES.items():
    for ext in extensions:
        EXTENSION_MAP[ext.lower()] = category

# In-progress download file extensions that should be skipped until download completes
INCOMPLETE_DOWNLOAD_EXTENSIONS = {
    ".crdownload", ".tmp", ".download", ".part", ".opdownload"
}

# System files and folders to ignore by default
DEFAULT_IGNORED_FILENAMES = {
    "desktop.ini", "thumbs.db", ".ds_store", "organizer_history.json",
    "organizer_log.txt", "file_organizer.py", "main.py", "organizer.py",
    "config.py", "gui.py", "watcher.py"
}

DEFAULT_IGNORED_DIRNAMES = {
    ".git", ".svn", "$recycle.bin", "system volume information",
    "node_modules", "__pycache__", ".venv", "venv", "env"
}

# Quick access folders on Windows/macOS/Linux
QUICK_FOLDERS = {
    "Downloads": Path.home() / "Downloads",
    "Desktop": Path.home() / "Desktop",
    "Documents": Path.home() / "Documents",
    "Pictures": Path.home() / "Pictures",
    "Music": Path.home() / "Music",
    "Videos": Path.home() / "Videos",
}
