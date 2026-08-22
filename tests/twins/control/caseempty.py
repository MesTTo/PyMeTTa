"""examples/control/caseempty.metta in Python: the `Empty` branch.

`Empty` is the branch a key with NO ANSWERS takes. In `wu` the key is
`(empty)`, so the default fires and the answer is 42; in `wu2` the key answers
42, so the ordinary branch fires and `Empty` is never reached. The pair is the
whole file: `Empty` is about the absence of an answer, not about the value
`()`.

`f` is the one equation here that is a computation, so it is written as one.
The two `case` equations are not: `Empty` asks whether the KEY HAS ANY
ANSWERS, and Python's `if` asks about a value, of which there is none when
there are no answers. Python's `match` statement has no lowering in the
compiled subset either, so both are stated as terms and filed against P14.4.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4784 to 3729, -1055 (-22.1%), by the twin contract
#: change: two `test` wrappers LEFT the engine for `assert`s, and only `f`
#: ENTERED as `@m.define`; the two `case` equations stay terms because
#: `Empty` asks whether the key answered at all. Measured min-of-3 over fresh
#: processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 6438 the ratio is 0.5792. Prior: 4784,
#: the transliterated twin this replaces.
BUDGET = 3729


def twin(m):
    """Take the `Empty` branch, then take an ordinary one instead."""
    # (= (wu) (case (empty) ((1 2) (Empty 42))))
    m += equation(S.wu()).to(S.case(S.empty(), ((1, 2), (S.Empty, 42))))  # rung: `Empty` asks whether the key answered at all, which Python's `if` cannot ask

    @m.define
    def f():
        # (= (f) 42)
        return 42

    # (= (wu2) (case (f) ((42 ok) (Empty nok))))
    m += equation(S.wu2()).to(S.case(S.f(), ((42, S.ok), (S.Empty, S.nok))))  # rung: the same `Empty` branch, with a key that does answer

    # !(test (wu) 42)
    assert m.eval(S.wu()) == [42]
    # !(test (wu2) ok)
    assert m.eval(S.wu2()) == [S.ok]
