from rsvpreader.session import ReadingSession

TEXT = "One two three four five six. Seven eight nine ten."


def test_navigation_bounds():
    s = ReadingSession(TEXT, sentence_mode=False, chunk_size=3)
    assert s.units == ["One two three", "four five six.", "Seven eight nine", "ten."]
    assert s.at_start and not s.at_end
    assert not s.back()
    assert s.advance() and s.index == 1
    s.last()
    assert s.at_end and not s.advance()
    s.first()
    assert s.index == 0


def test_progress_and_current():
    s = ReadingSession(TEXT, sentence_mode=False, chunk_size=3)
    assert s.current == "One two three"
    assert s.progress == 0.25
    s.last()
    assert s.progress == 1.0


def test_empty_book():
    s = ReadingSession("", sentence_mode=False, chunk_size=3)
    assert s.count == 0 and s.current == "" and s.progress == 0.0
    assert s.at_start and s.at_end
    assert not s.advance() and not s.back()
    s.rebuild(sentence_mode=True, chunk_size=1)
    assert s.index == 0


def test_offset_round_trip():
    s = ReadingSession(TEXT, sentence_mode=False, chunk_size=1)
    s.index = 4  # "five"
    off = s.char_offset
    t = ReadingSession(TEXT, sentence_mode=False, chunk_size=1)
    t.seek_offset(off)
    assert t.index == 4
    t.seek_offset(10_000)
    assert t.index == t.count - 1


def test_rebuild_never_skips_words():
    s = ReadingSession(TEXT, sentence_mode=False, chunk_size=1)
    s.index = 4  # "five", inside 3-chunk "four five six."
    s.rebuild(sentence_mode=False, chunk_size=3)
    assert s.current == "four five six."
    s.rebuild(sentence_mode=True, chunk_size=3)
    assert s.current == "One two three four five six."
    s.rebuild(sentence_mode=False, chunk_size=1)
    assert s.current == "One"


def test_rebuild_from_later_sentence():
    s = ReadingSession(TEXT, sentence_mode=True, chunk_size=3)
    s.advance()
    s.rebuild(sentence_mode=False, chunk_size=3)
    assert s.current == "Seven eight nine"
