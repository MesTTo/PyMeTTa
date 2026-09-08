"""Purpose: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/10-include.metta in Python: pasting a module rather than importing it.

A refusal here is a VALUE rather than a raise, so the three claims about it
compare error atoms rather than catching anything.

`include` answers what the module's LAST directive answered and puts its
forms in the INCLUDING space, where `import!` answers the unit and gives the
module a space of its own. Both take a module path, which is a name rather
than a string: `_fixtures/included/rows` is a path the reader spells, so it
comes through the exact subscript door.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, V

#: A module path resolves against the file that includes it, and the file
#: that includes these is a Python one four directories away from the
#: fixtures, so the paths are ABSOLUTE here where the original writes them
#: relative. The residue table records the relative form against P14.13.
_FIXTURES = (
    Path(__file__).resolve().parents[6]
    / Path("examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/included")
)
ROWS = S[str(_FIXTURES / "rows")]
SILENT = S[str(_FIXTURES / "silent")]


def twin(m):
    """Include a module, read what it left, and meet the three refusals."""
    include = m.fn.include

    # The module defines a function, states a fact, and ends in a runnable.
    # Including it answers that runnable's answer.
    assert include(ROWS) == [42]

    # And the function and the fact are in THIS space now.
    assert m.fn["included-double"](5) == [10]
    assert [row.x for row in m[S.included_fact(V.x)]] == [S.carried]

    # Which is the whole difference from `import!`: that door answers the
    # unit and the module's atoms are reachable through the space it made.
    assert m.fn["import!"](m, ROWS) == [True]

    # A module with no directive has no last answer, so the include answers
    # nothing at all rather than a unit standing in for one.
    assert include(SILENT) == []
    assert [row.x for row in m[S.silent_fact(V.x)]] == [S.here]

    # A name that resolves to nothing is refused by name, and so are the two
    # module-path BASES: `self` and `top` name directories rather than
    # modules, so including one is a category error.
    assert include(S.nosuchmodule) == [
        S.Error(S.include(S.nosuchmodule), G("no module named nosuchmodule is available"))
    ]
    not_a_module = G("include: the running context is not a module")
    assert include(S.self) == [S.Error(S.include(S.self), not_a_module)]
    assert include(S.top) == [S.Error(S.include(S.top), not_a_module)]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 5003 inferences, 0.5099x the example's 9811; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 5003 to 4998 (-5), metta_substitute_self/3 probes the
#: term for the text &self before walking it, one C write and one C substring
#: probe, where the twins-lane merge's one-equation door (08f6f4df) walked
#: every natively added equation in a named space unconditionally, so every
#: twin that adds or defines an equation in a named space drops by about that
#: equation's size in inferences; the same probe now guards the reader's per-
#: form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 4998 to 4982 (-16), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 4982 to 4999 (+17), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 4999 to 5122 (+123), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 5122 to 5183 (+61), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 5183
