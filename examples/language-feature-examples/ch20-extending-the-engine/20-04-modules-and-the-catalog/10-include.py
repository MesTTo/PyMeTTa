"""Purpose: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/10-include.metta in Python: pasting a module rather than importing it.

A refusal here is a VALUE rather than a raise, so the three claims about it
compare error atoms rather than catching anything.

`include` answers what the module's LAST directive answered and puts its
forms in the INCLUDING space. `import!` merges into its explicit receiving
space and answers True. Both take a module path, which is a name rather
than a string: `_fixtures/included/rows` is a path the reader spells, so it
comes through the exact subscript door.
[tested: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/10-include.metta;
commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
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

    # Importing into m also puts the atoms here, but reports load success.
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
#: RE-PINNED 2026-09-09, 5122 to 5276 (+154), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 5122 to 5183 (+61), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 5183 to 5337 (+154), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-10, 5337 to 5257 (-80), the binding resolves Janus
#: maplist/2 at boot, removing its first-failure autoload; one compiled option
#: policy removes repeated evaluation frames, and keyed dispatch removes
#: repeated transport/context selection. Indexed source-macro hooks preserve
#: unrelated compilation costs. Same-cut controls and all before/after rows are
#: in docs/journal/2026-09-09-the-binding-collapse.md. These three fresh serial
#: processes set file_search_cache_time=9223372036854775807 before boot,
#: matching the validated full-lane/277/workers=32/file-cache-
#: time=9223372036854775807 environment. Workloads, point tolerances and
#: empirical envelopes are unchanged [measured 2026-09-10: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-11, 5257 to 5265 (+8), end-of-wave re-pin on the merged
#: tree after FROM's reference rows and four engine units, the closed-set
#: derivations and two host services, BINDING's one native evaluation entry and
#: boot import, W-OBSERVE's observer guard, PERF's receipts batching and cursor
#: retirement, and the three REDS repairs (derived runtime resources and the
#: shared loader, the tool-lane repairs, the corpus example); serial minimum of
#: three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 5257 to 5378 (+121), the branch's landings since the
#: 09-10 pins, re-taken on the tip f06186a96: the compiled call law (e59104ace:
#: an Atom argument enters as written, a Python object crosses as a value, a
#: positional call of a bound callee is the plain application and a compiled
#: lambda is bare where it is applied), the one codec at the grounded call
#: (fd0af38f7, whose read of a call site's written keyword tail costs about six
#: inferences per translated site, read once since 7cc8fb863), the runnable
#: cache's dependency index written by the producer (a9e2c06d3, which takes
#: back the walk of the generated code 5416e741d charged at every miss), the
#: host patches of 09-17 and the class units of 09-13 to 09-16 the ladder in
#: docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 5378 to 5372 (-6), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 5372
