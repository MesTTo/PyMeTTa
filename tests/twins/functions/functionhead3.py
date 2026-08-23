"""Purpose: examples/functions/functionhead3.metta in Python: one constraint per argument.

`in` keeps a value only when it is a member of a list, and `myplus` chains one
constraint per argument, so the relation runs in BOTH directions: give it two
numbers and it filters, give it variables and it enumerates what is reachable.
The last form runs the whole relation backwards through a guard.

Both definitions are decorated Python functions, and both need the descent
ladder's bottom rung, each for its own reason. `in` is a Python KEYWORD, so no
Python function can carry that name: `name="in"` gives the equation the name
the example uses, and `S["in"]` is how `myplus`'s body then calls it, the
quoted-name escape for a name Python's grammar will not take. `is-member` is
an engine function whose spelling is hyphenated, and `fn.is_member` is its
mention door, rung 4's map applied at the factory.

The variables `myplus` chains over are holes rather than parameters, which
`V.x` and `V.y` say inside the body, and `S.let` names the relational `let`
Python's assignment does not reach.

A call answers what the relation reduces to, whether or not its arguments
carry variables, so running `myplus` backwards is the same Python line as
running it forwards; the bindings those variables took are the parallel row
face on the same view. `collapse` dissolves either way, because the view
already IS the list of answers. Only the last claim evaluates a term instead
of calling, because a `let`-as-guard has to wrap the call.
"""

from metta import TRUE, S, V, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Constrain both arguments and the result, then run it every way."""

    @m.define(name="in")
    def is_in(x, items):
        # (= (in $x $L) (let True (is-member $x $L) $x))
        return S.let(True, fn.is_member(x, items), x)  # noqa: FBT003  -- True is the ATOM the membership check answers, matched against, not a flag  # rung: let as a guard

    @m.define
    def myplus(a, b):
        # (= (myplus $A $B)
        #    (let $A (in $X (1 2 3))
        #      (let $B (in $Y (2 3))
        #        (in (+ $X $Y) (3 4 5)))))
        return S.let(a, S["in"](V.x, (1, 2, 3)),  # rung: relational let
                     S.let(b, S["in"](V.y, (2, 3)),  # rung: relational let, again
                           S["in"](V.x + V.y, (3, 4, 5))))

    # fine:
    assert myplus(1, 3) == [4]
    # output out of range:
    assert myplus(3, 3) == []
    # input out of range:
    assert myplus(3, 4) == []
    # what can be reached when adding $X to 3:
    assert myplus(V.x, 3) == [4, 5]
    # what can be reached when adding $X to $Y:
    assert myplus(V.x, V.y) == [3, 4, 4, 5, 5]
    # with which $x added to 2 can we reach values above 3?
    guard = S[">"](S.myplus(V.x, 2), 3)
    assert m.eval(S.let(TRUE, guard, V.x)) == [2, 3]  # rung: let as a guard
