"""Purpose: spell the admission-pool differential specification in Python.

Assumes:
  - the custom judge, pool setup, and seven claims mirror the source example
    [source: examples/spaces/admission_pools.metta lines 9-72; commit=WORKTREE]
Guarantees:
  - the custom and builtin judges agree before, at, and after the declared
    capacity boundary [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/spaces/admission_pools.metta; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import REFLECTION_SPACE, Expression, S, V, equation

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 57709..57789 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 57709,
    "maximum": 57789,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}
RUNG = "the custom judge embeds engine-time matching, branching, and sequence traversal"


def twin(m):
    """Install the MeTTa-bodied judge, claim one pool, and compare verdicts."""
    reflection = m.space(REFLECTION_SPACE)
    pool = m.space("&metta-pool")
    at_reflection = S[reflection.space_name]
    at_pool = S[pool.space_name]

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
                    at_reflection,
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
                    at_reflection,
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
                S["space-atom-count"](V.pool)
                < S["car-atom"](V.limits),  # rung: the value is an engine-time variable
                S.accept(),
                S.refuse(
                    S["pool-at-capacity"](
                        S["car-atom"](V.limits),  # rung: the value is an engine-time variable
                    )
                ),
            ),
        )
    )

    reflection += S.admits(at_pool, S.Ticket)
    reflection += S.capacity(at_pool, 2)
    m += S[":"](S.ticket(S.a), S.Ticket)
    m += S[":"](S.ticket(S.b), S.Ticket)

    guard = S["metta-pool-guard"]
    m += equation(guard(V.incoming)).to(
        admission_verdict(at_pool, V.incoming)
    )
    m.fn("declare-pre-add!")(at_pool, guard)

    pool += S.ticket(S.a)
    assert [row.x for row in pool[S.ticket(V.x)]] == [S.a]

    stowaway = S.stowaway(1)
    refused_stowaway = S.Error(
        S["petta_add_refused"](
            at_pool,
            stowaway,
            S["does-not-carry"](S.Ticket),
        ),
        S.none,
    )
    assert m.eval(
        S.catch(
            S["add-atom"](at_pool, stowaway)  # rung: catch keeps this failure as aggregate data
        )
    ) == [refused_stowaway]

    pool += S.ticket(S.b)
    refused_capacity = S.Error(
        S["petta_add_refused"](
            at_pool,
            S.ticket(S.a),
            S["pool-at-capacity"](2),
        ),
        S.none,
    )
    assert m.eval(
        S.catch(
            S["add-atom"](  # rung: catch keeps this failure as aggregate data
                at_pool,
                S.ticket(S.a),
            )
        )
    ) == [refused_capacity]

    builtin = S["space-admission-verdict"]
    assert m.eval(builtin(at_pool, stowaway)) == m.eval(
        admission_verdict(at_pool, stowaway)
    )
    assert m.eval(builtin(at_pool, S.ticket(S.a))) == m.eval(
        admission_verdict(at_pool, S.ticket(S.a))
    )

    reflection -= S.capacity(at_pool, 2)
    assert m.eval(builtin(at_pool, S.ticket(S.a))) == m.eval(
        admission_verdict(at_pool, S.ticket(S.a))
    )
    assert m.eval(builtin(at_pool, S.ticket(S.a))) == [S.accept()]
