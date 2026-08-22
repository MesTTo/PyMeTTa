"""examples/libraries/test_memo_variant_nonground.metta in Python: keying on structure.

`shape-kind` answers `pair` for anything shaped like a Pair, whatever the
variable inside is called, so two non-ground calls that differ only in variable
name are one cache key.

The equation goes to the container door for two reasons already in the residue
table: its head carries a PATTERN, `(shape-kind (Pair $x $y))`, where a
decorated function's parameters are always plain variables; and its body is the
bare lowercase symbol `pair`, which a compiled body resolves as a function.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 126917 to 126700, -217 (-0.17%), by the idiomatic
#: rewrite: two `test` wrappers left the engine for `assert`; the equation
#: keeps its pattern head at the container door, so nothing else moved.
#: Measured min-of-three with the MORK backend linked into this worktree,
#: which the earlier figure may not have been. Prior: 126917 was the last
#: figure for the generator twin that yielded `m.eval(S.test(...))` once per
#: runnable form.
BUDGET = 126700


def twin(m):
    """Ask the same shape twice, under two different variable names."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += equation(S["shape-kind"](S.Pair(V.x, V.y))).to(S.pair)
    m.eval(S.memoize(S["shape-kind"]))

    kind = m.fn("shape-kind")
    assert kind(S.Pair(V.a, 2)) == S.pair
    assert kind(S.Pair(V.b, 2)) == S.pair
