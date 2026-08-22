"""examples/control/metta4_streams.metta in Python: answers as a stream.

`range` answers one number at a time, and the three things the file does with
those answers are three ordinary Python lines: iterating them all, taking the
first, and folding them into a total.

metta4's `forall` runs its body once per answer and stops early if one answers
false, which is what a `for` loop over an iterator already does; `once` is the
first answer, which `m.fn(name).first` is the door for; and `foldall` with `+`
and a zero start is `sum`, because a fold over answers is collection work and
the dissolution table puts collection work in Python.

`gen` has three clauses for one head. Stacked `@m.define` will not say that:
stacking reads as first-match, so two clauses fixing no literal are a
REDEFINITION. `@rules` is the other shape of the definitional door and says it
directly.
"""

from petta import S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11712 to 6255, -5457 (-46.6%), by the twin contract
#: change: `forall`'s per-answer write became a Python `for` loop over the
#: answers, `once` became the `first` door, `get-atoms` and its collapse
#: became `list`, and `foldall` became `sum`; `range` and `gen` still run in
#: the engine, which is where the file's producers belong. Measured min-of-3
#: over fresh processes with the MORK backend linked in, which the artefact-
#: free worktree omits and which moves a compiled twin by about 10 inferences
#: per definition; against the example's 15928 the ratio is 0.3927. Prior:
#: 11712, the transliterated twin this replaces.
BUDGET = 6255


def twin(m):
    """Fan a range into two spaces, then fold three answers into one."""
    @m.define(name="range")
    def counter(k, n):
        # (= (range $K $N) (if (< $K $N) (superpose ($K (range (+ $K 1) $N))) (empty)))
        if k < n:
            yield k
            yield from counter(k + 1, n)

    s1 = m.space("&s1")
    s2 = m.space("&s2")

    # !(forall (range 1 5) (|-> ($x) (add-atom &s1 (num $x))))
    for x in counter(1, 5):
        s1 += S.num(x)

    # !(let $x (once (range 1 5)) (add-atom &s2 (num $x)))
    s2 += S.num(m.fn("range").first(1, 5))

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

    m.add(*gen)

    # !(test (foldall (|-> ($x $y) (+ $x $y)) (gen) 0) 6)
    assert sum(m.fn("gen").all()) == 6
