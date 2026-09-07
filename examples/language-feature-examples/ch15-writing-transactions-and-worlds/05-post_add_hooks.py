"""examples/ch15-writing-transactions-and-worlds/05-post_add_hooks.metta in Python: the four verdicts read against a LANDED atom.

The handler is one compiled definition where the original writes four
equations, the same shape `03-pre_add_hooks.py` uses and for the same reason:
four literal head patterns at one arity would overlap as bare coexisting
equations, so a Python `match` is the spelling and it lowers to MeTTa's own
case tower, with no fallback arm exactly as the four equations have none.

TWO lines still name an engine function. `pre-add` has a claim door,
`@space.pre_add`, and post-add has NONE, so both the claim and its release go
through `m.fn` here; the residue table records it against P14.10. PERFECT is
a `space.post_add` beside the one that exists.

The stored equations differ from the original's on purpose and for the same
reason the pre-add twin's do: four literal head patterns compile to one case
tower, which is one equation where the original has four. The tower has no
fallback arm, which is what keeps `(uncovered 9)` a stuck state.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, accept, drop, refuse
from metta.errors import EngineError

#: The two sentences this file's refusals print, in the Python door's own
#: wording rather than the Error atom the original reads with `repr`.
NO_SECRETS = "&pool refused [secret,1]: no secrets survive the audit"
UNCOVERED = (
    "the post-add hook on &pool is claimed by audit, whose equations do not "
    "cover [uncovered,9]; a request no rule covers is a stuck state that says "
    "so, so cover the shape or give the handler its own catch-all"
)
CLAIMED = (
    "audit already claims the post-add hook on &pool and other-audit tried to "
    "claim it too; one claimant per name, checked when the claim is made, so "
    "undeclare the standing one first"
)


def twin(m):
    """Accept, transform, drop, refuse, get stuck, and undeclare."""
    pool = m.metta.space(S.pool)

    # (= (audit (raw $x))    (accept (cooked $x)))
    # (= (audit (secret $x)) (refuse "no secrets survive the audit"))
    # (= (audit (dup $x))    (drop))
    # (= (audit (plain $x))  (accept))
    @m.define
    def audit(atom):
        match atom:
            case (S.raw, x):
                return accept(S.cooked(x))
            case (S.secret, _):
                return refuse("no secrets survive the audit")
            case (S.dup, _):
                return drop()
            case (S.plain, _):
                return accept()

    m.fn.declare_post_add(pool, S.audit).one()  # rung: post-add has no claim door

    # (accept) leaves the landed atom where it is.
    pool += (S.plain, 1)
    assert [row.x for row in pool[S.plain(V.x)]] == [1]

    # (accept <atom>) REPLACES it: what landed is removed and the handler's
    # is written through the same door, granted so the hook does not fire on
    # its own output.
    pool += (S.raw, 7)
    assert [row.x for row in pool[S.cooked(V.x)]] == [7]
    assert not pool[S.raw(V.x)]

    # (drop) removes what landed, so the caller still sees the success of a
    # write that leaves nothing behind.
    pool += (S.dup, 3)
    assert not pool[S.dup(V.x)]

    # (refuse <words>) throws with the handler's own sentence, and the write
    # is undone first: an audited-and-rejected atom is not left behind.
    refusal = None
    try:
        pool += (S.secret, 1)
    except EngineError as error:
        refusal = error
    assert str(refusal) == NO_SECRETS
    assert not pool[S.secret(V.x)]

    # A handler with no equation for the atom is a stuck state that names the
    # space, the slot, the handler and the atom -- and the write is undone on
    # that path too, which is the difference from the pre phase.
    stuck = None
    try:
        pool += (S.uncovered, 9)
    except EngineError as error:
        stuck = error
    assert str(stuck) == UNCOVERED
    assert not pool[S.uncovered(V.x)]

    # One claimant per name here as well, checked when the claim is made.
    @m.define
    def other_audit(_atom):
        # (= (other-audit $a) (accept))
        return accept()

    conflict = None
    try:
        m.fn.declare_post_add(pool, S.other_audit).one()  # rung: no claim door
    except EngineError as error:
        conflict = error
    assert str(conflict) == CLAIMED

    # The two slots are independent, so a space can carry both: the pre hook
    # decides what is allowed in and the post hook decides what to do about
    # what got in. The post phase runs only when the pre phase wrote the atom
    # AS OFFERED, so a pre transform is not audited twice.
    @pool.pre_add
    @m.define
    def gate(atom):
        # (= (gate (raw $x)) (accept)), and two more
        match atom:
            case (S.raw, _):
                return accept()
            case (S.banned, _):
                return drop()
            case (S.plain, _):
                return accept()

    pool += (S.raw, 8)
    assert [row.x for row in pool[S.cooked(V.x)]] == [7, 8]
    pool += (S.banned, 1)
    assert not pool[S.banned(V.x)]

    # Undeclaring is explicit and idempotent, and it frees the claim.
    m.fn.undeclare_post_add(pool).one()  # rung: post-add has no release door
    m.fn.undeclare_pre_add(pool).one()
    pool += (S.uncovered, 10)
    assert [row.x for row in pool[S.uncovered(V.x)]] == [10]
    m.fn.undeclare_post_add(pool).one()


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 11488 inferences, 0.7257x the example's 15830; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 11488 to 11709 (+221), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 11709 to 11502 (-207), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=WORKTREE].
BUDGET = 11502

#: DIVERGED 2026-09-08, the example holds 7 atoms the twin does not (7 =) and
#: the twin holds 2 atoms the example does not (2 =): re-settled on the tree
#: that merged the twins burn-down after the every-atom, gate-hygiene and
#: catalog-types merges; the census below is what the two spaces hold apart on
#: that tree, in the burn-down's own classes: knowledge rows the twin's file
#: states (an annotation is a (: name ...) row, a docstring an (@doc ...) row)
#: and lowering shapes an idiomatic Python program compiles to [measured
#: 2026-09-08: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
DIVERGENCE = "1a22f1d1d6ff3172a8c7bde1260abe1d6a7b97ea2d6f1c97e095de963c767345"
