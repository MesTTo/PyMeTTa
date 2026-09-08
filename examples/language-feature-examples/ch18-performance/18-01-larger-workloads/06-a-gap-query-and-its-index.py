"""Purpose: examples/ch18-performance/18-01-larger-workloads/06-a-gap-query-and-its-index.metta in Python: what a gap query reads.

A gap pattern cannot use the store's arity-keyed read, so the candidate set is
enumerated per admissible arity with the pattern's own leading child written
into the head first. The store's first-argument index therefore still selects
the relation, and the size of every other relation is not in the cost.

`m.limits(inferences=)` is the scoped form of the example's `(inferences N
...)`, and it can say one thing the example cannot: an expired bound is a
control signal, so in MeTTa it ends the file, while here it is an
InferenceLimitError this twin catches. The node query is asked under the same
bound the edge queries fit inside, and it does not fit.

The bulk loader is the example's own equation rather than a Python loop, so the
space this twin leaves behind holds what the example's holds.
"""

from metta import S, V, equation, if_, seg
from metta.errors import InferenceLimitError

#: The bound both edge queries fit inside at either store size, measured on the
#: MeTTa side of this pair by lowering it until the ask stopped fitting: 57
#: inferences gap-free, 144 with a gap, against 46,070 for the same gap over the
#: node relation at 2,000 nodes.
BOUND = 1000


def twin(m):
    """Grow the store tenfold and ask the same two questions under one bound."""
    m += equation(S.nodes(V.n)).to(  # rung: a compiled body has no spelling for a space write inside a let
        if_(
            S.eq(V.n, 0),
            S.done,
            S.let(V.t, S.add_atom(m, S.node(V.n, S.tag)), S.nodes(V.n - 1)),  # rung: as above
        )
    )
    m += S.edge(S.a, S.b)
    m += S.edge(S.a, S.c)
    m += S.edge(S.a, S.d, S.e)

    # Two hundred atoms in a relation the edge queries never touch.
    assert m.fn.nodes(200) == [S.done]
    with m.limits(inferences=BOUND):
        assert len(list(m[(S.edge, S.a, V.y)])) == 2
        assert len(list(m[(S.edge, ..., V.y)])) == 3

    # Two thousand more, and the same bound holds: the gap query reads the edge
    # clauses and nothing else.
    assert m.fn.nodes(2000) == [S.done]
    with m.limits(inferences=BOUND):
        assert len(list(m[(S.edge, S.a, V.y)])) == 2
        assert len(list(m[(S.edge, ..., V.y)])) == 3

    # The gap query over the node relation itself answers 2,200 rows, and no
    # ask can answer 2,200 rows for fewer than 2,200 inferences, so an edge
    # query fitting under 1,000 cannot have read them.
    assert len(list(m[(S.node, ..., V.y)])) == 2200
    expired = None
    try:
        with m.limits(inferences=BOUND):
            list(m[(S.node, ..., V.y)])
    except InferenceLimitError as error:
        expired = error
    assert str(BOUND) in str(expired)

    # The gap decides the arity, so one pattern spans all three edge rows while
    # the fixed pattern reads only the two of its own length.
    assert sorted(row.y for row in m[(S.edge, S.a, V.y)]) == [S.b, S.c]
    wide = S.edge(S.a, S.d, S.e)
    assert sorted(row.rest for row in m[(S.edge, S.a, seg(V.rest))]) == [
        S.edge(S.a, S.b)[2:],
        S.edge(S.a, S.c)[2:],
        wide[2:],
    ]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 51022, 51022, 51022 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch18-performance/18-01-larger-workloads/06-a-gap-query-and-its-index.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 51022 to 51301 (+279), ALL of it is drift between
#: a403e56b4 and this branch's base: the same twin on the base measures 51301
#: too, so the gap query over 2,000 stored atoms costs exactly what it cost
#: before this change [measured 2026-09-07: min-of-3 serial fresh processes,
#: this branch against the same twin on its base 5a85f5602; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f4ae837efd23791200846ba72556c2ce96a7d05a].
#: RE-PINNED 2026-09-07, 51022 to 51381 (+359), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 51381 to 51311 (-70), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 51311 to 51305 (-6), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 51305 to 51312 (+7), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 51305 to 51325 (+20), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 51325 to 53836 (+2511), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 53836 to 67112 (+13276), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 67112

#: DIVERGED 2026-09-07, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 1 atom the example does not (1 =): the twin is an ordinary Python
#: program and its body lowers to the engine's own forms: a match statement is
#: ONE equation whose body is a case tower where the example writes one clause
#: per arm, a named intermediate is a let* the original does not have, a Python
#: truth test wraps its condition in py-truthy, and the annotations and
#: docstrings that come with it are stored beside them [measured 2026-09-07:
#: the two stored-atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "6432f460084a9fc4f17e994a1477271c0cbe72cad8ef7514e8504c6cdc1fffd8"
