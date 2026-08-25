"""Purpose: prove reader token classes are declared and extensible from both APIs.

Guarantees:
  - compiled text patterns retain the supported Python regex flags through
    registration and removal, while bytes and untranslatable flags refuse
    before mutating the reader [tested:
    test_compiled_reader_patterns_preserve_flags_and_unregister;
    commit=WORKTREE]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import re

import pytest

from metta import Grounded, S
from metta.errors import EngineError


def test_a_registered_token_class_parses_like_a_shipped_one(metta):
    """Custom classes share the shipped path and only affect future parses."""
    python_pattern = r"[0-9]+kg"
    metta_pattern = r"[A-Z][0-9]+"
    number_pattern = r"[0-9]+"
    string_pattern = r'(?s)^".*"$'
    patterns = (python_pattern, metta_pattern, number_pattern, string_pattern)
    for pattern in patterns:
        metta.unregister_token(pattern)
    parsed_before_registration = metta.parse("12kg")

    try:
        shipped = list(
            metta.runtime.iter("metta_reader_token_class(Pattern, Constructor, shipped)")
        )
        assert {row["Constructor"] for row in shipped} == {"number", "string"}
        assert metta.parse("12") == Grounded(12)
        assert metta.parse('"12kg"') == Grounded("12kg")

        metta.register_token(
            python_pattern,
            lambda token: S.kilograms(int(token.removesuffix("kg"))),
        )
        assert metta.parse("12kg") == S.kilograms(12)
        assert parsed_before_registration == S["12kg"]

        metta.register_token(python_pattern, lambda token: S.mass(token))
        assert metta.parse("12kg") == S.mass("12kg")

        with pytest.raises(ValueError, match=r"12kg.*another literal"):
            metta.op(lambda value: value, name="12kg", effect="pureStructural")

        metta.run(f'!(register-token! "{metta_pattern}" tagged)')
        assert metta.parse("A7") == S.tagged("A7")
        metta.run(f'!(unregister-token! "{metta_pattern}")')
        assert metta.parse("A7") == S.A7

        metta.register_token(number_pattern, lambda token: S.digits(token))
        assert metta.parse("12") == S.digits("12")
        with pytest.raises(EngineError, match="read back as a different value"):
            metta.runtime.once("swrite(Value, Text)", Value=12)

        metta.register_token(string_pattern, lambda token: S.quoted(token))
        assert metta.parse('"literal"') == S.quoted('"literal"')
        with pytest.raises(EngineError, match="read back as a different value"):
            metta.runtime.once('swrite("literal", Text)')
    finally:
        for pattern in patterns:
            metta.unregister_token(pattern)

    assert metta.parse("12kg") == S["12kg"]
    assert metta.parse("12") == Grounded(12)
    assert metta.parse('"literal"') == Grounded("literal")


def test_token_registration_refuses_invalid_inputs_without_changing_the_reader(metta):
    """Validation precedes mutation for Python types and malformed PCRE."""
    before = metta.parse("not-a-token")

    with pytest.raises(TypeError, match="pattern"):
        metta.register_token(42, lambda token: token)
    with pytest.raises(TypeError, match="constructor"):
        metta.register_token("not-a-token", "not callable")
    with pytest.raises(EngineError):
        metta.register_token("[", lambda token: token)

    assert metta.parse("not-a-token") == before


def test_compiled_reader_patterns_preserve_flags_and_unregister(metta):
    """Compiled patterns carry their semantic flags into the engine PCRE."""
    pattern = re.compile(r"(?P<amount>[0-9]+)kg", re.IGNORECASE)
    metta.unregister_token(pattern)
    try:
        metta.register_token(pattern, lambda token: S.mass(token))
        assert metta.parse("12KG") == S.mass("12KG")
    finally:
        metta.unregister_token(pattern)
    assert metta.parse("12KG") == S["12KG"]

    with pytest.raises(ValueError, match="flags"):
        metta.register_token(re.compile(r"[a-z]+", re.ASCII), S.word)
    with pytest.raises(TypeError, match="text, not bytes"):
        metta.register_token(re.compile(b"[a-z]+"), S.word)


def test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback(metta):
    """A class that claimed a lexeme also owns a failure constructing it."""
    pattern = r"broken-token"

    def broken(_token):
        msg = "reader constructor failed"
        raise RuntimeError(msg)

    metta.unregister_token(pattern)
    metta.register_token(pattern, broken)
    try:
        with pytest.raises(EngineError, match="reader constructor failed"):
            metta.parse("broken-token")
    finally:
        metta.unregister_token(pattern)
