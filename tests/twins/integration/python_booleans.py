"""The Python twin of examples/integration/python_booleans.metta: booleans crossing.

Nothing here is a definition: every form is a `py-call` whose answer states one
half of the boolean conversion. The booleans are the named `TRUE`/`FALSE` atoms
rather than bare `True`/`False`, which is the corpus convention for a boolean in
an argument list and is right twice over here, since the whole file is about
which booleans are MeTTa's and which are Python's.

MeTTa's `(true false)` argument lists are Python tuples, and the string answers
cross as `val(...)`, the marked-data door.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 5917


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (repr (py-call (str true))) "True")
    yield m.eval(
        S.test(S.repr(S["py-call"](S.str(TRUE))),
            val("True"))
    )

    # !(test (repr (py-call (str false))) "False")
    yield m.eval(
        S.test(S.repr(S["py-call"](S.str(FALSE))),
            val("False"))
    )

    # !(test (py-call (sorted (true false))) (false true))
    yield m.eval(
        S.test(S["py-call"](S.sorted((TRUE, FALSE))),
            (FALSE, TRUE))
    )

    # !(test (py-call (len (true false true))) 3)
    yield m.eval(
        S.test(S["py-call"](S.len((TRUE, FALSE, TRUE))),
            3)
    )

    # !(test (py-call (isinstance true (py-call (type false)))) true)
    yield m.eval(
        S.test(S["py-call"](S.isinstance(TRUE,
                    S["py-call"](S.type(FALSE)))),
            TRUE)
    )

    # !(test (py-call (bool 1)) true)
    yield m.eval(S.test(S["py-call"](S.bool(1)), TRUE))

    # !(test (py-call (bool 0)) false)
    yield m.eval(S.test(S["py-call"](S.bool(0)), FALSE))

    # !(test (py-call (.bit_length true)) 1)
    yield m.eval(S.test(S["py-call"](S[".bit_length"](TRUE)), 1))

    # !(test (repr (py-call (.upper abc))) "ABC")
    yield m.eval(
        S.test(S.repr(S["py-call"](S[".upper"](S.abc))), val("ABC"))
    )
