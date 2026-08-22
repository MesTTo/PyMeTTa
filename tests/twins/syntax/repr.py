"""Purpose: examples/syntax/repr.metta in Python: how an atom prints.

`repr` answers the engine's own text for an atom, and in Python that text is
what `str` answers: `str(S.A(S.B(S.C)))` is `(A (B C))`. So the six claims are
six `str` calls over atoms built at the `S.` door, and the loop under them
states the seam claim the six rest on, that the engine's `repr` says the same
thing about the same atoms.

Expected printed output is Python text. The atom being printed still crosses
through `val` when it is a MeTTa String value.

Two spellings are worth naming. A plain Python tuple builds an expression, so
`(, B , C ,)` is `(S[","], S.B, S[","], S.C, S[","])`, five children under no
head; the subscript is there because `,` is not a Python identifier, which is
the only thing that form is for. And `()` is the empty expression, which
Python's own empty tuple already encodes to.

What no Python program here can say is the other half of a round trip: that
the TEXT `2025_12_12` READS as a symbol rather than as a number. That half is
the reader, whose input is MeTTa source, so it is residue against P14.1, the
same wall syntax/parse.metta's first five forms meet.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3394 to 1744, -1650 (-48.6%), by the twin contract
#: change: six `(test (repr X) "...")` terms became six Python `assert`s over
#: `str(atom)`, so the `test` wrapper left the engine entirely and what is left
#: is the six-call seam loop below. Against the example's 5730 the ratio is
#: 0.3044.
#: Prior: 3394, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1744

#: Every atom of the original, beside the text `repr` prints it as.
PRINTED = [
    (val(42), "42"),
    (val("42"), '"42"'),
    (S.A(S.B(S.C)), "(A (B C))"),
    (S.A((S[","], S.B, S[","], S.C, S[","])), "(A (, B , C ,))"),
    (S["2025_12_12"], "2025_12_12"),
    ((), "()"),
]


def twin(m):
    """Print six atoms, and check the engine prints them the same way."""
    number, text, nested, commas, underscores, unit = (atom for atom, _ in PRINTED)

    assert str(number) == "42"
    # A string atom prints WITH its quotes, which is what makes the text read
    # back as the same string rather than as a symbol.
    assert str(text) == '"42"'
    assert str(nested) == "(A (B C))"
    assert str(commas) == "(A (, B , C ,))"
    # A symbol that looks like a date is a symbol, and prints unchanged.
    assert str(underscores) == "2025_12_12"
    assert str(unit) == "()"

    # Python's `str` is the engine's `repr`: the same atom, the same text,
    # either side of the seam.
    assert [m.fn("repr")(atom) for atom, _ in PRINTED] == [text for _, text in PRINTED]
