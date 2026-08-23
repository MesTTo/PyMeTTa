"""Purpose: spell the admission-pool differential specification in Python.

Assumes:
  - the custom judge, pool setup, and seven claims mirror the source example
    [source: examples/spaces/admission_pools.metta lines 9-72; commit=WORKTREE]
Guarantees:
  - the custom and builtin judges agree before, at, and after the declared
    capacity boundary [measured 2026-08-23: the twin runs to completion under
    the lane, which is what proves every assert it states;
    command=python bindings/python/tools/twin_coverage.py
    examples/spaces/admission_pools.metta; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.

Both spaces the judge talks about are HANDLES here, in the stored equations as
well as at the call sites: a space is an ordinary term operand, so nothing has
to read a name back out of a handle to put it in a term.
"""

import petta
from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. This file's previous pin was an empirical envelope rather than a
#: point, because its judge runs engine-time matching whose count moves with
#: the lane's own scheduling; the re-pin pass owns that decision too
#: [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1
RUNG = "the custom judge embeds engine-time matching, branching, and sequence traversal"


def twin(m):
    """Install the MeTTa-bodied judge, claim one pool, and compare verdicts."""
    reflection = petta.reflection
    pool = petta.space("&metta-pool")

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
                # DEFECT: `<` is the one comparison that no longer BUILDS.
                # R5 put the engine's sort order on Atom.__lt__ so that plain
                # sorted() is msort, and that took the term-building `<` with
                # it: `V.a < 2` raises TypeError and its mirror `2 > V.a`
                # raises too, while >, <= and >= all still build. It is silent
                # rather than loud, and it read as the constant False here
                # until the head was named [measured 2026-08-23;
                # source: bindings/python/petta/_atoms_core.py:1353-1365;
                # commit=WORKTREE]. PERFECT: `S["space-atom-count"](V.pool) <
                # S["car-atom"](V.limits)`, the way every other comparison in
                # this file's judge is written.
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
