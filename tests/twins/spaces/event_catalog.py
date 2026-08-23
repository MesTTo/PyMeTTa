"""Purpose: examples/spaces/event_catalog.metta in Python: the event layer's own declarations.

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

The two spaces the declarations are ABOUT go into those declarations as
handles, because a space is an ordinary term operand.
"""

import petta
from petta import S, V
from petta.errors import EngineError

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):  # noqa: ARG001  -- the declarations live in the reflection space; the default handle stays untouched
    """Read the event declarations, then try to write an unsayable one."""
    reflection = petta.reflection

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
    feed = petta.space("&feed")
    refusal = None
    try:
        reflection += (S.events, feed, S.eventually)
    except EngineError as error:
        refusal = error
    assert refusal is not None

    # A native space needs no declaration and is watchable anyway: every write
    # into the engine's own store runs its write hooks, which is a fact about
    # this engine rather than a promise a provider is making.
    native = petta.space("&native-events")
    native += (S.reading, 1)
    assert not reflection[S.events(native, V.d, V.o)]

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
