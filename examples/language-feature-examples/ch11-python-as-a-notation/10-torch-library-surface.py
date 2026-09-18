"""Purpose: examples/ch11-python-as-a-notation/10-torch-library-surface.metta in Python: the rest of lib_torch's surface.

lib_torch is MeTTa equations over `py-call`, so its names are MeTTa functions
and the twin calls them through the function namespace rather than reaching
for `torch` directly: what is being checked is the LIBRARY, not the package
under it.

Whether torch is importable is asked the way the original asks it: one call
under `catch`, read with `if-error`. Python's own `find_spec` would be the
shorter question and the module NAME it takes is host text a twin may not
write, so the engine's guard is the one that stays.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

TOLERANCE = 1e-6

#: The question the original asks, built rather than called: try one torch
#: call under `catch` and read the answer. `find_spec` would be the Python
#: way to ask, and the module NAME it takes is host text a twin may not
#: write, so the engine's own guard is the one that stays.
AVAILABLE = S.if_error(S.catch(S.py_call(S["torch.zeros"](1))), S.no, S.yes)


def available(m):
    """Whether torch is importable and answers, asked without the engine.

    The lane asks this before `twin(m)` and compares the budget below only
    where it answers True: the budget was measured with torch installed, and
    without it the twin takes the same guarded path its example takes. The
    question is asked of Python directly, so the twin's own first evaluation
    is still the first the counted engine makes.
    """
    del m
    try:
        import torch
    except ImportError:
        return False
    torch.zeros(1)
    return True


def twin(m):
    """Constructors, elementwise operations, a reduction, two activations."""
    m += lib.torch
    if m.answers(AVAILABLE) == [S.no]:
        # The example prints its skip here. A twin has no door for prose.
        return

    tensor, to_list, item = m.fn.torch_tensor, m.fn.torch_tolist, m.fn.torch_item
    zeros, ones = m.fn.torch_zeros, m.fn.torch_ones
    randn, arange = m.fn.torch_randn, m.fn.torch_arange

    # The four constructors. Each is one `py-call`, so what comes back is a
    # Python object held as a grounded atom and `torch-tolist` is the exit.
    assert to_list(zeros(3)[0]) == [(0.0, 0.0, 0.0)]
    assert to_list(ones(3)[0]) == [(1.0, 1.0, 1.0)]
    assert to_list(arange(4)[0]) == [(0, 1, 2, 3)]
    assert len(to_list(randn(5)[0])[0]) == 5

    # `torch-randn` draws from a normal distribution, so the one claim that
    # does not depend on the draw is that two of them differ.
    assert to_list(randn(8)[0]) != to_list(randn(8)[0])

    # The four elementwise operations.
    left, right = tensor((1.0, 2.0))[0], tensor((10.0, 20.0))[0]
    assert to_list(m.fn.torch_add(left, right)[0]) == [(11.0, 22.0)]
    assert to_list(m.fn.torch_sub(right, left)[0]) == [(9.0, 18.0)]
    assert to_list(m.fn.torch_mul(tensor((2.0, 3.0))[0], tensor((4.0, 5.0))[0])[0]) == [
        (8.0, 15.0)
    ]
    assert to_list(m.fn.torch_div(right, tensor((4.0, 5.0))[0])[0]) == [(2.5, 4.0)]

    # `torch-mean` is a reduction, so it answers a zero-dimensional tensor
    # and `torch-item` is what takes the number out of one.
    assert item(m.fn.torch_mean(tensor((1.0, 2.0, 3.0))[0])[0]) == [2.0]
    assert item(m.fn.torch_mean(ones(4)[0])[0]) == [1.0]

    # The two activations, on the values that pin their shape: relu is the
    # hinge at zero and sigmoid is a half at zero.
    assert to_list(m.fn.torch_relu(tensor((-2.0, 0.0, 3.0))[0])[0]) == [(0.0, 0.0, 3.0)]
    assert item(m.fn.torch_sigmoid(tensor(0.0)[0])[0]) == [0.5]

    # They compose the way any other function does, which is the point of the
    # library being MeTTa equations over `py-call`. The comparison is a
    # tolerance because torch's default tensor is float32 and MeTTa's number
    # is a double, so a third is not the same third on both sides.
    hinged = m.fn.torch_relu(
        m.fn.torch_sub(tensor((1.0, 2.0, 3.0))[0], tensor((2.0, 2.0, 2.0))[0])[0]
    )[0]
    assert abs(item(m.fn.torch_mean(hinged)[0])[0].value - 1 / 3) < TOLERANCE


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 38332 inferences, 0.8389x the example's 45695; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 38332 to 38260 (-72), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 38260 to 38126 (-134), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 38126 to 143365 (+105239), lib_torch is generated from
#: torch's own signatures (feat/a-face-from-a-modules-own-signatures): the same
#: twenty heads now carry thirty-nine equations, one per call form the
#: signatures reach, thirty-nine arrows and nineteen (@doc ...) atoms where the
#: hand-written file carried twenty-one equations and no declarations, so
#: importing the library compiles and declares that much more before the first
#: call. Measured on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=4a6029296381da416c61a3b25d1609c72a3e062a].
#: RE-PINNED 2026-09-08, 143365 to 143404 (+39), boot content moved: the
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
#: RE-PINNED 2026-09-08, 143365 to 144077 (+712), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 144077 to 143916 (-161), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 143916 to 144466 (+550), the module boundary merged
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
#: RE-PINNED 2026-09-09, 144466 to 144460 (-6), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 144460 to 145226 (+766), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 144466 to 147100 (+2634), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 147100 to 147860 (+760), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 144466 to 141556 (-2910), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 141556 to 144950 (+3394), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -2910 against the trunk's own pin of 147860 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +6304 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 144950 to 144795 (-155), the binding resolves Janus
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
#: RE-PINNED 2026-09-11, 144795 to 147060 (+2265), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 144795 to 189373 (+44578), the branch's landings since
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
#: RE-PINNED 2026-09-18, 189373 to 186191 (-3182), the trunk merged (f97c4b0a3,
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
BUDGET = 186191
