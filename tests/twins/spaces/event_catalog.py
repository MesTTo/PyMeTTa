"""examples/spaces/event_catalog.metta in Python: the event layer's own declarations.

Whether a context can emit change events at all, and which reaction fires first
when several match one write, are both DECLARED rather than inferred, and the
catalog describes their shapes the way it describes every other kind. So the
whole file is reading and writing one space, and both are container doors.

Two claims are about what the catalog REFUSES. A value set is closed, so a
delivery promise nobody could act on is a loud error at the write, which at the
Python door is an exception carrying the checker's own sentence. And a native
space needs no declaration to be watchable, which shows up as the absence of a
row: `not reflection[...]` is the empty answer, and empty is a legitimate
answer here rather than a shape error.
"""

from petta import REFLECTION_SPACE, EngineError, S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6469 to 3259, -3210 (-49.6%), by the twin contract
#: change: nine `(test ...)` terms became nine Python `assert`s, so `test` left
#: the engine nine times and one `collapse`, one `catch` and one `if-error`
#: went with it, the refusal becoming an ordinary exception. The eight matches
#: and both writes stayed. Against the example's 18203 the ratio is 0.1790.
#: Prior: 6469, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3259


def twin(m):
    """Read the event declarations, then try to write an unsayable one."""
    reflection = m.space(REFLECTION_SPACE)

    # Delivery is drawn from messaging's own three promises, and order is the
    # second axis, because a channel may deliver every write out of order.
    assert [
        (row.a, row.b, row.c)
        for row in reflection[S.vocabulary(S.delivery, V.a, V.b, V.c)]
    ] == [(S["at-most-once"], S["at-least-once"], S["per-write-exactly"])]
    assert [
        (row.a, row.b) for row in reflection[S.vocabulary(S["event-order"], V.a, V.b)]
    ] == [(S.ordered, S.unordered)]
    assert [
        row.delivery for row in reflection[S.kind(S.events, V.ctx, V.delivery, V.order)]
    ] == [S["one-of"](S.delivery)]

    # The value set is closed, so a promise nobody could act on is refused at
    # the write rather than stored as an atom that never matches.
    feed = m.space("&feed")
    refusal = None
    try:
        reflection += (S.events, S[feed.space_name], S.eventually)
    except EngineError as error:
        refusal = error
    assert refusal is not None

    # A native space needs no declaration and is watchable anyway: every write
    # into the engine's own store runs its write hooks, which is a fact about
    # this engine rather than a promise a provider is making.
    native = m.space("&native-events")
    native += (S.reading, 1)
    assert not reflection[S.events(S[native.space_name], V.d, V.o)]

    # Which reaction fires first is the second declaration, and its default is
    # STATED rather than accidental.
    assert [
        (row.a, row.b, row.c, row.d, row.e)
        for row in reflection[S.vocabulary(S["agenda-policy"], V.a, V.b, V.c, V.d, V.e)]
    ] == [(S.declaration, S.recency, S.specificity, S.priority, S.user)]
    assert [
        (row.knob, row.default)
        for row in reflection[S.policy(S["reaction-order"], V.knob, V.default)]
    ] == [(S.agenda, S.declaration)]
    assert [
        row.policy for row in reflection[S.kind(S.agenda, V.ctx, V.policy, V.fn)]
    ] == [S["one-of"](S["agenda-policy"])]

    # A reaction carries its own priority as an optional fifth field, so every
    # (on ...) written before the agenda existed keeps its meaning.
    assert [
        row.priority
        for row in reflection[S.kind(S.on, V.ctx, V.pattern, V.op, V.priority)]
    ] == [S.optional(S.integer)]
