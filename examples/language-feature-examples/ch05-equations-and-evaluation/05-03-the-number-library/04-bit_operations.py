"""examples/ch05-equations-and-evaluation/05-03-the-number-library/04-bit_operations.metta in Python: masks over exact integers.

Python's own `&`, `|`, `^` and `~` are what these operations exist to lower
from inside a compiled body, so the twin says them BOTH ways: the function
namespace for the engine's own names, and the operators for the spelling a
Python author writes. They answer the same numbers, which is the claim the
lowering rests on.

A float earns the operation's own words rather than being truncated, and that
answer is an error ATOM, so the twin compares it as data.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S


def twin(m):
    """The six bit operations, their operator spellings, and two refusals."""
    f = m.fn

    # 12 is 1100 and 10 is 1010, so the three binary operations read straight
    # off the bits: 1000, 1110, 0110.
    assert f.bit_and(12, 10) == [8]
    assert f.bit_or(12, 10) == [14]
    assert f.bit_xor(12, 10) == [6]
    assert (12 & 10, 12 | 10, 12 ^ 10) == (8, 14, 6)

    # `bit-not` is two's complement, not a boolean negation: -(n+1).
    assert f.bit_not(0) == [-1]
    assert f.bit_not(12) == [-13]
    assert f.bit_not(f.bit_not(12)[0]) == [12]

    # The shifts are multiplication and division by a power of two, and
    # nothing is truncated at a word boundary: MeTTa's integers are unbounded.
    assert f.bit_shift_left(1, 4) == [16]
    assert f.bit_shift_right(16, 2) == [4]
    assert f.bit_shift_left(3, 62) == [13835058055282163712]

    # A right shift on a negative number keeps the sign, which follows from
    # the unbounded representation: there is no top bit to shift a zero into.
    assert f.bit_shift_right(-8, 1) == [-4]
    assert f.bit_shift_right(-1, 40) == [-1]

    # Exact integers only, and the refusal carries the operation's own words.
    assert f.bit_and(1.5, 2) == [S.Error(S.bit_and(1.5, 2), G("bit-and expects two integers"))]
    assert f.bit_shift_left(1.5, 2) == [
        S.Error(
            S.bit_shift_left(1.5, 2),
            G(
                "bit-shift-left expects two arguments: integer (value) and "
                "non-negative integer (count)"
            ),
        )
    ]

    # A mask reads as a predicate: bit 2 of 12 is set, bit 1 is not.
    assert f.bit_and(12, 4) == [4]
    assert f.bit_and(12, 2) == [0]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 3464 inferences, 0.4635x the example's 7473; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 3464 to 3417 (-47), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 3417 to 3638 (+221), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 3638 to 3911 (+273), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-10, 3911 to 3688 (-223), the binding resolves Janus
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
BUDGET = 3688
