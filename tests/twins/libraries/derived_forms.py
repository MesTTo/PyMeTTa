"""The Python twin of examples/libraries/derived_forms.metta.

`once` is a form the compiler fuses AND a form MeTTa can write, and this file
swaps one for the other in a live session and shows the answers do not move.

`noisy` stays at the container door, recorded against P14.4: its body calls
`add-atom`, and a compiled body reaches a free name exactly as written, so a
hyphenated MeTTa name has no Python spelling.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 15606 to 15603, -3 (-0.02%), by the P14 twin-style
#: rewrite: reading the source's own anonymous variable as one: the let in (=
#: (noisy $x) ...) binds $_ where the previous twin renamed it $_1210, and an
#: A/B that renames it back restores 15606 exactly, so the whole move is
#: those three inferences. Prior: ADDED 2026-08-22 at 15606 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 15603


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Before the import, `once` is the compiler's own clause.
    # !(test (once (superpose (1 2 3))) 1)
    yield m.eval(S.test(S.once(S.superpose((1, 2, 3))), 1))

    # !(import! &self (library lib_derived))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_derived)))

    # After it, `once` is an ordinary MeTTa equation that rewrites the call into
    # `(take 1 ...)`, and it answers exactly the same thing.
    # !(test (once (superpose (1 2 3))) 1)
    yield m.eval(S.test(S.once(S.superpose((1, 2, 3))), 1))
    # !(test (collapse (once (superpose (1 2 3)))) (1))
    yield m.eval(S.test(S.collapse(S.once(S.superpose((1, 2, 3)))), (1,)))
    # !(test (collapse (once (empty))) ())
    yield m.eval(S.test(S.collapse(S.once(S.empty())), ()))

    # It is still the first answer of a generator that has side effects, so the
    # rest of the generator does not run.
    # !(bind! &seen (new-space))
    yield m.eval(S["bind!"](S["&seen"], S["new-space"]()))

    # (= (noisy $x) (let $_ (add-atom &seen (saw $x)) $x))
    m += equation(S.noisy(V.x)).to(
        S.let(V._, S["add-atom"](S["&seen"], S.saw(V.x)), V.x)
    )

    # !(test (once (superpose ((noisy a) (noisy b)))) a)
    yield m.eval(
        S.test(S.once(S.superpose((S.noisy(S.a), S.noisy(S.b)))), S.a)
    )
    # !(test (collapse (get-atoms &seen)) ((saw a)))
    yield m.eval(
        S.test(S.collapse(S["get-atoms"](S["&seen"])), (S.saw(S.a),))
    )

    # The swap is a session decision, not a per-call one: `add-translator-rule!`
    # registers globally. `remove-translator-rule!` puts the compiler's own
    # clause back in charge.
    # !(remove-translator-rule! once)
    yield m.eval(S["remove-translator-rule!"](S.once))

    # !(test (once (superpose (1 2 3))) 1)
    yield m.eval(S.test(S.once(S.superpose((1, 2, 3))), 1))
