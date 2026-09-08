"""Purpose: mirror safe held deconstruction in examples/ch08-data/08-01-atoms-lists-and-folds/16-if_decons_expr.metta.

Python starred unpacking binds an expression's first item and remaining items.
The native call binds the first item and remaining expression,
then evaluates its selected branch. Empty or unbound operands choose fallback.
Already-bound head and tail positions act as constraints. A known wrong type
produces an Error answer through the same engine contract as other builtins.
"""

from metta import Expression, S, V


def twin(m):
    """Exercise binding, fallback, held inputs and selected-branch answers."""
    deconstruct = m.fn.if_decons_expr
    h, t = V.h, V.t
    pair = S.pair(h, t)
    fallback = S.fallback

    head, *tail = Expression(S.a, S.b, S.c)
    assert S.pair(head, Expression(tail)) == S.pair(S.a, Expression(S.b, S.c))
    assert deconstruct(Expression(), h, t, pair, fallback) == [fallback]
    assert deconstruct(V.unknown, h, t, pair, fallback) == [fallback]
    assert deconstruct(S['+'](1, 2), h, t, t, fallback) == [Expression(1, 2)]
    assert deconstruct(Expression(1, 2), h, t, S['+'](h, 10), S['/'](1, 0)) == [11]
    assert deconstruct(Expression(S.a, S.b), S.a, Expression(S.b), S.matched, fallback) == [S.matched]
    assert deconstruct(Expression(S.a, S.b), S.wrong, Expression(S.b), S.matched, fallback) == [fallback]
    assert deconstruct(Expression(S.a, S.b), S.a, Expression(), S.matched, fallback) == [fallback]
    assert deconstruct(Expression(S.a, S.b), h, t, S.superpose(Expression(1, 2, 2)), fallback) == [1, 2, 2]
    assert m.eval(S.if_error(
        S.if_decons_expr(42, h, t, S.yes, fallback), S.refused, S.answered,
    )) == [S.refused]


#: The final image includes the provisioned engine and MORK artifacts.
#: [measured: 16981, 16981, 16981 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-01-atoms-lists-and-folds/16-if_decons_expr.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
#: RE-PINNED 2026-09-06, 16981 to 17036 (+55), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 17036 to 8424 (-8612), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 8424 to 8398 (-26), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 8398 to 8681 (+283), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 8681 to 8799 (+118), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 8799 to 8776 (-23), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-09, 8776 to 9035 (+259), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 9035

#: OVERRUN 2026-09-07, 900: it puts Python starred unpacking beside the native
#: decons call at every claim. Measured 8424 against a ceiling of 7567; a
#: MINIMAL twin of this example -- its own forms stored and asked through the
#: structured door, nothing else -- costs 8866 against the ceiling's 7567, so
#: no twin of it fits the band at all [measured 2026-09-07: one fresh process
#: per side; command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-08, 900 to 1086 (+186): the module boundary merged with
#: trunk (refactor/engine-and-libraries-as-modules at b64291369): the twin's
#: host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine; every
#: crossing this twin makes pays it and the example pays none. Measured 8799
#: against a ceiling of 8613; a minimal twin costs 9001 against the band's
#: 7713, above that ceiling, so no twin of it fits the band at all, as before
#: [measured 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
OVERRUN = 1086
