"""examples/ch08-data/08-01-atoms-lists-and-folds/21-compose.metta in Python: functions applied right to left.

`compose` takes a LIST of function names and a list of arguments, so both
sides are ordinary tuples of atoms and the function names are symbols rather
than Python callables: the innermost one meets every argument and each one
outside it is unary by construction.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib


def twin(m):
    """Apply one function, then two, then a whole argument list."""
    m += lib.patrick

    # The annotations are load-bearing: a typed number operand lowers `+` and
    # `*` to the engine's own heads, where an untyped one lowers to
    # `(py-operator add ...)` and the space would hold a different program.
    @m.define
    def inc(x: int) -> int:
        # (= (inc $x) (+ $x 1))
        return x + 1

    @m.define
    def double(x: int) -> int:
        # (= (double $x) (* $x 2))
        return x * 2

    compose = m.fn.compose

    # A one-function list is application, and it is the case the definition
    # special-cases: a single argument is handed over directly.
    assert compose((S.inc,), (5,)) == [6]
    assert compose((S.double,), (5,)) == [10]

    # Two functions, innermost last.
    assert compose((S.inc, S.double), (5,)) == [11]
    assert compose((S.double, S.inc), (5,)) == [12]

    # The innermost function is the one that meets the argument list, so it
    # can take more than one; everything outside it is unary.
    plus = S["+"]
    assert compose((plus,), (2, 3)) == [5]
    assert compose((S.inc, plus), (2, 3)) == [6]
    assert compose((S.double, S.inc, plus), (2, 3)) == [12]

    # Composition is associative, so composing a longer list is composing the
    # shorter ones.
    inner = compose((S.double,), (5,))[0]
    assert compose((S.inc,), (inner,)) == [11]
    assert compose((S.inc, S.double), (5,)) == compose((S.inc,), (inner,))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 34466 inferences, 1.0075x the example's 34210; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 34466
