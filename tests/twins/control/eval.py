"""Purpose: examples/control/eval.metta in Python: reading a body, then running it.

A `match` over the space answers a definition's BODY as data; it does not
interpret what it answers. Running the body is a second and separate act, and
in Python the two acts are two doors: the query door answers rows, and the
evaluation door takes the atom out of one and reduces it.

Both equations are compiled. `f` is an ordinary computation. `evalCustom`
writes to a space from inside an equation, which is the thing a compiled body
has no spelling for: `space += atom` is a Python STATEMENT over a handle, and
a body is pure atoms, so the write is the head itself over `(context-space)`,
the space the equation is running in. The statement spelling does not merely
refuse there, it MISCOMPILES to arithmetic, which is why naming the head is
the right rung and not a shortcut [measured 2026-08-24: `space += atom` inside
a compiled body stores `(+ $space $atom)` and writes nothing; commit=WORKTREE].
That stays filed against control/and_then_or_else.metta, where the space is
neither a parameter nor the context space and so cannot be reached at all.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Read a specialised body out of the space, then evaluate it."""
    @m.define
    def f(li, a, b):
        # (= (f $L $a $b) (let $result (+ $a $b) (append ($result) $L)))
        result = a + b
        return fn.append((result,), li)

    # !(test (let $fbody_specialized (match &self (= (f (42) 40.7 2) $x) $x)
    #          (eval $fbody_specialized))
    #        (42.7 42))
    bodies = m[equation(S.f((42,), 40.7, 2)).to(V.x)]
    assert m.eval(bodies.x[0]) == [Expression((42.7, 42))]

    @m.define(name="evalCustom")
    def eval_custom(body):
        # (= (evalCustom $body)
        #    (let* (($a   (add-atom &self (= (myfunc) $body)))
        #           ($res (reduce (myfunc)))
        #           ($r   (remove-atom &self (= (myfunc) $body))))
        #          $res))
        # The top rung is the write door itself, as a body statement:
        #     here = S.context_space()
        #     here += equation(S.myfunc()).to(body)
        # A compiled body is pure atoms, so `+=` and `equation(...)` have no
        # image there; worse, `+=` COMPILES, to `(+ $here $atom)`, and stores
        # nothing. Residue: P14.4.
        _a = S.add_atom(S.context_space(), S["="](S.myfunc(), body))  # rung: `space += atom` is a Python statement over a handle, and a compiled body is pure atoms
        res = S.reduce(S.myfunc())
        _r = S.remove_atom(S.context_space(), S["="](S.myfunc(), body))  # rung: `space -= atom` the same way
        return res

    # !(test (evalCustom (match &self (= (f (42) 40.7 2) $x) $x))
    #        (42.7 42))
    assert eval_custom(bodies.x[0]) == [Expression((42.7, 42))]
