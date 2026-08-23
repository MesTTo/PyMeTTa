"""Purpose: examples/control/once.metta in Python: committing to the first answer.

The companion of cut.metta, saying the same thing with the form built for it:
two atoms match, `once` commits to the first, and one `(bar 1)` is stored.

`match-single` is a compiled definition whose space, pattern and template are
PARAMETERS, and the handle crosses as a term operand, so the space itself is
what the call hands over. The rest is ordinary Python: a write is
`space += atom` and a read is the subscript door.

Two things about the answer view are worth knowing here, both measured
2026-08-23 and both the library's to fix rather than this file's. Calling a
DEFINITION answers binding rows for the caller's own variables outside a
`stats()` scope and the bare answers inside one, and a twin runs inside one;
and `m.fn.<name>(...)` answers binding rows in BOTH, which discards the
answer when the variable is an argument rather than an answer template
(`m.fn.unify(V.x, S.f(V.x), S.cyclic, S.sound)` answers `[Row(x=$_70)]` where
the form answers `sound`).
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Commit to one answer out of two, then read back what was stored."""
    # (foo 1)
    m += S.foo(1)
    # (foo 2)
    m += S.foo(2)

    # A compiled body is MeTTa, so `fn.match` IS the ruled spelling there: the
    # quotation tier reads `fn.<name>` as a callee exactly as it reads `S.done`
    # as data. The lane still reports it, because its dissolution table fires
    # everywhere and names `space[pattern]`, a Python expression over a handle
    # that a body cannot have; the operator rule is scoped to lowered bodies
    # and the dissolution rule is not. That is why this line carries a rung
    # note. Nine lines in control/ carry one for the same reason: `match` in
    # cut.py and once.py, `add-atom`/`remove-atom` in eval.py, `add-atom` twice
    # in unify.py and three times in thin_forms.py.
    @m.define(name="match-single")
    def match_single(space, pat, ret):
        # (= (match-single $space $pat $ret) (once (match $space $pat $ret)))
        return S.once(fn.match(space, pat, ret))  # rung: the subscript door is a Python statement over a handle, and the space here is a parameter of the equation

    # !(let $x (match-single &self (foo $1) $1) (add-atom &self (bar $x)))
    # Calling IS evaluation, and a `let` over a value that answers once is a
    # loop that runs once.
    for hit in match_single(m, S.foo(V.hit), V.hit):
        m += S.bar(hit)

    # !(test (collapse (match &self (bar $1) (bar $1))) ((bar 1)))
    assert [S.bar(row.hit) for row in m[S.bar(V.hit)]] == [S.bar(1)]
