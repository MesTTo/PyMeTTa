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
original means too. `repra` is an engine function named through the static
namespace, `fn.repra`, which reads and autocompletes without the engine having
to be running.

The two type declarations are written as the atoms they are. Annotations are
the decorator's own declaration door, but they emit ONE arrow per definition
and this head carries two, so no annotation says it. The residue table records
that against P14.9.
"""

from metta import Atom, S, arrow, fn, typed

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Declare two arrows for one head, specialize it, and find both on the copy."""

    @m.define
    def g(x):
        # (= (g $x) $x)
        return x

    # (: f (-> Atom Number Atom)) and (: f (-> Atom String Atom))
    # rung: below the ANNOTATION door, both declarations: this head carries two
    #   arrows and a Python signature emits one (residue, P14.9)
    m += typed(S.f, arrow(Atom, int, Atom))
    m += typed(S.f, arrow(Atom, str, Atom))

    @m.define
    def f(g, x):
        # (= (f $g $x) (repra ($g $x)))
        return fn.repra(g(x))

    # !(f g 42), the call that specializes it. A call answers a LAZY view and
    # creating one performs no engine work, so the answer has to be READ for
    # the specialization to happen at all; `.one()` reads it and states its
    # cardinality in the same breath.
    assert f(S.g, 42).one() == S.repra(S.g(42))

    specialized = S["f_Spec_[g]"]
    assert m[typed(specialized, arrow(Atom, int, Atom))]
    assert m[typed(specialized, arrow(Atom, str, Atom))]
