"""Purpose: compare MeTTa byte and UUID recipes with Python's standard codecs.

Guarantees: generated Unicode, NUL, byte values and arbitrary namespaces agree
with independent standard-library oracles; recipes remain callable data
[tested: test_encoding_python_oracles, test_uuid_python_oracles; commit=8fe20f1bdcde1af8b3e1753c545924f978246dba].
"""

from __future__ import annotations

import base64
import uuid

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from metta import G, S, V, lib, library
from metta._errors.errors import MettaError


@pytest.fixture(scope="module")
def codecs(metta):
    """Load the public UUID composition and its Encoding dependency."""
    metta += lib.uuid
    return metta


@settings(max_examples=100, deadline=None)
@example(b"\x00\xff\x80")
@example(b"")
@given(st.binary(max_size=64))
def test_encoding_python_oracles(codecs, data):
    """One byte expression agrees with hex and both base64 policies."""
    fn = codecs.fn
    values = tuple(data)
    assert fn.hex_encode(values).one() == data.hex()
    for text in (data.hex(), data.hex().upper()):
        assert list(fn.hex_decode(G(text)).one()) == list(data)
    for alphabet, encoder, padded in (
        (S.standard, base64.b64encode, True), (S.url, base64.urlsafe_b64encode, False),
    ):
        text = encoder(data).decode("ascii")
        if not padded:
            text = text.rstrip("=")
        assert fn.base64_encode(alphabet, values).one() == text
        assert list(fn.base64_decode(alphabet, G(text)).one()) == list(data)


@settings(max_examples=80, deadline=None)
@example("a\0🦊é")
@given(st.text(st.characters(blacklist_categories=("Cs",)), max_size=32))
def test_encoding_utf8_python_oracle(codecs, text):
    """UTF8 counts complete encoded bytes rather than host character widths."""
    data = text.encode("utf-8")
    assert list(codecs.fn.utf8_encode(G(text)).one()) == list(data)
    assert codecs.fn.utf8_decode(tuple(data)).one() == text


@pytest.mark.parametrize("text", ["a", "abc", "_a", "0g", "\U0001d7e20", "\uff100", "a\0", "ff ", "é0"])
def test_hex_malformed_spelling_names_the_decoder(codecs, text):
    """Unicode lookalikes, whitespace and NUL never become hexadecimal digits."""
    with pytest.raises(MettaError, match="hex-decode"):
        codecs.fn.hex_decode(G(text)).one()


@pytest.mark.parametrize("value", [V.x, True, 1.0, 256, -1, S["+"](1, 2)])
def test_encoding_literal_nonbytes_are_refused(codecs, value):
    """Validation never evaluates a literal expression to manufacture a byte."""
    with pytest.raises(MettaError, match="hex-encode"):
        codecs.fn.hex_encode(S.quote((value,))).one()


def test_encoding_typed_literal_errors_remain_values(codecs):
    """String rejects Numbers as Error values; byte shape has a strict boundary."""
    assert codecs.eval(S.hex_decode(7)) == [
        S.Error(S.hex_decode(7), S.BadArgType(1, S.String, S.Number)),
    ]
    with pytest.raises(MettaError, match=r"hex-encode.*list.*bad"):
        codecs.eval(S.hex_encode(S.bad))


@settings(max_examples=80, deadline=None)
@example(5, bytes(16), "a\0🦊")
@given(st.sampled_from((3, 5)), st.binary(min_size=16, max_size=16),
       st.text(st.characters(blacklist_categories=("Cs",)), max_size=24))
def test_uuid_python_oracles(codecs, version, namespace_bytes, name):
    """RFC names preserve arbitrary namespace bits and complete UTF8 text."""
    namespace = uuid.UUID(bytes=namespace_bytes)
    expected = (uuid.uuid3 if version == 3 else uuid.uuid5)(namespace, name)
    actual = codecs.fn.uuid_name(version, G(str(namespace).upper()), G(name)).one()
    assert actual == str(expected)


@settings(max_examples=80, deadline=None)
@example(bytes(16))
@example(b"\xff" * 16)
@given(st.binary(min_size=16, max_size=16))
def test_uuid_every_layout_round_trips(codecs, data):
    """Version and variant queries expose bits even for reserved identifiers."""
    text = str(uuid.UUID(bytes=data))
    fn = codecs.fn
    assert fn.uuid_of_bytes(tuple(data)).one() == text
    assert list(fn.uuid_bytes(G(text.upper())).one()) == list(data)
    assert fn.uuid_is(G(text)).one() is True
    assert fn.uuid_version(G(text)).one() == data[6] // 16
    byte = data[8]
    expected = S.ncs if byte < 128 else S.rfc if byte < 192 else S.microsoft if byte < 224 else S.future
    assert fn.uuid_variant(G(text)).one() == expected


def test_uuid_requires_literal_ascii_fields_and_separators(codecs):
    """Every position refuses nonhex text, Unicode lookalikes and embedded NUL."""
    text = str(uuid.UUID(int=0))
    for index in range(len(text)):
        for char in ("g", "\0", "\uff10", "\U0001d7e2"):
            bad = text[:index] + char + text[index + 1:]
            assert codecs.fn.uuid_is(G(bad)).one() is False


@pytest.mark.parametrize("version", [1, 2, 4, 6, 3.0, V.version])
def test_uuid_name_requires_an_exact_supported_version(codecs, version):
    """The version relation compares identity and never binds an unknown slot."""
    with pytest.raises(MettaError, match="choose version 3 or 5"):
        codecs.fn.uuid_name(version, S.dns, G("x")).one()


@pytest.mark.parametrize("namespace", [S.missing, G("bad"), V.namespace])
def test_uuid_name_refuses_an_invalid_namespace(codecs, namespace):
    """The shared UUID byte boundary names the invalid namespace value."""
    with pytest.raises(MettaError, match="uuid-bytes"):
        codecs.fn.uuid_name(5, namespace, G("x")).one()


@pytest.mark.parametrize("head,args,expected", [
    ("hex-encode", ((0, 255),), "00ff"),
    ("hex-decode", (G("00FF"),), (0, 255)),
    ("uuid-version", (G("ffffffff-ffff-ffff-ffff-ffffffffffff"),), 15),
    ("uuid-variant", (G("ffffffff-ffff-ffff-ffff-ffffffffffff"),), S.future),
])
def test_codec_equations_can_be_reconstructed(codecs, head, args, expected):
    """Stored equation bodies can be returned and called as ordinary functions."""
    row = codecs.match(S["="](S[head](V.input), V.body)).one()
    function = codecs.eval(S["|->"]((row.input,), row.body))[0]
    assert codecs.eval((function, *args)) == [expected]


def test_uuid_name_equation_can_be_reconstructed(codecs):
    """A three-argument name recipe preserves parameter sharing in its body."""
    row = codecs.match(S["="](S.uuid_name(V.version, V.namespace, V.name), V.body)).one()
    function = codecs.eval(S["|->"]((row.version, row.namespace, row.name), row.body))[0]
    assert codecs.eval((function, 5, S.dns, G("example.com"))) == [
        G("cfbff0d1-9375-5685-968c-48ce8b15ae17"),
    ]


@pytest.mark.parametrize("program", [S.hex_decode(G("00ff")), S.uuid_version(S.uuid_nil())])
def test_codec_shape_assertions_keep_recording_conservative(codecs, program):
    """Assertions can emit diagnostics, so valid inputs do not promise replay."""
    recording = codecs.record(program, seed=42)
    assert recording.replayable is False
    assert "assertEqualMsg" in recording.reason
    with pytest.raises(MettaError, match="not replayable"):
        recording.replay(codecs)


def test_codec_library_cards_expose_the_complete_surface():
    """The public catalog keeps native and derived heads in the same library."""
    assert len(library.card("lib_encoding").heads) == 6
    assert len(library.card("lib_uuid").heads) == 11
