"""The Python twin of examples/reasoning/scallop_readme.metta: five Scallop programs.

`sc-pick-max` is the one definition a compiled body can spell, and it is the
one whose body names no other `sc-` function: Python's ternary is MeTTa's `if`
and `>` builds the comparison. Every other definition calls a SIBLING whose
MeTTa name is hyphenated, and a compiled body names a function by exactly its
MeTTa spelling, which `sc-edge-to` is not a Python identifier for. That is the
same gap examples/basics/fibsmart.metta already records against P14.4, and it
is what keeps the rest of this file at the term door.

Everything the term door does reach is written as Python: the eleven
`sc-number` facts are a `range`, `(0 1)` is the tuple `(0, 1)`, `(> $a $b)` is
`V.a > V.b`, `(- $n 2)` is `V.n - 2`, and `(== $ancestor animal)` is
`V.ancestor.eq(S.animal)` because `==` between atoms is structural equality and
the equality TERM is `.eq`.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 43276 to 44899, +1623 (+3.75%), by `sc-pick-max` moving
#: to the definitional decorator. The compiled clause is the same clause; the
#: charge is @m.define's per-name admission, the three reflection facts the
#: container door never writes (`(defined &self sc-pick-max)`,
#: `(effect sc-pick-max immutable)` and `(source-span &self sc-pick-max ...)`),
#: measured at ~1.6k inferences per decorated name and paid once at decoration.
#: Prior: ADDED 2026-08-22 at 43276 by the wave-3 twin baseline.
BUDGET = 44899

#: `(context-space)`, the space a definition reads when it names none.
HERE = S["context-space"]()


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # Path over edges: README result {(0,1), (0,2), (1,2)}.
    # (sc-edge 0 1)
    m += S["sc-edge"](0, 1)
    # (sc-edge 1 2)
    m += S["sc-edge"](1, 2)

    # (= (sc-edge-to $a)
    #    (match (context-space) (sc-edge $a $b) $b))
    m += equation(S["sc-edge-to"](V.a)).to(
        S.match(HERE, S["sc-edge"](V.a, V.b), V.b)
    )

    # (= (sc-path-to $a) (sc-edge-to $a))
    m += equation(S["sc-path-to"](V.a)).to(S["sc-edge-to"](V.a))

    # (= (sc-path-to $a)
    #    (let $b (sc-edge-to $a) (sc-path-to $b)))
    m += equation(S["sc-path-to"](V.a)).to(
        S.let(V.b, S["sc-edge-to"](V.a), S["sc-path-to"](V.b))
    )

    # (= (sc-paths)
    #    (collapse
    #       (let $a (match (context-space) (sc-edge $a $_) $a)
    #         (let $b (sc-path-to $a) ($a $b)))))
    m += equation(S["sc-paths"]()).to(
        S.collapse(
            S.let(
                V.a,
                S.match(HERE, S["sc-edge"](V.a, V._), V.a),
                S.let(V.b, S["sc-path-to"](V.a), (V.a, V.b)),
            )
        )
    )

    # !(test (sc-paths) ((0 1) (0 2) (1 2)))
    yield m.eval(S.test(S["sc-paths"](), ((0, 1), (0, 2), (1, 2))))

    # Stratified even/odd: negation sees the finite number relation whole.
    # (sc-number 0) ... (sc-number 10)
    for number in range(11):
        m += S["sc-number"](number)

    # (= (sc-odd? 1) True)
    m += equation(S["sc-odd?"](1)).to(TRUE)

    # (= (sc-odd? $x)
    #    (let $n (match (context-space) (sc-number $x) $x)
    #      (sc-odd? (- $n 2))))
    m += equation(S["sc-odd?"](V.x)).to(
        S.let(
            V.n,
            S.match(HERE, S["sc-number"](V.x), V.x),
            S["sc-odd?"](V.n - 2),
        )
    )

    # (= (sc-evens)
    #    (collapse
    #       (let $y (match (context-space) (sc-number $y) $y)
    #         (let True (not-provable (sc-odd? $y)) $y))))
    m += equation(S["sc-evens"]()).to(
        S.collapse(
            S.let(
                V.y,
                S.match(HERE, S["sc-number"](V.y), V.y),
                S.let(TRUE, S["not-provable"](S["sc-odd?"](V.y)), V.y),
            )
        )
    )

    # !(test (sc-evens) (0 2 4 6 8 10))
    yield m.eval(S.test(S["sc-evens"](), (0, 2, 4, 6, 8, 10)))

    # Count per color through the general fold operation.
    # (sc-object-color 0 "blue")
    m += S["sc-object-color"](0, val("blue"))
    # (sc-object-color 1 "green")
    m += S["sc-object-color"](1, val("green"))
    # (sc-object-color 2 "blue")
    m += S["sc-object-color"](2, val("blue"))

    # (= (sc-one-color $c)
    #    (let $o (match (context-space) (sc-object-color $o $c) $o) 1))
    m += equation(S["sc-one-color"](V.c)).to(
        S.let(V.o, S.match(HERE, S["sc-object-color"](V.o, V.c), V.o), 1)
    )

    # (= (sc-color-count $c) (foldall + (sc-one-color $c) 0))
    m += equation(S["sc-color-count"](V.c)).to(
        S.foldall(S["+"], S["sc-one-color"](V.c), 0)
    )

    # (= (sc-color-counts)
    #    (collapse
    #       (let $c (superpose ("blue" "green"))
    #         ($c (sc-color-count $c)))))
    m += equation(S["sc-color-counts"]()).to(
        S.collapse(
            S.let(
                V.c,
                S.superpose((val("blue"), val("green"))),
                (V.c, S["sc-color-count"](V.c)),
            )
        )
    )

    # !(test (sc-color-counts) (("blue" 2) ("green" 1)))
    yield m.eval(
        S.test(S["sc-color-counts"](), ((val("blue"), 2), (val("green"), 1)))
    )

    # Argmax per class through an open reducer rather than a closed aggregate list.
    # (sc-class-student-grade 0 "tom" 50)
    m += S["sc-class-student-grade"](0, val("tom"), 50)
    # (sc-class-student-grade 0 "jerry" 70)
    m += S["sc-class-student-grade"](0, val("jerry"), 70)
    # (sc-class-student-grade 0 "alice" 60)
    m += S["sc-class-student-grade"](0, val("alice"), 60)
    # (sc-class-student-grade 1 "bob" 80)
    m += S["sc-class-student-grade"](1, val("bob"), 80)
    # (sc-class-student-grade 1 "sherry" 90)
    m += S["sc-class-student-grade"](1, val("sherry"), 90)
    # (sc-class-student-grade 1 "frank" 30)
    m += S["sc-class-student-grade"](1, val("frank"), 30)

    @m.define(name="sc-pick-max")
    def sc_pick_max(a, b):
        # (= (sc-pick-max $a $b) (if (> $a $b) $a $b))
        return a if a > b else b  # noqa: FURB136  -- max(b, a) compiles to (max $b $a), a different equation from the example's (if (> $a $b) $a $b)

    # (= (sc-class-max $c)
    #    (foldall sc-pick-max
    #             (match (context-space)
    #                    (sc-class-student-grade $c $_ $g)
    #                    $g)
    #             -1))
    m += equation(S["sc-class-max"](V.c)).to(
        S.foldall(
            S["sc-pick-max"],
            S.match(HERE, S["sc-class-student-grade"](V.c, V._, V.g), V.g),
            -1,
        )
    )

    # (= (sc-class-top)
    #    (collapse
    #       (let $c (superpose (0 1))
    #         (let $g (sc-class-max $c)
    #           (let $s
    #             (match (context-space)
    #                    (sc-class-student-grade $c $s $g)
    #                    $s)
    #             ($c $s))))))
    m += equation(S["sc-class-top"]()).to(
        S.collapse(
            S.let(
                V.c,
                S.superpose((0, 1)),
                S.let(
                    V.g,
                    S["sc-class-max"](V.c),
                    S.let(
                        V.s,
                        S.match(
                            HERE,
                            S["sc-class-student-grade"](V.c, V.s, V.g),
                            V.s,
                        ),
                        (V.c, V.s),
                    ),
                ),
            )
        )
    )

    # !(test (sc-class-top) ((0 "jerry") (1 "sherry")))
    yield m.eval(
        S.test(S["sc-class-top"](), ((0, val("jerry")), (1, val("sherry"))))
    )

    # The probabilistic animal example counts relation values as a set. The raw
    # proof multiset has four derivations, while unique makes Scallop's two.
    # (sc-is-a giraffe mammal)
    m += S["sc-is-a"](S.giraffe, S.mammal)
    # (sc-is-a tiger mammal)
    m += S["sc-is-a"](S.tiger, S.mammal)
    # (sc-is-a mammal animal)
    m += S["sc-is-a"](S.mammal, S.animal)
    # (sc-name 1 giraffe)
    m += S["sc-name"](1, S.giraffe)
    # (sc-name 1 tiger)
    m += S["sc-name"](1, S.tiger)
    # (sc-name 2 giraffe)
    m += S["sc-name"](2, S.giraffe)
    # (sc-name 2 tiger)
    m += S["sc-name"](2, S.tiger)

    # (= (sc-parent-kind $x)
    #    (match (context-space) (sc-is-a $x $y) $y))
    m += equation(S["sc-parent-kind"](V.x)).to(
        S.match(HERE, S["sc-is-a"](V.x, V.y), V.y)
    )

    # (= (sc-ancestor-kind $x) (sc-parent-kind $x))
    m += equation(S["sc-ancestor-kind"](V.x)).to(S["sc-parent-kind"](V.x))

    # (= (sc-ancestor-kind $x)
    #    (let $y (sc-parent-kind $x) (sc-ancestor-kind $y)))
    m += equation(S["sc-ancestor-kind"](V.x)).to(
        S.let(V.y, S["sc-parent-kind"](V.x), S["sc-ancestor-kind"](V.y))
    )

    # (= (sc-animal-object)
    #    (let ($o $kind)
    #      (match (context-space) (sc-name $o $kind) ($o $kind))
    #      (let $ancestor (sc-ancestor-kind $kind)
    #        (if (== $ancestor animal) $o (empty)))))
    m += equation(S["sc-animal-object"]()).to(
        S.let(
            (V.o, V.kind),
            S.match(HERE, S["sc-name"](V.o, V.kind), (V.o, V.kind)),
            S.let(
                V.ancestor,
                S["sc-ancestor-kind"](V.kind),
                S["if"](V.ancestor.eq(S.animal), V.o, S.empty()),
            ),
        )
    )

    # (= (sc-one-animal)
    #    (let $o (unique (sc-animal-object)) 1))
    m += equation(S["sc-one-animal"]()).to(
        S.let(V.o, S.unique(S["sc-animal-object"]()), 1)
    )

    # (= (sc-animal-count) (foldall + (sc-one-animal) 0))
    m += equation(S["sc-animal-count"]()).to(
        S.foldall(S["+"], S["sc-one-animal"](), 0)
    )

    # !(test (sc-animal-count) 2)
    yield m.eval(S.test(S["sc-animal-count"](), 2))
