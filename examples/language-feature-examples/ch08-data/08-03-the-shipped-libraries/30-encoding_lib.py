"""Purpose: UTF-8, hex and base64, each one head in and one head out.

Bytes are a tuple of numbers and text is `G("...")`; an alphabet is a symbol. The
two heads that answer bytes answer an expression, which `list()` reads.

Guarantees: the same claims as 30-encoding_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/30-encoding_lib.metta; commit=2b8c0afd38dcfe3994d5047dba2d035970311d0e].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Encode and decode the three, compose them, and refuse what is not bytes."""
    m += lib.encoding
    # lib_string is beside it for the one comparison that makes UTF-8 worth having:
    # string-length counts characters where these bytes count bytes.
    m += lib.string

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def bytes_of(answers):
        """One answer's expression of bytes, as a list."""
        return list(answers.one())

    utf8, unutf8 = m.fn.utf8_encode, m.fn.utf8_decode
    hex_of, unhex = m.fn.hex_encode, m.fn.hex_decode
    b64, unb64 = m.fn.base64_encode, m.fn.base64_decode

    # Bytes are an expression of Numbers from 0 to 255, which is lib_file's byte
    # shape, so what a file answers is what these heads take.
    assert bytes_of(utf8(G("hi"))) == [104, 105]
    assert unutf8((104, 105)) == [G("hi")]
    assert bytes_of(utf8(G(""))) == []
    assert unutf8(()) == [G("")]

    # UTF-8 is where a byte count and a character count part company.
    assert bytes_of(utf8(G("é"))) == [195, 169]
    assert m.fn.string_length(G("é")) == [1]
    assert len(utf8(G("é")).one()) == 2
    assert len(utf8(G("🙂")).one()) == 4
    assert m.fn.string_length(G("🙂")) == [1]
    assert unutf8(S.utf8_encode(G("héllo 🙂"))) == [G("héllo 🙂")]

    # Hex answers lower case, two digits a byte and nothing between them, and reads
    # either case back.
    assert hex_of((255, 16, 0)) == [G("ff1000")]
    assert bytes_of(unhex(G("ff1000"))) == [255, 16, 0]
    assert bytes_of(unhex(G("FF1000"))) == [255, 16, 0]
    assert hex_of(()) == [G("")]
    assert bytes_of(unhex(G(""))) == []
    assert hex_of(S.utf8_encode(G("hi"))) == [G("6869")]

    # Base64 takes its ALPHABET as an argument.
    assert b64(S.standard, (104, 105)) == [G("aGk=")]
    assert bytes_of(unb64(S.standard, G("aGk="))) == [104, 105]
    assert b64(S.standard, (255, 254)) == [G("//4=")]
    assert b64(S.url, (255, 254)) == [G("__4")]
    assert bytes_of(unb64(S.url, S.base64_encode(S.url, (255, 254)))) == [255, 254]
    assert b64(S.standard, ()) == [G("")]
    assert bytes_of(unb64(S.standard, G(""))) == []
    # The two alphabets are the same encoding.
    assert bytes_of(unb64(S.standard, G("//79"))) == [255, 254, 253]
    assert bytes_of(unb64(S.url, G("__79"))) == [255, 254, 253]

    # The encodings compose, which is the whole reason they are here.
    assert unutf8(S.base64_decode(S.url, S.base64_encode(S.url, S.utf8_encode(G("héllo"))))) == [
        G("héllo"),
    ]
    assert b64(S.standard, S.hex_decode(G("6869"))) == [G("aGk=")]

    # Malformed input is refused rather than repaired.
    assert refused(S.hex_decode(G("abc")))
    assert refused(S.hex_decode(G("zz")))
    assert refused(S.utf8_decode((255,)))
    assert refused(S.utf8_decode((195,)))
    assert refused(S.base64_decode(S.standard, G("not base64!")))
    assert refused(S.base64_encode(S.nosuch, (1,)))
    # A code point is not a byte: string-codes answers code points, and one above
    # 255 is refused naming the value.
    assert refused(S.hex_encode((256,)))
    assert refused(S.base64_encode(S.standard, S.string_codes(G("🙂"))))
    # A code point that happens to fit in a byte is accepted as one, which is why
    # the two are worth telling apart: this is the byte 233, not the letter é.
    assert hex_of(S.string_codes(G("é"))) == [G("e9")]
    assert hex_of(S.utf8_encode(G("é"))) == [G("c3a9")]
    assert refused(S.utf8_decode((1, S.two)))
    assert list(m.eval(S.hex_decode(7))) == [
        S.Error(S.hex_decode(7), S.BadArgType(1, S.String, S.Number)),
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 39 claims cover the six heads, the two alphabets,
#: the compositions and the nine refusals
#: [measured 2026-09-12: 147669 inferences against the example's 149599, minimum
#: of three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/30-encoding_lib.metta;
#: fixture=lib_encoding at its functional commit, artifacts purged before the run;
#: commit=2b8c0afd38dcfe3994d5047dba2d035970311d0e].
#: RE-PINNED 2026-09-13, 147669 to 148200 (+531), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-14, 148200 to 170173 (+21973), String now derives nine
#: text recipes through MeTTa equations, with one function parameter for
#: padding and complete validation before empty construction; all import
#: consumers are measured after the provider change [measured 2026-09-14: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 170173
