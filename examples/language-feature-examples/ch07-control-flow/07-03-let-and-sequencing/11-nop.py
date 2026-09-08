"""Purpose: examples/ch07-control-flow/07-03-let-and-sequencing/11-nop.metta in Python: the step whose answer you do not want.

`nop` evaluates every argument and answers the unit. `UNIT` is the package's
own value for `()`, so the claims compare against it rather than against a
rebuilt empty expression.

What it discards is the ANSWERS, not the work, so the writes inside one still
land. They go into spaces of their own through the ordinary write door, which
is what `add-atom` is.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import UNIT, S, V, fn


def twin(m):
    """Discard answers, keep effects, and stay one answer per branch."""
    nop = m.fn.nop
    assert nop() == [UNIT]
    assert nop(1) == [UNIT]
    assert nop(1, 2, 3) == [UNIT]

    log = m.metta.space(S.log)
    assert m.answers(fn.nop(fn.add_atom(log, S.seen(1)), fn.add_atom(log, S.seen(2)))) == [UNIT]
    assert [row.n for row in log[S.seen(V.n)]] == [1, 2]

    # The difference from `empty`: `empty` answers nothing at all, so the
    # answer LIST is empty, while `nop` answers exactly one thing and that
    # thing is the unit.
    assert nop(1) == [UNIT]
    assert m.answers(fn.empty()) == []

    # It is not a collapse. An argument with three answers is three calls of
    # `nop`, so three units come back and all three writes land.
    drained = m.metta.space(S.drained)
    written = fn.let(  # rung: let as a binder over a generator, which `for` cannot build as data
        V.x, fn.superpose((1, 2, 3)), fn.add_atom(drained, S.x(V.x))
    )
    assert m.answers(fn.nop(written)) == [UNIT, UNIT, UNIT]
    assert len(drained[S.x(V.n)]) == 3

    # The unit is the same value every runnable that exists for its effect
    # answers, which is why a `nop` composes with them without a special case.
    assert nop(1) != m.fn.add_atom(log, S.seen(3))
    assert nop(1) == nop(2)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 3246 inferences, 0.8178x the example's 3969; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 3246 to 3217 (-29), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 3217 to 3374 (+157), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 3374 to 3545 (+171), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 3545 to 3796 (+251), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 3545 to 3624 (+79), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 3624 to 3875 (+251), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
BUDGET = 3875
