"""Application shell: window, navigation stack, settings ownership, key dispatch."""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

from rsvp_reader.browser_view import FolderView
from rsvp_reader.colors import apply_brightness
from rsvp_reader.progress import ProgressStore
from rsvp_reader.reader_view import ReaderView
from rsvp_reader.settings import Settings, SettingsStore, platform_default_font_family
from rsvp_reader.settings_panel import SettingsPanel
from rsvp_reader.theme import (
    BG,
    STATUS_BRIGHTNESS_FACTOR,
    UI_FONT_CANDIDATES,
    Theme,
    resolve_font_family,
)

WINDOWED_GEOMETRY = "1100x700"
SETTINGS_SAVE_DEBOUNCE_MS = 300
GEAR_GLYPH = "⚙"
REBUILD_KEYS = frozenset({"chunk_size", "sentence_mode"})


class App:
    def __init__(
        self,
        root: tk.Tk,
        *,
        book_root: Path,
        settings_store: SettingsStore,
        progress_store: ProgressStore,
        fullscreen: bool = True,
    ) -> None:
        self.root = root
        self.book_root = Path(book_root)
        self.settings_store = settings_store
        self.progress = progress_store
        self.installed_fonts = frozenset(tkfont.families(root))
        self.theme = Theme(resolve_font_family("", self.installed_fonts, UI_FONT_CANDIDATES))
        self._fonts: dict[tuple[str, int, str], tkfont.Font] = {}
        self._settings_save_job: str | None = None

        loaded = settings_store.load()
        self.settings: Settings = loaded.with_changes(
            font_family=resolve_font_family(
                loaded.font_family,
                self.installed_fonts,
                (platform_default_font_family(), *UI_FONT_CANDIDATES),
            )
        )

        root.title("RSVP Reader")
        root.configure(bg=BG)
        self.is_fullscreen = fullscreen
        if fullscreen:
            root.attributes("-fullscreen", True)
        else:
            root.geometry(WINDOWED_GEOMETRY)

        self.container = tk.Frame(root, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.nav_stack: list[tuple[str, Path]] = []
        self.view: FolderView | ReaderView | None = None
        self.settings_panel: SettingsPanel | None = None
        self._gear: tk.Label | None = None

        root.bind("<Escape>", lambda e: self.on_escape())
        root.bind("<Key>", self._on_key)
        root.protocol("WM_DELETE_WINDOW", self.quit)

        self.push_folder(self.book_root)

    # -- appearance -----------------------------------------------------------------
    def accent(self) -> str:
        return apply_brightness(self.settings.font_color, self.settings.brightness)

    def dim_accent(self) -> str:
        return apply_brightness(
            self.settings.font_color, self.settings.brightness * STATUS_BRIGHTNESS_FACTOR
        )

    def font(self, family: str, size: int, weight: str = "normal") -> tkfont.Font:
        """Cached named fonts; creating one per redraw would leak Tk font objects."""
        key = (family, size, weight)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(root=self.root, family=family, size=size, weight=weight)
        return self._fonts[key]

    def reader_font(self) -> tkfont.Font:
        return self.font(self.settings.font_family, self.settings.font_size, "bold")

    # -- navigation --------------------------------------------------------------------
    def push_folder(self, folder: Path) -> None:
        self.nav_stack.append(("folder", Path(folder)))
        self._show_top()

    def open_book(self, book_path: Path) -> None:
        self.nav_stack.append(("reader", Path(book_path)))
        self._show_top()

    def _show_top(self, focus: Path | None = None) -> None:
        """Render the top of the stack; `focus` preselects that entry in a folder view."""
        self.close_settings_panel()
        if self.view is not None:
            self.view.destroy()
            self.view = None
        kind, path = self.nav_stack[-1]
        if kind == "folder":
            self.view = FolderView(self, self.container, path, focus=focus)
        else:
            self.view = ReaderView(self, self.container, path)
        self._add_gear()

    def on_escape(self) -> None:
        if self.settings_panel is not None:
            self.close_settings_panel()
            return
        if len(self.nav_stack) > 1:
            _, left = self.nav_stack.pop()
            self._show_top(focus=left)
            return
        if self.is_fullscreen:
            self.root.attributes("-fullscreen", False)
            self.root.geometry(WINDOWED_GEOMETRY)
            self.is_fullscreen = False

    def quit(self) -> None:
        if self.view is not None:
            self.view.destroy()  # the reader view saves its position on destroy
            self.view = None
        self._flush_settings_save()
        self.progress.save()
        self.root.destroy()

    def _on_key(self, event: tk.Event) -> None:
        keysym = event.keysym
        if keysym == "Escape":
            return  # handled by the dedicated <Escape> binding
        if event.char == "q":
            self.quit()
            return
        if event.char == "s":
            self.toggle_settings_panel()
            return
        if self.settings_panel is not None:
            return  # keys belong to the panel's widgets while it is open
        if self.view is not None:
            self.view.on_key(event)

    # -- gear icon + settings panel -------------------------------------------------
    def _add_gear(self) -> None:
        self._gear = tk.Label(
            self.container,
            text=GEAR_GLYPH,
            font=self.theme.gear,
            fg=self.accent(),
            bg=BG,
            cursor="hand2",
        )
        self._gear.place(relx=1.0, rely=0.0, x=-16, y=10, anchor="ne")
        self._gear.bind("<Button-1>", lambda e: self.toggle_settings_panel())

    def toggle_settings_panel(self) -> None:
        if self.settings_panel is None:
            self.open_settings_panel()
        else:
            self.close_settings_panel()

    def open_settings_panel(self) -> None:
        if self.settings_panel is None:
            self.settings_panel = SettingsPanel(self, self.container)

    def close_settings_panel(self) -> None:
        if self.settings_panel is not None:
            self.settings_panel.destroy()
            self.settings_panel = None

    # -- settings ---------------------------------------------------------------------
    def update_settings(self, **changes: object) -> None:
        new = self.settings.with_changes(**changes)
        if new == self.settings:
            return
        rebuild = any(getattr(new, k) != getattr(self.settings, k) for k in REBUILD_KEYS)
        self.settings = new
        self._schedule_settings_save()
        if self.view is not None:
            self.view.on_settings_changed(rebuild=rebuild)
        if self._gear is not None:
            self._gear.configure(fg=self.accent())
        if self.settings_panel is not None:
            self.settings_panel.refresh()

    def _schedule_settings_save(self) -> None:
        if self._settings_save_job is not None:
            self.root.after_cancel(self._settings_save_job)
        self._settings_save_job = self.root.after(
            SETTINGS_SAVE_DEBOUNCE_MS, self._flush_settings_save
        )

    def _flush_settings_save(self) -> None:
        if self._settings_save_job is not None:
            self.root.after_cancel(self._settings_save_job)
            self._settings_save_job = None
        self.settings_store.save(self.settings)


def run_app(
    *,
    book_root: Path,
    settings_store: SettingsStore,
    progress_store: ProgressStore,
    fullscreen: bool,
) -> int:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"rsvp-reader: cannot open a display: {exc}", file=sys.stderr)
        return 1
    App(
        root,
        book_root=book_root,
        settings_store=settings_store,
        progress_store=progress_store,
        fullscreen=fullscreen,
    )
    root.mainloop()
    return 0
