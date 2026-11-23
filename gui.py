"""
Modern Tkinter Graphical User Interface for File Organizer.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from organizer import FileOrganizer
from watcher import FolderWatcher
from config import QUICK_FOLDERS


class FileOrganizerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart File Organizer")
        self.root.geometry("820x680")
        self.root.minsize(720, 560)

        # State
        self.selected_path = tk.StringVar(value=str(QUICK_FOLDERS.get("Downloads", Path.home() / "Downloads")))
        self.mode_var = tk.StringVar(value="category")
        self.conflict_var = tk.StringVar(value="rename")
        self.dry_run_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=False)
        self.detect_duplicates_var = tk.BooleanVar(value=False)

        self.watcher: Optional[FolderWatcher] = None
        self.is_watching = False
        self._busy = False
        self._closing = False

        self._configure_styles()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Color Palette
        self.bg_color = "#f4f6f9"
        self.text_dark = "#1e293b"

        self.root.configure(bg=self.bg_color)

        self.style.configure(".", background=self.bg_color, font=("Segoe UI", 10))
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_dark)
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#0f172a")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 10), foreground="#64748b")
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=6)

    def _build_ui(self):
        main_container = ttk.Frame(self.root, padding=16)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header Banner
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header_frame, text="📁 Smart File Organizer", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header_frame,
            text="Organize messy folders into clean, structured categories with duplicate detection and safe undo.",
            style="SubHeader.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        # Target Folder Selection Card
        folder_card = ttk.LabelFrame(main_container, text=" Select Folder to Organize ", padding=12)
        folder_card.pack(fill=tk.X, pady=(0, 10))

        path_row = ttk.Frame(folder_card)
        path_row.pack(fill=tk.X, pady=(0, 8))

        path_entry = ttk.Entry(path_row, textvariable=self.selected_path, font=("Segoe UI", 10))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        browse_btn = ttk.Button(path_row, text="Browse...", command=self._browse_folder, style="Action.TButton")
        browse_btn.pack(side=tk.LEFT)

        # Quick access buttons
        quick_row = ttk.Frame(folder_card)
        quick_row.pack(fill=tk.X)
        ttk.Label(quick_row, text="Quick Shortcuts:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        for name, p in QUICK_FOLDERS.items():
            if p.exists():
                b = ttk.Button(
                    quick_row,
                    text=name,
                    command=lambda target=p: self.selected_path.set(str(target)),
                )
                b.pack(side=tk.LEFT, padx=3)

        # Organization Options Card
        options_card = ttk.LabelFrame(main_container, text=" Organization Settings ", padding=12)
        options_card.pack(fill=tk.X, pady=(0, 10))

        # Mode row
        mode_row = ttk.Frame(options_card)
        mode_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(mode_row, text="Sorting Mode:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 12))

        modes = [
            ("By Category (Images, Docs, etc.)", "category"),
            ("By Date (Year / Month)", "date"),
            ("By Extension (PDF, JPG, etc.)", "extension"),
            ("Category + Extension", "category_then_extension"),
        ]
        for label, val in modes:
            rb = ttk.Radiobutton(mode_row, text=label, value=val, variable=self.mode_var)
            rb.pack(side=tk.LEFT, padx=6)

        # Checkboxes row
        chk_row = ttk.Frame(options_card)
        chk_row.pack(fill=tk.X, pady=(0, 4))

        cb_dry = ttk.Checkbutton(chk_row, text="Dry Run (Preview Only)", variable=self.dry_run_var)
        cb_dry.pack(side=tk.LEFT, padx=(0, 16))

        cb_dup = ttk.Checkbutton(chk_row, text="Detect Duplicates (Move to Duplicates/)", variable=self.detect_duplicates_var)
        cb_dup.pack(side=tk.LEFT, padx=(0, 16))

        cb_sub = ttk.Checkbutton(chk_row, text="Include Subfolders (Recursive)", variable=self.recursive_var)
        cb_sub.pack(side=tk.LEFT, padx=(0, 16))

        # Conflict row
        conflict_row = ttk.Frame(options_card)
        conflict_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(conflict_row, text="If File Name Exists:").pack(side=tk.LEFT, padx=(0, 8))

        conflict_combo = ttk.Combobox(
            conflict_row,
            textvariable=self.conflict_var,
            values=["rename", "skip", "overwrite"],
            state="readonly",
            width=12,
        )
        conflict_combo.pack(side=tk.LEFT)
        ttk.Label(conflict_row, text="(rename = auto 'file (1).ext')", foreground="#64748b").pack(side=tk.LEFT, padx=8)

        # Action Buttons Card
        btn_bar = ttk.Frame(main_container)
        btn_bar.pack(fill=tk.X, pady=(0, 10))

        self.preview_btn = ttk.Button(btn_bar, text="🔍 Preview Changes", command=self._on_preview, style="Action.TButton")
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.organize_btn = ttk.Button(btn_bar, text="🚀 Organize Now", command=self._on_organize, style="Action.TButton")
        self.organize_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.undo_btn = ttk.Button(btn_bar, text="↩️ Undo Last Organize", command=self._on_undo, style="Action.TButton")
        self.undo_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.watch_btn = ttk.Button(btn_bar, text="👀 Start Auto-Watch", command=self._toggle_watcher, style="Action.TButton")
        self.watch_btn.pack(side=tk.RIGHT)

        # Progress bar & Status
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=tk.X, pady=(0, 6))

        self.progress_bar = ttk.Progressbar(status_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        self.status_lbl = ttk.Label(status_frame, text="Ready. Select a folder and click Organize Now.", foreground="#475569")
        self.status_lbl.pack(anchor=tk.W)

        # Log & Preview Text Area
        log_frame = ttk.LabelFrame(main_container, text=" Activity Log / Preview ", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#1e293b",
            relief="flat",
            padx=8,
            pady=8,
            state=tk.DISABLED,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Log tags for coloring
        self.log_text.tag_config("moved", foreground="#16a34a")       # Green
        self.log_text.tag_config("duplicate", foreground="#d97706")   # Amber
        self.log_text.tag_config("skipped", foreground="#64748b")     # Gray
        self.log_text.tag_config("error", foreground="#dc2626")       # Red
        self.log_text.tag_config("info", foreground="#2563eb")        # Blue
        self.log_text.tag_config("bold", font=("Consolas", 9, "bold"))

    def _safe_after(self, callback):
        """Schedule a callback on the Tk main loop if the window is still alive."""
        if self._closing:
            return
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in (self.preview_btn, self.organize_btn, self.undo_btn, self.watch_btn):
            btn.config(state=state)

    def _on_close(self):
        self._closing = True
        if self.watcher:
            try:
                self.watcher.stop()
            except Exception:
                pass
            self.watcher = None
            self.is_watching = False
        self.root.destroy()

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.selected_path.get())
        if folder:
            self.selected_path.set(folder)

    def _append_log(self, text: str, tag: str = ""):
        if self._closing:
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        if self._closing:
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _validate_path(self) -> Optional[Path]:
        raw = self.selected_path.get().strip()
        if not raw:
            messagebox.showerror("Invalid Directory", "Please select a folder to organize.")
            return None
        p = Path(raw)
        if not p.exists() or not p.is_dir():
            messagebox.showerror("Invalid Directory", f"The directory does not exist:\n{p}")
            return None
        return p

    def _snapshot_options(self) -> dict:
        """Read all Tkinter option variables safely on the main thread."""
        return {
            "mode": self.mode_var.get(),
            "recursive": self.recursive_var.get(),
            "conflict": self.conflict_var.get(),
            "detect_duplicates": self.detect_duplicates_var.get(),
            "dry_run": self.dry_run_var.get(),
        }

    def _on_preview(self):
        if self._busy:
            return
        target = self._validate_path()
        if not target:
            return

        opts = self._snapshot_options()
        self._set_busy(True)
        self._clear_log()
        self._append_log(f"--- PREVIEWING ORGANIZATION FOR: {target} ---", "bold")
        self.progress_bar["value"] = 0
        self.status_lbl.config(text="Scanning and planning...")

        def run_preview():
            try:
                organizer = FileOrganizer(target)
                planned = organizer.plan_organization(
                    mode=opts["mode"],
                    recursive=opts["recursive"],
                    conflict_resolution=opts["conflict"],
                    detect_duplicates=opts["detect_duplicates"],
                )
                self._safe_after(lambda: self._preview_completed(planned))
            except Exception as ex:
                err_msg = str(ex)
                self._safe_after(lambda: self._operation_failed("Preview failed", err_msg))

        threading.Thread(target=run_preview, daemon=True).start()

    def _preview_completed(self, planned: list):
        self._set_busy(False)
        self.progress_bar["value"] = 100

        if not planned:
            self._append_log("No files to organize! Everything is already organized.", "info")
            self.status_lbl.config(text="No files found to organize.")
            return

        counts = {"moved": 0, "duplicate": 0, "skipped": 0, "error": 0}
        for op in planned:
            counts[op.action] = counts.get(op.action, 0) + 1
            if op.action == "moved":
                self._append_log(f"[MOVE] {op.src.name} -> {op.dest.parent.name}/{op.dest.name} ({op.details})", "moved")
            elif op.action == "duplicate":
                self._append_log(f"[DUPLICATE] {op.src.name} -> Duplicates/{op.dest.name} ({op.details})", "duplicate")
            elif op.action == "skipped":
                self._append_log(f"[SKIP] {op.src.name} ({op.details})", "skipped")
            elif op.action == "error":
                self._append_log(f"[ERROR] {op.src.name} ({op.details})", "error")

        summary = (
            f"\nPreview Summary: {len(planned)} files scanned | {counts['moved']} will move | "
            f"{counts['duplicate']} duplicates | {counts['skipped']} skipped | {counts['error']} errors."
        )
        self._append_log(summary, "bold")
        self.status_lbl.config(
            text=f"Preview ready: {counts['moved']} to move, {counts['duplicate']} duplicates."
        )

    def _on_organize(self):
        if self._busy:
            return
        target = self._validate_path()
        if not target:
            return

        opts = self._snapshot_options()
        is_dry = opts["dry_run"]
        if not is_dry:
            confirm = messagebox.askyesno(
                "Confirm Organization",
                f"Are you sure you want to organize files in:\n{target}\n\n(You can undo this operation afterwards).",
            )
            if not confirm:
                return

        self._set_busy(True)
        self._clear_log()
        action_name = "SIMULATING (DRY RUN)" if is_dry else "ORGANIZING"
        self._append_log(f"--- {action_name} IN PROGRESS: {target} ---", "bold")
        self.progress_bar["value"] = 0

        def run_thread():
            try:
                organizer = FileOrganizer(target)

                def progress_cb(current, total, filename, action):
                    pct = int((current / total) * 100) if total > 0 else 100
                    msg = f"Processing ({current}/{total}): {filename}"
                    self._safe_after(lambda p=pct, m=msg: self._update_progress(p, m))

                result = organizer.execute_organization(
                    mode=opts["mode"],
                    recursive=opts["recursive"],
                    conflict_resolution=opts["conflict"],
                    detect_duplicates=opts["detect_duplicates"],
                    dry_run=is_dry,
                    progress_callback=progress_cb,
                )

                self._safe_after(lambda: self._organization_completed(result))
            except Exception as ex:
                err_msg = str(ex)
                self._safe_after(lambda: self._operation_failed("Organization failed", err_msg))

        threading.Thread(target=run_thread, daemon=True).start()

    def _update_progress(self, pct: int, status_text: str):
        if self._closing:
            return
        self.progress_bar["value"] = pct
        self.status_lbl.config(text=status_text)

    def _operation_failed(self, title: str, err_msg: str):
        self._set_busy(False)
        self._append_log(f"✗ {title}: {err_msg}", "error")
        self.status_lbl.config(text=f"{title}.")
        messagebox.showerror(title, err_msg)

    def _organization_completed(self, result: dict):
        self._set_busy(False)
        self.progress_bar["value"] = 100

        for op in result.get("operations", []):
            if op.action == "moved":
                self._append_log(f"✓ Moved: {op.src.name} -> {op.dest.parent.name}/{op.dest.name}", "moved")
            elif op.action == "duplicate":
                self._append_log(f"★ Duplicate: {op.src.name} -> Duplicates/{op.dest.name}", "duplicate")
            elif op.action == "skipped":
                self._append_log(f"- Skipped: {op.src.name} ({op.details})", "skipped")
            elif op.action == "error":
                self._append_log(f"✗ Error on {op.src.name}: {op.details}", "error")

        if result.get("history_warning"):
            self._append_log(result["history_warning"], "error")

        total = result["total"]
        moved = result["moved"]
        dups = result["duplicates"]
        errs = result["errors"]
        acted = moved + dups
        prefix = "[DRY RUN COMPLETE]" if result["dry_run"] else "[COMPLETE]"

        summary = f"\n{prefix} Finished! Processed: {total} | Moved: {moved} | Duplicates: {dups} | Errors: {errs}"
        self._append_log(summary, "bold")
        self.status_lbl.config(text=f"Completed. {moved} moved, {dups} duplicates isolated.")

        if not result["dry_run"] and acted > 0:
            messagebox.showinfo(
                "Success",
                f"Organization complete!\n{moved} file(s) moved and {dups} duplicate(s) isolated.",
            )

    def _on_undo(self):
        if self._busy:
            return
        target = self._validate_path()
        if not target:
            return

        confirm = messagebox.askyesno(
            "Confirm Undo",
            f"Are you sure you want to undo the last organize operation in:\n{target}?",
        )
        if not confirm:
            return

        self._set_busy(True)
        self._clear_log()
        self._append_log("--- UNDO IN PROGRESS ---", "bold")
        self.progress_bar["value"] = 0
        self.status_lbl.config(text="Reverting moves...")

        def run_undo():
            try:
                organizer = FileOrganizer(target)

                def progress_cb(current, total, filename, action):
                    pct = int((current / total) * 100) if total > 0 else 100
                    msg = f"Restoring ({current}/{total}): {filename}"
                    self._safe_after(lambda p=pct, m=msg: self._update_progress(p, m))

                restored, errors, logs = organizer.undo_last_operation(progress_callback=progress_cb)
                self._safe_after(lambda: self._undo_completed(restored, errors, logs))
            except Exception as ex:
                err_msg = str(ex)
                self._safe_after(lambda: self._operation_failed("Undo failed", err_msg))

        threading.Thread(target=run_undo, daemon=True).start()

    def _undo_completed(self, restored: int, errors: int, logs: list):
        self._set_busy(False)
        self.progress_bar["value"] = 100

        for line in logs:
            if any(marker in line for marker in ("Error", "Cannot restore", "Failed")):
                tag = "error"
            elif line.startswith("Note:") or line.startswith("No history") or line.startswith("History is empty"):
                tag = "info"
            else:
                tag = "moved"
            self._append_log(line, tag)

        summary = f"\nUndo Finished: {restored} files restored, {errors} errors."
        self._append_log(summary, "bold")
        self.status_lbl.config(text=summary.strip())
        messagebox.showinfo("Undo Completed", f"{restored} files restored back to their original locations ({errors} errors).")

    def _toggle_watcher(self):
        if self._busy:
            return
        if not self.is_watching:
            target = self._validate_path()
            if not target:
                return

            opts = self._snapshot_options()
            self.watcher = FolderWatcher(
                target,
                mode=opts["mode"],
                conflict_resolution=opts["conflict"],
                detect_duplicates=opts["detect_duplicates"],
                on_event=lambda msg: self._safe_after(lambda m=msg: self._append_log(f"[Auto-Watch] {m}", "info")),
            )
            self.watcher.start()
            self.is_watching = True
            self.watch_btn.config(text="⏹ Stop Auto-Watch")
            self.status_lbl.config(text=f"Auto-watching active for {target.name}...")
            self._append_log(f"Auto-watcher active for: {target}. New downloads will be organized automatically.", "info")
        else:
            if self.watcher:
                self.watcher.stop()
                self.watcher = None
            self.is_watching = False
            self.watch_btn.config(text="👀 Start Auto-Watch")
            self.status_lbl.config(text="Auto-watcher stopped.")
            self._append_log("Auto-watcher stopped.", "info")


def launch_gui():
    root = tk.Tk()
    FileOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
