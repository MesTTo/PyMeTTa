"""examples/ch20-extending-the-engine/20-03-prolog-underneath/05-the-module-doors.metta in Python: six doors that load Prolog.

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
    G(str(_REPO / _FIXTURES / "static_rows.pl")),
    G(str(_REPO / _FIXTURES / "static_rows.qlf")),
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
    # code: one Prolog fact per form, compiled to a .qlf and loaded, so a
    # large table costs one compile rather than one parse per run. Every fact
    # lands in the space, which is what makes it an import.
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
#: RE-PINNED 2026-09-08, 134110 to 140992 (+6882), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-08, 140992 to 141000 (+8), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 141000
