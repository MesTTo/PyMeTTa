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
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import HERE, TRUE, Expression, S, V, equation, val

#: Why this file sits below the top rung: every definition but `sc-pick-max`
#: calls a hyphenated sibling, which a compiled body cannot name.
RUNG = "every definition but sc-pick-max calls a hyphenated sibling, and a compiled body names a callee by exactly its MeTTa spelling"

#: The colours, the grades and the taxonomy the last three programs work over.
COLOURS = ((0, val("blue")), (1, val("green")), (2, val("blue")))
GRADES = ((0, val("tom"), 50), (0, val("jerry"), 70), (0, val("alice"), 60),
          (1, val("bob"), 80), (1, val("sherry"), 90), (1, val("frank"), 30))
KINDS = ((S.giraffe, S.mammal), (S.tiger, S.mammal), (S.mammal, S.animal))
NAMES = ((1, S.giraffe), (1, S.tiger), (2, S.giraffe), (2, S.tiger))

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 44899 to 40968, -3931 (-8.75%), by the twin contract
#: change: five `test` wrappers left the engine for Python's own `assert`, which
#: is all that could move; the five README programs are the example.
#: `sc-pick-max` was already compiled at the previous pin, so `@m.define`'s
#: per-name admission (~1.6k inferences paid once at decoration) is inside both
#: figures. Against the example's 76585 the ratio is 0.5349 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/reasoning/scallop_readme.metta`]. Prior: RE-PINNED at 44899, +1623,
#: when `sc-pick-max` gained the decorator; ADDED 2026-08-22 at 43276 by the
#: wave-3 twin baseline.
BUDGET = 40968


def twin(m):
    """Five README programs, and the five answers Scallop prints for them."""
    # 1. Paths over edges. README result {(0,1), (0,2), (1,2)}.
    m += S["sc-edge"](0, 1)
    m += S["sc-edge"](1, 2)
    m += equation(S["sc-edge-to"](V.a)).to(S.match(HERE, S["sc-edge"](V.a, V.b), V.b))
    m += equation(S["sc-path-to"](V.a)).to(S["sc-edge-to"](V.a))
    m += equation(S["sc-path-to"](V.a)).to(
        S.let(V.b, S["sc-edge-to"](V.a), S["sc-path-to"](V.b))
    )
    m += equation(S["sc-paths"]()).to(
        S.collapse(S.let(V.a, S.match(HERE, S["sc-edge"](V.a, V._), V.a),
                         S.let(V.b, S["sc-path-to"](V.a), (V.a, V.b))))
    )

    assert m.eval(S["sc-paths"]()) == [Expression((Expression((0, 1)), Expression((0, 2)), Expression((1, 2))))]

    # 2. Stratified even-or-odd: negation sees the finite number relation whole.
    for number in range(11):
        m += S["sc-number"](number)
    m += equation(S["sc-odd?"](1)).to(TRUE)
    m += equation(S["sc-odd?"](V.x)).to(
        S.let(V.n, S.match(HERE, S["sc-number"](V.x), V.x), S["sc-odd?"](V.n - 2))
    )
    m += equation(S["sc-evens"]()).to(
        S.collapse(S.let(V.y, S.match(HERE, S["sc-number"](V.y), V.y),
                         S.let(TRUE, S["not-provable"](S["sc-odd?"](V.y)), V.y)))
    )

    assert m.eval(S["sc-evens"]()) == [Expression((0, 2, 4, 6, 8, 10))]

    # 3. A count per colour, through the general fold rather than a counter.
    for obj, colour in COLOURS:
        m += S["sc-object-color"](obj, colour)
    m += equation(S["sc-one-color"](V.c)).to(
        S.let(V.o, S.match(HERE, S["sc-object-color"](V.o, V.c), V.o), 1)
    )
    m += equation(S["sc-color-count"](V.c)).to(S.foldall(S["+"], S["sc-one-color"](V.c), 0))
    m += equation(S["sc-color-counts"]()).to(
        S.collapse(S.let(V.c, S.superpose((val("blue"), val("green"))),
                         (V.c, S["sc-color-count"](V.c))))
    )

    assert m.eval(S["sc-color-counts"]()) == [
        Expression((Expression((val("blue"), 2)), Expression((val("green"), 1))))
    ]

    # 4. An argmax per class, through an open reducer rather than a closed list.
    for klass, student, grade in GRADES:
        m += S["sc-class-student-grade"](klass, student, grade)

    @m.define(name="sc-pick-max")
    def sc_pick_max(a, b):
        """The larger of two grades."""
        return a if a > b else b  # noqa: FURB136  -- max(b, a) compiles to (max $b $a), a different equation from the example's (if (> $a $b) $a $b)

    m += equation(S["sc-class-max"](V.c)).to(
        S.foldall(S["sc-pick-max"],
                  S.match(HERE, S["sc-class-student-grade"](V.c, V._, V.g), V.g),
                  -1)
    )
    m += equation(S["sc-class-top"]()).to(
        S.collapse(S.let(V.c, S.superpose((0, 1)),
                         S.let(V.g, S["sc-class-max"](V.c),
                               S.let(V.s,
                                     S.match(HERE,
                                             S["sc-class-student-grade"](V.c, V.s, V.g),
                                             V.s),
                                     (V.c, V.s)))))
    )

    assert m.eval(S["sc-class-top"]()) == [
        Expression((Expression((0, val("jerry"))), Expression((1, val("sherry")))))
    ]

    # 5. The animal count as a SET: the raw proof multiset has four
    # derivations, and `unique` makes Scallop's two.
    for kind, parent in KINDS:
        m += S["sc-is-a"](kind, parent)
    for obj, kind in NAMES:
        m += S["sc-name"](obj, kind)
    m += equation(S["sc-parent-kind"](V.x)).to(S.match(HERE, S["sc-is-a"](V.x, V.y), V.y))
    m += equation(S["sc-ancestor-kind"](V.x)).to(S["sc-parent-kind"](V.x))
    m += equation(S["sc-ancestor-kind"](V.x)).to(
        S.let(V.y, S["sc-parent-kind"](V.x), S["sc-ancestor-kind"](V.y))
    )
    m += equation(S["sc-animal-object"]()).to(
        S.let((V.o, V.kind),
              S.match(HERE, S["sc-name"](V.o, V.kind), (V.o, V.kind)),
              S.let(V.ancestor, S["sc-ancestor-kind"](V.kind),
                    S["if"](V.ancestor.eq(S.animal), V.o, S.empty())))
    )
    m += equation(S["sc-one-animal"]()).to(S.let(V.o, S.unique(S["sc-animal-object"]()), 1))
    m += equation(S["sc-animal-count"]()).to(S.foldall(S["+"], S["sc-one-animal"](), 0))

    assert m.eval(S["sc-animal-count"]()) == [2]
