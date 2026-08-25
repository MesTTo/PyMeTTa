"""Purpose: examples/functions/invertpeanoplus.metta in Python: Peano addition, run every way.

Two equations define `plus` forwards. Unifying the SUM with what the call
produces then runs it backwards: fix the sum and one operand and the other
comes out bound; fix only the sum and every pair that reaches it is
enumerated; ask for the first answer only and one pair comes back.

The definition takes the `@m.rules` shape of the definitional decorator
because both heads are PATTERNS rather than parameters: `(plus Z $y)` fixes a
symbol and `(plus (S $x) $y)` fixes a whole subterm. A stacked `@m.define`
clause fixes a head position with a literal DEFAULT, and a literal is a bool,
int, float or str, so neither head has a function-shape spelling. The residue
table records that against P14.4. The bound decorator writes the bundle and
lands it in this space in one act, and its parameters ARE the equations'
variables.

The numerals are built by a Python function, since `(S (S (S (S Z))))` is just
`S` applied four times, and writing that out in three different forms is what
made the original hard to read.

`m.solve(pattern, subject)` inverts: the sum on `let`'s pattern side, the call
on its subject side, and the answer projected by the variable's own name.
`once` dissolves into `first()`, the rows' own row-or-nothing accessor.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11835 to 11854, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 11854 to 11793, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 11793 to 11795, on the release tree:
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
BUDGET = 11795


def peano(n):
    """The Peano numeral for n: `(S (S ... Z))`, n successors deep."""
    return S.Z if n == 0 else S.S(peano(n - 1))


def twin(m):
    """Add two numerals, then solve for each operand and for both."""

    @m.rules
    def plus(x, y):
        # (= (plus Z $y) $y)
        yield equation(S.plus(S.Z, y)).to(y)
        # (= (plus (S $x) $y) (S (plus $x $y)))
        yield equation(S.plus(S.S(x), y)).to(S.S(S.plus(x, y)))

    # forward: 2 + 1 = 3
    assert m.eval(S.plus(peano(2), peano(1))) == [peano(3)]

    # half-inverted, searching for $A: $A + 1 = 4, so $A = 3
    assert m.solve(peano(4), S.plus(V.A, peano(1))).A == peano(3)
    # half-inverted, searching for $B: 1 + $B = 4, so $B = 3
    assert m.solve(peano(4), S.plus(peano(1), V.B)).B == peano(3)

    # inverted: every input pair that reaches 4.
    pairs = m.solve(peano(4), S.plus(V.A, V.B))
    assert [tuple(pair) for pair in pairs] == [
        (peano(a), peano(4 - a)) for a in range(5)
    ]

    # inverted, first answer only: (0, 4).
    assert tuple(pairs.first()) == (peano(0), peano(4))
