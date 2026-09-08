from pathlib import Path

from rsvp_reader.settings import Settings, SettingsStore, platform_default_font_family


def test_defaults_are_sane():
    s = Settings()
    assert s.sanitized() == s


def test_from_dict_clamps_and_ignores_unknown():
    s = Settings.from_dict(
        {
            "chunk_size": 7,
            "wpm": "9000",
            "font_size": 3,
            "brightness": -1,
            "font_color": "zzz",
            "sentence_mode": 1,
            "font_family": None,
            "bogus": True,
        }
    )
    assert s == Settings(
        chunk_size=3,
        wpm=1200,
        font_size=16,
        brightness=10,
        font_color="#FF4500",
        sentence_mode=True,
        font_family="",
    )


def test_from_dict_none_and_bad_types():
    assert Settings.from_dict(None) == Settings()
    assert Settings.from_dict({"chunk_size": "x", "wpm": None}) == Settings()


def test_with_changes_sanitizes():
    assert Settings().with_changes(wpm=10).wpm == 60
    assert Settings().with_changes(font_color="#ca8435").font_color == "#CA8435"


def test_store_round_trip(tmp_path: Path):
    store = SettingsStore(tmp_path / "cfg" / "settings.json")
    assert store.load() == Settings()
    assert store.save(Settings(wpm=352, font_size=41, chunk_size=1))
    loaded = store.load()
    assert (loaded.wpm, loaded.font_size, loaded.chunk_size) == (352, 41, 1)


def test_store_ignores_corrupt_file(tmp_path: Path):
    p = tmp_path / "settings.json"
    p.write_text("{not json", encoding="utf-8")
    assert SettingsStore(p).load() == Settings()
    p.write_text("[1, 2]", encoding="utf-8")
    assert SettingsStore(p).load() == Settings()


def test_store_migrates_legacy(tmp_path: Path):
    legacy = tmp_path / "rsvp_settings.json"
    legacy.write_text('{"wpm": 352, "font_color": "#ca8435"}', encoding="utf-8")
    store = SettingsStore(tmp_path / "new" / "settings.json", legacy_paths=(legacy,))
    s = store.load()
    assert (s.wpm, s.font_color) == (352, "#CA8435")
    store.save(s.with_changes(wpm=400))
    assert store.load().wpm == 400  # new path wins once written


def test_store_save_failure_returns_false(tmp_path: Path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert not SettingsStore(blocker / "settings.json").save(Settings())


def test_platform_default_font_family():
    assert platform_default_font_family("darwin") == "Menlo"
    assert platform_default_font_family("win32") == "Consolas"
    assert platform_default_font_family("linux") == "DejaVu Sans Mono"
