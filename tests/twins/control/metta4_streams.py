"""Purpose: examples/control/metta4_streams.metta in Python: answers as a stream.

`range` answers one number at a time, and the three things the file does with
those answers are three ordinary Python lines: iterating them all, taking the
first, and folding them into a total.

metta4's `forall` runs its body once per answer and stops early if one answers
false, which is what a `for` loop over an iterator already does; `once` is
`first(default=...)`, which pulls at most one answer out of the lazy view and
leaves the producer where it stands; and `foldall` with `+` and a zero start is
`sum`, because a fold over answers is collection work and the dissolution
table puts collection work in Python.

`gen` has three clauses for one head. Stacked `@m.define` will not say that:
stacking reads as first-match, so two clauses fixing no literal are a
REDEFINITION. `@rules` is the other shape of the definitional door and says it
directly, and `space += bundle` lands the clause set through the one write
door.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import UNIT, S, equation, rules

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Fan a range into two spaces, then fold three answers into one."""
    @m.define(name="range")
    def counter(k, n):
        # (= (range $K $N) (if (< $K $N) (superpose ($K (range (+ $K 1) $N))) (empty)))
        if k < n:
            yield k
            yield from counter(k + 1, n)

    s1 = petta.space("&s1")
    s2 = petta.space("&s2")

    # !(forall (range 1 5) (|-> ($x) (add-atom &s1 (num $x))))
    for x in counter(1, 5):
        s1 += S.num(x)

    # !(let $x (once (range 1 5)) (add-atom &s2 (num $x)))
    s2 += S.num(counter(1, 5).first(default=UNIT))

    # !(test (collapse (get-atoms &s1)) ((num 1) (num 2) (num 3) (num 4)))
    assert list(s1) == [S.num(1), S.num(2), S.num(3), S.num(4)]

    # !(test (collapse (get-atoms &s2)) ((num 1)))
    assert list(s2) == [S.num(1)]

    @rules
    def gen():
        # (= (gen) 1) (= (gen) 2) (= (gen) 3)
        yield equation(S.gen()).to(1)
        yield equation(S.gen()).to(2)
        yield equation(S.gen()).to(3)

    m += gen

    # !(test (foldall (|-> ($x $y) (+ $x $y)) (gen) 0) 6)
    assert sum(m.fn.gen()) == 6
