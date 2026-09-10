"""Purpose: examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/04-spaces_find.metta in Python: a match used as a condition.

lib_spaces' `find` asks whether a pattern matches AND binds what it matched, so
the original nests two of them and falls back twice: no continuation gives
`MissedSecondPiece`, no starting link at all would give `MissedAllPieces`.

A call keeps both faces. Iterating `find(...)` answers what the predicate
DECIDED, one `True` per solution or a single `False` when there is none, and
`.rows` answers the bindings it made, paired position for position. So `find`
is asked here exactly as the original asks it, the decision drives Python's own
`if` the way it drives the original's, and the bindings come off the row beside
it. The library's own name reaches the bound namespace once it is imported, so
the ask is `m.fn.find(...)` and nothing is spelled twice.

The library arrives through the write door, `m += lib.spaces`, because a
library IS knowledge and the receiver is the target space. The lib
namespace joins its `lib_` family prefix with underscores kept, which is
why no bracket spelling is needed for a name MeTTa writes as
`lib_spaces`.
"""

from metta import S, V, lib


def chains(space, find):
    """Every friendship chain the space holds, with the original's fallbacks."""
    found = []
    starts = find(space, S.friend(V.a, V.b))
    for started, start in zip(starts, starts.rows, strict=True):
        if not started:
            return [S.MissedAllPieces()]
        onward = find(space, S.friend(start.b, V.c))
        for continued, row in zip(onward, onward.rows, strict=True):
            found.append(
                S.FoundChain(start.a, start.b, row.c)
                if continued
                else S.MissedSecondPiece()
            )
    return found


def twin(m):
    """Import lib_spaces, store two friendships, then walk them."""
    m += lib.spaces
    find = m.fn.find

    m += (S.friend, S.a, S.b)
    m += (S.friend, S.b, S.c)

    # What `find` says at this door: one row per solution, bound.
    assert [(row.a, row.b) for row in find(m, S.friend(V.a, V.b)).rows] == [
        (S.a, S.b),
        (S.b, S.c),
    ]

    assert chains(m, find) == [S.FoundChain(S.a, S.b, S.c), S.MissedSecondPiece()]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 9493 to 9572, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 9572 to 9573, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 9573 to 9575, on the release tree:
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
#: RE-PINNED 2026-08-26, 9575 to 11401 (+1826), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 11401 to 9896 (-1505), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 9896 to 9488 (-408), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 9488 to 9474 (-14), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 9474 to 9498 (+24), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 9498 to 9779 (+281), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 9779 to 9787 (+8), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 9787 to 9536 (-251), the one pricing pass at the 0.8.0
#: release cut, and trunk's own movement rather than any mechanism in this
#: twin: each pin was taken on the base its own branch had, and the September
#: merge wave has moved the engine's clause layout, the evaluation path and the
#: library's write doors since [measured 2026-09-06: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 9536 to 9661 (+125), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 9661 to 9645 (-16), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 9645 to 9859 (+214), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 9859 to 9934 (+75), the module boundary merged with
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
#: RE-PINNED 2026-09-08, 9645 to 9669 (+24), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 9669 to 9954 (+285), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 9954 to 10040 (+86), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 9934 to 10139 (+205), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 10139 to 10245 (+106), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 9934 to 9917 (-17), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 9917 to 9977 (+60), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 9977 to 10288 (+311), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +43 against the trunk's own pin of 10245 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +268 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 10288 to 10283 (-5), Public add-atom calls
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
BUDGET = 10283

#: OVERRUN 2026-09-07, 600: it asks `find` a fourth time for the claim the
#: example does not state, that one row comes back per solution bound. Measured
#: 9661 against a ceiling of 9078; a minimal twin of this example costs 8300,
#: inside the ceiling's 9078, so the distance is this twin's own program
#: [measured 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-08, 600 to 802 (+202): the module boundary merged with
#: trunk (refactor/engine-and-libraries-as-modules at b64291369): the twin's
#: host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine; every
#: crossing this twin makes pays it and the example pays none. Measured 9934
#: against a ceiling of 9732; a minimal twin costs 8355 against the band's
#: 9132, within that ceiling, so the rest is this twin's own program [measured
#: 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: OVERRUN 2026-09-09, 802 to 824 (+22): the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved; every crossing this twin makes pays it and
#: the example pays none. Measured 9954 against a ceiling of 9932; a minimal
#: twin costs 8353 against the band's 9130, within that ceiling, so the rest
#: is this twin's own program [measured 2026-09-09: one fresh process per
#: side; command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: OVERRUN 2026-09-09, 824 to 999 (+175): the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): a Python decode with one named variable
#: builds no index and one with more builds it at the second distinct name,
#: which moves a twin's engine-side cost while its example, which decodes
#: nothing, holds; boot content and clause layout moved the rest; against the
#: trunk's own run at da0e5755d the twin moved +43 and the example -13, and
#: the twin sat 117 over its ceiling there already. Measured 10288 against a
#: ceiling of 10114; a minimal twin costs 8627 against the band's 9290, within
#: that ceiling, so the rest is this twin's own program [measured 2026-09-09:
#: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
OVERRUN = 999
