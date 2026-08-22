"""Purpose: exercise the finger-tree example through Python calls.

The twin covers every claim in examples/libraries/datastructures_fingertree.metta.
Assumes:
  - lib_datastructures publishes the eleven ``ft-*`` functions used below
    [source: lib/lib_datastructures.metta:ft-empty; commit=WORKTREE]
Guarantees:
  - twin imports the library and asserts all fifteen source claims, including
    both end operations, deep trees, concatenation, and nested data
    [measured: twin completed; command=bindings/python/tools/twin_coverage.py --measure examples/libraries/datastructures_fingertree.metta; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 312515..312779 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 312515,
    "maximum": 312779,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Build, inspect, drain, and concatenate finger trees from Python."""
    m.eval(
        S["import!"](
            S["&self"],  # rung: import!'s target is a named space argument; handles do not yet encode there
            S.library(S.lib_datastructures),
        )
    )

    ft_empty = m.fn("ft-empty")
    push_front = m.fn("ft-push-front")
    push_back = m.fn("ft-push-back")
    from_list = m.fn("ft-from-list")
    to_list = m.fn("ft-to-list")
    front = m.fn("ft-front")
    back = m.fn("ft-back")
    pop_front = m.fn("ft-pop-front")
    pop_back = m.fn("ft-pop-back")
    concat = m.fn("ft-concat")
    is_empty = m.fn("ft-is-empty")

    built_at_both_ends = push_front(1, push_back(3, push_front(2, ft_empty())))
    assert tuple(to_list(built_at_both_ends)) == (1, 2, 3)

    ten = (S.a, S.b, S.c, S.d, S.e, S.f, S.g, S.h, S.i, S.j)
    assert tuple(to_list(from_list(ten))) == ten

    abc = from_list((S.a, S.b, S.c))
    assert front(abc) == S.a
    assert back(abc) == S.c

    item, remainder = pop_front(abc)
    assert (item, tuple(to_list(remainder))) == (S.a, (S.b, S.c))

    item, remainder = pop_back(abc)
    assert (item, tuple(to_list(remainder))) == (S.c, (S.a, S.b))

    deep = tuple(range(1, 16))
    assert tuple(to_list(from_list(deep))) == deep

    deque = push_back(9, push_front(0, from_list((4, 5, 6))))
    assert tuple(to_list(deque)) == (0, 4, 5, 6, 9)

    left, right = from_list((1, 2, 3, 4, 5)), from_list((6, 7, 8, 9, 10))
    assert tuple(to_list(concat(left, right))) == tuple(range(1, 11))
    assert tuple(to_list(concat(ft_empty(), from_list((S.x, S.y))))) == (S.x, S.y)
    assert tuple(to_list(concat(from_list((S.x, S.y)), ft_empty()))) == (S.x, S.y)

    singleton = push_front(S.a, ft_empty())
    assert tuple(to_list(concat(singleton, from_list((S.b, S.c, S.d, S.e, S.f, S.g, S.h))))) == (
        S.a,
        S.b,
        S.c,
        S.d,
        S.e,
        S.f,
        S.g,
        S.h,
    )

    assert is_empty(ft_empty()) is True
    assert is_empty(push_front(1, ft_empty())) is False

    nested = from_list((S.nested(S.pair), S.plain))
    assert front(nested) == S.nested(S.pair)
