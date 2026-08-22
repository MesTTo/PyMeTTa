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

The handler's own equations are at the container door. Each head matches a
literal SHAPE, `(guard (secret $x))`, where a compiled head pattern is a
literal default and reaches neither a structure nor a symbol, and each body
answers a lowercase verdict as data (residue, P14.4). Claiming and releasing
the hook go through `m.fn`, because the claim has no Python door yet (residue,
P14.10).
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import EngineError, S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9549 to 7270, -2279 (-23.9%), by the twin contract
#: change: seven `(test ...)` terms became seven Python `assert`s, so `test`
#: left the engine seven times, two `catch`es and two `repr`s went with it, and
#: one `collapse` over a match became an empty subscript answer. Every write
#: still runs the hook and every hook decision is still the engine's. Against
#: the example's 23410 the ratio is 0.3106.
#: Prior: 9549, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 7270

#: The three sentences this file's refusals print. Each is the Python door's
#: own wording rather than the Error atom the original reads with `repr`, and
#: each prints the offered atom in the wire's list form, `[secret,1]` where
#: engine-exact text would say `(secret 1)` [measured 2026-08-22; reported to
#: the integrator].
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
    pool = m.space("&pool")
    at_pool = S[pool.space_name]

    m += equation(S.guard(S.secret(V.x))).to(S.refuse(val("no secrets in this pool")))
    m += equation(S.guard(S.raw(V.x))).to(S.accept(S.cooked(V.x)))
    m += equation(S.guard(S.dup(V.x))).to(S.drop())
    m += equation(S.guard(S.plain(V.x))).to(S.accept())

    m.fn("declare-pre-add!")(at_pool, S.guard)

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
        m.fn("declare-pre-add!")(at_pool, S["other-guard"])
    except EngineError as error:
        conflict = error
    assert str(conflict) == CLAIMED

    # Undeclaring is explicit and frees the claim; the space is direct again.
    m.fn("undeclare-pre-add!")(at_pool)
    pool += (S.uncovered, 10)
    assert [row.x for row in pool[S.uncovered(V.x)]] == [10]
