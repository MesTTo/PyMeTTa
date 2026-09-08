"""examples/ch20-extending-the-engine/20-03-prolog-underneath/04-registering_prolog_predicates.metta in Python: the two operations a registration is.

`check_prolog_function_names` asks whether a list of names MAY be registered
from a source, before that source loads, and `import_prolog_functions`
registers every name or none. Both keep their underscores, so both come
through the exact subscript door.

A name list is HELD, and the reason is not decoration: a name the engine
already holds a function for would be CALLED if the list were evaluated, so
`fn.noeval(...)` is what the original writes and what this builds.

Every fixture predicate keeps its Prolog underscore, so every one of them is
written `S["rung_double"]` and not `S.rung_double`, which the host-convention
map would read as `rung-double` -- a name no predicate answers to.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, V, arrow, fn, lib, typed
from metta.errors import MettaError

_REPO = Path(__file__).resolve().parents[6]
FUNCTIONS = _REPO / Path(
    "examples/ch20-extending-the-engine/20-03-prolog-underneath/_fixtures/rung_functions.pl"
)
FIXTURES = _REPO / Path(
    "examples/ch20-extending-the-engine/20-03-prolog-underneath/_fixtures"
)


def refused(call, *arguments):
    """The error one refused registration raises, or None where it held."""
    try:
        list(call(*arguments))
    except MettaError as failure:
        return failure
    return None


def twin(m):
    """Ask, then register; assert and retract; then register a directory."""
    m += lib["lib_import"]
    # The declaration the original writes, so both spaces hold it.
    m += typed(S.Predicate, arrow(S.Expression, S["%Undefined%"]))
    check = m.fn["check_prolog_function_names"]
    register = m.fn["import_prolog_functions"]

    # Asking is all this does, and it touches nothing.
    assert check(fn.noeval((S["rung_fresh_one"], S["rung_fresh_two"])), G("example.pl")) == [
        True
    ]

    # Asking FIRST is not politeness, it is the only order that can work:
    # consulting a file that defines a builtin's name has already replaced
    # the engine's predicate by the time a per-name refusal could fire.
    reserved = refused(check, fn.noeval((S.car_atom,)), G("example.pl"))
    assert "car-atom is a builtin" in str(reserved)
    assert "would replace the engine's own for every space" in str(reserved)

    # It is all-or-nothing about the LIST too, so a bad name anywhere in it
    # refuses the whole list.
    mixed = refused(check, fn.noeval((S["rung_fresh_one"], S.car_atom)), G("example.pl"))
    assert "car-atom is a builtin" in str(mixed)

    # The other half refuses a name with no predicate behind it, because
    # registering one compiles every call into a partial application.
    absent = refused(register, fn.noeval((S["rung_absent_predicate"],)))
    assert "would compile every call to it into a partial application" in str(absent)

    # With the predicates there, the same call registers them and they are
    # MeTTa functions from then on.
    # Consulted through the ordinary import door, whose name list is kept
    # literal by the translator, and then registered by the operation this
    # file is about.
    assert m.fn["import_prolog_functions_from_file"](G(str(FUNCTIONS)), ()) == [True]
    assert register(fn.noeval((S["rung_double"], S["rung_greeting"]))) == [True]
    assert m.fn["rung_double"](21) == [42]
    assert m.fn["rung_greeting"]() == [S.world]

    # The Prolog database from MeTTa: assert at the END of the clause list,
    # retract the first clause that unifies. Both answer a Bool, and
    # retracting something that is not there answers False.
    assert_last, assert_first = m.fn.assertzPredicate, m.fn.assertaPredicate
    retract, call_it = m.fn.retractPredicate, m.fn.callPredicate
    fact = S.Predicate(S["rung_fact"](S.a))
    assert assert_last(fact) == [True]
    assert assert_last(S.Predicate(S["rung_fact"](S.b))) == [True]
    solutions = S.let(  # rung: let as a binder over a predicate's own solutions
        V.verdict, S.callPredicate(S.Predicate(S["rung_fact"](V.x))), V.x
    )
    assert m.answers(solutions) == [
        S.a,
        S.b,
    ]  # rung: let as a binder over a predicate's own solutions
    assert retract(fact) == [True]
    assert retract(S.Predicate(S["rung_fact"](S.zzz))) == [False]

    # `assertaPredicate` asserts at the FRONT, which is the difference
    # between the two and the reason both exist: clause order is answer order.
    assert assert_first(S.Predicate(S["rung_fact"](S.earliest))) == [True]
    solutions = S.let(  # rung: let as a binder over a predicate's own solutions
        V.verdict, S.callPredicate(S.Predicate(S["rung_fact"](V.x))), V.x
    )
    assert m.answers(solutions) == [
        S.earliest,
        S.b,
    ]  # rung: let as a binder over a predicate's own solutions
    assert call_it(S.Predicate(S["rung_fact"](S.b))) == [True]

    # `register_metta_library_path` puts a directory under an alias, so a
    # package can point MeTTa at files it ships beside itself. It is
    # idempotent, and a directory that is not there is refused where the
    # caller can still act on it.
    alias = m.fn["register_metta_library_path"]
    assert alias(S.rung_alias, G(str(FIXTURES))) == [True]
    assert alias(S.rung_alias, G(str(FIXTURES))) == [True]
    m.fn["import!"](m, S.library(S.rung_alias, S["rung_library.metta"])).one()
    assert m.fn["rung-aliased"](5) == [105]
    missing = refused(alias, S.rung_nowhere, G("/no/such/directory"))
    assert "a library path must be a directory that exists" in str(missing)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 42186 inferences, 0.9902x the example's 42605; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 42186 to 42191 (+5), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 42191 to 42179 (-12), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 42179 to 42129 (-50), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 42129 to 42144 (+15), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 42129 to 42193 (+64), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 42193 to 42503 (+310), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 42503 to 42878 (+375), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 42878
