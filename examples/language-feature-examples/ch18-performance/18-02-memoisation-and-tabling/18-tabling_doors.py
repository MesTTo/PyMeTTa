"""examples/ch18-performance/18-02-memoisation-and-tabling/18-tabling_doors.metta in Python: withdrawing, clearing, and the escape hatch.

A tabling declaration names a CALL rather than making one, so every argument
here is a built atom: `S.reach(V.x, V.y)` is the pattern, never a call.

The five Prolog predicates underneath take that call QUOTED, and each keeps
its underscore, so they come through the exact subscript door.

The stored equation is deliberately not source-identical, the same divergence
`07-eval.py` records: the body names the running space as the HANDLE it is
here and as the source token `&self` there, so the digest lane reports both
equations. Writing `&self` as a symbol is not the way out; a space is a
handle, and the engine cannot resolve a tabled function's reads through one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, V, fn, lib

#: The call every declaration and every statistics read is about.
REACH = S.reach(V.x, V.y)



def twin(m):
    """Declare, withdraw, declare again, clear, and inject Prolog source."""
    m += lib.tabling
    m += lib.spaces
    m += S.edge(S.a, S.b)

    @m.define
    def reach(x, y):
        # (= (reach $x $y) (match &self (edge $x $y) $y))
        return fn.match(m, S.edge(x, y), y)  # rung: a tabled body's read must name one space predicate

    tabled, untabled = m.fn.tabled, m.fn.untabled
    stats, clear_all = m.fn["table-stats"], m.fn["table-clear-all"]

    # A declaration installs the table, and the statistics carry the policy
    # in force while it stands.
    assert tabled(REACH) == [True]
    assert m.answers(S.reach(S.a, V.y)) == [S.b]
    assert stats(REACH) == [
        (
            S.tables(1),
            S.answers(1),
            S.complete_call(1),
            S.invalidated(0),
            S.reevaluated(0),
            S.policy((S.incremental, S.shared)),
        )
    ]

    # `untabled` removes the instrumentation. The table's own counters
    # survive as SWI's, and the POLICY pair is gone, because a policy is a
    # property of a standing declaration rather than of a table.
    assert untabled(REACH) == [True]
    assert len(stats(REACH)[0]) == 5

    # Declaring again is the same operation and it is idempotent.
    assert tabled(REACH) == [True]
    assert tabled(REACH) == [True]
    assert stats(REACH)[0][5] == S.policy((S.incremental, S.shared))

    # `table-clear-all` abolishes every table in the process.
    assert m.answers(S.reach(S.a, V.y)) == [S.b]
    assert clear_all() == [True]
    assert stats(REACH)[0][1] == S.answers(0)

    # Underneath, five Prolog predicates, each taking the call QUOTED because
    # a tabling declaration names a call rather than making one.
    quoted = fn.quote(REACH)
    assert m.fn["metta_untabled_decl"](quoted) == [True]
    assert m.fn["metta_tabled_decl"](quoted) == [True]
    assert m.answers(S.reach(S.a, V.y)) == [S.b]
    assert m.fn["metta_table_statistics"](quoted) == stats(REACH)
    assert m.fn["metta_table_clear"](quoted) == [True]
    assert m.fn["metta_table_statistics"](quoted)[0][1] == S.answers(0)
    assert m.fn["metta_table_clear_all"]() == [True]

    # `injectPrologCode` is the expert door tabling used to ride through: it
    # loads Prolog SOURCE from a string, so a program can define a predicate
    # the interop surface has no spelling for.
    inject, succeeds = m.fn.injectPrologCode, m.fn.succeedsPredicate
    assert inject(G("metta_doors_greeting(world).")) == [True]
    assert succeeds(S["metta_doors_greeting"](S.world)) == [True]
    assert succeeds(S["metta_doors_greeting"](S.mars)) == [False]

    # A clause body works the same way, so this is a whole predicate rather
    # than a fact table.
    assert inject(G("metta_doors_add(X, Y) :- Y is X + 1.")) == [True]
    assert succeeds(S["metta_doors_add"](41, 42)) == [True]
    assert succeeds(S["metta_doors_add"](41, 43)) == [False]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 159093 inferences, 1.0002x the example's 159054; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 159093
