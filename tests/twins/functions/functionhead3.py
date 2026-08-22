"""Purpose: examples/functions/functionhead3.metta in Python: one constraint per argument.

`in` keeps a value only when it is a member of a list, and `myplus` chains one
constraint per argument, so the relation runs in BOTH directions: give it two
numbers and it filters, give it variables and it enumerates what is reachable.
The last form runs the whole relation backwards through a guard.

Both definitions take the `@rules` shape of the definitional decorator, and
here neither could take the function shape even in principle. `in` is a Python
KEYWORD, so no Python function can carry that name and no Python body can call
it either. Its body also names `is-member`, and a compiled body resolves a
free name EXACTLY, so a hyphenated engine function is unreachable from one.
`myplus` calls `in`, so the same wall stops it. In the equational shape both
are ordinary atoms: `S["in"]` and `S["is-member"]` are the subscript form,
which is exactly what the subscript is for, a name Python's own grammar will
not take as an attribute. The residue table records the keyword gap against
P14.4, where the hyphenated-name gap already sits.

Every `collapse` dissolves, because an evaluation already answers the list of
its answers. The last form's guard is `(> (myplus $x 2) 3)`, and there Python's
own operator builds the term.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, S, V, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9302 to 6201, -3101 (-33.3%), by the twin contract
#: change: six `test` wrappers and six `collapse` calls left the engine for
#: `assert` and the list an evaluation already answers; every `let` chain
#: and both directions of the relation stayed. Against the example's 15477
#: the ratio is 0.4007 [measured 2026-08-22 min-of-3, `twin_coverage.py
#: --measure`]. The old figure priced a different program.
BUDGET = 6201


def twin(m):
    """Constrain both arguments and the result, then run it every way."""

    def where(condition, answer):
        """Answer `answer` only where `condition` reduces to True.

        MeTTa's `(let True <condition> <answer>)`, the guard reading of `let`.
        Everything it guards is evaluated in ONE derivation, which is what a
        posted constraint needs, since the store is undone on the way out.
        Python's `where=` says this on a query, but a guard over a CALL has no
        Python spelling; the residue table records it against P14.4.
        """
        return S.let(TRUE, condition, answer)  # rung: let as a guard

    # rung: `in` is a Python KEYWORD, so no function can carry that name and no
    #   body can call it, and `is-member` is hyphenated, which a body cannot name
    #   either (residue, P14.4)
    @rules
    def constrained(a, b, x, y, items):
        # (= (in $x $L) (let True (is-member $x $L) $x))
        yield equation(S["in"](x, items)).to(where(S["is-member"](x, items), x))
        # (= (myplus $A $B)
        #    (let $A (in $X (1 2 3))
        #      (let $B (in $Y (2 3))
        #        (in (+ $X $Y) (3 4 5)))))
        inner = S.let(b, S["in"](y, (2, 3)), S["in"](x + y, (3, 4, 5)))  # rung: relational let
        yield equation(S.myplus(a, b)).to(
            S.let(a, S["in"](x, (1, 2, 3)), inner)  # rung: relational let
        )

    m.add(*constrained)

    # fine:
    assert m.eval(S.myplus(1, 3)) == [4]
    # output out of range:
    assert m.eval(S.myplus(3, 3)) == []
    # input out of range:
    assert m.eval(S.myplus(3, 4)) == []
    # what can be reached when adding $X to 3:
    assert m.eval(S.myplus(V.x, 3)) == [4, 5]
    # what can be reached when adding $X to $Y:
    assert m.eval(S.myplus(V.x, V.y)) == [3, 4, 4, 5, 5]
    # with which $x added to 2 can we reach values above 3?
    assert m.eval(where(S.myplus(V.x, 2) > 3, V.x)) == [2, 3]
