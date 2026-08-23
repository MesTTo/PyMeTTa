"""Purpose: spell the admission-pool differential specification in Python.

Assumes:
  - the custom judge, pool setup, and seven claims mirror the source example
    [source: examples/spaces/admission_pools.metta lines 9-72; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4]
Guarantees:
  - the custom and builtin judges agree before, at, and after the declared
    capacity boundary [measured 2026-08-23: the twin runs to completion under
    the lane, which is what proves every assert it states;
    command=python bindings/python/tools/twin_coverage.py
    examples/spaces/admission_pools.metta; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.

Both spaces the judge talks about are HANDLES here, in the stored equations as
well as at the call sites: a space is an ordinary term operand, so nothing has
to read a name back out of a handle to put it in a term.
"""

import metta
from metta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. This file's previous pin was an empirical envelope rather than a
#: point, because its judge runs engine-time matching whose count moves with
#: the lane's own scheduling; the re-pin pass owns that decision too
#: [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1
RUNG = "the custom judge embeds engine-time matching, branching, and sequence traversal"


def twin(m):
    """Install the MeTTa-bodied judge, claim one pool, and compare verdicts."""
    reflection = metta.reflection
    pool = metta.space("&metta-pool")

    admission_verdict = S["metta-admission-verdict"]
    admission_typed = S["metta-admission-typed"]
    admission_bounded = S["metta-admission-bounded"]
    admission_within = S["metta-admission-within"]

    m += S[":"](
        admission_verdict,
        S["->"](S["%Undefined%"], S.Atom, S["%Undefined%"]),
    )
    m += equation(admission_verdict(V.pool, V.atom)).to(
        admission_typed(
            V.pool,
            V.atom,
            S.collapse(
                S["match"](  # rung: a stored definition embeds a query against another space
                    reflection,
                    S.admits(V.pool, V.type),
                    V.type,
                )
            ),
        )
    )

    m += S[":"](
        admission_typed,
        S["->"](
            S["%Undefined%"],
            S.Atom,
            S["%Undefined%"],
            S["%Undefined%"],
        ),
    )
    m += equation(admission_typed(V.pool, V.atom, V.types)).to(
        S["if"](
            V.types.eq(Expression(())),
            admission_bounded(V.pool),
            S["if"](
                S["has-declared-type"](
                    V.atom,
                    S["car-atom"](V.types),  # rung: the value is an engine-time variable
                ),
                admission_typed(
                    V.pool,
                    V.atom,
                    S["cdr-atom"](V.types),  # rung: the value is an engine-time variable
                ),
                S.refuse(
                    S["does-not-carry"](
                        S["car-atom"](V.types),  # rung: the value is an engine-time variable
                    )
                ),
            ),
        )
    )

    m += equation(admission_bounded(V.pool)).to(
        admission_within(
            V.pool,
            S.collapse(
                S["match"](  # rung: a stored definition embeds a query against another space
                    reflection,
                    S.capacity(V.pool, V.limit),
                    V.limit,
                )
            ),
        )
    )
    m += equation(admission_within(V.pool, V.limits)).to(
        S["if"](
            V.limits.eq(Expression(())),
            S.accept(),
            S["if"](
                # The comparison names its head, like every other comparison
                # in this judge: `<`, `>`, `<=` and `>=` all carry the
                # engine's total atom ORDER, so none of the four builds a
                # term and a guard a stored definition holds is written at
                # the naming door
                # [source: bindings/python/metta/_atoms_core.py:1353-1365].
                S["<"](
                    S["space-atom-count"](V.pool),
                    S["car-atom"](V.limits),  # rung: the value is an engine-time variable
                ),
                S.accept(),
                S.refuse(
                    S["pool-at-capacity"](
                        S["car-atom"](V.limits),  # rung: the value is an engine-time variable
                    )
                ),
            ),
        )
    )

    reflection += S.admits(pool, S.Ticket)
    reflection += S.capacity(pool, 2)
    m += S[":"](S.ticket(S.a), S.Ticket)
    m += S[":"](S.ticket(S.b), S.Ticket)

    guard = S["metta-pool-guard"]
    m += equation(guard(V.incoming)).to(admission_verdict(pool, V.incoming))
    m.fn["declare-pre-add!"](pool, guard).one()

    pool += S.ticket(S.a)
    assert [row.x for row in pool[S.ticket(V.x)]] == [S.a]

    stowaway = S.stowaway(1)
    refused_stowaway = S.Error(
        S["petta_add_refused"](
            pool,
            stowaway,
            S["does-not-carry"](S.Ticket),
        ),
        S.none,
    )
    assert m.eval(
        S.catch(
            S["add-atom"](pool, stowaway)  # rung: catch keeps this failure as aggregate data
        )
    ) == [refused_stowaway]

    pool += S.ticket(S.b)
    refused_capacity = S.Error(
        S["petta_add_refused"](
            pool,
            S.ticket(S.a),
            S["pool-at-capacity"](2),
        ),
        S.none,
    )
    assert m.eval(
        S.catch(
            S["add-atom"](  # rung: catch keeps this failure as aggregate data
                pool,
                S.ticket(S.a),
            )
        )
    ) == [refused_capacity]

    builtin = m.fn["space-admission-verdict"]
    custom = m.fn["metta-admission-verdict"]
    assert builtin(pool, stowaway).one() == custom(pool, stowaway).one()
    assert builtin(pool, S.ticket(S.a)).one() == custom(pool, S.ticket(S.a)).one()

    reflection -= S.capacity(pool, 2)
    assert builtin(pool, S.ticket(S.a)).one() == custom(pool, S.ticket(S.a)).one()
    assert builtin(pool, S.ticket(S.a)).one() == S.accept()
