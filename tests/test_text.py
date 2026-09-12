from pathlib import Path

import pytest

from rsvpreader.text import (
    Word,
    build_chunks,
    build_sentences,
    decode_text,
    ends_chunk,
    ends_sentence,
    load_book_text,
    normalize_text,
    tokenize,
    word_count,
)


class TestNormalize:
    def test_collapses_whitespace_and_newlines(self):
        assert normalize_text("a\r\nb \n\n  c\td") == "a b c d"

    def test_glued_comma_before_letter_gets_space(self):
        assert normalize_text("forth,The") == "forth, The"

    def test_thousands_separator_untouched(self):
        assert normalize_text("costs 1,000 units") == "costs 1,000 units"

    def test_glued_period_before_capital_gets_space(self):
        assert normalize_text("end.Next one") == "end. Next one"

    def test_decimal_untouched(self):
        assert normalize_text("one year. 0.99365 = 00.") == "one year. 0.99365 = 00."

    def test_lowercase_abbreviations_untouched(self):
        assert normalize_text("at 7.25p.m., e.g. now") == "at 7.25p.m., e.g. now"

    def test_uppercase_abbreviation_untouched(self):
        assert normalize_text("the U.S.A. is") == "the U.S.A. is"

    def test_ellipsis_before_capital(self):
        assert normalize_text("wait...Then") == "wait... Then"

    def test_glued_question_and_exclamation(self):
        assert normalize_text("what?Then who!Me") == "what? Then who! Me"

    def test_straight_quote_parity(self):
        assert normalize_text('it."Believe me,"he said') == 'it. "Believe me," he said'

    def test_closing_straight_quote_keeps_following_punctuation_tight(self):
        assert normalize_text('"hi", she said') == '"hi", she said'

    def test_space_before_closing_quote_removed(self):
        assert normalize_text('"hi " and') == '"hi" and'

    def test_curly_quotes(self):
        assert normalize_text("said“Go”now") == "said “Go” now"

    def test_first_quote_in_text_opens_by_parity(self):
        assert normalize_text('done."Next') == 'done. "Next'

    def test_closing_quote_after_period(self):
        assert normalize_text('"All done."Next') == '"All done." Next'

    def test_empty(self):
        assert normalize_text("   \n ") == ""


class TestTokenize:
    def test_marks_opening_quote(self):
        assert tokenize('say "hi" now') == [
            Word("say"),
            Word('"hi"', opens_quote=True),
            Word("now"),
        ]

    def test_lone_opening_quote_glued_to_next_word(self):
        assert tokenize('a " b') == [Word("a"), Word('"b', opens_quote=True)]

    def test_trailing_lone_quote_dropped(self):
        assert tokenize('a "') == [Word("a")]

    def test_standalone_dash_glued_to_previous_word_with_space(self):
        assert tokenize("one – two") == [Word("one –"), Word("two")]

    def test_standalone_period_glued_tight(self):
        assert tokenize("one . two") == [Word("one."), Word("two")]

    def test_leading_punctuation_only_token_kept(self):
        assert tokenize("– one") == [Word("–"), Word("one")]


class TestUnitEnds:
    @pytest.mark.parametrize(
        "word", ["end.", "end!", "end?", 'end."', "end”", 'end"', "end.)", "end. –"]
    )
    def test_ends_chunk(self, word):
        assert ends_chunk(word)

    @pytest.mark.parametrize("word", ["end,", "end;", "end", "0.5", "end’", "–"])
    def test_not_ends_chunk(self, word):
        assert not ends_chunk(word)

    @pytest.mark.parametrize("word", ["end.", 'end."', "end.”", "end?’", "end!)"])
    def test_ends_sentence(self, word):
        assert ends_sentence(word)

    @pytest.mark.parametrize("word", ['end"', "end”", "end,", "3.5"])
    def test_not_ends_sentence(self, word):
        assert not ends_sentence(word)


class TestBuildChunks:
    def test_fills_to_chunk_size(self):
        assert build_chunks("a b c d e f g", 3) == ["a b c", "d e f", "g"]

    def test_regular_punctuation_does_not_break(self):
        assert build_chunks("a, b; c: d", 3) == ["a, b; c:", "d"]

    def test_period_closes_chunk_early(self):
        assert build_chunks("a b. c d e", 3) == ["a b.", "c d e"]

    def test_question_and_exclamation_close_chunk(self):
        assert build_chunks("a? b c! d", 3) == ["a?", "b c!", "d"]

    def test_opening_quote_closes_previous_chunk(self):
        assert build_chunks('a b "c d e', 3) == ["a b", '"c d e']

    def test_closing_quote_closes_chunk(self):
        assert build_chunks('"a b" c d', 3) == ['"a b"', "c d"]

    def test_curly_quotes_same_rules(self):
        assert build_chunks("x “a b” c", 3) == ["x", "“a b”", "c"]

    def test_chunk_size_one(self):
        assert build_chunks('a "b c." d', 1) == ["a", '"b', 'c."', "d"]

    def test_chunk_size_two_and_decimals(self):
        assert build_chunks("rate 0.99365 = 37. end", 2) == ["rate 0.99365 =", "37.", "end"]

    def test_dash_does_not_consume_slot(self):
        assert build_chunks("one – two three four", 3) == ["one – two three", "four"]

    def test_empty_text(self):
        assert build_chunks("", 3) == []

    def test_invalid_chunk_size(self):
        with pytest.raises(ValueError):
            build_chunks("a", 0)


class TestBuildSentences:
    def test_basic(self):
        assert build_sentences("A b. C d e! F?") == ["A b.", "C d e!", "F?"]

    def test_quote_after_terminator_stays_in_sentence(self):
        assert build_sentences('He said "go." Then left.') == ['He said "go."', "Then left."]

    def test_closing_quote_alone_does_not_end_sentence(self):
        assert build_sentences('"go" he said.') == ['"go" he said.']

    def test_trailing_text_without_period(self):
        assert build_sentences("A b. c d") == ["A b.", "c d"]

    def test_joined_units_identical_across_modes(self):
        text = normalize_text('One two three. "Four five," six. Seven – eight nine ten!')
        for size in (1, 2, 3):
            assert " ".join(build_chunks(text, size)) == " ".join(build_sentences(text))


def test_word_count():
    assert word_count("a b c") == 3
    assert word_count("") == 1


class TestDecode:
    def test_utf8_bom(self):
        assert decode_text("\ufeffhéllo".encode()) == "héllo"

    def test_cp1252_fallback(self):
        assert decode_text(b"caf\xe9 \x93quoted\x94") == "café “quoted”"

    def test_never_raises(self):
        assert decode_text(b"\x81\x8d\x8f\x90\x9d") != ""


def test_load_book_text(tmp_path: Path):
    p = tmp_path / "b.txt"
    p.write_text("Line one,Two\nline three.Four", encoding="utf-8")
    assert load_book_text(p) == "Line one, Two line three. Four"
