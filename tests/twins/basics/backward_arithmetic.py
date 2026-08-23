"""Purpose: examples/basics/backward_arithmetic.metta in Python: arithmetic run backwards.

`+ - * /` are RELATIONS: give any two of the three and the engine solves for
the third, so a function written forwards reads backwards for free. Past one
unknown the rearrangement runs out and a CONSTRAINT begins, which is what the
`#` family is for, and past that the engine refuses by name rather than
guessing.

Both definitions are ordinary Python functions, and every backward query is
built with Python's own operators, because an operator over an atom BUILDS
the term (`V.p + 2` is `(+ $p 2)`) and a backward query always has a variable
in it. The inversion itself is `m.solve(pattern, subject)`: the known value
goes on `let`'s pattern side, the call goes on its subject side, and the
answer template is derived from the subject's variables, so the third
hand-written `let` argument disappears and each solution is projected by the
variable's own name.

The `#` family takes both function-namespace doors, one per job: `m.fn["#div"]`
CALLS the constraint, and the static `fn["#>="]` names the symbol itself, which
is what a term the engine must receive unevaluated needs.

One form still writes `let` by hand, and it is the GUARD reading rather than
the inversion: `(let True <constraint> <question>)` posts a bound and then
asks inside the same derivation, because the constraint store is undone on
the way out. `solve` does not reach it, since its answer template comes from
the subject and here the answer is another query.

An expected answer is a Python tuple, which encodes to the expression the
original writes, and a collapse is the list an evaluation already answers, so
the original's `(noeval ...)` wrappers have nothing to guard against here: a
Python list is data and is never evaluated a second time.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, S, V, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Run two functions forwards, then run everything backwards."""

    @m.define
    def double(x):
        # (= (double $x) (* 2 $x))
        return 2 * x

    assert double(5) == [10]
    assert m.solve(10, S.double(V.x)).x == 5

    # Each operator solves for its one unbound slot.
    assert m.solve(5, V.p + 2).p == 3
    assert m.solve(12, V.q * 4).q == 3
    assert m.solve(6, V.r - 4).r == 10
    assert m.solve(3, V.s / 4).s == 12

    # No integer doubles to 7, so the query FAILS rather than erroring: no
    # answers at all, which is what collapsing it to `()` says.
    assert m.solve(7, S.double(V.x)).x == []

    @m.define
    def square(x):
        # (= (square $x) (* $x $x))
        return x * x

    # Past one unknown a constraint begins: 25 = X*X is nonlinear, so the
    # engine posts it to CLP(FD) and labels what propagation leaves, which
    # answers EVERY solution rather than one.
    assert m.solve(25, S.square(V.x)).x == [-5, 5]
    assert [tuple(pair) for pair in m.solve(25, V.x * V.y)] == [
        (-25, -1), (-5, -5), (-1, -25), (1, 25), (5, 5), (25, 1),
    ]

    # A domain the constraint leaves unbounded has nothing finite to search,
    # so the engine refuses by name. Bounding the unknown first is what the
    # refusal asks for, and the `#` family is how a MeTTa program bounds one.
    bounded = S.let(TRUE, fn["#>="](V.x, 0), S.let(25, S.square(V.x), V.x))  # rung: the GUARD reading of let, a bound posted and then asked inside ONE derivation
    assert m.eval(bounded) == [5]

    # THE LIMIT: ordinary evaluation is inside-out, so a composed backward
    # query reaches the INNER operation with two unknowns and refuses. The `#`
    # operators POST rather than solve, so the inner constraint waits for the
    # outer one to narrow it and the same query answers.
    composed = fn["#*"](fn["#+"](V.a, 1), 4)
    assert m.solve(20, composed).a == 4

    divide, modulo = m.fn["#div"], m.fn["#mod"]
    smallest, largest = m.fn["#min"], m.fn["#max"]
    less, greater = m.fn["#<"], m.fn["#>"]
    equal, unequal = m.fn["#="], m.fn[r"#\="]
    at_most, at_least = m.fn["#=<"], m.fn["#>="]

    # Integer division, remainder, and the two extremes.
    assert divide(13, 4) == [3]
    assert modulo(13, 4) == [1]
    assert smallest(3, 7) == [3]
    assert largest(3, 7) == [7]

    # All six comparisons answer True or False rather than succeeding or
    # failing, so they compose with `if`.
    assert less(1, 2) == [True]
    assert less(2, 1) == [False]
    assert greater(2, 1) == [True]
    assert equal(3, 3) == [True]
    assert unequal(3, 4) == [True]
    assert at_most(1, 2) == [True]
    assert at_most(2, 1) == [False]
    assert at_least(2, 1) == [True]
    assert at_least(1, 2) == [False]

    # Composed, and still solvable backwards through two constraints.
    assert m.solve(20, composed).a == 4
