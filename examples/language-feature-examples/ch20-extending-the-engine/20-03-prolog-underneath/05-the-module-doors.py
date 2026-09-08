"""Purpose: exercise the six Prolog loading doors beside 05-the-module-doors.metta.

Guarantees: static-import! writes and cleans the versioned inert image cache
[tested: python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch20-extending-the-engine/20-03-prolog-underneath/05-the-module-doors.metta; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].

The split is `consult` against `use_module`: a consult loads every clause a
file has, a use_module takes only its export list, and the hidden predicate
below is what proves the difference. Every door keeps its underscores, so
every one comes through the exact subscript door.

Paths are ABSOLUTE where the original writes them relative, for the reason
the residue table records against P14.13: a relative path resolves against
the file that names it, and the file naming these is a Python one four
directories away. `static-import!` is the exception, because what it resolves
against is the process's working directory when no MeTTa source load is
active, which is the repository root either way.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, V, fn, lib
from metta.errors import MettaError

_REPO = Path(__file__).resolve().parents[6]
_FIXTURES = Path(
    "examples/ch20-extending-the-engine/20-03-prolog-underneath/_fixtures"
)

FUNCTIONS = _REPO / _FIXTURES / "rung_functions.pl"
MODULE = _REPO / _FIXTURES / "rung_module.pl"
GLOBAL = _REPO / _FIXTURES / "rung_global.pl"
PRED_FILE = _REPO / _FIXTURES / "rung_pred_file.pl"
PRED_MODULE = _REPO / _FIXTURES / "rung_pred_module.pl"

#: The two artefacts `static-import!` writes beside its source, named
#: relative to the repository root because that is what it resolves against.
STATIC = str(_FIXTURES / "static_rows")
GENERATED = (
    G(str(_REPO / _FIXTURES / "static_rows.tokens-v1.pl")),
    G(str(_REPO / _FIXTURES / "static_rows.tokens-v1.qlf")),
)


def refused(call, *arguments):
    """The error one refused registration raises, or None where it held."""
    try:
        list(call(*arguments))
    except MettaError as failure:
        return failure
    return None


def twin(m):
    """Consult, use_module, both predicate spellings, and the data import."""
    for library in (lib["lib_import"], lib["lib_zar"], lib.file):
        m += library
    register = m.fn["import_prolog_functions"]

    # lib_zar's `consult_file` takes the path as an ordinary argument, so it
    # can be computed rather than being a literal. Registration is a separate
    # step, which is what makes this the low-level door.
    assert m.fn["consult_file"](G(str(FUNCTIONS))) == [True]
    assert register(fn.noeval((S["rung_double"], S["rung_greeting"]))) == [True]
    assert m.fn["rung_double"](21) == [42]

    # `use_module_file` is the same shape over a MODULE. Only the export list
    # arrives, so registering the hidden predicate is refused.
    assert m.fn["use_module_file"](G(str(MODULE))) == [True]
    assert register(fn.noeval((S["rung_module_triple"],))) == [True]
    assert m.fn["rung_module_triple"](14) == [42]
    hidden = refused(register, fn.noeval((S["rung_module_hidden"],)))
    assert "would compile every call to it into a partial application" in str(hidden)

    # `use_module_global` is the predicate-form spelling of the same load: its
    # one argument is the ANSWER position, so the path goes in through a `let`
    # that unifies with it.
    loaded = S.let(  # rung: let unifying with a predicate's answer position
        G(str(GLOBAL)), S["use_module_global"](), S.loaded
    )
    assert m.answers(loaded) == [S.loaded]

    # lib_import's `import_prolog_functions_from_module` is that `let` plus a
    # checked registration, in one call.
    assert m.fn["import_prolog_functions_from_module"](
        G(str(GLOBAL)), (S["rung_global_six"],)
    ) == [True]
    assert m.fn["rung_global_six"](7) == [42]

    # lib_zar's two `_pred` spellings are the same two operations again,
    # written over `consult_file` and `use_module_file`.
    assert m.fn["import_prolog_functions_from_file_pred"](
        G(str(PRED_FILE)), (S["rung_pred_quad"],)
    ) == [True]
    assert m.fn["rung_pred_quad"](10) == [40]
    assert m.fn["import_prolog_functions_from_module_pred"](
        G(str(PRED_MODULE)), (S["rung_pred_five"],)
    ) == [True]
    assert m.fn["rung_pred_five"](10) == [50]

    # `use-module!` is the shortest of them and the least general: it loads a
    # library of SWI's own by bare name, so there is no path and nothing to
    # register.
    assert m.fn["use-module!"](S.lists) == [True]

    # `static-import!` is the odd one out, and it is for DATA rather than
    # code: an inert image carries each form and its occurrence identity.
    # The QLF cache avoids reparsing, and the loader restores its rows through
    # the space storage door.
    assert m.fn["static-import!"](m, G(STATIC)) == [True]
    assert sorted((row.c for row in m[S.city(V.c, S.france)]), key=str) == [
        S.lyon,
        S.paris,
    ]
    assert [row.n for row in m[S.population(S.paris, V.n)]] == [2100000]

    # The two artefacts it wrote are beside the source, and this removes them
    # again: they are build products rather than examples.
    exists, delete = m.fn["file-exists"], m.fn["delete-file!"]
    for artefact in GENERATED:
        assert exists(artefact) == [True]
        assert delete(artefact) == [True]
    assert exists(GENERATED[0]) == [False]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 134200 inferences, 1.0018x the example's 133953; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 134200 to 134171 (-29), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 134171 to 134110 (-61), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 134110 to 134122 (+12), boot content moved: the
#: refusal table and the typing point are modules this package did not have,
#: three convert doors became one, per-library faces are projections, and the
#: engine gained a catalog watch point, and SWI clause-indexing shape shifts a
#: twin count by tens whenever boot content moves, the mechanism every earlier
#: entry in these chains names. The watch point itself is one inference per
#: &metta write, which a twin that defines a function pays three of (2239
#: against 2236 on ch03 01-comments with the two announcement clauses taken
#: out), and the (limit ...) rows it exists for cost nothing at all: 2239
#: either way with every row-backed bound removed, because boot seeds the
#: mirror those bounds are read from [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 134110 to 140992 (+6882), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 140992 to 141000 (+8), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 141000 to 141374 (+374), the module boundary merged
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
#: RE-PINNED 2026-09-09, 141374 to 141817 (+443), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 141374 to 135358 (-6016), Static imports now restore
#: the tokens-v1 inert occurrence image through the native storage funnel and
#: clean its versioned cache files [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 135358 to 149160 (+13802), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 149160 to 150104 (+944), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 141374 to 141340 (-34), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 141340 to 150069 (+8729), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -35 against the trunk's own pin of 150104 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +8764 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 150069
