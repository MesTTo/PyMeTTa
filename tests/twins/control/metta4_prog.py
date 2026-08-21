"""The Python twin of examples/control/metta4_prog.metta: sequencing.

`progn` runs every form and answers the LAST; `prog1` runs every form and
answers the FIRST. Both are special forms, so their arguments reach them
unevaluated and a built term is unevaluated by construction.

The first form is a whole little program: two writes, one removal and a query,
all sequenced by `progn`, which is what a Python author would write as four
statements. There is no definition here to hold statements, so the sequence is
the term it is.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
BUDGET = 1752


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (progn (add-atom &self (friend sam tom))
    #               (remove-atom &self (friend sam tom))
    #               (add-atom &self (friend sam tim))
    #               (match &self (friend sam $1) $1))
    #        tim)
    yield m.eval(
        S.test(
            S["progn"](
                S["add-atom"](S["&self"], S.friend(S.sam, S.tom)),
                S["remove-atom"](S["&self"], S.friend(S.sam, S.tom)),
                S["add-atom"](S["&self"], S.friend(S.sam, S.tim)),
                S["match"](S["&self"], S.friend(S.sam, V.who), V.who),
            ),
            S.tim,
        )
    )

    # !(test (prog1 1 2 3) 1)
    yield m.eval(S.test(S["prog1"](1, 2, 3), 1))
    # !(test (progn 1 2 3) 3)
    yield m.eval(S.test(S["progn"](1, 2, 3), 3))
