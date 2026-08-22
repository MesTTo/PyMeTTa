"""examples/libraries/he_error.metta in Python: errors as data, and the railway.

`catch`, `if-error` and `return-on-error` are HE's error algebra and the
subject here, so they stay named; the example's `let` around them is Python's
own assignment, spelled as a one-element unpacking so the twin says out loud
that exactly one answer is expected.

That unpacking is also the door that WORKS. `m.one` and `m.fn` take the loud
reading of an error ANSWER and raise MettaResultError, which is right for a
caller that wanted a value and wrong for this file, whose claims are about the
error atoms themselves. `m.eval` hands them over as the data they are.

Four kinds of nothing-went-right are drawn apart here. An operand whose type
RULES THE CALL OUT is already an error atom, so if-error sees one with no catch
in between; an operand whose type merely does not DECIDE is not an error, and
the call is left as written, which is upstream's NoReduce; a HOST error, the
kind the language has no atom for, needs the catch; and integer division by
zero already is error data.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17863 to 16189, -1674 (-9.37%), by the idiomatic
#: rewrite: eight `test` wrappers and the two `let` chains left the engine
#: for `assert` and one-element unpacking; the catches and the if-error
#: routing still run there, which is the file's subject. Measured min-of-
#: three with the MORK backend linked into this worktree, which the earlier
#: figure may not have been. Prior: 17863 was the last figure for the
#: generator twin that yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 16189

#: The error atom the last three claims are about.
BAD_TYPE = S.Error(5, S.BadType)


def twin(m):
    """Catch what needs catching, then route four answers through if-error."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    if_error = m.fn("if-error")

    [caught] = m.eval(S.catch(S["+"](40, 2)))
    assert if_error(caught, S.Error, caught) == 42

    # An operand whose type RULES THE CALL OUT is an error atom already: `a` is
    # declared a String and the arrow says Number.
    m += S[":"](S.a, S.String)
    assert if_error(S["+"](40, S.a), S.Error, S.fine) == S.Error

    # An operand whose type merely does not DECIDE is not an error. The call is
    # left as written, so if-error takes its second branch.
    assert if_error(S["+"](40, S["undeclared-operand"]), S.Error, S.fine) == S.fine

    # catch is for a HOST error, the kind the language has no atom for. Two
    # unbound arithmetic operands are one.
    [host] = m.eval(S.catch(S["+"](V.left, V.right)))
    assert if_error(host, S.Error, host) == S.Error

    # Integer division by zero already is Error data, so it needs no catch.
    assert if_error(S["/"](40, 0), S.Error, S.fine) == S.Error

    assert if_error(BAD_TYPE, val("Error!"), val("No error")) == val("Error!")

    # return-on-error passes an error through and answers its second argument
    # for anything else.
    assert m.eval(S["return-on-error"](BAD_TYPE, 6)) == [BAD_TYPE]
    assert m.fn("return-on-error")(5, 6) == 6
