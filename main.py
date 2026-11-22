"""
Smart File Organizer - Main Entry Point.
Supports both graphical user interface (GUI) and command-line interface (CLI).
"""

import sys
import argparse
from pathlib import Path
from organizer import FileOrganizer
from watcher import FolderWatcher
from config import QUICK_FOLDERS


def run_cli(args):
    target = Path(args.path).resolve()
    if not target.exists() or not target.is_dir():
        print(f"[Error] Target directory does not exist: {target}")
        sys.exit(1)

    organizer = FileOrganizer(target)

    # Undo mode
    if args.undo:
        print(f"Undoing last organization in: {target}")
        restored, errors, logs = organizer.undo_last_operation()
        for log in logs:
            print(f"  {log}")
        print(f"\nUndo Complete: {restored} files restored, {errors} errors.")
        return

    # Watcher mode
    if args.watch:
        print(f"Starting live folder watcher on: {target}")
        print("Press Ctrl+C to stop.")
        watcher = FolderWatcher(target, mode=args.mode)
        watcher.start()
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping watcher...")
            watcher.stop()
            print("Watcher stopped.")
        return

    # Organize / Dry run
    mode_desc = f"Mode: {args.mode}"
    if args.dry_run:
        print(f"\n=== PREVIEWING (DRY RUN) ORGANIZATION ===")
    else:
        print(f"\n=== ORGANIZING FILES ===")
    print(f"Target: {target}")
    print(f"{mode_desc} | Conflict: {args.conflict} | Recursive: {args.recursive} | Duplicates: {args.duplicates}\n")

    def cli_progress(current, total, filename, action):
        print(f"[{current}/{total}] {action.upper()}: {filename}")

    result = organizer.execute_organization(
        mode=args.mode,
        recursive=args.recursive,
        conflict_resolution=args.conflict,
        detect_duplicates=args.duplicates,
        dry_run=args.dry_run,
        progress_callback=cli_progress if not args.quiet else None,
    )

    print("\n" + "=" * 40)
    if args.dry_run:
        print(f"DRY RUN COMPLETE (No files were moved)")
    else:
        print(f"ORGANIZATION COMPLETE")
    print(f"Total scanned: {result['total']}")
    print(f"Files moved:   {result['moved']}")
    print(f"Duplicates:    {result['duplicates']}")
    print(f"Skipped:       {result['skipped']}")
    print(f"Errors:        {result['errors']}")
    print("=" * 40)

    if not args.dry_run and result["moved"] > 0:
        print(f"\nTip: To undo this operation, run:")
        print(f'  python main.py --path "{target}" --undo')


def main():
    parser = argparse.ArgumentParser(
        description="Smart File Organizer: Categorize, date-sort, deduplicate, and auto-organize files."
    )
    parser.add_argument(
        "-p", "--path",
        default=str(QUICK_FOLDERS.get("Downloads", Path.home() / "Downloads")),
        help="Path to folder to organize (defaults to your Downloads folder).",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["category", "date", "extension", "category_then_extension"],
        default="category",
        help="Organization mode: category (default), date, extension, or category_then_extension.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without moving files.",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Include subfolders recursively.",
    )
    parser.add_argument(
        "-d", "--duplicates",
        action="store_true",
        help="Calculate SHA-256 hashes to isolate duplicates into a Duplicates folder.",
    )
    parser.add_argument(
        "-c", "--conflict",
        choices=["rename", "skip", "overwrite"],
        default="rename",
        help="How to handle existing files at destination: rename (default), skip, overwrite.",
    )
    parser.add_argument(
        "-u", "--undo",
        action="store_true",
        help="Undo the last organize operation in the target folder.",
    )
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Run live auto-organizer watcher in background.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Do not print per-file progress in CLI.",
    )
    parser.add_argument(
        "-g", "--gui",
        action="store_true",
        help="Launch the Graphical User Interface.",
    )

    # If no arguments were given on the command line, default to GUI
    if len(sys.argv) == 1:
        from gui import launch_gui
        launch_gui()
    else:
        args = parser.parse_args()
        if args.gui:
            from gui import launch_gui
            launch_gui()
        else:
            run_cli(args)


if __name__ == "__main__":
    main()
