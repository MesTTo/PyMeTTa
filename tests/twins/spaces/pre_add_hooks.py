"""Purpose: examples/spaces/pre_add_hooks.metta in Python: arbitrary MeTTa at the write door.

A pre-add hook claims the write door of one space for one function of one
argument, the incoming atom. Every write consults it first, and the handler
answers one of four verdicts: `(accept)` lets the atom in as offered,
`(accept <atom>)` lets a TRANSFORMED atom in instead, `(refuse <words>)` throws
carrying the handler's own words, and `(drop)` skips the write silently while
the caller sees success.

So the writes here are ordinary `space += atom`, and what the example proves is
what happens on the other side of that operator. A refusal is an exception with
the handler's sentence in it, which is the loud spelling `catch` and `repr`
reach in the original; a drop is a write that leaves the space unchanged.

The handler's own equations are at the container door, and one blocker is left
of the two this file used to carry. Each head matches a literal SHAPE,
`(guard (secret $x))`, and the compiled subset spells a head pattern only as a
literal default, so a symbol default is refused with "a default here is a head
pattern, so it must be a literal" (residue, P14.4). PERFECT:
`@m.define def guard(atom=S.secret(V.x))`, a head pattern the decorator admits.
What is no longer a
blocker is the body: the mention door reads `S.refuse` and `S.accept` as the
data they are. Claiming and releasing the hook still go through the engine's
own functions, because the claim has no Python door yet (residue, P14.10), and
the pool goes into both calls as the handle it is.

Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import S, V, equation, ground
from metta.errors import EngineError

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1

#: The three sentences this file's refusals print. Each is the Python door's
#: own wording rather than the Error atom the original reads with `repr`, and
#: each prints the offered atom in the wire's list form, `[secret,1]` where
#: engine-exact text would say `(secret 1)` [measured 2026-08-23: unchanged
#: under the handle operand; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
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
    pool = metta.space("&pool")

    m += equation(S.guard(S.secret(V.x))).to(S.refuse(ground("no secrets in this pool")))
    m += equation(S.guard(S.raw(V.x))).to(S.accept(S.cooked(V.x)))
    m += equation(S.guard(S.dup(V.x))).to(S.drop())
    m += equation(S.guard(S.plain(V.x))).to(S.accept())

    m.fn["declare-pre-add!"](pool, S.guard).one()

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
    m += equation(S["other-guard"](V.a)).to(S.accept())
    conflict = None
    try:
        m.fn["declare-pre-add!"](pool, S["other-guard"]).one()
    except EngineError as error:
        conflict = error
    assert str(conflict) == CLAIMED

    # Undeclaring is explicit and frees the claim; the space is direct again.
    m.fn["undeclare-pre-add!"](pool).one()
    pool += (S.uncovered, 10)
    assert [row.x for row in pool[S.uncovered(V.x)]] == [10]
