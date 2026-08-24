"""examples/integration/python_booleans.metta in Python: booleans crossing.

MeTTa's `true` and `false` become Python's `True` and `False` on the way in, in
argument position and inside lists, and Python's booleans come back as MeTTa's.
Every claim runs through `m.fn.py_call`, the host-call door read as an ordinary
Python callable through rung 4's map, because the CROSSING is this example's
subject: calling `str` or `sorted` from Python directly would test nothing.

The example asserts its string answers through `repr` because a MeTTa program
has no other way to look at a symbol. Here the answer is an atom in hand, so
each claim names the atom: `py(...) == S["True"]` says both that the text is
"True" and that it came back as a SYMBOL rather than a String, which is the
conversion the file is about.
"""

from metta import FALSE, TRUE, Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
BUDGET = 1


def twin(m):
    """Ten crossings of the boolean, and what each one answers."""
    py = m.fn.py_call

    # str() sees a Python bool, and its text returns as a symbol.
    assert py(S.str(TRUE)).one() == S["True"]      # (repr (py-call (str true))) is "True"
    assert py(S.str(FALSE)).one() == S["False"]

    # A list argument converts its booleans in, and a list answer converts them
    # back out, elementwise.
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
