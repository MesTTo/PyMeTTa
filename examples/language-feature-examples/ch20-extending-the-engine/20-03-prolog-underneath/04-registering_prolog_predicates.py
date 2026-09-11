"""Purpose: examples/ch20-extending-the-engine/20-03-prolog-underneath/04-registering_prolog_predicates.metta in Python: the two operations a registration is.

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
from metta._errors.errors import MettaError

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
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 42503 to 43545 (+1042), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 43545 to 43920 (+375), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 42503 to 42461 (-42), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 42461 to 42539 (+78), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 42539 to 43956 (+1417), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +36 against the trunk's own pin of 43920 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +1381 is what
#: landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 43956 to 30445 (-13511), a library's Prolog half
#: compiles beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): a twin whose example imports
#: a library with a Prolog half pays the artifact load where both sides paid
#: the source consult and its compile-time expansion in every process,
#: lib_thread's import 278,309 to 5,925 inferences; every import now resolves
#: its spec and asks the boot's claim, about 180 inferences an import, and the
#: boot's content moved (the door, the seam and the three library imports the
#: tokens, receipts and seed units gained), which shifts clause layout by tens;
#: measured on this tree with the artifacts warm [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-PINNED 2026-09-10, 30445 to 29102 (-1343), the binding resolves Janus
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
#: RE-PINNED 2026-09-10, 29102 to 29107 (+5), automatic memo reconciliation
#: uses a trailed marker so an inference-limit signal cannot leak its guard.
#: The ordinary dirty drain saves two inferences; the first unset-marker read
#: in each engine invokes SWI's undefined-global hook. Removing the old thread-
#: local predicate also changes catalog-arity enumeration order: five
#: inferences per visited arity in metta_catalog_clause/2 or the partial-list
#: get_native_atom/3 lookup. Same-worktree old/current/restore measurements,
#: native call-site coverage and actual missing-global events separate those
#: costs. See docs/journal/2026-09-09-the-binding-collapse.md. These are three
#: fresh sequential samples per row with 32 concurrent row runners, warmed
#: library artifacts, and file_search_cache_time=9223372036854775807 before
#: boot. Every workload, point allowance and empirical envelope is unchanged
#: [measured 2026-09-10: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-11, 29107 to 29691 (+584), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
BUDGET = 29691
