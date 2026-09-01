"""Purpose: examples/ch16-events-and-standing-queries/01-event_catalog.metta in Python: the event layer's own declarations.

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

import metta
from metta import S, V
from metta.errors import EngineError
from metta.vocabularies import AgendaPolicy, Delivery, EventOrder


def twin(m):  # noqa: ARG001  -- the declarations live in the reflection space; the default handle stays untouched
    """Read the event declarations, then try to write an unsayable one."""
    reflection = metta.reflection

    # Delivery is drawn from messaging's own three promises, and order is the
    # second axis, because a channel may deliver every write out of order.
    assert [
        (row.a, row.b, row.c)
        for row in reflection[S.vocabulary(S.delivery, V.a, V.b, V.c)]
    ] == [(
        S[Delivery.at_most_once],
        S[Delivery.at_least_once],
        S[Delivery.per_write_exactly],
    )]
    assert [
        (row.a, row.b) for row in reflection[S.vocabulary(S.event_order, V.a, V.b)]
    ] == [(S[EventOrder.ordered], S[EventOrder.unordered])]
    assert [
        row.delivery for row in reflection[S.kind(S.events, V.ctx, V.delivery, V.order)]
    ] == [S.one_of(S.delivery)]

    # The value set is closed, so a promise nobody could act on is refused at
    # the write rather than stored as an atom that never matches.
    feed = metta.space(S.feed)
    refusal = None
    try:
        reflection += (S.events, feed, S.eventually)
    except EngineError as error:
        refusal = error
    assert refusal is not None

    # A native space needs no declaration and is watchable anyway: every write
    # into the engine's own store runs its write hooks, which is a fact about
    # this engine rather than a promise a provider is making.
    native = metta.space(S.native_events)
    native += (S.reading, 1)
    assert not reflection[S.events(native, V.d, V.o)]

    # Which reaction fires first is the second declaration, and its default is
    # STATED rather than accidental.
    assert [
        (row.a, row.b, row.c, row.d, row.e)
        for row in reflection[S.vocabulary(S.agenda_policy, V.a, V.b, V.c, V.d, V.e)]
    ] == [(
        S[AgendaPolicy.declaration],
        S[AgendaPolicy.recency],
        S[AgendaPolicy.specificity],
        S[AgendaPolicy.priority],
        S[AgendaPolicy.user],
    )]
    assert [
        (row.knob, row.default)
        for row in reflection[S.policy(S.reaction_order, V.knob, V.default)]
    ] == [(S.agenda, S[AgendaPolicy.declaration])]
    assert [
        row.policy for row in reflection[S.kind(S.agenda, V.ctx, V.policy, V.fn)]
    ] == [S.one_of(S.agenda_policy)]

    # A reaction carries its own priority as an optional fifth field, so every
    # (on ...) written before the agenda existed keeps its meaning.
    assert [
        row.priority
        for row in reflection[S.kind(S.on, V.ctx, V.pattern, V.op, V.priority)]
    ] == [S.optional(S.integer)]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2415 to 2426, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2426 to 2428, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 2428 to 2438, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 2438 to 2417 (-21), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2417 to 2432 (+15), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 2432 to 2437 (+5), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 2437 to 1993 (-444), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 1993 to 2033 (+40), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 2033
