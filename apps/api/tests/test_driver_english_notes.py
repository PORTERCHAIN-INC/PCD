"""L46: drivers (English-only app) get the English translation after a French note."""

from unittest.mock import MagicMock

from porterchain_api.platform.free_text_translation import english_note_lines


def _db(rows):
    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = rows
    return db


def test_adds_english_line_after_translated_note():
    row = MagicMock(original="Code de la porte 4521", translated_en="Door code 4521")
    out = english_note_lines(_db([row]), "o1", ["Leave at door", "Site access: Code de la porte 4521"])
    assert out == ["Leave at door", "Site access: Code de la porte 4521", "English: Door code 4521"]


def test_no_translation_leaves_lines():
    assert english_note_lines(_db([]), "o1", ["Site access: x"]) == ["Site access: x"]


def test_lookup_error_is_swallowed():
    db = MagicMock()
    db.query.side_effect = RuntimeError("boom")
    assert english_note_lines(db, "o1", ["a"]) == ["a"]
