"""Purpose: examples/integration/python_booleans.metta in Python: booleans crossing.

MeTTa's `true` and `false` become Python's `True` and `False` on the way in, in
argument position and inside lists, and Python's booleans come back as MeTTa's.
Every claim runs through `m.fn.py_call`, the host-call door read as an
ordinary Python callable through rung 4's hyphen map, because the crossing IS
this example's subject: calling `str` or `sorted` from Python directly would
test nothing.

The example asserts its string answers through `repr` because a MeTTa program
has no other way to look at a symbol. Here the answer is an atom in hand, so
each claim names the atom: `py(...) == S["True"]` says both that the text is
"True" and that it came back as a SYMBOL rather than a String, which is the
conversion the file is about.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Nine crossings of the boolean, and what each one answers."""
    py = m.fn.py_call

    # str() sees a Python bool, and its text returns as a symbol.
    assert py(S.str(TRUE)).one() == S["True"]
    assert py(S.str(FALSE)).one() == S["False"]

    # A list argument converts its booleans in, and a list answer converts
    # them back out, elementwise.
    assert py(S.sorted((TRUE, FALSE))).one() == Expression((FALSE, TRUE))
    assert py(S.len((TRUE, FALSE, TRUE))).one() == 3

    # Python sees bool all the way down, so isinstance and bool() agree.
    assert py(S.isinstance(TRUE, S["py-call"](S.type(FALSE)))).one() is True
    assert py(S.bool(1)).one() is True
    assert py(S.bool(0)).one() is False

    # A boolean RECEIVER dispatches on bool, not on the text "true".
    assert py(S[".bit_length"](TRUE)).one() == 1

    # Only the boolean atoms convert; every other symbol stays text.
    assert py(S[".upper"](S.abc)).one() == S.ABC
