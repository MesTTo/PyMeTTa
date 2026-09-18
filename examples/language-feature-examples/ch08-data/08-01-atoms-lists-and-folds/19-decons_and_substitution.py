"""Purpose: examples/ch08-data/08-01-atoms-lists-and-folds/19-decons_and_substitution.metta in Python: one step apart, one value in.

`decons-atom` answers the head and the tail together, which Python reads as
an unpackable pair, so the twin destructures it the way any Python program
destructures a two-element answer.

`atom-subst`'s second operand is a BINDER position, held as written, and the
refusal for a non-binder is an error ATOM, so the twin compares it as data
rather than catching anything.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn


def twin(m):
    """Take an expression apart, put it back, and substitute into it."""
    # COST, recorded rather than hidden: 10771 against the example's 8541,
    # past the 10% band with no compiled definition to earn its per-definition
    # credit. The gap is the Python boundary -- twenty calls cross it where
    # the example's twelve forms compile into one program -- and it is the
    # library's to close, not this twin's [measured 2026-09-07: python
    # extensions/python/tools/twin_coverage.py --measure --rounds 3].
    decons_atom, decons = m.fn.decons_atom, m.fn["decons"]
    substitute = m.fn.atom_subst

    # One call does what car-atom and cdr-atom do in two, and the pair
    # destructures.
    [head, tail] = decons_atom((S.a, S.b, S.c))[0]
    assert (head, tail) == (S.a, (S.b, S.c))
    [only, rest] = decons_atom((S.a,))[0]
    assert (only, rest) == (S.a, ())
    # The pair is what a `let` destructures in MeTTa, and what a Python
    # unpacking destructures here.
    assert m.answers(fn.car_atom(tail)) == [S.b]

    # `decons` is the same operation under its un-suffixed name, and `cons`
    # puts back what it took apart.
    assert decons((S.a, S.b, S.c)) == decons_atom((S.a, S.b, S.c))
    assert m.fn.cons_atom(head, tail) == [(S.a, S.b, S.c)]
    assert m.fn.cons_atom(only, rest) == [(S.a,)]

    # The head comes back AS WRITTEN: taking a list apart is not evaluating
    # it, so a call sitting in head position stays a call.
    [call, others] = decons((S.f(1), S.b))[0]
    assert (call, others) == (S.f(1), (S.b,))

    # `atom-subst` puts a value where a named variable stands: value first,
    # the variable second, the term third. Every occurrence goes.
    assert substitute(1, V.x, S.foo(V.x, V.x)) == [S.foo(1, 1)]
    assert substitute(S.g(2), V.x, S.foo(V.x, S.bar(V.x))) == [S.foo(S.g(2), S.bar(S.g(2)))]

    # Only the variable named is touched; the others stay free.
    assert m.fn["=alpha"](substitute(1, V.y, S.foo(V.x, V.y))[0], S.foo(V.a, 1)) == [True]

    # The binder position is HELD, so a call that would reduce to a variable
    # is refused as the non-binder it is rather than evaluated into one.
    refused = S.Error(S.atom_subst(1, S.car_atom((V.x,)), S.foo(V.x)), S.NoReturn)
    # Compared up to renaming, because the engine mints its own variable for
    # the one the refusal carries.
    assert m.fn["=alpha"](substitute(1, S.car_atom((V.x,)), S.foo(V.x))[0], refused) == [True]

    # A term with nothing to substitute comes back unchanged.
    assert substitute(1, V.x, S.foo(S.bar)) == [S.foo(S.bar)]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 10771 inferences, 1.2611x the example's 8541; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 10771 to 10727 (-44), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 10727 to 11053 (+326), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 11053 to 11244 (+191), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 11244 to 11500 (+256), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 11244 to 11369 (+125), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 11369 to 11625 (+256), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-09, 11244 to 11332 (+88), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 11332 to 11713 (+381), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +88 against the trunk's own pin of 11625 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +293 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 11713 to 11501 (-212), the binding resolves Janus
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
#: RE-PINNED 2026-09-18, 11501 to 11800 (+299), the branch's landings since the
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
BUDGET = 11800

#: OVERRUN 2026-09-08, 1400: the twin reads 10771 against a ceiling of 9395 (the
#: example's 8541 plus 10%, no definition to author), and the floor any Python
#: twin of this example can reach is 10239, above the ceiling: the band is
#: tighter than the library's floor for a program that takes expressions
#: apart and substitutes through the structured evaluation door. The 532
#: above the floor is this twin's own program [measured 2026-09-08: one fresh
#: process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: OVERRUN 2026-09-08, 1400 to 1627 (+227): the module boundary merged with
#: trunk (refactor/engine-and-libraries-as-modules at b64291369): the twin's
#: host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine; every
#: crossing this twin makes pays it and the example pays none. Measured 11244
#: against a ceiling of 11017; a minimal twin costs 10598 against the band's
#: 9617, above that ceiling, so no twin of it fits the band at all, as before
#: [measured 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: OVERRUN 2026-09-09, 1627 to 1629 (+2): the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved; every crossing this twin makes pays it and
#: the example pays none. Measured 11244 against a ceiling of 11242; a minimal
#: twin costs 10596 against the band's 9615, above that ceiling, so no twin of
#: it fits the band at all, as before [measured 2026-09-09: one fresh process
#: per side; command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: OVERRUN 2026-09-09, 1629 to 2083 (+454): the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): a Python decode with one named variable
#: builds no index and one with more builds it at the second distinct name,
#: which moves a twin's engine-side cost while its example, which decodes
#: nothing, holds; boot content and clause layout moved the rest; against the
#: trunk's own run at da0e5755d the twin moved +88 and the example +0, and the
#: twin sat 366 over its ceiling there already. Measured 11713 against a
#: ceiling of 11260; a minimal twin costs 10873 against the band's 9630, above
#: that ceiling, so no twin of it fits the band at all, as before [measured
#: 2026-09-09: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: OVERRUN 2026-09-10, 2083 to 2584: The existing program is priced after the
#: reference census, ordered catalog reads and source-scoped translation
#: work. It costs 12207 against the unchanged band and authoring ceiling of
#: 9623.9. The literal structured control costs 11303; it measures that
#: encoding only. [measured 2026-09-10: one fresh process per side;
#: command=python extensions/python/benchmarks/probes/twin_floor.py
#: examples/ch08-data/08-01-atoms-lists-and-folds/19-decons_and_substitution.metta;
#: commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
OVERRUN = 2584
