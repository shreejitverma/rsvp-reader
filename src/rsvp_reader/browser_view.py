"""Folder browser: keyboard- and mouse-navigable list of subfolders and books."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

from rsvp_reader.library import Entry, display_path, list_entries
from rsvp_reader.theme import BG

if TYPE_CHECKING:
    from rsvp_reader.app import App

HINT = "Click or Enter: open   Up/Down: select   Esc: back   s: settings   q: quit"
LIST_TOP_MARGIN = 10
LIST_BOTTOM_MARGIN = 50
MIN_LIST_HEIGHT = 40


class FolderView:
    def __init__(self, app: App, parent: tk.Misc, folder: Path, focus: Path | None = None) -> None:
        self.app = app
        self.folder = folder
        self.entries: list[Entry] = list_entries(folder)
        self.selected = next((i for i, e in enumerate(self.entries) if e.path == focus), 0)
        theme = app.theme

        self.frame = tk.Frame(parent, bg=BG)
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)

        self.header = tk.Label(
            self.frame,
            text=display_path(folder, app.book_root),
            font=theme.header,
            fg=app.accent(),
            bg=BG,
        )
        self.header.pack(side="top", pady=(20, 4))
        self.separator = tk.Frame(self.frame, bg=app.accent(), height=2)
        self.separator.pack(side="top", fill="x", padx=40, pady=(0, 10))

        self.hint = tk.Label(self.frame, text=HINT, font=theme.hint, fg=app.dim_accent(), bg=BG)
        self.hint.place(relx=0.5, rely=0.97, anchor="center")

        self.list_canvas = tk.Canvas(self.frame, bg=BG, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.list_canvas, bg=BG)
        self.list_canvas.create_window(0, 0, window=self.inner, anchor="nw")

        self.labels: list[tk.Label] = []
        if not self.entries:
            tk.Label(
                self.inner, text="(empty folder)", font=theme.browser, fg=app.accent(), bg=BG
            ).pack(pady=10)
        for i, entry in enumerate(self.entries):
            prefix = "[Folder]" if entry.is_folder else "[Book]"
            label = tk.Label(
                self.inner,
                text=f"{prefix} {entry.name}",
                font=theme.browser,
                fg=app.accent(),
                bg=BG,
                cursor="hand2",
                padx=12,
                pady=2,
            )
            label.pack(pady=2)
            label.bind("<Button-1>", lambda e, i=i: self._open(i))
            self.labels.append(label)

        for widget in (self.list_canvas, self.inner, *self.labels):
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Button-4>", lambda e: self._scroll(-1))
            widget.bind("<Button-5>", lambda e: self._scroll(1))
        self.frame.bind("<Configure>", lambda e: self._relayout())
        self._highlight()

    # -- layout -----------------------------------------------------------------------
    def _relayout(self) -> None:
        self.inner.update_idletasks()
        content_w = self.inner.winfo_reqwidth()
        content_h = self.inner.winfo_reqheight()
        list_top = self.separator.winfo_y() + self.separator.winfo_height() + LIST_TOP_MARGIN
        available = max(MIN_LIST_HEIGHT, self.frame.winfo_height() - LIST_BOTTOM_MARGIN - list_top)
        canvas_h = min(content_h, available)
        self.list_canvas.configure(
            width=content_w, height=canvas_h, scrollregion=(0, 0, content_w, content_h)
        )
        self.list_canvas.place(relx=0.5, y=list_top + (available - canvas_h) // 2, anchor="n")
        self._ensure_visible()

    def _on_wheel(self, event: tk.Event) -> None:
        self._scroll(-1 if event.delta > 0 else 1)

    def _scroll(self, direction: int) -> None:
        self.list_canvas.yview_scroll(direction, "units")

    def _ensure_visible(self) -> None:
        if not self.labels:
            return
        label = self.labels[self.selected]
        content_h = max(1, self.inner.winfo_reqheight())
        view_h = self.list_canvas.winfo_height()
        top, bottom = label.winfo_y(), label.winfo_y() + label.winfo_reqheight()
        first, last = self.list_canvas.yview()
        view_top, view_bottom = first * content_h, last * content_h
        if top < view_top:
            self.list_canvas.yview_moveto(top / content_h)
        elif bottom > view_bottom and view_h > 0:
            self.list_canvas.yview_moveto((bottom - view_h) / content_h)

    def _highlight(self) -> None:
        accent = self.app.accent()
        for i, label in enumerate(self.labels):
            if i == self.selected:
                label.configure(fg=BG, bg=accent)
            else:
                label.configure(fg=accent, bg=BG)
        self._ensure_visible()

    # -- actions ------------------------------------------------------------------------
    def _open(self, index: int) -> None:
        entry = self.entries[index]
        if entry.is_folder:
            self.app.push_folder(entry.path)
        else:
            self.app.open_book(entry.path)

    def on_key(self, event: tk.Event) -> None:
        keysym = event.keysym
        if not self.entries:
            if keysym == "BackSpace":
                self.app.on_escape()
            return
        if keysym in ("Down", "j"):
            self.selected = (self.selected + 1) % len(self.entries)
            self._highlight()
        elif keysym in ("Up", "k"):
            self.selected = (self.selected - 1) % len(self.entries)
            self._highlight()
        elif keysym in ("Return", "KP_Enter", "space", "Right"):
            self._open(self.selected)
        elif keysym in ("BackSpace", "Left"):
            self.app.on_escape()

    def on_settings_changed(self, rebuild: bool) -> None:
        accent = self.app.accent()
        self.header.configure(fg=accent)
        self.separator.configure(bg=accent)
        self.hint.configure(fg=self.app.dim_accent())
        self._highlight()

    def destroy(self) -> None:
        self.frame.destroy()
