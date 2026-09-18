"""Purpose: examples/ch07-control-flow/07-01-if-and-booleans/12-implication_and_unifiability.metta in Python: three questions about two atoms.

`implies` is the connective `and`, `or` and `not` leave out. `=?` asks
whether two atoms COULD be made equal without making them so, and
`if-equal2` preserves variable identity through upstream's exact equality.
The pair `(f $x)` against `(f 1)` is unifiable but fails that equality.
Guarantees: this twin checks shared and distinct variables at that boundary
[tested: python extensions/python/tools/twin_coverage.py examples/ch07-control-flow/07-01-if-and-booleans/12-implication_and_unifiability.metta; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

The four relations are a `@m.rules` bundle rather than stacked `@m.define`
clauses, because `age` and `registered?` each have two clauses that COEXIST
and a stacked define reads as first-match. `registered?` and `adult?` and
`may-vote?` carry a `?` Python cannot spell, so they come through the exact
subscript door, which is rung 5 and the one the ladder keeps for a head
outside identifier grammar.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, V, equation, fn


def twin(m):
    """Material implication, unifiability, and exact equality."""
    # Each handle is resolved ONCE: `m.fn[...]` asks the engine on every
    # access, about 1,200 inferences a name, which is most of a small twin.
    implies, unifiable = m.fn.implies, m.fn["=?"]
    same_or_not = m.fn.if_equal2

    # False implies anything, and only a true antecedent with a false
    # consequent is False.
    assert implies(FALSE, FALSE) == [True]
    assert implies(FALSE, TRUE) == [True]
    assert implies(TRUE, TRUE) == [True]
    assert implies(TRUE, FALSE) == [False]

    # Three bundles, one per relation, because `@m.rules` is the door for
    # equations that COEXIST: stacked `@m.define` clauses read as first-match,
    # which would make the second age and the second registration unreachable.
    @m.rules
    def ages():
        """(= (age ann) 30) and (= (age bo) 12)."""
        yield equation(S.age(S.ann)).to(30)
        yield equation(S.age(S.bo)).to(12)

    @m.rules
    def registrations():
        """(= (registered? ann) True) and (= (registered? bo) True)."""
        yield equation(S["registered?"](S.ann)).to(TRUE)
        yield equation(S["registered?"](S.bo)).to(TRUE)

    @m.rules
    def eligibility(person):
        """The guard shape "if this holds then that must too", written once."""
        # (= (adult? $p) (> (age $p) 17))
        yield equation(S["adult?"](person)).to(S.age(person).gt(17))
        # (= (may-vote? $p) (implies (registered? $p) (adult? $p)))
        yield equation(S["may-vote?"](person)).to(
            fn.implies(S["registered?"](person), S["adult?"](person))
        )

    # Resolved after the bundle, because a handle names a function that
    # exists.
    may_vote = m.fn["may-vote?"]
    assert may_vote(S.ann) == [True]
    assert may_vote(S.bo) == [False]

    # `=?` answers whether two atoms COULD be made equal, and binds neither.
    assert unifiable(S.f(V.x), S.f(1)) == [True]
    assert unifiable(S.f(2), S.f(1)) == [False]
    assert unifiable(V.a, V.b) == [True]
    assert unifiable(S.f(V.x), S.g(V.x)) == [False]

    # Nothing is bound, so the same variable answers True against two atoms
    # that cannot both be true of it.
    assert unifiable(S.f(V.x), S.f(1)) == [True] and unifiable(S.f(V.x), S.f(2)) == [True]

    # Upstream == keeps the identity of each variable.
    assert same_or_not(S.f(V.x), S.f(V.x), S.same, S.different) == [S.same]
    assert same_or_not(S.f(V.x), S.f(V.y), S.renamed, S.different) == [S.different]
    assert same_or_not(S.f(V.x), S.f(1), S.renamed, S.different) == [S.different]
    assert same_or_not(S.f(V.x, V.x), S.f(V.y, V.z), S.renamed, S.different) == [S.different]

    # The same pair is unifiable but fails exact equality.
    assert unifiable(S.f(V.x), S.f(1)) == [True]
    assert same_or_not(S.f(V.x), S.f(1), S.renamed, S.different) == [S.different]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 12664 inferences, 0.7714x the example's 16417; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 12664 to 12801 (+137), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 12801 to 12692 (-109), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 12692 to 12642 (-50), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 12642 to 12883 (+241), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 12883 to 13121 (+238), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 13121 to 13411 (+290), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 13121 to 13466 (+345), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 13466 to 13756 (+290), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 13121 to 13109 (-12), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 13109 to 13239 (+130), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 13239 to 13874 (+635), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +118 against the trunk's own pin of 13756 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +517 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 13874 to 13868 (-6), Public add-atom calls
#: metta_add_atom/4 directly and the native bulk loop calls add_sexp_in/5
#: directly, removing one forwarding inference per accepted atom while keeping
#: the atomic token clock, hooks and errors. Open native enumeration uses the
#: shared native_storage_functor/2 mapping, including parametric scalar
#: storage. Receipt scopes retain the nearest unnested transaction and post no
#: cleanup when no reservation exists. Full-lane ten-round observations on the
#: repaired tree place this point below the published budget; the provisioned
#: cut is 3e5855a35d7b206c847845f12467551ea4c54a59. See the 2026-09-09 entries in
#: docs/journal/2026-09-07-every-fact-has-a-token.md. Autoload-only excursions
#: are excluded from this point selection and keep their pins [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-PINNED 2026-09-11, 13868 to 14752 (+884), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 13868 to 14613 (+745), the branch's landings since the
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
#: RE-PINNED 2026-09-18, 14613 to 14404 (-209), the trunk merged (f97c4b0a3,
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
BUDGET = 14404
