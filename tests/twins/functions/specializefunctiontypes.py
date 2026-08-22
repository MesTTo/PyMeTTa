"""examples/functions/specializefunctiontypes.metta in Python: types survive specialization.

`f` applies its first argument, so calling `(f g 42)` specializes `f` on `g`,
and the specialized function keeps `f`'s TYPES: both declared arrows reappear
on `f_Spec_[g]`. Asking whether they are there is a match over the space, and
`m[pattern]` is that door: a query with no rows is falsy, so the claim reads
as an ordinary Python truth test.

Both definitions are ordinary Python functions. `f`'s parameter is named `g`
exactly as the original's variable is, so inside the body `g` is that
parameter and `g(x)` is `($g $x)`, the variable-head application; the `g`
defined above it is a different thing with the same name, which is what the
original means too.

The two type declarations are written as the atoms they are. Annotations are
the decorator's own declaration door, but they emit ONE arrow per definition
and this head carries two, so no annotation says it. The residue table records
that against P14.9.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6016 to 5108, -908 (-15.1%), by the twin contract
#: change: two `test` wrappers left the engine for `assert` and both `match
#: &self` forms became `m[pattern]`, the subscript door, whose emptiness is
#: Python's own truth test. Against the example's 7609 the ratio is 0.6713
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 5108


def twin(m):
    """Declare two arrows for one head, specialize it, and find both on the copy."""
    repra = m.fn("repra")

    @m.define
    def g(x):
        # (= (g $x) $x)
        return x

    # (: f (-> Atom Number Atom)) and (: f (-> Atom String Atom))
    # rung: below the ANNOTATION door, both declarations: this head carries two
    #   arrows and a Python signature emits one (residue, P14.9)
    m += S[":"](S.f, S["->"](S.Atom, S.Number, S.Atom))
    m += S[":"](S.f, S["->"](S.Atom, S.String, S.Atom))

    @m.define
    def f(g, x):
        # (= (f $g $x) (repra ($g $x)))
        return repra(g(x))

    # The call that specializes it.
    f(S.g, 42)

    specialized = S["f_Spec_[g]"]
    assert m[S[":"](specialized, S["->"](S.Atom, S.Number, S.Atom))]
    assert m[S[":"](specialized, S["->"](S.Atom, S.String, S.Atom))]
