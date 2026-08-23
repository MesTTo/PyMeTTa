"""Purpose: examples/reasoning/scallop_readme.metta in Python: the five Scallop README programs.

Transitive paths over edges, stratified even-or-odd through negation, a count
per colour, an argmax per class, and a set-valued animal count. Each is a
handful of facts plus a handful of equations, and each claim is the answer the
Scallop README prints.

`sc-pick-max` is the one definition a compiled body can spell, and it is the
one whose body names no other `sc-` function: Python's ternary is MeTTa's `if`
and `>` builds the comparison. Every other definition calls a SIBLING whose
MeTTa name is hyphenated, and a compiled body names a callee by exactly its
MeTTa spelling, which `sc-edge-to` is not a Python identifier for. That is the
same wall examples/basics/fibsmart.metta records against P14.4, and it is what
keeps the rest of this file at the container door.

Everything the container door does reach is Python's: the facts are loops over
tuples, `(> $a $b)` is `V.a > V.b`, `(- $n 2)` is `V.n - 2`, and
`(== $ancestor animal)` is `V.ancestor.eq(S.animal)`, because `==` between atoms
is Python's own structural equality and the equality TERM is `.eq`. The five
`collapse` calls stay where they are: each is inside a DEFINITION, so it is the
example's own body rather than a claim the twin could make in Python.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import HERE, TRUE, Expression, G, S, V, equation, fn, if_

#: The colours, the grades and the taxonomy the last three programs work over.
COLOURS = ((0, G("blue")), (1, G("green")), (2, G("blue")))
GRADES = ((0, G("tom"), 50), (0, G("jerry"), 70), (0, G("alice"), 60),
          (1, G("bob"), 80), (1, G("sherry"), 90), (1, G("frank"), 30))
KINDS = ((S.giraffe, S.mammal), (S.tiger, S.mammal), (S.mammal, S.animal))
NAMES = ((1, S.giraffe), (1, S.tiger), (2, S.giraffe), (2, S.tiger))

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Five README programs, and the five answers Scallop prints for them."""
    # 1. Paths over edges. README result {(0,1), (0,2), (1,2)}.
    m += S["sc-edge"](0, 1)
    m += S["sc-edge"](1, 2)
    m += equation(S["sc-edge-to"](V.a)).to(
        fn.match(HERE, S["sc-edge"](V.a, V.b), V.b)  # rung: a match INSIDE a stored body, where the subscript door is a Python read (P14.4)
    )
    m += equation(S["sc-path-to"](V.a)).to(S["sc-edge-to"](V.a))
    m += equation(S["sc-path-to"](V.a)).to(
        fn.let(V.b, S["sc-edge-to"](V.a), S["sc-path-to"](V.b))  # rung: a let over a hyphenated sibling, which a compiled body cannot name (P14.4)
    )
    m += equation(S["sc-paths"]()).to(
        fn.collapse(  # rung: a collapse INSIDE a stored body, where list() is a Python read (P14.4)
            fn.let(V.a, fn.match(HERE, S["sc-edge"](V.a, V._), V.a),  # rung: the same let and match (P14.4)
                   fn.let(V.b, S["sc-path-to"](V.a), (V.a, V.b)))  # rung: the same let (P14.4)
        )
    )

    assert m.fn.sc_paths() == [
        Expression((Expression((0, 1)), Expression((0, 2)), Expression((1, 2))))
    ]

    # 2. Stratified even-or-odd: negation sees the finite number relation whole.
    for number in range(11):
        m += S["sc-number"](number)
    m += equation(S["sc-odd?"](1)).to(TRUE)
    m += equation(S["sc-odd?"](V.x)).to(
        fn.let(V.n, fn.match(HERE, S["sc-number"](V.x), V.x), S["sc-odd?"](V.n - 2))  # rung: the same let and match (P14.4)
    )
    m += equation(S["sc-evens"]()).to(
        fn.collapse(  # rung: the same collapse (P14.4)
            fn.let(V.y, fn.match(HERE, S["sc-number"](V.y), V.y),  # rung: the same let and match (P14.4)
                   fn.let(TRUE, fn.not_provable(S["sc-odd?"](V.y)), V.y))  # rung: the same let (P14.4)
        )
    )

    assert m.fn.sc_evens() == [Expression((0, 2, 4, 6, 8, 10))]

    # 3. A count per colour, through the general fold rather than a counter.
    for obj, colour in COLOURS:
        m += S["sc-object-color"](obj, colour)
    m += equation(S["sc-one-color"](V.c)).to(
        fn.let(V.o, fn.match(HERE, S["sc-object-color"](V.o, V.c), V.o), 1)  # rung: the same let and match (P14.4)
    )
    m += equation(S["sc-color-count"](V.c)).to(
        fn.foldall(fn["+"], S["sc-one-color"](V.c), 0)
    )
    m += equation(S["sc-color-counts"]()).to(
        fn.collapse(  # rung: the same collapse (P14.4)
            fn.let(V.c, fn.superpose((G("blue"), G("green"))),  # rung: the same let (P14.4)
                   (V.c, S["sc-color-count"](V.c)))
        )
    )

    assert m.fn.sc_color_counts() == [
        Expression((Expression((G("blue"), 2)), Expression((G("green"), 1))))
    ]

    # 4. An argmax per class, through an open reducer rather than a closed list.
    for klass, student, grade in GRADES:
        m += S["sc-class-student-grade"](klass, student, grade)

    @m.define
    def sc_pick_max(a, b):
        """The larger of two grades."""
        return a if a > b else b  # noqa: FURB136  -- max(b, a) compiles to (max $b $a), a different equation from the example's (if (> $a $b) $a $b)

    m += equation(S["sc-class-max"](V.c)).to(
        fn.foldall(S["sc-pick-max"],
                   fn.match(HERE, S["sc-class-student-grade"](V.c, V._, V.g), V.g),  # rung: the same match (P14.4)
                   -1)
    )
    m += equation(S["sc-class-top"]()).to(
        fn.collapse(  # rung: the same collapse (P14.4)
            fn.let(V.c, fn.superpose((0, 1)),  # rung: the same let (P14.4)
                   fn.let(V.g, S["sc-class-max"](V.c),  # rung: the same let (P14.4)
                          fn.let(V.s,  # rung: the same let (P14.4)
                                 fn.match(HERE,  # rung: the same match (P14.4)
                                          S["sc-class-student-grade"](V.c, V.s, V.g),
                                          V.s),
                                 (V.c, V.s))))
        )
    )

    assert m.fn.sc_class_top() == [
        Expression((Expression((0, G("jerry"))), Expression((1, G("sherry")))))
    ]

    # 5. The animal count as a SET: the raw proof multiset has four
    # derivations, and `unique` makes Scallop's two.
    for kind, parent in KINDS:
        m += S["sc-is-a"](kind, parent)
    for obj, kind in NAMES:
        m += S["sc-name"](obj, kind)
    m += equation(S["sc-parent-kind"](V.x)).to(
        fn.match(HERE, S["sc-is-a"](V.x, V.y), V.y)  # rung: the same match (P14.4)
    )
    m += equation(S["sc-ancestor-kind"](V.x)).to(S["sc-parent-kind"](V.x))
    m += equation(S["sc-ancestor-kind"](V.x)).to(
        fn.let(V.y, S["sc-parent-kind"](V.x), S["sc-ancestor-kind"](V.y))  # rung: the same let (P14.4)
    )
    m += equation(S["sc-animal-object"]()).to(
        fn.let((V.o, V.kind),  # rung: the same let (P14.4)
               fn.match(HERE, S["sc-name"](V.o, V.kind), (V.o, V.kind)),  # rung: the same match (P14.4)
               fn.let(V.ancestor, S["sc-ancestor-kind"](V.kind),  # rung: the same let (P14.4)
                      if_(V.ancestor.eq(S.animal), V.o, fn.empty())))
    )
    m += equation(S["sc-one-animal"]()).to(
        fn.let(V.o, fn.unique(S["sc-animal-object"]()), 1)  # rung: the same let (P14.4)
    )
    m += equation(S["sc-animal-count"]()).to(
        fn.foldall(fn["+"], S["sc-one-animal"](), 0)
    )

    assert m.fn.sc_animal_count() == [2]
