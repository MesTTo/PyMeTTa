"""examples/control/eval.metta in Python: reading a body, then running it.

A `match` over the space answers a definition's BODY as data; it does not
interpret what it answers. Running the body is a second and separate act, and
in Python the two acts are two doors: the query door answers rows, and the
evaluation door takes the atom out of one and reduces it.

`f` is a computation and is written as one. `evalCustom` is not: its body adds
an equation to a space, reduces through it and takes it out again, and a
compiled body has no spelling for a space write at all, so it stays a term.
Its own form is declined for a different reason the residue table records
against P14.14: it stores an equation whose body carries a variable the
enclosing match minted, and compiling that equation costs a number that moves
with the variable's identity, so the form answers correctly and cannot be
priced. It is defined here and not run.
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5975 to 5577, -398 (-6.7%), by the twin contract
#: change: the `let` and the `match` around the specialised body LEFT the
#: engine for an assignment and the query door; the evaluation of the body
#: and both definitions stay, and the declined second form is defined and not
#: run. Measured min-of-3 over fresh processes with the MORK backend linked
#: in, which the artefact-free worktree omits and which moves a compiled twin
#: by about 10 inferences per definition; against the example's 15439 the
#: ratio is 0.3612. Prior: 5975, the transliterated twin this replaces.
BUDGET = 5577


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
    assert m.eval(bodies["x"][0]) == [expr(42.7, 42)]

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
