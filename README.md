# 📁 Smart File Organizer (Python)

A powerful, reliable, and user-friendly file organization system built with Python. Organizes messy folders (like **Downloads**, **Desktop**, or **Documents**) into clean, categorized directories.

---

## ✨ Features

- **Category Sorting**: Automatically classifies files into `Documents`, `Pictures`, `Music`, `Videos`, `Archives`, `Programs`, `Code`, `3D Models & CAD`, `Fonts`, and `Torrents`.
- **Date-Based Sorting**: Organizes files by modification year and month (e.g. `2024/11 - November/`).
- **Extension-Based Sorting**: Organizes files directly by extension (e.g. `PDF/`, `JPG/`, `MP4/`).
- **🖥️ Modern Graphical User Interface (GUI)**:
  - Clean Tkinter interface with quick shortcut buttons for Downloads, Desktop, Documents.
  - Live progress bar and color-coded activity logs.
  - Dry-run preview mode before touching any files.
- **↩️ Safe Undo / Revert**:
  - Automatically journals operations in `organizer_history.json`.
  - Reverses file moves back to original locations and cleans up empty folders in 1 click.
- **⚡ Smart Conflict & Duplicate Handling**:
  - Automatically renames files with `(1)`, `(2)` to prevent overwriting existing files.
  - Computes SHA-256 hashes to isolate exact duplicates into a `Duplicates/` folder.
- **👀 Live Auto-Watcher**:
  - Monitors incoming downloads in real-time and organizes them automatically once downloads finish (with download completion detection for `.crdownload`, `.tmp`, `.part`).
- **Zero External Dependencies**: Works out of the box with standard Python (`pathlib`, `shutil`, `hashlib`, `tkinter`).

---

## 🚀 How to Run

### Option 1: Double-Click Launcher (Easiest)
Simply double-click:
```
run_organizer.bat
```
This automatically finds your installed Python 3.11 and opens the graphical application.

---

### Option 2: Run via Command Line

Open PowerShell or Command Prompt in this folder:

```powershell
# 1. Launch the Graphical Interface
python main.py

# 2. Preview changes in your Downloads folder without moving (Dry Run)
python main.py --dry-run

# 3. Organize your Downloads folder into categories
python main.py --path "C:\Users\MAN MAN\Downloads"

# 4. Organize by Date (Year and Month)
python main.py --path "C:\Users\MAN MAN\Downloads" --mode date

# 5. Detect and isolate duplicate files
python main.py --path "C:\Users\MAN MAN\Downloads" --duplicates

# 6. Undo the last organization
python main.py --path "C:\Users\MAN MAN\Downloads" --undo

# 7. Start the live background folder watcher
python main.py --path "C:\Users\MAN MAN\Downloads" --watch
```

---

### Option 3: Beginner Standalone Script
If you want to study or run the single-file beginner script:
```powershell
python file_organizer.py
```

---

## 📂 Project Architecture

| File | Purpose |
| :--- | :--- |
| [main.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/main.py) | Main entry point; handles both CLI flags and GUI launcher |
| [gui.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/gui.py) | Graphical interface with real-time logs, preview, and undo |
| [organizer.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/organizer.py) | Core engine: scanning, categorization, conflict resolution, hash check, and undo |
| [watcher.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/watcher.py) | Live folder monitor with write stabilization and debounce |
| [config.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/config.py) | Category rules, extension maps, and ignored system files |
| [file_organizer.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/file_organizer.py) | Standalone beginner script |
| [run_organizer.bat](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/run_organizer.bat) | 1-click Windows launcher batch script |
| [test_organizer.py](file:///C:/Users/MAN%20MAN/.gemini/antigravity/scratch/file_organizer/test_organizer.py) | Automated test suite verifying dry-run, moves, duplicates, and undo |
