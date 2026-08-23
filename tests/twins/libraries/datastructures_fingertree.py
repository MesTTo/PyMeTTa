"""Purpose: examples/libraries/datastructures_fingertree.metta in Python: the finger tree, walked.

The finger tree from lib_datastructures: O(1) at both ends, O(log n)
concatenation, one structure serving as sequence and deque at once. Fifteen
claims, every one of them about one of the eleven `ft-*` functions, so all
eleven are named.

DEFECT, and it decides how this file is written. Every claim below ought to
nest the calls the way Python nests calls,
`push_front(1, push_back(3, push_front(2, ft_empty())))` through
`space.fn.ft_push_front` and its siblings. A call through the function
namespace answers an ANSWER VIEW, and an answer view is not an operand:
handing one to another engine function crosses it as a grounded Python object
and answers `(BadArgType 1 Number Answers)`. Threading `.one()` through every
nesting level would say the same thing four times a line and would also cross
the boundary once per SUB-CALL, which the cost model prices per collection.
So the eleven names are bound as MENTIONS, each claim composes one term, and
`eval` performs it once, exactly as the example's own single form does.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 264 inferences over the concurrent lane's own observations, because
#: the shared engine's scheduling changes what a concurrent round costs
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Build, inspect, drain, and concatenate finger trees from Python."""
    m.eval(S["import!"](m, S.library(S["lib_datastructures"])))

    ft_empty, from_list, to_list = S.ft_empty, S.ft_from_list, S.ft_to_list
    push_front, push_back = S.ft_push_front, S.ft_push_back
    front, back = S.ft_front, S.ft_back
    pop_front, pop_back = S.ft_pop_front, S.ft_pop_back
    concat, is_empty = S.ft_concat, S.ft_is_empty

    built_at_both_ends = push_front(1, push_back(3, push_front(2, ft_empty())))
    assert m.eval(to_list(built_at_both_ends)) == [Expression((1, 2, 3))]

    ten = (S.a, S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert m.eval(to_list(from_list(ten))) == [Expression(ten)]

    abc = from_list((S.a, S.b, S.c))
    assert m.eval(front(abc)) == [S.a]
    assert m.eval(back(abc)) == [S.c]

    # A pop answers the element and the remaining tree, so the example reads
    # both out of one answer; Python's own unpacking is that reading.
    [popped] = m.eval(pop_front(abc))
    item, remainder = popped
    assert (item, m.eval(to_list(remainder))) == (S.a, [S.b(S.c)])

    [popped] = m.eval(pop_back(abc))
    item, remainder = popped
    assert (item, m.eval(to_list(remainder))) == (S.c, [S.a(S.b)])

    deep = tuple(range(1, 16))
    assert m.eval(to_list(from_list(deep))) == [Expression(deep)]

    deque = push_back(9, push_front(0, from_list((4, 5, 6))))
    assert m.eval(to_list(deque)) == [Expression((0, 4, 5, 6, 9))]

    left, right = from_list((1, 2, 3, 4, 5)), from_list((6, 7, 8, 9, 10))
    assert m.eval(to_list(concat(left, right))) == [Expression(range(1, 11))]
    assert m.eval(to_list(concat(ft_empty(), from_list((S.x, S.y))))) == [S.x(S.y)]
    assert m.eval(to_list(concat(from_list((S.x, S.y)), ft_empty()))) == [S.x(S.y)]

    singleton = push_front(S.a, ft_empty())
    seven = from_list((S.b, S.c, S.d, S.e, S.f, S.g, S.h))
    assert m.eval(to_list(concat(singleton, seven))) == [
        S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h)
    ]

    assert m.eval(is_empty(ft_empty())) == [True]
    assert m.eval(is_empty(push_front(1, ft_empty()))) == [False]

    nested = from_list((S.nested(S.pair), S.plain))
    assert m.eval(front(nested)) == [S.nested(S.pair)]
