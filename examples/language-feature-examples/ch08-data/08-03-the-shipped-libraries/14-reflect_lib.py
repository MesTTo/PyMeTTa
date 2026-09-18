"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/14-reflect_lib.metta in Python: the engine's own surface as data.

Every enumeration answers a name per solution, so a Python list IS the
collapse and `len` is the count. The `engine-` enumeration predicates under
the MeTTa names are the same operations. `origin-of` projects defining
occurrences from the common property reader; `engine-origin` retains its
implementation-tier classification [tested: twin; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

`surface-counts` moves as libraries are imported, so what is pinned here is
the SHAPE rather than the numbers.

An extension point's name keeps its underscore, `foreign_space`, so that one
comes through the exact subscript door where every other name here takes the
host-convention map.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib


def twin(m):
    """Ask what the engine knows, where a name came from, and how many."""
    m += lib.reflect

    @m.define
    def mine(x):
        # (= (mine $x) $x)
        return x

    knows, arity = m.fn["knows?"], m.fn["arity-of"]
    origin = m.fn["origin-of"]

    assert knows(S.car_atom) == [True]
    assert knows(S.mine) == [True]
    assert knows(S.no_such_name_anywhere) == [False]

    # A registered arity counts the ANSWER position, so `car-atom` takes one
    # argument and is registered at 2.
    assert arity(S.car_atom) == [2]
    assert arity(S.cons_atom) == [3]
    assert arity(S.no_such_name_anywhere) == []

    # Where a name comes from, which a flat list of names cannot say.
    assert origin(S.car_atom)[0][0] == S.origin
    assert origin(S.mine)[0][0] == S.origin
    assert origin(S.no_such_name_anywhere) == []

    # The four enumerations. `special-forms` is what the translator COMPILES
    # and so appears in no registry.
    builtins, special = m.fn["builtins"], m.fn["special-forms"]
    functions, mine_only = m.fn["functions"], m.fn["user-functions"]
    assert len(builtins()) > 100
    assert len(special()) > 10
    assert S.mine in mine_only()
    assert S.car_atom not in mine_only()
    assert S.car_atom in functions()
    assert S.case not in builtins()
    assert S.case in special()
    # `let` is in BOTH, which is what a name with a registered implementation
    # and a compiled form looks like.
    assert S.let in builtins()
    assert S.let in special()

    # The seam catalogue, one (name arity kind) per point.
    points = m.fn["extension-points"]
    assert len(points()) > 3
    assert S["foreign_space"](1, S.ownership) in points()

    # The cheap health check: four pairs rather than four enumerations.
    counts = m.fn["surface-counts"]()[0]
    assert len(counts) == 4
    assert counts[0][0] == S.builtins

    # The whole thing as JSON, which is what an outside tool consumes.
    surface = str(m.fn["surface-json"]()[0].value)
    assert len(surface) > 1000
    assert surface[0] == "{"

    # The enumeration wrappers share their Prolog rungs. engine-origin keeps
    # the legacy implementation-tier answer.
    assert m.fn["engine-arity"](S.car_atom) == arity(S.car_atom)
    assert m.fn["engine-knows"](S.car_atom) == [True]
    assert m.fn["engine-knows"](S.no_such_name_anywhere) == [False]
    assert m.fn["engine-origin"](S.car_atom) == [(S.builtin,)]
    assert m.fn["engine-surface-counts"]() == m.fn["surface-counts"]()
    assert len(m.fn["engine-builtin"]()) == len(builtins())
    assert len(m.fn["engine-special-form"]()) == len(special())
    assert len(m.fn["engine-function"]()) == len(functions())
    assert len(m.fn["engine-user-function"]()) == len(mine_only())
    assert len(m.fn["engine-extension-point"]()) == len(points())


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 161415 inferences, 1.0621x the example's 151980; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 161415 to 161491 (+76), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 161491 to 161419 (-72), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 161419 to 161350 (-69), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 161350 to 161489 (+139), boot content moved: the
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
#: RE-PINNED 2026-09-08, 161350 to 166460 (+5110), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 166460 to 166470 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 166470 to 167727 (+1257), the module boundary merged
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
#: RE-PINNED 2026-09-08, 161489 to 161524 (+35), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 161524 to 167747 (+6223), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 167747 to 168941 (+1194), structured concurrency
#: landed (feat/structured-concurrency merged at f80cc416d): every space mint
#: records its allocation in the library's lifetime rows, every write and run
#: pays the ownership hook and every drop asks the library whether a scope owns
#: the name, measured on a pristine control as 32 per mint, 2 per write and 44
#: per drop with none per read; measured on the merged tree [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 167727 to 170822 (+3095), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 170822 to 170762 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 170762 to 172021 (+1259), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 167727 to 167755 (+28), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 167755 to 171950 (+4195), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -71 against the trunk's own pin of 172021 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +4266 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 171950 to 118029 (-53921), a library's Prolog half
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
#: RE-PINNED 2026-09-09, 118029 to 118039 (+10), engine/qlf_boot.pl gained the
#: hermetic child that writes the engine's own artifact set and every library
#: half's (qlf_child/2, qlf_regenerate_aside/1, qlf_child_boot/0,
#: qlf_shell_words/2), so no process's flags, initialisation file or packs
#: shape an artifact the tree shares; the boot file's added predicates move the
#: first definition's warm-up by ten, the load-structure movement its header
#: records for any boot-content change, and the lane's authoring constant moves
#: with it (warmup 1482); a twin importing a half pays the claim's freshness
#: check besides; measured on this tree with the artifacts warm, against the
#: pins of f26de01fb [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=5f8a823d23fbed5c7395912a89ba32760e2df4b1].
#: RE-PINNED 2026-09-09, 118039 to 117522 (-517), Receipt cleanup stops at the
#: nearest native transaction when unnested and skips forget_scope when that
#: scope reserved no incoming occurrences. Nested transactions retain their
#: outer owner. The provisioned cut control is
#: 3e5855a35d7b206c847845f12467551ea4c54a59; the 2000-equation drop loses all
#: 2000 empty receipt posts. See the 2026-09-09 receipt profile in
#: docs/journal/2026-09-07-every-fact-has-a-token.md. Public and bulk writes
#: now call metta_add_atom/4 and add_sexp_in/5 directly, removing one
#: forwarding inference per accepted atom; parametric open enumeration shares
#: native_storage_functor/2 with named-space reads. Autoload-only excursions
#: are not a re-pin cause [measured 2026-09-09: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-PINNED 2026-09-10, 117522 to 117490 (-32), The receipt crash repair
#: replaces the separate nesting enumeration with metta_receipt_nearest_frame/3
#: and metta_receipt_watch_transaction/2, transferring the same scope at live
#: transaction completion. It removes the findnsols2/5 and findnsols_loop/5
#: work; nested paths also avoid the old outer-frame scan while retaining outer
#: rollback ownership. The same-path e70deddaa control changes only
#: receipts.pl; all ten full-lane samples agree on this lower cost. See the
#: 2026-09-10 receipt frame controls in docs/journal/2026-09-07-every-fact-has-
#: a-token.md and the final twin sweep in docs/journal/2026-09-07-merged-tree-
#: reconciliations.md [measured 2026-09-10: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-PINNED 2026-09-11, 117490 to 121843 (+4353), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 117490 to 126841 (+9351), the branch's landings since
#: the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 126841 to 126847 (+6), 49478d67a landed the polynomial
#: carrier, whose preset row and variable claim every catalog scan reads, the
#: product carriers and the guard read in the fixpoint door, and the binding's
#: five-element rule read: the examples that scan the catalog moved with their
#: twins (restricted_spaces +522, the three pln twins +63 each, the two tabling
#: twins +20 and +10, reflect_lib +6) and the twins that cross the seat's
#: declaration and query paths moved with their examples unmoved (the class
#: twins between -4212 and +2841, the reference twins +208 and +317, the tagged
#: fixpoint twin +610, the documentation twins -22 and -50, types_nondet +5)
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-PINNED 2026-09-18, 126847 to 126360 (-487), the trunk merged (f97c4b0a3,
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
BUDGET = 126360
