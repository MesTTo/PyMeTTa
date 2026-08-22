"""examples/control/cut.metta in Python: keeping the first answer only.

`(foo 1)` and `(foo 2)` both match, and `cut` throws the second away, so the
`let` above sees one answer and one `(bar 1)` is stored.

`match-single` takes its space, its pattern and its template as PARAMETERS,
and a compiled `match()` reads its pattern as SYNTAX against a space named on
the spot, so a definition that takes a query apart has no compiled spelling at
all. That is the one line below that is a term; everything around it is
ordinary Python, because a write is `space += atom` and a query is the
subscript door.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2605 to 1736, -869 (-33.4%), by the twin contract
#: change: `add-atom`, `match` and `collapse` LEFT the engine for `+=`, the
#: query door and a Python comprehension; only `match-single` still runs
#: there, because a definition whose space and pattern are parameters has no
#: compiled spelling. Measured min-of-3 over fresh processes with the MORK
#: backend linked in, which the artefact-free worktree omits and which moves
#: a compiled twin by about 10 inferences per definition; against the
#: example's 6067 the ratio is 0.2861. Prior: 2605, the transliterated twin
#: this replaces.
BUDGET = 1736


def twin(m):
    """Store one answer out of two, then read back what was stored."""
    # (foo 1)
    m += S.foo(1)
    # (foo 2)
    m += S.foo(2)

    # (= (match-single $space $pat $ret)
    #    (let* (($x (match $space $pat $ret)) ($temp (cut))) $x))
    single = S["let*"](((V.x, S.match(V.space, V.pat, V.ret)), (V.temp, S.cut())), V.x)  # rung: a definition whose space, pattern and template are parameters has no compiled spelling
    m += equation(S["match-single"](V.space, V.pat, V.ret)).to(single)

    # !(let $x (match-single &self (foo $1) $1) (add-atom &self (bar $x)))
    # `let` over a value that answers once is a loop that runs once.
    for one in m.eval(S["match-single"](S[m.space_name], S.foo(V.one), V.one)):
        m += S.bar(one)

    # !(test (collapse (match &self (bar $1) (bar $1))) ((bar 1)))
    assert [S.bar(row.one) for row in m.query(S.bar(V.one))] == [S.bar(1)]
