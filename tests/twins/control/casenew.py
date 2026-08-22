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

from petta import S, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `wu2`'s body is the lowercase term `(full)`, and a compiled body resolves a lowercase
#: free name as a FUNCTION and reads a capitalised one as a constructor, so neither spelling stores
#: this atom.
RUNG = "container door for wu2, whose body is the lowercase term (full)"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4638 to 4695, +57, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 4638 by 47554fc's control/types twin baseline.
BUDGET = 4695


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
    m += equation(S.wu2()).to(S.full())
    wu2 = m.fn("wu2")

    @m.define
    def wu():
        # (= (wu) (superpose ((wu1) (wu2))))
        yield wu1()
        yield wu2()

    # !(test (wu) (full))
    yield m.eval(S.test(S.wu(), S.full()))
