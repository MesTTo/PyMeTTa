"""Purpose: examples/functions/functionhead.metta in Python: an argument constrained to be a call's OUTPUT.

An equation HEAD cannot carry the constraint, because a head is a pattern and
a pattern is matched structurally at every depth: `(= (h (myfunc (10) $B) $C)
...)` asks for a first argument that IS the three-element expression, not for
one the call can produce. So the constraint goes in the BODY, where the
argument is unified with what the call produces, the call runs backwards, and
`$B` comes out bound.

`myfunc` is an ordinary Python function. `h` and `h_old` take the `@rules`
shape of the definitional decorator, because both bodies mint a variable that
is not a parameter: `$B` is the constraint's output, and a compiled body has
no way to introduce a MeTTa variable of its own (a free lowercase name there
is a call it cannot resolve, and an assignment binds a fresh name to a VALUE
rather than leaving a hole to unify against). In the `@rules` shape it is
simply another parameter, scoped to the generator, which is what the language
calls it too. The residue table records the gap against P14.4.

`h_old` tests with `=`, MeTTa's unification, and `equation(a).to(b)` is the
builder for exactly that atom; the newer `h` says the same thing with the
inversion door.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8240 to 7701, -539 (-6.5%), by the twin contract
#: change: two `test` wrappers left the engine for `assert`; both equations
#: and both backward calls stayed, which is why this is a 6% saving rather
#: than a half. Against the example's 13429 the ratio is 0.5735 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 7701


def twin(m):
    """Constrain an argument to be what a call produces, two ways."""

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

    append = m.fn("append")

    @m.define
    def myfunc(a, b):
        # (= (myfunc $A $B) (append (append (42) $A) $B))
        return append(append((42,), a), b)

    # rung: both bodies mint $B, a HOLE for the backwards call's unification to
    #   fill, which a compiled body cannot introduce (residue, P14.4)
    @rules
    def constrained(a, c, b):
        # (= (h_old $A $C) (if (= $A (myfunc (10) $B)) ($B $C) (empty)))
        yield equation(S.h_old(a, c)).to(
            S["if"](equation(a).to(S.myfunc((10,), b)), (b, c), S.empty())  # rung: MeTTa's if
        )
        # (= (h $A $C) (let $A (myfunc (10) $B) ($B $C)))
        yield equation(S.h(a, c)).to(solve(a, S.myfunc((10,), b), (b, c)))

    m.add(*constrained)

    assert m.eval(S.h((42, 10, 40), 42000)) == [Expression(((40,), 42000))]
    assert m.eval(S.h_old((42, 10, 40), 42000)) == [Expression(((40,), 42000))]
