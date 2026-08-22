"""Purpose: examples/control/eval.metta in Python: reading a body, then running it.

A `match` over the space answers a definition's BODY as data; it does not
interpret what it answers. Running the body is a second and separate act, and
in Python the two acts are two doors: the query door answers rows, and the
evaluation door takes the atom out of one and reduces it.

`f` is a computation and is written as one. `evalCustom` is not: its body adds
an equation to a space, reduces through it and takes it out again, and a
compiled body has no spelling for a space write at all, so it stays a term.
Its counter varies because the stored equation carries a variable the
enclosing match minted, so its BUDGET is an empirical envelope rather than a
point. The form still runs and proves its answer.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 12114..12162 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 12114,
    "maximum": 12162,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Read a specialised body out of the space, then evaluate it."""
    append = m.fn("append")

    @m.define
    def f(li, a, b):
        # (= (f $L $a $b) (let $result (+ $a $b) (append ($result) $L)))
        result = a + b
        return append((result,), li)

    # !(test (let $fbody_specialized (match &self (= (f (42) 40.7 2) $x) $x)
    #          (eval $fbody_specialized))
    #        (42.7 42))
    bodies = m.query(equation(S.f((42,), 40.7, 2)).to(V.x))
    assert m.eval(bodies["x"][0]) == [Expression((42.7, 42))]

    # (= (evalCustom $body)
    #    (let* (($a   (add-atom &self (= (myfunc) $body)))
    #           ($res (reduce (myfunc)))
    #           ($r   (remove-atom &self (= (myfunc) $body))))
    #          $res))
    stored = equation(S.myfunc()).to(V.body)
    write = (V.a, S["add-atom"](S[m.space_name], stored))  # rung: a compiled body has no spelling for a space write, so an equation that writes stays a term
    read = (V.res, S.reduce(S.myfunc()))
    erase = (V.r, S["remove-atom"](S[m.space_name], stored))  # rung: the removal, the same way
    m += equation(S.evalCustom(V.body)).to(S["let*"]((write, read, erase), V.res))  # rung: `let*` sequencing is a statement list, which a definition that cannot be compiled cannot have

    # !(test (evalCustom (match &self (= (f (42) 40.7 2) $x) $x))
    #        (42.7 42))
    assert m.eval(S.evalCustom(bodies["x"][0])) == [Expression((42.7, 42))]
