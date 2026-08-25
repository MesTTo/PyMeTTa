"""Purpose: examples/types/recursive_types2.metta in Python: Peano numbers and a test.

`Nat` is `Z` or `(S n)` for a `Nat`, and `Greater` walks two of them down in
step until one runs out. `Nat` itself is a Python class, so the three arrows
are written from Python types through the one conversion table.

The three clauses select on the SHAPE of their arguments, `(S $x)` against `Z`,
which is what `@m.rules` is for: it lands bare coexisting equations, derives no
guard, and its parameters ARE the equations' variables. A compiled parameter
list reaches none of it, because a head pattern there is a literal default, a
constant IN a position rather than a structure around one.

The constructor pair is declared rather than written as a class for one reason
beyond the head shapes: a Python class declares ITSELF as what its constructor
returns, where `(: S (-> Nat Nat))` declares the ADT the constructor belongs to
(friction, P14.10). The constructor here is also spelled `S`, which is already
the name of the symbol factory, so it is written `S.S`.
"""

from metta import FALSE, TRUE, S, arrow, equation, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11637 to 11673, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11673 to 11612, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11612 to 11614, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 11614


class Nat:
    """The MeTTa type `Nat`, so the three arrows can be built from Python types."""


def twin(m):
    """Build two Peano numbers and compare them."""
    succ = S.S

    # (: Z Nat) (: S (-> Nat Nat)) (: Greater (-> Nat Nat Bool))
    m += typed(S.Z, Nat)
    m += typed(succ, arrow(Nat, Nat))
    m += typed(S.Greater, arrow(Nat, Nat, bool))

    @m.rules
    def order(smaller, larger):
        """The example's three clauses, over two shared rule variables."""
        # (= (Greater (S $x) Z) True)
        yield equation(S.Greater(succ(smaller), S.Z)).to(TRUE)
        # (= (Greater Z $x) False)
        yield equation(S.Greater(S.Z, smaller)).to(FALSE)
        # (= (Greater (S $x) (S $y)) (Greater $x $y))
        yield equation(S.Greater(succ(smaller), succ(larger))).to(
            S.Greater(smaller, larger)
        )

    one, two = succ(S.Z), succ(succ(S.Z))
    # !(test (Greater (S Z) (S Z)) false)
    assert m.fn.Greater(one, one) == [False]
    # !(test (Greater (S (S Z)) (S Z)) true)
    assert m.fn.Greater(two, one) == [True]
