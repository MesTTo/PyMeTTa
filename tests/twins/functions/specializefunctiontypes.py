"""The Python twin of examples/functions/specializefunctiontypes.metta.

`f` applies its first argument, so calling `(f g 42)` specializes `f` on `g`
and the specialized function keeps `f`'s TYPES: both declared arrows reappear
on `f_Spec_[g]`, which is what the two `match` forms assert.

Both definitions are ordinary Python functions. `f`'s parameter is named `g`
exactly as the original's variable is, so inside the body `g` is that
parameter and `g(x)` is `($g $x)`, the variable-head application; the
module-level `g` above it is a different thing with the same name, which is
what the original means too.

The two type declarations are written as the atoms they are. Annotations are
the decorator's own declaration door, but they emit ONE arrow per definition
and this head carries two, so there is no annotation that says it. The residue
table already records that against P14.9.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3987 to 6016, +2029 (+50.89%), all of it the two
#: definitions moving onto the decorator. `g` costs 321 as an equation atom
#: and 1950 decorated, +1629, nearly all of it the one-time setup the FIRST
#: decorated definition in a process pays (2244 against the atom door's 600
#: for one equation, where every later one costs 793 against 600); `f` costs
#: 452 against 852, +400. The two declarations and all three runnable forms
#: are unchanged, so the percentage is large only because this twin is small:
#: the lane's parity still reads 0.79 of the original. Prior: ADDED
#: 2026-08-22 at 3987 by 7f15dc1's wave-3 baseline.
BUDGET = 6016


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    repra = m.fn("repra")

    @m.define
    def g(x):
        # (= (g $x) $x)
        return x

    # (: f (-> Atom Number Atom))
    # rung: below the ANNOTATION door, both declarations: this head carries two arrows
    #   and a Python signature emits one (residue, P14.9)
    m += S[":"](S.f, S["->"](S.Atom, S.Number, S.Atom))
    # (: f (-> Atom String Atom))
    m += S[":"](S.f, S["->"](S.Atom, S.String, S.Atom))

    @m.define
    def f(g, x):
        # (= (f $g $x) (repra ($g $x)))
        return repra(g(x))

    # !(f g 42)
    yield m.eval(S.f(S.g, 42))

    # !(test (match &self (: f_Spec_[g] (-> Atom Number Atom)) ok) ok)
    yield m.eval(
        S.test(
            S.match(
                S["&self"],
                S[":"](S["f_Spec_[g]"], S["->"](S.Atom, S.Number, S.Atom)),
                S.ok,
            ),
            S.ok,
        )
    )

    # !(test (match &self (: f_Spec_[g] (-> Atom String Atom)) ok) ok)
    yield m.eval(
        S.test(
            S.match(
                S["&self"],
                S[":"](S["f_Spec_[g]"], S["->"](S.Atom, S.String, S.Atom)),
                S.ok,
            ),
            S.ok,
        )
    )
