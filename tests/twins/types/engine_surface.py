"""The Python twin of examples/types/engine_surface.metta: types without a space.

The engine's own type surface is reported without being imported: the engine
reads `lib_builtin_types` at boot into facts that `get-type` consults LAST, so
`get-type` answers the engine's types while `&self` stays the program's own
space. That last sentence is what the file's two final claims assert, and it is
why nothing in this twin may add an atom the original does not add.

That rules out the annotation door here, which the other type twins do use:
`@m.define` writes a `(: name (-> ...))` atom into the space, and
`!(test (collapse (match &self (: $n $t) $n)) (program-own-type))` counts the
`(: ...)` atoms in `&self` exactly. So both program declarations are written as
the atoms they are, and every query is a term.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 15430 to 18710, +3280, by P14.8's typed state cell
#: plus fuel-scope parity: the source grew from two state queries to five; a
#: 22-form current-tree counterfactual costs 16330 (+900), and the three new
#: forms add 2380. The +900 includes m.eval's per-reduction fuel charge net of
#: b_getval/2's two-inference-per-runnable-form saving. Prior: ADDED 2026-08-22
#: at 15430 by 47554fc's control/types twin baseline.
BUDGET = 18710


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    kind = S["get-type"]
    undefined = S["%Undefined%"]

    # Special forms are compiled by the translator and have no registry
    # entry at all, so they were the least reachable half of the surface.
    # !(test (get-type if) (-> Bool Atom Atom $t))
    yield m.eval(
        S.test(
            kind(S["if"]),
            S["->"](S.Bool, S.Atom, S.Atom, V.t),
        )
    )
    # !(test (get-type let) (-> Atom %Undefined% Atom %Undefined%))
    yield m.eval(
        S.test(
            kind(S["let"]),
            S["->"](S.Atom, undefined, S.Atom, undefined),
        )
    )
    # !(test (get-type chain) (-> Atom Variable Atom %Undefined%))
    yield m.eval(
        S.test(
            kind(S["chain"]),
            S["->"](S.Atom, S.Variable, S.Atom, undefined),
        )
    )
    # !(test (get-type quote) (-> Atom Atom))
    yield m.eval(
        S.test(kind(S["quote"]), S["->"](S.Atom, S.Atom))
    )
    # !(test (get-type collapse) (-> Atom Atom))
    yield m.eval(
        S.test(kind(S["collapse"]), S["->"](S.Atom, S.Atom))
    )
    # !(test (get-type superpose) (-> Expression %Undefined%))
    yield m.eval(
        S.test(
            kind(S["superpose"]),
            S["->"](S.Expression, undefined),
        )
    )
    # !(test (get-type match) (-> SpaceType Atom Atom %Undefined%))
    yield m.eval(
        S.test(
            kind(S["match"]),
            S["->"](S.SpaceType, S.Atom, S.Atom, undefined),
        )
    )
    # !(test (get-type map-atom) (-> Expression Variable Atom Expression))
    yield m.eval(
        S.test(
            kind(S["map-atom"]),
            S["->"](
                S.Expression, S.Variable, S.Atom, S.Expression
            ),
        )
    )

    # Expression structure, from the reference corelib dump.
    # !(test (get-type car-atom) (-> Expression %Undefined%))
    yield m.eval(
        S.test(
            kind(S["car-atom"]), S["->"](S.Expression, undefined)
        )
    )
    # !(test (get-type cdr-atom) (-> Expression Expression))
    yield m.eval(
        S.test(
            kind(S["cdr-atom"]),
            S["->"](S.Expression, S.Expression),
        )
    )
    # !(test (get-type cons-atom) (-> Atom Expression Atom))
    yield m.eval(
        S.test(
            kind(S["cons-atom"]),
            S["->"](S.Atom, S.Expression, S.Atom),
        )
    )
    # !(test (get-type size-atom) (-> Expression Number))
    yield m.eval(
        S.test(
            kind(S["size-atom"]),
            S["->"](S.Expression, S.Number),
        )
    )
    # !(test (get-type index-atom) (-> Expression Number Atom))
    yield m.eval(
        S.test(
            kind(S["index-atom"]),
            S["->"](S.Expression, S.Number, S.Atom),
        )
    )

    # PeTTa's own, with no dump entry to take.
    # !(test (get-type sort-atom) (-> Expression Expression))
    yield m.eval(
        S.test(
            kind(S["sort-atom"]),
            S["->"](S.Expression, S.Expression),
        )
    )
    # !(test (get-type is-var) (-> Atom Bool))
    yield m.eval(
        S.test(kind(S["is-var"]), S["->"](S.Atom, S.Bool))
    )
    # !(test (get-type repr) (-> Atom String))
    yield m.eval(
        S.test(kind(S["repr"]), S["->"](S.Atom, S.String))
    )
    # !(test (get-type current-time) (-> Number))
    yield m.eval(
        S.test(kind(S["current-time"]), S["->"](S.Number))
    )

    # The state cell is a value whose type says what it holds, matching the
    # dump's parametric StateMonad signatures.
    # !(test (get-type new-state) (-> $t (StateMonad $t)))
    yield m.eval(
        S.test(
            kind(S["new-state"]),
            S["->"](V.t, S.StateMonad(V.t)),
        )
    )
    # !(test (get-type change-state!)
    #        (-> (StateMonad $t) $t (StateMonad $t)))
    yield m.eval(
        S.test(
            kind(S["change-state!"]),
            S["->"](S.StateMonad(V.t), V.t, S.StateMonad(V.t)),
        )
    )
    # !(test (get-type get-state) (-> (StateMonad $t) $t))
    yield m.eval(
        S.test(
            kind(S["get-state"]), S["->"](S.StateMonad(V.t), V.t)
        )
    )
    # !(test (get-type (new-state 5)) (StateMonad Number))
    yield m.eval(
        S.test(kind(S["new-state"](5)), S.StateMonad(S.Number))
    )
    # !(test (get-type (new-state "hi")) (StateMonad String))
    yield m.eval(
        S.test(
            kind(S["new-state"](val("hi"))), S.StateMonad(S.String)
        )
    )

    # The surface is FACTS, not atoms in &self: a program still sees only
    # its own space.
    # (: program-own-type MyType)
    m += S[":"](S["program-own-type"], S.MyType)
    # !(test (collapse (match &self (: $n $t) $n)) (program-own-type))
    yield m.eval(
        S.test(
            S["collapse"](
                S["match"](
                    S["&self"], S[":"](V.n, V.t), V.n
                )
            ),
            expr(S["program-own-type"]),
        )
    )

    # And a program's own declaration is answered ahead of the engine's,
    # because the table is consulted last.
    # (: car-atom MyOverride)
    m += S[":"](S["car-atom"], S.MyOverride)
    # !(test (car-atom (a b)) a)
    yield m.eval(
        S.test(S["car-atom"](expr(S.a, S.b)), S.a)
    )
    # !(test (collapse (get-type car-atom)) (MyOverride (-> Expression %Undefined%)))
    yield m.eval(
        S.test(
            S["collapse"](kind(S["car-atom"])),
            expr(
                S.MyOverride,
                S["->"](S.Expression, undefined),
            ),
        )
    )
