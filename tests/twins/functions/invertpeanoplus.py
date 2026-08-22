"""Purpose: examples/functions/invertpeanoplus.metta in Python: Peano addition, run every way.

Two equations define `plus` forwards. Unifying the SUM with what the call
produces then runs it backwards: fix the sum and one operand and the other
comes out bound; fix only the sum and every pair that reaches it is
enumerated; ask for the first answer only and one pair comes back.

The definition takes the `@rules` shape of the definitional decorator because
both heads are PATTERNS rather than parameters: `(plus Z $y)` fixes a symbol
and `(plus (S $x) $y)` fixes a whole subterm. A stacked `@m.define` clause
fixes a head position with a literal DEFAULT, and a literal is a bool, int,
float or str, so neither head has a function-shape spelling. The residue table
records that against P14.4.

The numerals are built by a Python function, since `(S (S (S (S Z))))` is just
`S` applied four times, and writing that out in three different forms is what
made the original hard to read. `once` dissolves too: `m.first` is the first
answer, which is the cardinality door Python's own vocabulary already has.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 12781 to 8164, -4617 (-36.1%), by the twin
#: contract change: five `test` wrappers and one `collapse` left the engine
#: for `assert` and the answer list, `once` became `m.first`, and the five
#: expected numerals are built by a Python comprehension over `peano(n)`
#: rather than written out. Against the example's 19894 the ratio is 0.4104
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 8164


def peano(n):
    """The Peano numeral for n: `(S (S ... Z))`, n successors deep."""
    return S.Z if n == 0 else S.S(peano(n - 1))


def twin(m):
    """Add two numerals, then solve for each operand and for both."""

    def solve(pattern, subject, answer):
        """Unify `pattern` with what `subject` produces, then answer `answer`.

        Either side may be the call, which is what makes it run BACKWARDS: the
        call's own variables come out bound. This is MeTTa's `let`, which
        dissolves into Python's assignment when the subject is a call and the
        pattern is a fresh name; the direction used here, a pattern the call
        has to reach, has no Python spelling at all. The design's name for the
        door it wants is `solve` (ai-python-first-revamp-discussion.md section
        9g, idea 1), and the residue table records it against P14.4.
        """
        return S.let(pattern, subject, answer)  # rung: relational let

    # rung: one head fixes the symbol Z and the other a whole subterm, neither of
    #   which a literal default can be (residue, P14.4)
    @rules
    def plus(x, y):
        # (= (plus Z $y) $y)
        yield equation(S.plus(S.Z, y)).to(y)
        # (= (plus (S $x) $y) (S (plus $x $y)))
        yield equation(S.plus(S.S(x), y)).to(S.S(S.plus(x, y)))

    m.add(*plus)

    # forward: 2 + 1 = 3
    assert m.eval(S.plus(peano(2), peano(1))) == [peano(3)]

    # half-inverted, searching for $A: $A + 1 = 4, so $A = 3
    assert m.eval(solve(S.plus(V.A, peano(1)), peano(4), V.A)) == [peano(3)]
    # half-inverted, searching for $B: 1 + $B = 4, so $B = 3
    assert m.eval(solve(S.plus(peano(1), V.B), peano(4), V.B)) == [peano(3)]

    # inverted: every input pair that reaches 4.
    pairs = m.eval(solve(S.plus(V.A, V.B), peano(4), (V.A, V.B)))
    assert pairs == [Expression((peano(a), peano(4 - a))) for a in range(5)]

    # inverted, first answer only: (0, 4).
    assert m.first(solve(S.plus(V.A, V.B), peano(4), (V.A, V.B))) == Expression(
        (peano(0), peano(4)))
