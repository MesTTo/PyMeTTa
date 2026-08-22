"""The Python twin of examples/types/typing_rules.metta: a user typing rule.

The checker ordinary typed calls go through is itself extensible.
`typing-rule-demo` accepts anything while nothing refuses it; adding a rule
that refuses `%Undefined%` where `DemoPayload` is expected turns the same call
into a `BadArgType` error naming the rule and its reason; removing the rule
restores the first answer. Three calls, one program, and the middle one is the
only thing that changed.

Everything here is a term. `add-typing-rule!` and `remove-typing-rule!` are
directives with no dedicated Python door, which the term builder covers, and
the equation's body `(seen $value)` is a lowercase CONSTRUCTOR application: a
compiled body resolves a lowercase free name as a function and reads a
capitalised one as a constructor, so it has no spelling for this one (wave one
recorded that against P14.4 for `time_and_pragmas`).
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5174 to 5359, +185, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 5174 by 47554fc's control/types twin baseline.
BUDGET = 5359


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: typing-rule-demo (-> DemoPayload Atom))
    m += S[":"](S["typing-rule-demo"], S["->"](S.DemoPayload, S.Atom))
    # (= (typing-rule-demo $value) (seen $value))
    m += equation(S["typing-rule-demo"](V.value)).to(S.seen(V.value))

    # !(test (typing-rule-demo unknown-demo) (seen unknown-demo))
    yield m.eval(
        S.test(
            S["typing-rule-demo"](S["unknown-demo"]),
            S.seen(S["unknown-demo"]),
        )
    )

    # !(add-typing-rule! deny-unknown-demo ordinary %Undefined% DemoPayload
    #                    (refuse unknown-demo-is-not-a-payload))
    # answers (True)
    yield m.eval(
        S["add-typing-rule!"](
            S["deny-unknown-demo"],
            S.ordinary,
            S["%Undefined%"],
            S.DemoPayload,
            S.refuse(S["unknown-demo-is-not-a-payload"]),
        )
    )

    # !(test (typing-rule-demo unknown-demo)
    #        (Error (typing-rule-demo unknown-demo)
    #               (BadArgType 1 DemoPayload %Undefined%
    #                (TypingRuleRefusal deny-unknown-demo
    #                                     unknown-demo-is-not-a-payload))))
    yield m.eval(
        S.test(
            S["typing-rule-demo"](S["unknown-demo"]),
            S.Error(
                S["typing-rule-demo"](S["unknown-demo"]),
                S.BadArgType(
                    1,
                    S.DemoPayload,
                    S["%Undefined%"],
                    S.TypingRuleRefusal(
                        S["deny-unknown-demo"],
                        S["unknown-demo-is-not-a-payload"],
                    ),
                ),
            ),
        )
    )

    # !(remove-typing-rule! deny-unknown-demo) answers (True)
    yield m.eval(S["remove-typing-rule!"](S["deny-unknown-demo"]))

    # !(test (typing-rule-demo unknown-demo) (seen unknown-demo))
    yield m.eval(
        S.test(
            S["typing-rule-demo"](S["unknown-demo"]),
            S.seen(S["unknown-demo"]),
        )
    )
