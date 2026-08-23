"""examples/data/atomops.metta in Python: structure, and what refuses.

The file has three parts and each belongs on its own rung.

Taking apart an expression that IS an expression is Python's own work and costs
no engine at all: `e[0]` is the head, `e[1:]` is the rest, `e[i]` is a position,
and `Expression((0, *e))` builds a new one around it. Those claims are written
that way and nothing crosses.

The second part is about what the operations do with an argument they cannot
use, and Python cannot say it: `e[5]` raises IndexError where `index-atom`
answers `()`, and `len(5)` raises TypeError where `size-atom` answers `()`.
ANSWERING rather than raising is the claim, so those go to the operations
themselves, named through `m.fn.<name>` where rung 4's map turns each
underscore back into the hyphen the engine holds. Two of them answer an
`(Error ...)` atom instead, which is data in aggregation, so those two are read
by iterating rather than through the scalar door, which raises on an error.

The third part is sharper still. An unbound VARIABLE is not a value Python has,
and handing one where an expression is expected used to be answered rather than
refused: `(car-atom $u)` unified its argument with a fresh cons cell and
answered the head it had just invented. Each of those claims names its own
operation, because the refusal belongs to that operation.
"""

from metta import Expression, S, V, ground

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Take an expression apart, then ask what refuses and how."""

    def guarded(call):
        """Whether an operation refuses a call or answers it.

        Most of these calls carry an unbound variable, and the call answers the
        verdict all the same: the bindings those variables took are the
        parallel row face on the same view.
        """
        return m.fn.if_error(S.catch(call), S.refused, S.answered).one()

    e = Expression((1, 2, 3))
    pair = S.A(S.B)
    nothing = Expression(())

    # Structure, in Python, with no crossing at all.
    assert Expression((0, *e)) == Expression((0, 1, 2, 3))   # (cons-atom 0 (1 2 3))
    assert e[0] == 1                                          # (car-atom (1 2 3))
    assert list(e[1:]) == [2, 3]                              # (cdr-atom (1 2 3))
    assert e[1] == 2                                          # (index-atom (1 2 3) 1)

    assert m.fn.id(5).one() == 5
    assert S.Father(V.X).alpha_eq(S.Father(V.Y))              # (=alpha ...) is True
    assert not S.Father(V.X).alpha_eq(S.Son(V.X))
    assert m.fn.first_from_pair(pair).one() == S.A
    assert m.fn.second_from_pair(pair).one() == S.B

    # An argument the operation cannot use is ANSWERED, not raised.
    assert m.fn.index_atom(e, 5).one() == nothing             # past the end
    assert m.fn.index_atom(e, S.a).one() == nothing           # not an index at all
    assert m.fn.size_atom(5).one() == nothing
    assert m.fn.sort_atom(5).one() == nothing
    assert m.fn.unique_atom(5).one() == nothing
    assert m.fn.alpha_unique_atom(5).one() == nothing
    assert m.fn.intersection_atom(5, S.a()).one() == nothing

    # Two answer an Error that QUOTES the call, so each head is built as data
    # to say what the answer must contain. An error stays data while it is
    # iterated, and the scalar door would raise it instead.
    not_expression = ground("Atom is not an ExpressionAtom")
    assert m.fn.min_atom(5) == [S.Error(S.min_atom(5), not_expression)]
    assert m.fn.max_atom(5) == [S.Error(S.max_atom(5), not_expression)]

    # An unbound variable is a program error, and every guarded position
    # refuses it by name rather than solving for it.
    assert guarded(S.car_atom(V.unbound)) == S.refused
    assert guarded(S.size_atom(V.unbound)) == S.refused
    assert guarded(S.sort_atom(V.unbound)) == S.refused
    assert guarded(S.index_atom(V.unbound, 0)) == S.refused
    assert guarded(S.subtraction_atom(V.unbound, S.a(S.b))) == S.refused

    # A bound argument is untouched, which is the half that makes the refusal
    # worth anything.
    assert guarded(S.car_atom(Expression((1, 2)))) == S.answered
    assert Expression((1, 2))[0] == 1

    # The refusal is narrow: index-atom's SECOND argument is relational by
    # design, so an unbound index still enumerates every position in turn.
    assert m.fn.index_atom(S.a(S.b, S.c), V.i) == [S.a, S.b, S.c]
