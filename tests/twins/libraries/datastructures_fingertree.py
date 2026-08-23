"""Purpose: examples/libraries/datastructures_fingertree.metta in Python: the finger tree, walked.

The finger tree from lib_datastructures: O(1) at both ends, O(log n)
concatenation, one structure serving as sequence and deque at once. Fifteen
claims, every one of them about one of the eleven `ft-*` functions, so all
eleven are named.

Every claim nests the calls the way Python nests calls,
`push_front(1, push_back(3, push_front(2, ft_empty())))` through
`m.fn.ft_push_front` and its siblings. A call answers a lazy view, and a view
crossing into term position is an observation point: exactly one answer is
encoded, and zero or several refuse loudly, so a deterministic function
composes without any `.one()` between the levels. The one place `.one()` is
written is where a pop's single answer is UNPACKED into two Python names.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 264 inferences over the concurrent lane's own observations, because
#: the shared engine's scheduling changes what a concurrent round costs
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Build, inspect, drain, and concatenate finger trees from Python."""
    m.fn["import!"](m, S.library(S["lib_datastructures"]))

    ft_empty, from_list, to_list = m.fn.ft_empty, m.fn.ft_from_list, m.fn.ft_to_list
    push_front, push_back = m.fn.ft_push_front, m.fn.ft_push_back
    front, back = m.fn.ft_front, m.fn.ft_back
    pop_front, pop_back = m.fn.ft_pop_front, m.fn.ft_pop_back
    concat, is_empty = m.fn.ft_concat, m.fn.ft_is_empty

    built_at_both_ends = push_front(1, push_back(3, push_front(2, ft_empty())))
    assert to_list(built_at_both_ends) == [Expression((1, 2, 3))]

    ten = (S.a, S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert to_list(from_list(ten)) == [Expression(ten)]

    abc = from_list((S.a, S.b, S.c))
    assert front(abc) == [S.a]
    assert back(abc) == [S.c]

    # A pop answers the element and the remaining tree, so the example reads
    # both out of one answer; Python's own unpacking is that reading.
    item, remainder = pop_front(abc).one()
    assert (item, to_list(remainder)) == (S.a, [S.b(S.c)])

    item, remainder = pop_back(abc).one()
    assert (item, to_list(remainder)) == (S.c, [S.a(S.b)])

    deep = tuple(range(1, 16))
    assert to_list(from_list(deep)) == [Expression(deep)]

    deque = push_back(9, push_front(0, from_list((4, 5, 6))))
    assert to_list(deque) == [Expression((0, 4, 5, 6, 9))]

    left, right = from_list((1, 2, 3, 4, 5)), from_list((6, 7, 8, 9, 10))
    assert to_list(concat(left, right)) == [Expression(range(1, 11))]
    assert to_list(concat(ft_empty(), from_list((S.x, S.y)))) == [S.x(S.y)]
    assert to_list(concat(from_list((S.x, S.y)), ft_empty())) == [S.x(S.y)]

    singleton = push_front(S.a, ft_empty())
    seven = from_list((S.b, S.c, S.d, S.e, S.f, S.g, S.h))
    assert to_list(concat(singleton, seven)) == [
        S.a(S.b, S.c, S.d, S.e, S.f, S.g, S.h)
    ]

    assert is_empty(ft_empty()) == [True]
    assert is_empty(push_front(1, ft_empty())) == [False]

    nested = from_list((S.nested(S.pair), S.plain))
    assert front(nested) == [S.nested(S.pair)]
