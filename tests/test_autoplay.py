import pytest

from rsvp_reader.autoplay import Autoplay, Ramp


def test_ramp_start_and_end():
    r = Ramp(max_wpm=600)
    assert r.start_wpm == 100  # 600 / 6
    assert r.wpm_at(0) == 100
    assert r.wpm_at(2500) == 350
    assert r.wpm_at(5000) == 600
    assert r.wpm_at(99_999) == 600
    assert r.wpm_at(-5) == 100


def test_ramp_respects_min_start_and_max():
    assert Ramp(max_wpm=120).start_wpm == 60
    assert Ramp(max_wpm=30).start_wpm == 30


def test_zero_duration_is_instant():
    assert Ramp(max_wpm=300, duration_ms=0).wpm_at(0) == 300


def test_autoplay_due_scales_with_word_count():
    a = Autoplay(Ramp(max_wpm=600, duration_ms=0), now_ms=1000)
    assert a.interval_ms(1000) == pytest.approx(100)
    assert a.interval_ms(1000, words=3) == pytest.approx(300)
    assert not a.due(1099, words=1)
    assert a.due(1100, words=1)
    assert not a.due(1299, words=3)
    assert a.due(1300, words=3)
    a.mark_advanced(1300)
    assert not a.due(1350)


def test_autoplay_ramps_from_start():
    a = Autoplay(Ramp(max_wpm=600), now_ms=0)
    assert a.wpm(0) == 100
    assert a.wpm(5000) == 600
