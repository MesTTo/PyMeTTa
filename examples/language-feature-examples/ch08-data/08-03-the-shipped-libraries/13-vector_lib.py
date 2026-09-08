"""examples/ch08-data/08-03-the-shipped-libraries/13-vector_lib.metta in Python: four operations a similarity search needs.

There is no vector type: a vector is an ordinary expression, so every
argument here is a Python tuple of floats and every list operation still
applies to one.

The random draws are checked to a TOLERANCE rather than to an equality,
because a square root and a division are not exact.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import lib

TOLERANCE = 1e-6


def twin(m):
    """Dot, norm, cosine, the normalised shortcut, and a random direction."""
    m += lib.vector
    dot, norm = m.fn.dot, m.fn.norm
    cosine, quick = m.fn.cosine, m.fn["cosine-of-normalized"]
    draw = m.fn["random-normal-vector"]

    # `dot` walks both expressions together, so it is defined exactly when
    # they are the same length.
    assert dot((1.0, 2.0), (3.0, 4.0)) == [11.0]
    assert dot((), ()) == [0.0]
    assert dot((1.0, 0.0), (0.0, 1.0)) == [0.0]

    # `norm` is that product with itself under a square root.
    assert norm((3.0, 4.0)) == [5.0]
    assert norm((1.0, 0.0)) == [1.0]
    assert norm(()) == [0.0]

    # `cosine` divides by both lengths, so it measures ANGLE and ignores
    # magnitude.
    assert cosine((1.0, 0.0), (2.0, 0.0)) == [1.0]
    assert cosine((1.0, 0.0), (0.0, 1.0)) == [0.0]
    assert cosine((1.0, 0.0), (-2.0, 0.0)) == [-1.0]

    # `cosine-of-normalized` skips both divisions, because on unit vectors
    # the dot product IS the cosine.
    assert quick((1.0, 0.0), (1.0, 0.0)) == [1.0]
    assert quick((1.0, 0.0), (0.0, 1.0)) == [0.0]
    assert quick((1.0, 0.0), (0.6, 0.8)) == cosine((1.0, 0.0), (0.6, 0.8))

    # It says `of-normalized` rather than checking, so a caller who has not
    # normalised gets a number that is not a cosine, and that is the trade
    # the name is warning about.
    assert quick((3.0, 4.0), (3.0, 4.0)) == [25.0]
    assert cosine((3.0, 4.0), (3.0, 4.0)) == [1.0]

    # A random DIRECTION, which is what the whole library is for.
    assert len(draw(3)[0]) == 3
    assert abs(norm(draw(5)[0])[0].value - 1.0) < TOLERANCE
    unit = draw(4)[0]
    assert abs(quick(unit, unit)[0].value - 1.0) < TOLERANCE


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 32171 inferences, 1.0066x the example's 31959; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 32171 to 32135 (-36), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 32135 to 30378 (-1757), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 30378 to 30526 (+148), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 30526 to 30801 (+275), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 30801 to 31159 (+358), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
BUDGET = 31159
