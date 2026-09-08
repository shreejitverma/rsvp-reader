"""Settings overlay panel (gear icon / hold right-click / `s`)."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser
from typing import TYPE_CHECKING

from rsvp_reader.settings import BRIGHTNESS_RANGE, CHUNK_SIZES, FONT_SIZE_RANGE, WPM_RANGE
from rsvp_reader.theme import PANEL_BG, PANEL_FG, PANEL_TROUGH, available_reader_fonts

if TYPE_CHECKING:
    from rsvp_reader.app import App

PANEL_WIDTH = 340


class SettingsPanel:
    def __init__(self, app: App, parent: tk.Misc) -> None:
        self.app = app
        theme = app.theme
        settings = app.settings

        self.frame = tk.Frame(
            parent, bg=PANEL_BG, highlightbackground=app.accent(), highlightthickness=2
        )
        self.frame.place(relx=1.0, rely=0.0, x=-10, y=54, anchor="ne", width=PANEL_WIDTH)
        self._labels: list[tk.Label] = []

        def row(text: str) -> tk.Frame:
            r = tk.Frame(self.frame, bg=PANEL_BG)
            r.pack(fill="x", padx=12, pady=(10, 0))
            label = tk.Label(
                r, text=text, font=theme.panel_label, fg=app.accent(), bg=PANEL_BG, anchor="w"
            )
            label.pack(fill="x")
            self._labels.append(label)
            return r

        def scale(parent_row: tk.Frame, lo: int, hi: int, value: int, key: str) -> tk.Scale:
            var = tk.IntVar(value=value)
            widget = tk.Scale(
                parent_row,
                from_=lo,
                to=hi,
                orient="horizontal",
                variable=var,
                bg=PANEL_BG,
                fg=PANEL_FG,
                troughcolor=PANEL_TROUGH,
                highlightthickness=0,
                command=lambda v: app.update_settings(**{key: int(float(v))}),
            )
            widget.pack(fill="x")
            return widget

        chunk_row = row("Chunk size")
        self.chunk_var = tk.IntVar(value=settings.chunk_size)
        for size in CHUNK_SIZES:
            tk.Radiobutton(
                chunk_row,
                text=f"{size} word{'s' if size > 1 else ''}",
                variable=self.chunk_var,
                value=size,
                font=theme.panel,
                fg=PANEL_FG,
                bg=PANEL_BG,
                selectcolor=PANEL_TROUGH,
                activebackground=PANEL_BG,
                command=lambda: app.update_settings(chunk_size=self.chunk_var.get()),
            ).pack(side="left", padx=(0, 10))

        self.wpm_scale = scale(row("Autoplay max speed (WPM)"), *WPM_RANGE, settings.wpm, "wpm")

        font_row = row("Font")
        self.font_var = tk.StringVar(value=settings.font_family)
        choices = available_reader_fonts(app.installed_fonts, settings.font_family)
        menu = tk.OptionMenu(
            font_row,
            self.font_var,
            *choices,
            command=lambda v: app.update_settings(font_family=v),
        )
        menu.configure(font=theme.panel, bg=PANEL_BG, fg=PANEL_FG, highlightthickness=0)
        menu["menu"].configure(font=theme.panel)
        menu.pack(fill="x")

        self.size_scale = scale(row("Font size"), *FONT_SIZE_RANGE, settings.font_size, "font_size")
        self.bright_scale = scale(
            row("Brightness"), *BRIGHTNESS_RANGE, settings.brightness, "brightness"
        )

        color_row = tk.Frame(row("Font color"), bg=PANEL_BG)
        color_row.pack(fill="x", pady=(4, 0))
        self.swatch = tk.Label(
            color_row, text="  ", bg=settings.font_color, width=4, relief="ridge", bd=2
        )
        self.swatch.pack(side="left", padx=(0, 8))
        pick = tk.Label(
            color_row,
            text="Choose color...",
            font=theme.panel,
            fg="black",
            bg="#DDDDDD",
            cursor="hand2",
            padx=8,
            pady=3,
        )
        pick.pack(side="left", fill="x", expand=True)
        pick.bind("<Button-1>", lambda e: self.pick_color())

        self.sentence_var = tk.BooleanVar(value=settings.sentence_mode)
        tk.Checkbutton(
            row("Sentence mode"),
            text="Show full sentences, no pivot box",
            variable=self.sentence_var,
            font=theme.panel,
            fg=PANEL_FG,
            bg=PANEL_BG,
            selectcolor=PANEL_TROUGH,
            activebackground=PANEL_BG,
            command=lambda: app.update_settings(sentence_mode=self.sentence_var.get()),
        ).pack(fill="x")

        self.close_btn = tk.Label(
            self.frame, text="Close", font=theme.panel, fg="black", bg=app.accent(), cursor="hand2"
        )
        self.close_btn.pack(fill="x", padx=12, pady=12)
        self.close_btn.bind("<Button-1>", lambda e: app.close_settings_panel())

    def pick_color(self) -> None:
        result = colorchooser.askcolor(
            color=self.app.settings.font_color, title="Choose RSVP text color", parent=self.app.root
        )
        if result and result[1]:
            self.app.update_settings(font_color=result[1])

    def refresh(self) -> None:
        """Reflect externally changed settings (keyboard WPM, color picker) in the widgets."""
        settings = self.app.settings
        accent = self.app.accent()
        self.wpm_scale.set(settings.wpm)
        self.swatch.configure(bg=settings.font_color)
        self.frame.configure(highlightbackground=accent)
        self.close_btn.configure(bg=accent)
        for label in self._labels:
            label.configure(fg=accent)

    def destroy(self) -> None:
        self.frame.destroy()
