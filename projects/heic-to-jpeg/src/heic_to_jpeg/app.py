from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, __version__
from .converter import ConvertResult, collect_heic_files, convert_many

HEIC_FILETYPES = [("HEIC / HEIF photos", "*.heic *.heif *.hif *.HEIC *.HEIF *.HIF"), ("All files", "*.*")]


class HeicToJpegApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {__version__}")
        self.geometry("820x560")
        self.minsize(680, 460)

        self.files: list[Path] = []
        self.output_dir: Path | None = None
        self.quality = tk.IntVar(value=92)
        self.conflict = tk.StringVar(value="rename")
        self.output_mode = tk.StringVar(value="same")
        self.status_text = tk.StringVar(value="Add HEIC photos to get started.")
        self._events: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self._apply_icon()
        self.after(100, self._drain_events)

    # ---- UI --------------------------------------------------------------

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        toolbar = ttk.Frame(root)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Add photos…", command=self.add_files).pack(side="left")
        ttk.Button(toolbar, text="Add folder…", command=self.add_folder).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Remove selected", command=self.remove_selected).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Clear list", command=self.clear_files).pack(side="left", padx=(6, 0))

        columns = ("name", "folder", "status")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="Photo")
        self.tree.heading("folder", text="Folder")
        self.tree.heading("status", text="Status")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("folder", width=360, anchor="w")
        self.tree.column("status", width=160, anchor="w")
        scroll = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="top", fill="both", expand=True, pady=(10, 0))
        scroll.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.tree.tag_configure("failed", foreground="#b00020")
        self.tree.tag_configure("converted", foreground="#1b6e2b")
        self.tree.tag_configure("skipped", foreground="#7a6a00")

        options = ttk.LabelFrame(root, text="Output", padding=10)
        options.pack(fill="x", pady=(10, 0))

        ttk.Radiobutton(
            options, text="Save JPEGs next to the original photos", variable=self.output_mode, value="same",
            command=self._refresh_output_label,
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(
            options, text="Save JPEGs to this folder:", variable=self.output_mode, value="folder",
            command=self._refresh_output_label,
        ).grid(row=1, column=0, sticky="w")
        self.output_label = ttk.Label(options, text="(no folder chosen)", foreground="#555")
        self.output_label.grid(row=1, column=1, sticky="w", padx=(6, 6))
        ttk.Button(options, text="Choose…", command=self.choose_output).grid(row=1, column=2, sticky="e")

        ttk.Label(options, text="JPEG quality:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        quality_row = ttk.Frame(options)
        quality_row.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Scale(quality_row, from_=60, to=100, variable=self.quality, orient="horizontal",
                  command=lambda _v: self.quality_value.configure(text=f"{self.quality.get()}")).pack(side="left", fill="x", expand=True)
        self.quality_value = ttk.Label(quality_row, text="92", width=4)
        self.quality_value.pack(side="left", padx=(6, 0))

        ttk.Label(options, text="If a JPEG already exists:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        conflict_row = ttk.Frame(options)
        conflict_row.grid(row=3, column=1, columnspan=2, sticky="w", pady=(8, 0))
        for label, value in (("Keep both (rename)", "rename"), ("Skip", "skip"), ("Replace", "overwrite")):
            ttk.Radiobutton(conflict_row, text=label, variable=self.conflict, value=value).pack(side="left", padx=(0, 12))
        options.columnconfigure(1, weight=1)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(10, 0))
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(fill="x")
        status_row = ttk.Frame(bottom)
        status_row.pack(fill="x", pady=(6, 0))
        ttk.Label(status_row, textvariable=self.status_text).pack(side="left")
        self.open_button = ttk.Button(status_row, text="Open output folder", command=self.open_output, state="disabled")
        self.open_button.pack(side="right", padx=(6, 0))
        self.cancel_button = ttk.Button(status_row, text="Cancel", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right", padx=(6, 0))
        self.convert_button = ttk.Button(status_row, text="Convert to JPEG", command=self.start, state="disabled")
        self.convert_button.pack(side="right")

    def _apply_icon(self) -> None:
        icon = _resource_path("icon.ico")
        if icon.exists() and sys.platform.startswith("win"):
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

    # ---- file list -------------------------------------------------------

    def add_files(self) -> None:
        chosen = filedialog.askopenfilenames(title="Choose HEIC photos", filetypes=HEIC_FILETYPES)
        if chosen:
            self._add_paths([Path(p) for p in chosen])

    def add_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose a folder of HEIC photos", mustexist=True)
        if chosen:
            self._add_paths([Path(chosen)])

    def _add_paths(self, paths: list[Path]) -> None:
        new_files = [f for f in collect_heic_files(paths) if f not in self.files]
        if not new_files and paths:
            self.status_text.set("No HEIC or HEIF photos found in that selection.")
        for path in new_files:
            self.files.append(path)
            self.tree.insert("", "end", iid=str(path), values=(path.name, str(path.parent), "Ready"))
        self._refresh_counts()

    def remove_selected(self) -> None:
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.files = [f for f in self.files if str(f) != iid]
        self._refresh_counts()

    def clear_files(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.progress["value"] = 0
        self._refresh_counts()

    def _refresh_counts(self) -> None:
        count = len(self.files)
        self.convert_button.configure(state="normal" if count and not self._running() else "disabled")
        if count:
            self.status_text.set(f"{count} photo{'s' if count != 1 else ''} ready to convert.")
        else:
            self.status_text.set("Add HEIC photos to get started.")

    # ---- output ----------------------------------------------------------

    def choose_output(self) -> None:
        chosen = filedialog.askdirectory(title="Choose where to save JPEGs")
        if chosen:
            self.output_dir = Path(chosen)
            self.output_mode.set("folder")
            self._refresh_output_label()

    def _refresh_output_label(self) -> None:
        if self.output_dir:
            self.output_label.configure(text=str(self.output_dir), foreground="#000")
        else:
            self.output_label.configure(text="(no folder chosen)", foreground="#555")

    def _effective_output(self) -> Path | None:
        if self.output_mode.get() == "folder":
            if not self.output_dir:
                messagebox.showinfo(APP_NAME, "Choose an output folder first, or save next to the originals.")
                return None
            return self.output_dir
        return None

    def open_output(self) -> None:
        target = self.output_dir if self.output_mode.get() == "folder" and self.output_dir else (
            self.files[0].parent if self.files else None
        )
        if target:
            _open_in_file_manager(target)

    # ---- conversion ------------------------------------------------------

    def _running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def start(self) -> None:
        if self._running() or not self.files:
            return
        if self.output_mode.get() == "folder" and not self.output_dir:
            self._effective_output()
            return
        output_dir = self.output_dir if self.output_mode.get() == "folder" else None

        self._stop.clear()
        self.progress.configure(maximum=len(self.files), value=0)
        for iid in self.tree.get_children():
            self.tree.item(iid, tags=())
            self.tree.set(iid, "status", "Waiting…")
        self.convert_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.open_button.configure(state="disabled")
        self.status_text.set("Converting…")

        files = list(self.files)
        quality = int(self.quality.get())
        conflict = self.conflict.get()

        def work() -> None:
            results = convert_many(
                files,
                output_dir=output_dir,
                quality=quality,
                on_conflict=conflict,  # type: ignore[arg-type]
                progress=lambda done, total, result: self._events.put(("progress", done, total, result)),
                should_stop=self._stop.is_set,
            )
            self._events.put(("done", results))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def cancel(self) -> None:
        self._stop.set()
        self.status_text.set("Cancelling after the current photo…")

    def _drain_events(self) -> None:
        try:
            while True:
                event = self._events.get_nowait()
                if event[0] == "progress":
                    _, done, total, result = event
                    self._show_result(result)
                    self.progress["value"] = done
                    self.status_text.set(f"Converting… {done} of {total}")
                elif event[0] == "done":
                    self._finish(event[1])
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _show_result(self, result: ConvertResult) -> None:
        iid = str(result.source)
        if not self.tree.exists(iid):
            return
        if result.status == "converted":
            text = f"Saved → {result.destination.name}"
        elif result.status == "skipped":
            text = "Skipped (JPEG already exists)"
        else:
            text = f"Failed: {result.error}"
        self.tree.set(iid, "status", text)
        self.tree.item(iid, tags=(result.status,))

    def _finish(self, results: list[ConvertResult]) -> None:
        converted = sum(r.status == "converted" for r in results)
        skipped = sum(r.status == "skipped" for r in results)
        failed = sum(r.status == "failed" for r in results)
        cancelled = len(results) < len(self.files)
        summary = f"{converted} converted, {skipped} skipped, {failed} failed"
        if cancelled:
            summary = "Cancelled — " + summary
        self.status_text.set(summary + ".")
        self.cancel_button.configure(state="disabled")
        self.convert_button.configure(state="normal")
        self.open_button.configure(state="normal" if converted else "disabled")
        if failed:
            messagebox.showwarning(
                APP_NAME,
                f"{failed} photo{'s' if failed != 1 else ''} could not be converted. "
                "See the Status column for details. The other photos were saved.",
            )


def _resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _open_in_file_manager(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])  # noqa: S603,S607
    else:
        subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607


def main() -> None:
    app = HeicToJpegApp()
    app.mainloop()
