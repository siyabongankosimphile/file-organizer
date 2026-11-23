# 📁 Smart File Organizer (Python)

A reliable, zero-dependency file organization system built with Python 3.10+. Organizes messy folders (like **Downloads**, **Desktop**, or **Documents**) into clean, structured directories via a Tkinter GUI, CLI, or live background watcher.

---

## ✨ Features

- **Category Sorting**: Classifies files into `Documents`, `Pictures`, `Music`, `Videos`, `Archives`, `Programs`, `Code`, `3D Models & CAD`, `Fonts`, `Torrents & Links`, and `Others`.
- **Date-Based Sorting**: Organizes files by modification year and month (e.g. `2026/11 - November/`).
- **Extension-Based Sorting**: Organizes files directly by extension (e.g. `PDF/`, `JPG/`, `MP4/`).
- **Category + Extension Sorting**: Groups files by category and then by extension (e.g. `Documents/PDF/`).
- **🖥️ Graphical User Interface (GUI)**:
  - Clean Tkinter interface with quick shortcut buttons for Downloads, Desktop, Documents, Pictures, Music, and Videos.
  - Non-blocking background operations with progress bar and color-coded read-only activity log.
  - Dry-run preview mode before touching any files.
- **↩️ Safe Undo / Revert**:
  - Journals operations in `organizer_history.json` (up to the last 50 batches).
  - Reverses moves back to original locations, recursively cleans up empty folders, and retains any unrestored items for retry.
- **⚡ Smart Conflict & Duplicate Handling**:
  - Prevents both on-disk and intra-batch filename collisions (`rename`, `skip`, or `overwrite`).
  - Computes SHA-256 hashes (including against already-organized files) to isolate exact duplicates into a `Duplicates/` folder.
- **👀 Live Auto-Watcher**:
  - Monitors incoming downloads in real time and organizes **only newly arriving files** once writes stabilize (ignoring `.crdownload`, `.tmp`, `.part`, `.download`, `.opdownload` until complete).
- **Zero External Dependencies**: Uses only the Python standard library (`pathlib`, `shutil`, `hashlib`, `tkinter`, `threading`).

---

## 📋 Requirements

- **Python 3.10+** (includes `tkinter` on standard Windows/macOS installers).

---

## 🚀 How to Run

### Option 1: Double-Click Launcher (Windows)
Double-click:
```text
run_organizer.bat
```
It automatically locates Python 3.10+ (even in paths with spaces) and launches the GUI. You can also pass CLI flags to it, e.g. `run_organizer.bat --dry-run`.

---

### Option 2: Run via Command Line

Open PowerShell, Command Prompt, or a terminal in this folder:

```powershell
# 1. Launch the Graphical Interface (default with no flags, or pass --gui)
python main.py

# 2. Preview changes in your Downloads folder without moving (Dry Run)
python main.py --dry-run

# 3. Organize a specific folder into categories
python main.py --path "$HOME/Downloads"

# 4. Organize by Date (Year / Month), Extension, or Category + Extension
python main.py --path "$HOME/Downloads" --mode date
python main.py --path "$HOME/Downloads" --mode extension
python main.py --path "$HOME/Downloads" --mode category_then_extension

# 5. Include subfolders recursively and isolate duplicates
python main.py --path "$HOME/Downloads" --recursive --duplicates

# 6. Control filename conflict behavior (rename, skip, overwrite)
python main.py --path "$HOME/Downloads" --conflict skip

# 7. Undo the last organization
python main.py --path "$HOME/Downloads" --undo

# 8. Start the live background folder watcher
python main.py --path "$HOME/Downloads" --watch --mode category --duplicates
```

---

### Option 3: Standalone Beginner Script
If you want to study or run the single-file script:
```powershell
python file_organizer.py --dry-run
python file_organizer.py --path "$HOME/Downloads"
```

---

## 🧪 Running Tests

Run the full automated `unittest` suite:
```powershell
python -m unittest discover -v
```
Or run directly:
```powershell
python test_organizer.py
```

---

## 📂 Project Architecture

| File | Purpose |
| :--- | :--- |
| [main.py](main.py) | Main entry point handling CLI flags and GUI startup |
| [gui.py](gui.py) | Tkinter graphical interface with preview, live logs, undo, and watcher controls |
| [organizer.py](organizer.py) | Core engine: scanning, sorting modes, collision safety, duplicate hashing, and undo |
| [watcher.py](watcher.py) | Live folder monitor with write stabilization, retries, and clean shutdown |
| [config.py](config.py) | Category rules, extension maps, and ignored system/app files |
| [file_organizer.py](file_organizer.py) | Standalone beginner-friendly script with dry-run and confirmation prompt |
| [run_organizer.bat](run_organizer.bat) | 1-click Windows launcher batch script |
| [test_organizer.py](test_organizer.py) | Automated `unittest` suite covering engine, watcher, CLI, and standalone script |
| [pyproject.toml](pyproject.toml) | Project metadata, Python version constraint, and CLI entry point |
