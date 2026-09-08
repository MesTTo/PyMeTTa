"""examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/09-carrier_vocabulary.metta in Python: the vocabulary row a generated enum is made of.

The MeTTa half reads the catalog rows directly, because in MeTTa the catalog IS
data and `match` is how you ask. Python has a second way to reach the same row,
and it is the reason the row matters: `metta.vocabularies` is GENERATED from the
shipped catalog, so `Semiring.budget` exists as a typed member exactly when the
`(vocabulary semiring ...)` row names budget.

So the twin asserts the two against each other rather than restating the MeTTa
literal. `tuple(S[member] for member in Semiring)` is the generated side and the
matched row is the catalog side, and they are the same tuple in the same order
because one is made from the other. A copy of the ten words would have passed
whatever the generator did.
"""

import metta
from metta import S, V
from metta.vocabularies import Semiring


def twin(m):  # noqa: ARG001  -- the catalog lives in the reflection space; the default handle stays untouched
    """The generated enum and the row it is generated from are one statement."""
    reflection = metta.reflection

    # Ten algebras ship, and the vocabulary row is exactly their names, in the
    # order the enum renders them.
    assert [
        (row.a, row.b, row.c, row.d, row.e, row.f, row.g, row.h, row.i, row.j)
        for row in reflection[
            S.vocabulary(S.semiring, V.a, V.b, V.c, V.d, V.e, V.f, V.g, V.h, V.i, V.j)
        ]
    ] == [tuple(S[member] for member in Semiring)]

    # Each of those names also has an (algebra ...) row saying what it computes.
    # budget is a cost carrier: min to combine, + to extend, and infinity for
    # the path that does not exist yet, so every real path improves on it. The
    # last field is the row's OWNER: a shipped preset says global, a declared
    # one names the space that declared it.
    assert [
        (row.zero, row.owner)
        for row in reflection[
            S.algebra(
                S[Semiring.budget],
                V.combine,
                V.extend,
                V.zero,
                V.one,
                V.laws,
                V.carrier,
                V.needs,
                V.owner,
            )
        ]
    ] == [(S.infinity, S.global_)]

    # Orderedness is a separate claim, because combining with min does not by
    # itself say which end a (top k ...) slice takes. budget reads ASCENDING,
    # cheapest first, the direction tropical reads.
    for carrier in (Semiring.budget, Semiring.tropical):
        assert [
            row.direction
            for row in reflection[
                S.claim(S.semiring, S[carrier], V.property, V.direction)
            ]
        ] == [S.ascending], carrier

    # A carrier NAMED in the vocabulary but never defined would answer
    # nothing here, which is the failure the two rows exist to keep apart:
    # budget shipped for five days usable through `metta.under` and absent
    # from the vocabulary, so `Semiring.budget` raised AttributeError while
    # `(algebra budget ...)` sat in the catalog. amplitude's zero is the
    # complex origin.
    # !(test (match &metta (algebra amplitude $c $e $z $o $l $ca $r $w) $z)
    #        (complex 0 0))
    assert [
        row.zero
        for row in reflection[
            S.algebra(
                S[Semiring.amplitude],
                V.combine,
                V.extend,
                V.zero,
                V.one,
                V.laws,
                V.carrier,
                V.needs,
                V.owner,
            )
        ]
    ] == [S.complex(0, 0)]

    # The member IS its wire word, which is why S[member] above needed no
    # conversion: a StrEnum member crosses as the bare symbol it always was.
    assert S[Semiring.budget] == S.budget


#: FIRST PIN, 2026-09-05, on the tree that widened the semiring vocabulary to
#: the ten algebras the catalog defines. The MeTTa half costs 13,733 and this
#: one 123, a ratio of 0.009, and the gap is the door rather than the work: a
#: first draft that asked through `m.run(...)` with MeTTa text measured 3,068,
#: twenty-five times this, because that door PARSES its argument before any of
#: it is knowledge. The subscript match hands the engine a term that already
#: is. The corpus's own source scan refuses the first draft for the same
#: reason it is slow, which is the ladder working
#: [measured 2026-09-05: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/09-carrier_vocabulary.metta;
#: fixture=worktree with libmork_ffi.so provisioned and the QLF warmed;
#: commit=f2b818bc2c894ff2f386d67fca8271aa69cb308d].
#:
#: RE-MEASURED 2026-09-06, when the algebra row gained its owner field and the
#: two (algebra ...) matches here gained the variable that reads it. The twin
#: does not move: 119 on the unchanged tree and 119 with the field, so the pin
#: stands and the 4 between it and 123 is the point allowance absorbing older
#: engine work rather than anything this change did. The MeTTa half moves
#: 2,621 -> 2,794, +173, which is the extra variable in two matches and the
#: wider answer template. The 13,733 above is stale for a reason that is not
#: this file's: the same command reads 2,621 on the unchanged tree, so the
#: five-fold drop happened on trunk between f2b818bc and 903a42e6, where ten
#: predicate_property/2 sites stopped paying SWI's 1,030-inference autoload
#: search per probe [measured 2026-09-06: min-of-3 serial fresh processes on
#: both arms; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 3
#: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/09-carrier_vocabulary.metta;
#: fixture=two worktrees, 903a42e6 and this tree, each with engine/*.so and
#: libmork_ffi.so provisioned and the QLF warmed; commit=2e627a593413191cda3170f2eb716835f7f62543].
#: RE-PINNED 2026-09-07, 123 to 147 (+24), the twin gained the claims of its
#: example it had been silently short of: this file's own count moves with the
#: asks it now makes [measured 2026-09-07: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 147 to 218 (+71), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 218 to 328 (+110), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
BUDGET = 328
