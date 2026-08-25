"""Purpose: examples/basics/booleansolver.metta in Python: solving for a boolean.

`and` and `or` are generate-and-test over two values, so an unbound variable
in one is SOLVED FOR rather than read, and one form answers twice. The public
`and_`, `or_`, and `if_` builders preserve that relational term at the term
door, while `V.x` is the variable `$x`.

The answers are pairs, so Python reads them as pairs: an expression is a
sequence and `tuple(pair)` is the unpacking.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, V, and_, if_, or_

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1325 to 1326, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 1326 to 1328, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 1328


def twin(m):
    """Ask which pairs of booleans satisfy the condition."""
    # (if (and (or $x True) $y) ($x $y)): the two-argument `if` is the FILTER
    # that turns a solved condition into the pair that solved it, and nothing
    # where it does not hold.
    solutions = m.eval(if_(and_(or_(V.x, TRUE), V.y), (V.x, V.y)))
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
