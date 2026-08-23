"""examples/libraries/he_error.metta in Python: errors as data, and the railway.

`catch`, `if-error` and `return-on-error` are HE's error algebra and the
subject here, so they stay named; the example's `let` around them is Python's
own assignment, spelled as a one-element unpacking so the twin says out loud
that exactly one answer is expected.

Iterating the answer view is what hands an error atom over AS DATA. The scalar
doors take the loud reading and raise, which is right for a caller that wanted
a value and wrong for this file, whose claims are about the error atoms
themselves; unpacking iterates, so it keeps them.

One call goes through `m.eval` instead, and the reason is the answer view
rather than the error: a call whose ARGUMENT carries the caller's own
variables answers binding rows, and the claim here is about the term.

Four kinds of nothing-went-right are drawn apart here. An operand whose type
RULES THE CALL OUT is already an error atom, so if-error sees one with no catch
in between; an operand whose type merely does not DECIDE is not an error, and
the call is left as written, which is upstream's NoReduce; a HOST error, the
kind the language has no atom for, needs the catch; and integer division by
zero already is error data.
"""

from petta import G, S, V, typed

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1

#: The error atom the last three claims are about.
BAD_TYPE = S.Error(5, S.BadType)


def twin(m):
    """Catch what needs catching, then route four answers through if-error."""
    m.eval(S["import!"](m, S.library(S["lib_he"])))

    if_error = m.fn.if_error

    [caught] = m.fn.catch(S["+"](40, 2))
    assert if_error(caught, S.Error, caught) == [42]

    # An operand whose type RULES THE CALL OUT is an error atom already: `a` is
    # declared a String and the arrow says Number.
    m += typed(S.a, S.String)
    assert if_error(S["+"](40, S.a), S.Error, S.fine) == [S.Error]

    # An operand whose type merely does not DECIDE is not an error. The call is
    # left as written, so if-error takes its second branch.
    assert if_error(S["+"](40, S["undeclared-operand"]), S.Error, S.fine) == [S.fine]

    # catch is for a HOST error, the kind the language has no atom for. Two
    # unbound arithmetic operands are one.
    #
    # DEFECT, and this line is what it costs. It ought to read
    # `m.fn.catch(S["+"](V.left, V.right))` like the first catch above. The
    # argument carries `$left` and `$right`, and the answer view reads every
    # variable in a call as one of the caller's own, so the call door answers a
    # binding row where the claim is about the error atom.
    [host] = m.eval(S.catch(S["+"](V.left, V.right)))
    assert if_error(host, S.Error, host) == [S.Error]

    # Integer division by zero already is Error data, so it needs no catch.
    assert if_error(S["/"](40, 0), S.Error, S.fine) == [S.Error]

    assert if_error(BAD_TYPE, G("Error!"), G("No error")) == [G("Error!")]

    # return-on-error passes an error through and answers its second argument
    # for anything else.
    return_on_error = m.fn.return_on_error
    assert return_on_error(BAD_TYPE, 6) == [BAD_TYPE]
    assert return_on_error(5, 6) == [6]
