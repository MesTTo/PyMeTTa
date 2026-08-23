"""examples/libraries/test_memo_variant_nonground.metta in Python: keying on structure.

`shape-kind` answers `pair` for anything shaped like a Pair, whatever the
variable inside is called, so two non-ground calls that differ only in variable
name are one cache key.

The equation goes to the container door for two reasons already in the residue
table: its head carries a PATTERN, `(shape-kind (Pair $x $y))`, where a
decorated function's parameters are always plain variables; and its body is the
bare lowercase symbol `pair`, which a compiled body resolves as a function.

DEFECT, and it decides both claims. They ought to read
`m.fn.shape_kind(S.Pair(V.a, 2))`, the call door. The argument CARRIES a
variable without the answer depending on it, and the answer view reads every
variable in a call as one of the caller's own, so the call door answers a
binding row for `$a` where the claim is about the answer `pair`. Until it
distinguishes them, both are stated as the terms they are, which is also the
only way to keep the example's point: the two calls differ ONLY in the
variable's name.
"""

from petta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Ask the same shape twice, under two different variable names."""
    m.eval(S["import!"](m, S.library(S["lib_memo"])))

    m += equation(S["shape-kind"](S.Pair(V.x, V.y))).to(S.pair)
    m.eval(S.memoize(S["shape-kind"]))

    assert m.eval(S["shape-kind"](S.Pair(V.a, 2))) == [S.pair]
    assert m.eval(S["shape-kind"](S.Pair(V.b, 2))) == [S.pair]
