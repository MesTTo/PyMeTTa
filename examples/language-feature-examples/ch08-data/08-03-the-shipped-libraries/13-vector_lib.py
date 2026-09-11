"""Purpose: call every Vector head from the Python expression interface.

There is no vector type: a vector is an ordinary expression, so every
vector argument here is a Python tuple of numbers and every list operation still
applies to one.

Guarantees: exact reductions, component arithmetic and both random arities
carry the same claims as 13-vector_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/13-vector_lib.metta; commit=615e8a68dce996a0c05b3ddddc71b80bc598442d].
"""

import math

from metta import S, lib

TOLERANCE = 1e-6


def twin(m):
    """Exact reductions, component arithmetic, construction and directions."""
    m += lib.vector
    dot, norm = m.fn.dot, m.fn.norm
    cosine, quick = m.fn.cosine, m.fn.cosine_of_normalized
    draw = m.fn.random_normal_vector

    # Dot validates dimensions and rounds the exact finite sum once.
    assert dot((1.0, 2.0), (3.0, 4.0)) == [11.0]
    assert dot((), ()) == [0.0]
    assert dot((1.0, 0.0), (0.0, 1.0)) == [0.0]

    # Norm takes the root before rounding the squared sum.
    assert norm((3.0, 4.0)) == [5.0]
    assert norm((1.0, 0.0)) == [1.0]
    assert norm(()) == [0.0]

    # Cosine measures angle and ignores magnitude.
    assert cosine((1.0, 0.0), (2.0, 0.0)) == [1.0]
    assert cosine((1.0, 0.0), (0.0, 1.0)) == [0.0]
    assert cosine((1.0, 0.0), (-2.0, 0.0)) == [-1.0]

    # The shortcut is dot; on unit vectors it is the cosine.
    assert quick((1.0, 0.0), (1.0, 0.0)) == [1.0]
    assert quick((1.0, 0.0), (0.0, 1.0)) == [0.0]
    assert quick((1.0, 0.0), (0.6, 0.8)) == cosine((1.0, 0.0), (0.6, 0.8))

    # Nonunit inputs keep the historical dot result.
    assert quick((3.0, 4.0), (3.0, 4.0)) == [25.0]
    assert cosine((3.0, 4.0), (3.0, 4.0)) == [1.0]

    # Positive uniform draws projected onto the sphere are not uniform directions.
    assert len(m.fn.with_seed(17, S.random_normal_vector(3))[0]) == 3
    assert abs(norm(m.fn.with_seed(17, S.random_normal_vector(5))[0])[0].value - 1.0) < TOLERANCE
    unit = m.fn.with_seed(17, S.random_normal_vector(4))[0]
    assert abs(quick(unit, unit)[0].value - 1.0) < TOLERANCE

    assert m.fn.vector_add((1, 2), (3, 4)) == [(4, 6)]
    assert m.fn.vector_subtract((3, 4), (1, 2)) == [(2, 2)]
    assert m.fn.vector_multiply((1, 2), (3, 4)) == [(3, 8)]
    assert m.fn.vector_divide((6, 8), (2, 4)) == [(3, 2)]
    assert m.fn.vector_scale((1, 2), 3) == [(3, 6)]
    assert m.fn.vector_normalize((3, 4)) == [(0.6, 0.8)]
    assert m.fn.vector_distance((1, 2), (4, 6)) == [5.0]
    assert m.fn.vector_fill(3, 7) == [(7, 7, 7)]
    assert m.fn.vector_fill(0, 7) == [()]
    assert m.fn.vector_normalize(()) == [()]
    assert dot((2.0**54, 1.0, -(2.0**54)), (1, 1, 1)) == [1.0]
    assert norm((1e-300,)) == [1e-300]
    assert cosine((1e308, 1e308), (1e308, 1e308)) == [1.0]
    assert math.isnan(cosine((0, 0), (1, 2)).one())
    assert math.isinf(norm((math.inf,)).one())
    assert draw(0, (3, 4)) == [(0.6, 0.8)]
    assert draw(-2) == [()]


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
#: RE-PINNED 2026-09-08, 30801 to 31244 (+443), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 31244 to 31602 (+358), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 30801 to 30836 (+35), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 30836 to 31637 (+801), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +35 against the trunk's own pin of 31602 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +766 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 31637 to 31537 (-100), the binding resolves Janus
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
#: RE-PINNED 2026-09-12, 31537 to 62208 (+30671), The Vector example now proves
#: 34 claims over all thirteen native heads and both random arities: exact
#: rational reductions round once through the integer quotient/remainder
#: kernel, component arithmetic and normalization validate every input, and the
#: three random draws run under with-seed 17 so the data-dependent rounding
#: branches are reproducible (two unseeded runs read 61500 and 61503; ten
#: seeded runs read 62208 with zero spread). The seventeen-claim example
#: measured 32104 on this cut against its 31537 pin before any Vector change,
#: so 567 of the movement predates this library [measured 2026-09-12: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=615e8a68dce996a0c05b3ddddc71b80bc598442d].
BUDGET = 62208
