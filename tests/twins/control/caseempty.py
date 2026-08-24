"""Purpose: examples/control/caseempty.metta in Python: the `Empty` branch.

`Empty` is the branch a key with NO ANSWERS takes. In `wu` the key is
`(empty)`, so the default fires and the answer is 42; in `wu2` the key answers
42, so the ordinary branch fires and `Empty` is never reached. The pair is the
whole file: `Empty` is about the absence of an answer, not about the value
`()`.

`wu2` is Python's `match` statement, which is what a `case` is, and the
equation it stores is the case tower with the `Empty` arm intact. `wu` cannot
be, and the reason is measurable rather than a missing lowering: the statement
lowers its SUBJECT into a `let*` binding first, and a `let*` over a key with no
answers prunes the whole form, so the compiled `wu` answers nothing where the
example answers 42 [measured 2026-08-24: `match empty(): case 1: ...;
case S.Empty: return 42` stores
`(let* (($k (empty))) (case $k ((1 2) ($_ (case $k ((Empty 42) ...))))))` and
answers `[]`; commit=WORKTREE]. So `wu` is stated as the term it is, and the
gap is filed against P14.4.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, equation

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Take the `Empty` branch, then take an ordinary one instead."""
    # The top rung is the `match` statement `wu2` writes below. It answers
    # nothing here, because the lowering binds the subject with a `let*` and a
    # `let*` over a key with no answers prunes the form, which is the one
    # thing `Empty` exists to catch. Residue: P14.4.
    # (= (wu) (case (empty) ((1 2) (Empty 42))))
    m += equation(S.wu()).to(S.case(S.empty(), ((1, 2), (S.Empty, 42))))  # rung: the compiled `match` binds its subject first, and a binding over a key with no answers prunes the whole form

    @m.define
    def f():
        # (= (f) 42)
        return 42

    @m.define
    def wu2():
        # (= (wu2) (case (f) ((42 ok) (Empty nok))))
        match f():
            case 42:
                return S.ok
            case S.Empty:
                return S.nok

    # !(test (wu) 42)
    assert m.eval(S.wu()) == [42]
    # !(test (wu2) ok)
    assert wu2() == [S.ok]
