"""Purpose: examples/control/caseempty.metta in Python: the `Empty` branch.

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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, equation

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Take the `Empty` branch, then take an ordinary one instead."""
    # The top rung compiles both equations, which needs two things the
    # subset has not got: a `match` statement, and a pattern that asks
    # whether the KEY ANSWERED AT ALL rather than what it answered.
    #
    #     @m.define
    #     def wu():
    #         match empty():          # `ast.Match` has no lowering
    #             case 1: return 2
    #             case Empty: return 42   # and `Empty` is not a value pattern
    #
    # Residue: P14.4.
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
