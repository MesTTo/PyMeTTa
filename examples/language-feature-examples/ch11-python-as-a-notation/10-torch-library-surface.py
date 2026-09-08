"""examples/ch11-python-as-a-notation/10-torch-library-surface.metta in Python: the rest of lib_torch's surface.

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
#: RE-PINNED 2026-09-08, 144466 to 141556 (-2910), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 141556
