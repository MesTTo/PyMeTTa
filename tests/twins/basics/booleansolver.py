"""Purpose: examples/basics/booleansolver.metta in Python: solving for a boolean.

`and` and `or` are generate-and-test over two values, so an unbound variable
in one is SOLVED FOR rather than read, and one form answers twice. `|` and `&`
build those connectives at the term door, and `V.x` is the variable `$x`.

Two walls, and both are why this is a term rather than a decorated function.
Python's `and` and `or` are keywords, so a compiled body cannot name MeTTa's;
and Python's own `and` in a body lowers to a `py-truthy` short circuit, which
tests a value and never generates one, so a compiled `if x and y: yield ...`
answers once with both variables still unbound instead of enumerating the
solutions. Measured on this engine 2026-08-22.

The answers are pairs, so Python reads them as pairs: an expression is a
sequence and `tuple(pair)` is the unpacking.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1231 to 880, -351 (-28.5%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`, and reading the
#: two answers as pairs is Python's own unpacking; the solving itself is
#: untouched. Against the example's 2538 the ratio is 0.3467 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 880


def twin(m):
    """Ask which pairs of booleans satisfy the condition."""
    # (if (and (or $x True) $y) ($x $y)): the two-argument `if` is the FILTER
    # that turns a solved condition into the pair that solved it, and nothing
    # where it does not hold.
    solutions = m.eval(S["if"]((V.x | TRUE) & V.y, (V.x, V.y)))  # rung: two-argument if
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
