"""Purpose: examples/spaces/pre_add_hooks.metta in Python: arbitrary MeTTa at the write door.

A pre-add hook claims the write door of one space for one function of one
argument, the incoming atom. Every write consults it first, and the handler
answers one of four verdicts: `accept()` lets the atom in as offered,
`accept(atom)` lets a TRANSFORMED atom in instead, `refuse(words)` throws
carrying the handler's own words, and `drop()` skips the write silently while
the caller sees success.

So the writes here are ordinary `space += atom`, and what the example proves is
what happens on the other side of that operator. A refusal is an exception with
the handler's sentence in it, which is the loud spelling `catch` and `repr`
reach in the original; a drop is a write that leaves the space unchanged.

The handler is one compiled definition where the original writes four
equations, and the door picked the form: four literal head patterns at one
arity would overlap if they were written as bare coexisting equations, so a
Python `match` statement is the spelling and it lowers to MeTTa's own case
tower. The tower has no fallback arm, exactly as the four equations have no
catch-all, which is what leaves `(uncovered 9)` a stuck state that says so.
`@pool.pre_add` above `@m.define` is the claim itself, so the handler keeps the
module that owns its equations and the space keeps its write door.

Releasing the claim is the one line that still names an engine function.
`undeclare-pre-add!` has no Python door (residue, P14.10); PERFECT is a
`space.pre_add` that answers something releasable, the way the ops scopes
release theirs.

Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import S, V, accept, drop, refuse
from metta.errors import EngineError

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11806 to 11863, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11863 to 11872, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11872 to 11843, on the release tree:
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
#: RE-PINNED 2026-08-25, 11843 to 11848, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 11848

#: The three sentences this file's refusals print. Each is the Python door's
#: own wording rather than the Error atom the original reads with `repr`, and
#: each prints the offered atom in the wire's list form, `[secret,1]` where
#: engine-exact text would say `(secret 1)` [measured 2026-08-24: unchanged
#: under the compiled judge and the pre_add claim door; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
NO_SECRETS = "&pool refused [secret,1]: no secrets in this pool"
UNCOVERED = (
    "the pre-add hook on &pool is claimed by guard, whose equations do not "
    "cover [uncovered,9]; a request no rule covers is a stuck state that says "
    "so, so cover the shape or give the handler its own catch-all"
)
CLAIMED = (
    "guard already claims the pre-add hook on &pool and other-guard tried to "
    "claim it too; one claimant per name, checked when the claim is made, so "
    "undeclare the standing one first"
)


def twin(m):
    """Claim a space's write door, then write four atoms it judges."""
    pool = metta.space(S.pool)

    # (= (guard (secret $x)) (refuse "no secrets in this pool"))
    # (= (guard (raw $x))    (accept (cooked $x)))
    # (= (guard (dup $x))    (drop))
    # (= (guard (plain $x))  (accept))
    @pool.pre_add
    @m.define
    def guard(atom):
        match atom:
            case (S.secret, _):
                return refuse("no secrets in this pool")
            case (S.raw, x):
                return accept(S.cooked(x))
            case (S.dup, _):
                return drop()
            case (S.plain, _):
                return accept()

    # An accepted atom lands as offered.
    pool += (S.plain, 1)
    assert [row.x for row in pool[S.plain(V.x)]] == [1]

    # A transformed atom lands in the handler's chosen form, and the handler's
    # output is not re-asked: one decision per request, the way a database
    # BEFORE trigger's modified row does not re-fire the trigger.
    pool += (S.raw, 7)
    assert [row.x for row in pool[S.cooked(V.x)]] == [7]

    # A dropped atom is skipped and the caller sees the success an accepted
    # add answers, which is how set semantics is written as a rule.
    pool += (S.dup, 3)
    assert not pool[S.dup(V.x)]

    # A refusal carries the handler's own sentence to the caller.
    refusal = None
    try:
        pool += (S.secret, 1)
    except EngineError as error:
        refusal = error
    assert str(refusal) == NO_SECRETS

    # A claimed handler whose equations do not cover the atom is a stuck state
    # that says so, naming the space, the slot, the handler and the atom.
    stuck = None
    try:
        pool += (S.uncovered, 9)
    except EngineError as error:
        stuck = error
    assert str(stuck) == UNCOVERED

    # One claimant per name, checked when the claim is made: a second claimant
    # is refused with both named, never raced at call time.
    @m.define
    def other_guard(_atom):
        return accept()

    conflict = None
    try:
        pool.pre_add(other_guard)
    except EngineError as error:
        conflict = error
    assert str(conflict) == CLAIMED

    # Undeclaring is explicit and frees the claim; the space is direct again.
    m.fn.undeclare_pre_add(pool).one()
    pool += (S.uncovered, 10)
    assert [row.x for row in pool[S.uncovered(V.x)]] == [10]
