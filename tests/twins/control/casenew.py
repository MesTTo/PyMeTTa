"""The Python twin of examples/control/casenew.metta: a branch that answers nothing.

`wu` superposes two calls; one of them answers nothing at all, so the whole
form answers only the other. That is the file's subject, and it is where a
Python generator says exactly what MeTTa says: **each `yield` is one answer,
which is what `superpose` spells**, and a yielded call contributes its own
answers rather than a generator object.

Two of the three equations do not fit a compiled body:

- `(= (wu2) (full))` builds the lowercase term `(full)`, and a compiled body
  resolves a lowercase free name as a FUNCTION and a capitalised one as a
  constructor, so `full` raises and `Full` would store the wrong atom. Wave
  one recorded that spelling gap against P14.4 for `time_and_pragmas`.
- `wu1` answers `(empty)`, which the compiled subset does spell, so it is
  written as a function.

`m.fn("wu2")` binds the container-door equation's name on the Python side, so
the generator below names it the way it names `wu1`.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 4638


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    empty = m.fn("empty")

    @m.define
    def wu1():
        # (= (wu1) (empty))
        return empty()

    # (= (wu2) (full))
    m += S["="](S.wu2(), S.full())
    wu2 = m.fn("wu2")

    @m.define
    def wu():
        # (= (wu) (superpose ((wu1) (wu2))))
        yield wu1()
        yield wu2()

    # !(test (wu) (full))
    yield m.eval(S.test(wu(), S.full()))
