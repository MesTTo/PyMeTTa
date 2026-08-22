"""examples/control/once.metta in Python: committing to the first answer.

The companion of cut.metta, saying the same thing with the form built for it:
two atoms match, `once` commits to the first, and one `(bar 1)` is stored.

`match-single` is a term for cut.metta's reason: its space, pattern and
template are PARAMETERS, and a compiled `match()` reads its pattern as syntax
against a space named on the spot. The rest is ordinary Python: a write is
`space += atom`, a query is the subscript door, and `let` over a value that
answers once is a loop that runs once.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2376 to 1507, -869 (-36.6%), by the twin contract
#: change: `add-atom`, `match` and `collapse` LEFT the engine for `+=`, the
#: query door and a Python comprehension; only `match-single` still runs
#: there. Measured min-of-3 over fresh processes with the MORK backend linked
#: in, which the artefact-free worktree omits and which moves a compiled twin
#: by about 10 inferences per definition; against the example's 5405 the
#: ratio is 0.2788. Prior: 2376, the transliterated twin this replaces.
BUDGET = 1507


def twin(m):
    """Commit to one answer out of two, then read back what was stored."""
    # (foo 1)
    m += S.foo(1)
    # (foo 2)
    m += S.foo(2)

    # (= (match-single $space $pat $ret) (once (match $space $pat $ret)))
    single = S.once(S.match(V.space, V.pat, V.ret))  # rung: a definition whose space, pattern and template are parameters has no compiled spelling
    m += equation(S["match-single"](V.space, V.pat, V.ret)).to(single)

    # !(let $x (match-single &self (foo $1) $1) (add-atom &self (bar $x)))
    for one in m.eval(S["match-single"](S[m.space_name], S.foo(V.one), V.one)):
        m += S.bar(one)

    # !(test (collapse (match &self (bar $1) (bar $1))) ((bar 1)))
    assert [S.bar(row.one) for row in m.query(S.bar(V.one))] == [S.bar(1)]
