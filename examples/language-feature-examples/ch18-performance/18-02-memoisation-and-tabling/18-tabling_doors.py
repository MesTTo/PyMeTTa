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
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 159093 to 159066 (-27), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 159066 to 158991 (-75), metta_substitute_self/3 probes
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
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 158991 to 158917 (-74), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 158917

#: DIVERGED 2026-09-08, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 1 atom the example does not (1 =): re-settled on the tree
#: that merged the twins burn-down after the every-atom, gate-hygiene and
#: catalog-types merges; the census below is what the two spaces hold apart on
#: that tree, in the burn-down's own classes: knowledge rows the twin's file
#: states (an annotation is a (: name ...) row, a docstring an (@doc ...) row)
#: and lowering shapes an idiomatic Python program compiles to [measured
#: 2026-09-08: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
DIVERGENCE = "85dc77fd4e2f8d91d2c5f71e5b25057f731f109dce328ed2a16d6339d16dd92a"
