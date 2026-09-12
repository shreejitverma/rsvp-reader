import pytest

from rsvpreader.pivot import PivotSplit, pivot_letter_index, pivot_word_index, split_for_pivot


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("Bull", 1),
        ("cat", 1),
        ("a", 0),
        ("abcd", 1),
        ("abcde", 2),
        ('"Bull"', 2),
        ("2000", 1),
        ("$2.25", 3),
        ("7.25p.m.", 4),
        ("...", None),
    ],
)
def test_pivot_letter_index(word, expected):
    assert pivot_letter_index(word) == expected


def test_pivot_word_index_rules():
    assert pivot_word_index(["a", "b", "c"]) == 1
    assert pivot_word_index(["long", "longer"]) == 1
    assert pivot_word_index(["same", "size"]) == 0
    assert pivot_word_index(["it's", "ab"]) == 0  # letters only: 3 vs 2
    assert pivot_word_index(["solo"]) == 0
    assert pivot_word_index([]) == 0


def test_split_three_words():
    assert split_for_pivot("the Bull ran") == PivotSplit("the B", "u", "ll ran")


def test_split_single_word():
    assert split_for_pivot("Bull") == PivotSplit("B", "u", "ll")


def test_split_two_words_prefers_longer():
    assert split_for_pivot("a Bull") == PivotSplit("a B", "u", "ll")


def test_split_digits_fallback():
    assert split_for_pivot("123 4567") == PivotSplit("1", "2", "3 4567")  # tie -> first word


def test_split_no_pivot():
    assert split_for_pivot("-- ...") == PivotSplit("-- ...", None, "")


@pytest.mark.parametrize(
    "chunk",
    ["one", "one two", "one two three", '"quoted," said', "0.5 x", "a – b", "Zw. Ab’s"],
)
def test_split_reconstructs_chunk(chunk):
    before, letter, after = split_for_pivot(chunk)
    assert before + (letter or "") + after == chunk
