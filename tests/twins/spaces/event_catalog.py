"""The Python twin of examples/spaces/event_catalog.metta: the event layer declares itself.

Whether a context can emit change events at all, and which reaction fires first
when several match one write, are both DECLARED in the reflection space rather
than inferred, so a program reads exactly what the engine acts on. The value sets
are closed, so a promise nobody could act on is a loud error at the write.

The reflection space is a handle here and the one write goes through
`native += (S.reading, 1)`. The refusal is deliberately left as a term: it is an
assertion ABOUT a refused write, so it has to reach the write door the way the
example reaches it, through `catch`.
"""

from petta import REFLECTION_SPACE, S, V, expr

#: The answer group a write form contributes: `add-atom` answers the unit,
#: which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6716 to 6469, -247 (-3.7%), by the P14 twin-style
#: rewrite, and the whole delta is the one write: `!(add-atom &native-events
#: (reading 1))` moved to `native += (S.reading, 1)`, inside the 239-to-311 band
#: this folder measures across six files for a plain-atom write. The nine
#: assertions are the same terms spelled with named symbols and tuples.
#: Prior: ADDED 2026-08-22 at 6716 by the wave-3 spaces baseline.
BUDGET = 6469


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    reflection = m.space(REFLECTION_SPACE)
    here = S[reflection.space_name]
    one_of = S["one-of"]

    # Subscribability is DECLARED, with delivery drawn from messaging's own
    # three promises and order as the second axis.
    # !(test (match &petta (vocabulary delivery $a $b $c) ($a $b $c))
    #        (at-most-once at-least-once per-write-exactly))
    yield m.eval(
        S.test(
            S.match(here, S.vocabulary(S.delivery, V.a, V.b, V.c), (V.a, V.b, V.c)),
            (S["at-most-once"], S["at-least-once"], S["per-write-exactly"]),
        )
    )
    # !(test (match &petta (vocabulary event-order $a $b) ($a $b)) (ordered unordered))
    yield m.eval(
        S.test(
            S.match(here, S.vocabulary(S["event-order"], V.a, V.b), (V.a, V.b)),
            (S.ordered, S.unordered),
        )
    )
    # !(test (match &petta (kind events $ctx $delivery $order) $delivery)
    #        (one-of delivery))
    yield m.eval(
        S.test(
            S.match(here, S.kind(S.events, V.ctx, V.delivery, V.order), V.delivery),
            one_of(S.delivery),
        )
    )

    # The value set is closed, so a promise nobody could act on is a loud error
    # at the write.
    # !(test (if-error (catch (add-atom &petta (events &feed eventually)))
    #                  refused admitted)
    #        refused)
    yield m.eval(
        S.test(
            S["if-error"](
                S.catch(
                    S["add-atom"](here, S.events(S["&feed"], S.eventually))
                ),
                S.refused,
                S.admitted,
            ),
            S.refused,
        )
    )

    # A native space needs no declaration and is watchable anyway: every write
    # into the engine's own store already runs its write hooks.
    # !(add-atom &native-events (reading 1))
    native = m.space("&native-events")
    native += (S.reading, 1)
    yield WROTE

    # !(test (collapse (match &petta (events &native-events $d $o) declared)) ())
    yield m.eval(
        S.test(
            S.collapse(
                S.match(
                    here,
                    S.events(S[native.space_name], V.d, V.o),
                    S.declared,
                )
            ),
            (),
        )
    )

    # Which reaction fires first is the second declaration, and its default is
    # STATED rather than accidental.
    # !(test (match &petta (vocabulary agenda-policy $a $b $c $d $e) ($a $b $c $d $e))
    #        (declaration recency specificity priority user))
    yield m.eval(
        S.test(
            S.match(
                here,
                S.vocabulary(S["agenda-policy"], V.a, V.b, V.c, V.d, V.e),
                (V.a, V.b, V.c, V.d, V.e),
            ),
            (S.declaration, S.recency, S.specificity, S.priority, S.user),
        )
    )
    # !(test (match &petta (policy reaction-order $knob $default) ($knob $default))
    #        (agenda declaration))
    yield m.eval(
        S.test(
            S.match(
                here,
                S.policy(S["reaction-order"], V.knob, V.default),
                (V.knob, V.default),
            ),
            (S.agenda, S.declaration),
        )
    )
    # !(test (match &petta (kind agenda $ctx $policy $fn) $policy)
    #        (one-of agenda-policy))
    yield m.eval(
        S.test(
            S.match(here, S.kind(S.agenda, V.ctx, V.policy, V.fn), V.policy),
            one_of(S["agenda-policy"]),
        )
    )

    # A reaction carries its own priority as an optional fifth field, so every
    # (on ...) written before the agenda existed keeps its meaning.
    # !(test (match &petta (kind on $ctx $pattern $op $priority) $priority)
    #        (optional integer))
    yield m.eval(
        S.test(
            S.match(
                here,
                S.kind(S.on, V.ctx, V.pattern, V.op, V.priority),
                V.priority,
            ),
            S.optional(S.integer),
        )
    )
