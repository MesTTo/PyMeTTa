"""Purpose: examples/ch20-extending-the-engine/20-01-translator-rules/02-translatorrule_direction.metta in Python: which way a rule fires.

A rule is left-to-right by default and saying so explicitly changes nothing. A
BIDIRECTIONAL rule is one declaration from which the engine derives the inverse
equation and registers the head it is rooted at, so nobody writes it twice.
Both sides are then rewritable, and what decides a given call is the form's
COST: a rewrite fires only when it lowers the node count.

Both rules are laws with structured heads, `(celsius (degrees $c))` and
`(unpack (wrap (box $x)))`, so both are `@m.rules` bundles: the head is the
pattern it looks like, the parameters ARE the equations' variables, and the
inverse the engine derives is rooted at the head the author wrote rather than
at whatever a lowered body would have left there. Their type declarations are
data for the same reason, since a bundle has no signature to annotate.

A bundle body EXECUTES rather than lowering, and the arithmetic on a rule
variable builds, so `c + 273` there is the term `(+ $c 273)`.
"""

from typing import Any

from metta import Atom, Expression, S, arrow, equation, typed


def twin(m):
    """Register both direction policies, exercise them, then withdraw one."""
    m += typed(S.celsius, arrow(Atom, Any))     # (: celsius (-> Atom %Undefined%))

    @m.rules
    def scale(c):                               # (= (celsius (degrees $c))
        yield equation(S.celsius(S.degrees(c))).to(
            S.noeval(S.kelvin(c + 273)))        #    (noeval (kelvin (+ $c 273))))

    m.fn.add_translator_rule(S.celsius, Expression((S.direction(S.forward),)))

    assert m.fn.celsius(S.degrees(27)) == [S.kelvin(300)]   # (kelvin 300)

    m += typed(S.unpack, arrow(Atom, Any))      # (: unpack (-> Atom %Undefined%))

    @m.rules
    def unwrapping(x):                          # (= (unpack (wrap (box $x)))
        yield equation(S.unpack(S.wrap(S.box(x)))).to(
            S.noeval(S.twin(x, x)))             #    (noeval (twin $x $x)))

    m.fn.add_translator_rule(S.unpack, Expression((S.direction(S.bidirectional),)))

    small, small_unpack = S.twin(1, 1), S.unpack(S.wrap(S.box(1)))
    large = S.a(S.b, S.c)
    large_twin, large_unpack = S.twin(large, large), S.unpack(S.wrap(S.box(large)))

    # Four nodes against three, so this call goes forwards.
    assert m.eval(small_unpack) == [small]
    # Seven against six, because the argument is written twice on one side and
    # once on the other, so this one goes back.
    assert m.eval(large_twin) == [large_unpack]

    # A form already at its cheapest is left alone, exactly as the prose
    # says: `(twin 1 1)` is three nodes and its rewrite is four, so the
    # backward direction is BLOCKED by cost, and the fixed door shows it.
    # The old pin here recorded the pre-P14.32 fast path running the
    # derived equation raw, past the orientation gate that only lives in
    # translation; a rule-owned head's call now routes through the rule.
    assert m.eval(small) == [small]
    assert m.eval(large_unpack) == [large_unpack]

    # The measure holds at every DOOR, not only for the written call. A call
    # that arrives as data reaches the same equations and the same cost
    # comparison blocks the same up-rewrite there, which the engine asked
    # only at the compile-time door until 2026-08-30: `(eval (twin 1 1))`
    # answered `(unpack (wrap (box 1)))`, a rewrite UP the written spelling
    # of the very same call refused. Both engine doors stay named, because
    # both are the subject.
    # !(test (eval (twin 1 1)) (twin 1 1)) and the same through reduce
    assert m.fn.eval(small) == [small]
    assert m.fn.reduce(small) == [small]

    # Withdrawing the rule withdraws the derived equation with it, so the
    # inverse never outlives the declaration that produced it.
    m.fn.remove_translator_rule(S.unpack)       # (remove-translator-rule! unpack)

    assert m.eval(large_twin) == [large_twin]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 18967 to 19112, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 19112 to 19147, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 19147 to 19366, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-PINNED 2026-09-01 on the operator-protocol tree. Ten fresh full-lane
#: observations had no spread, and the serial min-of-three confirmed the point
#: [measured: twin minimum 15562 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch20-extending-the-engine/20-01-translator-rules/02-translatorrule_direction.metta;
#: fixture=operator-protocol tree after python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 15562 to 16123 (+561), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 16123 to 15622 (-501), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 15622 to 15944 (+322), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-07, 15944 to 16944 (+1000), the twin gained the claims of
#: its example it had been silently short of: this file's own count moves with
#: the asks it now makes [measured 2026-09-07: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 16944 to 16830 (-114), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 16830 to 16811 (-19), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 16811 to 16860 (+49), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 16860 to 16944 (+84), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 16944 to 17047 (+103), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 16944 to 17861 (+917), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 17861 to 17964 (+103), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 16944 to 16925 (-19), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 16925 to 16918 (-7), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 16918 to 17938 (+1020), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, -26 against the trunk's own pin of 17964 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +1046 is what
#: landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
BUDGET = 17938
