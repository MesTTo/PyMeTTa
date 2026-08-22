"""The Python twin of examples/control/letstarcomputed.metta: bindings as a value.

The bindings of a `let*` are usually written out, and then they are syntax.
They do not have to be: a bindings argument that arrives as a VALUE is
rewritten when it arrives, so a program can decide its own bindings while it
runs, which is what lets it give `let*` another name.

`mylet`'s declaration `(: mylet (-> Atom Atom %Undefined%))` is the metatype
that stops the arguments evaluating on the way in, and it is written as the
atom it is. The annotation door writes the same atom where the equation is a
compiled function, `def mylet(bindings: Atom, body: Atom)`, since `Atom` the
Python class projects to `Atom` the MeTTa metatype; this equation is not one,
because its body applies `let*` and `let*` is not a Python identifier.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8608 to 8844, +236, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 8608 by 47554fc's control/types twin baseline.
BUDGET = 8844


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: mylet (-> Atom Atom %Undefined%))
    m += S[":"](S.mylet, S["->"](S.Atom, S.Atom, S["%Undefined%"]))
    # (= (mylet $bindings $body) (let* $bindings $body))
    m += equation(S.mylet(V.bindings, V.body)).to(S["let*"](V.bindings, V.body))

    # !(test (mylet (($x 1) ($y 2)) (+ $x $y)) 3)
    yield m.eval(
        S.test(
            S.mylet(((V.x, 1), (V.y, 2)), V.x + V.y),
            3,
        )
    )

    # Handed over or written out, the same bindings answer the same thing.
    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    yield m.eval(
        S.test(
            S["let*"](((V.x, 1), (V.y, 2)), V.x + V.y),
            3,
        )
    )

    # A binding is a (pattern value) pair, not only (variable value), and a
    # pattern that does not match gives the whole form no answer.
    # !(test (mylet ((($a $b) (1 2))) $b) 2)
    yield m.eval(S.test(S.mylet((((V.a, V.b), (1, 2)),), V.b), 2))
    # !(test (mylet ((5 5)) matched) matched)
    yield m.eval(S.test(S.mylet(((5, 5),), S.matched), S.matched))
    # !(test (collapse (mylet ((5 6)) matched)) ())
    yield m.eval(S.test(S.collapse(S.mylet(((5, 6),), S.matched)), ()))

    # Without the `Atom` metatype the arguments evaluate on the way in, so
    # this is the other way to hand bindings over: `noeval` carries them as
    # data, and the body is a variable the same call site wrote.
    # (= (mylet-evaluating $bindings $body) (let* $bindings $body))
    m += equation(S["mylet-evaluating"](V.bindings, V.body)).to(S["let*"](V.bindings, V.body))

    # !(test (mylet-evaluating (noeval (($x 1))) $x) 1)
    yield m.eval(
        S.test(
            S["mylet-evaluating"](S.noeval(((V.x, 1),)), V.x),
            1,
        )
    )

    # Bindings are checked when they arrive, because nothing after that
    # point can check them.
    # !(test (car-atom (catch (mylet-evaluating (noeval ((1 2 3))) done))) Error)
    yield m.eval(
        S.test(
            S["car-atom"](S.catch(S["mylet-evaluating"](S.noeval(((1, 2, 3),)), S.done))),
            S.Error,
        )
    )

    # A bindings argument that is no list at all is not bindings, it is a
    # program using the name as data, and it stays the unapplied form it
    # always was.
    # !(test (repr (let* foo ok)) "(partial let* (foo ok))")
    yield m.eval(
        S.test(
            S.repr(S["let*"](S.foo, S.ok)),
            val("(partial let* (foo ok))"),
        )
    )
