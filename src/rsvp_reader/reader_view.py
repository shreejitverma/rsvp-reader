"""Reader view: center-anchored pivot display, sentence mode, autoplay and navigation."""

from __future__ import annotations

import string
import time
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

from rsvp_reader.autoplay import Autoplay, Ramp
from rsvp_reader.layout import flow_positions, pivot_box
from rsvp_reader.pivot import split_for_pivot
from rsvp_reader.session import ReadingSession
from rsvp_reader.text import load_book_text, word_count
from rsvp_reader.theme import BG, PIVOT_FG

if TYPE_CHECKING:
    from rsvp_reader.app import App

HOLD_TO_AUTOPLAY_MS = 2000
HOLD_TO_SETTINGS_MS = 3000
AUTOPLAY_TICK_MS = 40
PROGRESS_SAVE_DEBOUNCE_MS = 1000
WPM_KEY_STEP = 10
WORD_SPACING_REDUCTION = 6  # px trimmed from the natural space width between words
MIN_WORD_SPACING = 2
SENTENCE_WRAP_FRAC = 0.8
# Probe set for the fixed pivot-box width: the widest glyph the font renders.
WIDTH_PROBE_CHARS = string.ascii_letters


def _now_ms() -> float:
    return time.monotonic() * 1000.0


class ReaderView:
    def __init__(self, app: App, parent: tk.Misc, book_path: Path) -> None:
        self.app = app
        self.book_path = book_path
        self.error: str | None = None
        try:
            text = load_book_text(book_path)
        except OSError as exc:
            text = ""
            self.error = f"Cannot read file: {exc.strerror or exc}"
        settings = app.settings
        self.session = ReadingSession(
            text, sentence_mode=settings.sentence_mode, chunk_size=settings.chunk_size
        )
        self.session.seek_offset(app.progress.get(book_path))

        self.canvas = tk.Canvas(parent, bg=BG, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.status = tk.Label(parent, text="", font=app.theme.status, fg=app.dim_accent(), bg=BG)
        self.status.place(relx=0.5, rely=0.97, anchor="center")

        self._box_width_cache: dict[str, int] = {}
        self._hold_job: str | None = None
        self._settings_hold_job: str | None = None
        self._settings_triggered = False
        self._stopped_autoplay_on_press = False
        self._autoplay: Autoplay | None = None
        self._autoplay_job: str | None = None
        self._save_job: str | None = None

        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._on_left_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        # Button-2 is the secondary button on macOS Tk, Button-3 elsewhere.
        for button in ("2", "3"):
            self.canvas.bind(f"<ButtonPress-{button}>", self._on_right_press)
            self.canvas.bind(f"<ButtonRelease-{button}>", self._on_right_release)
        self.redraw()

    # -- drawing ---------------------------------------------------------------------
    @property
    def autoplay_active(self) -> bool:
        return self._autoplay is not None

    def _fixed_box_width(self) -> int:
        font = self.app.reader_font()
        key = str(font)
        if key not in self._box_width_cache:
            self._box_width_cache[key] = max(font.measure(c) for c in WIDTH_PROBE_CHARS)
        return self._box_width_cache[key]

    def redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        center_x, center_y = width // 2, height // 2
        accent = self.app.accent()
        font = self.app.reader_font()
        session = self.session

        if session.count == 0:
            canvas.create_text(
                center_x,
                center_y,
                text="(no readable text in this file)",
                font=self.app.theme.browser,
                fill=accent,
                anchor="center",
            )
        elif self.app.settings.sentence_mode:
            canvas.create_text(
                center_x,
                center_y,
                text=session.current,
                font=font,
                fill=accent,
                anchor="center",
                width=int(width * SENTENCE_WRAP_FRAC),
                justify="center",
            )
        else:
            self._draw_pivot_chunk(session.current, center_x, center_y, accent)
        self._update_status()

    def _draw_pivot_chunk(self, chunk: str, center_x: int, center_y: int, accent: str) -> None:
        canvas = self.canvas
        font = self.app.reader_font()
        before, letter, after = split_for_pivot(chunk)
        if letter is None:
            canvas.create_text(
                center_x, center_y, text=chunk, font=font, fill=accent, anchor="center"
            )
            return

        text_h = font.metrics("ascent") + font.metrics("descent")
        box = pivot_box(
            center_x=center_x,
            center_y=center_y,
            text_height=text_h,
            inner_width=self._fixed_box_width(),
        )
        canvas.create_line(*box.tick_top, fill=accent, width=2)
        canvas.create_line(*box.tick_bottom, fill=accent, width=2)
        canvas.create_rectangle(
            box.left, box.top, box.right, box.bottom, fill=accent, outline=accent
        )
        canvas.create_text(
            center_x, center_y, text=letter, font=font, fill=PIVOT_FG, anchor="center"
        )

        space_w = max(font.measure(" ") - WORD_SPACING_REDUCTION, MIN_WORD_SPACING)
        runs = (
            (before.split(" ") if before else [], box.left, True),
            (after.split(" ") if after else [], box.right, False),
        )
        for words, edge, anchor_right in runs:
            for x, word in flow_positions(words, font.measure, space_w, edge, anchor_right):
                canvas.create_text(x, box.text_top, text=word, font=font, fill=accent, anchor="nw")

    def _update_status(self) -> None:
        if self.error:
            self.status.configure(
                text=f"{self.book_path.name} | {self.error}", fg=self.app.accent()
            )
            return
        session = self.session
        label = "Sentence" if self.app.settings.sentence_mode else "Chunk"
        parts = [
            self.book_path.name,
            f"{label} {session.index + 1} / {session.count}",
            f"{session.progress * 100:.0f}%",
        ]
        if self._autoplay is not None:
            wpm = self._autoplay.wpm(_now_ms())
            parts.append(f"~{wpm:.0f} WPM (max {self.app.settings.wpm})")
        self.status.configure(text=" | ".join(parts), fg=self.app.dim_accent())

    # -- navigation -----------------------------------------------------------------
    def step(self, forward: bool) -> bool:
        moved = self.session.advance() if forward else self.session.back()
        if moved:
            self.redraw()
            self._schedule_progress_save()
        return moved

    def jump(self, to_end: bool) -> None:
        if to_end:
            self.session.last()
        else:
            self.session.first()
        self.redraw()
        self._schedule_progress_save()

    def _schedule_progress_save(self) -> None:
        if self._save_job is not None:
            self.app.root.after_cancel(self._save_job)
        self._save_job = self.app.root.after(PROGRESS_SAVE_DEBOUNCE_MS, self.save_progress)

    def save_progress(self) -> None:
        if self._save_job is not None:
            self.app.root.after_cancel(self._save_job)
            self._save_job = None
        if self.error is None and self.session.count:
            self.app.progress.set(self.book_path, self.session.char_offset)
            self.app.progress.save()

    # -- autoplay --------------------------------------------------------------------
    def start_autoplay(self) -> None:
        if self._autoplay is not None or self.session.at_end:
            return
        now = _now_ms()
        self._autoplay = Autoplay(Ramp(self.app.settings.wpm), now)
        self.step(True)
        self._autoplay.mark_advanced(now)
        self._autoplay_job = self.app.root.after(AUTOPLAY_TICK_MS, self._autoplay_tick)

    def stop_autoplay(self) -> None:
        if self._autoplay_job is not None:
            self.app.root.after_cancel(self._autoplay_job)
            self._autoplay_job = None
        if self._autoplay is not None:
            self._autoplay = None
            self.redraw()

    def toggle_autoplay(self) -> None:
        if self._autoplay is None:
            self.start_autoplay()
        else:
            self.stop_autoplay()

    def _autoplay_tick(self) -> None:
        self._autoplay_job = None
        player = self._autoplay
        if player is None:
            return
        now = _now_ms()
        if player.due(now, word_count(self.session.current)):
            player.mark_advanced(now)
            if not self.step(True):
                self.stop_autoplay()
                return
        else:
            self._update_status()  # keeps the ramped WPM readout live
        self._autoplay_job = self.app.root.after(AUTOPLAY_TICK_MS, self._autoplay_tick)

    # -- mouse -------------------------------------------------------------------------
    def _cancel(self, job_attr: str) -> None:
        job = getattr(self, job_attr)
        if job is not None:
            self.app.root.after_cancel(job)
            setattr(self, job_attr, None)

    def _on_left_press(self, event: tk.Event) -> None:
        self._stopped_autoplay_on_press = self._autoplay is not None
        self.stop_autoplay()
        self._cancel("_hold_job")
        self._hold_job = self.app.root.after(HOLD_TO_AUTOPLAY_MS, self._start_autoplay_from_hold)

    def _start_autoplay_from_hold(self) -> None:
        self._hold_job = None
        self.start_autoplay()

    def _on_left_release(self, event: tk.Event) -> None:
        held_into_autoplay = self._hold_job is None and self._autoplay is not None
        self._cancel("_hold_job")
        if held_into_autoplay:
            self.stop_autoplay()
        elif not self._stopped_autoplay_on_press:
            self.step(True)
        self._stopped_autoplay_on_press = False

    def _on_right_press(self, event: tk.Event) -> None:
        self._settings_triggered = False
        self._cancel("_settings_hold_job")
        self._settings_hold_job = self.app.root.after(
            HOLD_TO_SETTINGS_MS, self._open_settings_from_hold
        )

    def _open_settings_from_hold(self) -> None:
        self._settings_hold_job = None
        self._settings_triggered = True
        self.app.open_settings_panel()

    def _on_right_release(self, event: tk.Event) -> None:
        self._cancel("_settings_hold_job")
        if not self._settings_triggered:
            self.step(False)

    # -- keyboard ----------------------------------------------------------------------
    def on_key(self, event: tk.Event) -> None:
        keysym = event.keysym
        if keysym in ("Right", "space"):
            self.stop_autoplay()
            self.step(True)
        elif keysym == "Left":
            self.stop_autoplay()
            self.step(False)
        elif keysym == "Home":
            self.stop_autoplay()
            self.jump(to_end=False)
        elif keysym == "End":
            self.stop_autoplay()
            self.jump(to_end=True)
        elif keysym == "p":
            self.toggle_autoplay()
        elif keysym == "Up":
            self.app.update_settings(wpm=self.app.settings.wpm + WPM_KEY_STEP)
        elif keysym == "Down":
            self.app.update_settings(wpm=self.app.settings.wpm - WPM_KEY_STEP)

    # -- lifecycle ----------------------------------------------------------------------
    def on_settings_changed(self, rebuild: bool) -> None:
        if rebuild:
            settings = self.app.settings
            self.session.rebuild(
                sentence_mode=settings.sentence_mode, chunk_size=settings.chunk_size
            )
            self._schedule_progress_save()
        self.redraw()

    def destroy(self) -> None:
        self.stop_autoplay()
        self._cancel("_hold_job")
        self._cancel("_settings_hold_job")
        self.save_progress()
        self.status.destroy()
        self.canvas.destroy()
