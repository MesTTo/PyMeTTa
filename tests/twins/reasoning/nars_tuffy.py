"""Purpose: examples/reasoning/nars_tuffy.metta in Python: the Tuffy smokers knowledge base.

Ten NARS sentences say who smokes, who is friends with whom, that friends of
smokers smoke, and that smokers get cancer. The claim asks NARS what it makes
of Edward being cancerous, and gets back a truth value and the five premises it
came from.

The knowledge base is ONE equation whose body is a ten-element expression, so
it is written as data: a Python tuple of ten `sentence(...)` calls. NARS spells
four things with punctuation, so each gets a named Python function and the ten
rows then read as the logic they are: `-->` is inheritance, `==>` implication,
`[] p` the property `p`, and U+00D7 the product of two terms. That last head is
written as the escape `\N{MULTIPLICATION SIGN}` and called `multiplication-sign`
in prose, because a bare one is a confusable ruff refuses.

`kb` is ONE equation whose body is DATA, so it goes through the write door as
the atom it is. The punctuation heads are not what keeps it there: measured
2026-08-24, `S["-->"](a, S["[]"](b))` inside a compiled body stores
`(--> $a ([] $b))`. What a compiled body cannot do is CALL the seven host
helpers that make the ten rows readable, because a body is pure atoms, so
compiling `kb` would mean inlining every bracket again. The import takes the
space HANDLE, because a space crosses a term position as itself.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
"""

from metta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
BUDGET = 1


def inheritance(subject, predicate):
    """`(--> subject predicate)`, NARS inheritance."""
    return S["-->"](subject, predicate)


def implication(premise, conclusion):
    """`(==> premise conclusion)`, NARS implication."""
    return S["==>"](premise, conclusion)


def product(left, right):
    """`(multiplication-sign left right)`, the NARS product of two terms.

    The head is the REAL U+00D7, and it matches the rules in
    `lib/lib_nars.metta` because the engine reads its sources as UTF-8
    whatever the locale, which `twin_coverage.py`'s `_environment` pins to
    `LC_ALL=C` [measured 2026-08-23 under `LC_ALL=C`: 0 U+FFFD replacement
    characters and 12 real U+00D7 heads in the imported library, where the
    locale-dependent reader gave 123 replacements over the 51 `|-` clauses;
    commit=3459d4f6fce103269ff5cdd575edec4bb9e4be95].
    """
    return S["\N{MULTIPLICATION SIGN}"](left, right)


def prop(name):
    """`([] name)`, the NARS property `name`."""
    return S["[]"](name)


def sentence(statement, strength, ident):
    """`(Sentence (statement (stv strength 0.9)) (ident))`, one row of the KB.

    Every row of this example carries the same 0.9 confidence, so only the
    strength varies.
    """
    return S.Sentence((statement, S.stv(strength, 0.9)), (ident,))


def friends(left, right):
    """`(--> (multiplication-sign left right) friend)`, the friendship relation."""
    return inheritance(product(left, right), S.friend)


def smokes(who):
    """`(--> who ([] smokes))`."""
    return inheritance(who, prop(S.smokes))


def twin(m):
    """State ten sentences, then ask NARS about one of their consequences."""
    # The library's file name is `lib_nars.metta`, and the factory attribute
    # door maps every underscore to a hyphen, so the name takes the bracket.
    # !(import! &self (library lib_nars))
    m.fn["import!"](m, S.library(S["lib_nars"]))

    # The knowledge base, as the ten rows it is. `$1` and `$2` in the first two
    # rows are the rules' variables; everything below them is ground.
    # (= (kb)
    #    ((Sentence ((==> (--> (multiplication-sign $1 $2) friend)
    #                     (==> (--> $1 ([] smokes))
    #                          (--> $2 ([] smokes))))
    #                (stv 0.4 0.9)) (1))
    #     (Sentence ((==> (--> $1 ([] smokes))
    #                     (--> $1 ([] cancerous)))
    #                (stv 0.6 0.9)) (2))
    #     (Sentence ((--> (multiplication-sign Anna Bob) friend) (stv 1.0 0.9)) (3))
    #     (Sentence ((--> (multiplication-sign Anna Edward) friend) (stv 1.0 0.9)) (4))
    #     (Sentence ((--> (multiplication-sign Anna Frank) friend) (stv 1.0 0.9)) (5))
    #     (Sentence ((--> (multiplication-sign Edward Frank) friend) (stv 1.0 0.9)) (6))
    #     (Sentence ((--> (multiplication-sign Gary Helen) friend) (stv 1.0 0.9)) (7))
    #     (Sentence ((--> (multiplication-sign Gary Frank) friend) (stv 0.0 0.9)) (8))
    #     (Sentence ((--> Anna ([] smokes)) (stv 1.0 0.9)) (9))
    #     (Sentence ((--> Edward ([] smokes)) (stv 1.0 0.9)) (10))))
    m += equation(S.kb()).to(
        (
            sentence(
                implication(
                    friends(V["1"], V["2"]),
                    implication(smokes(V["1"]), smokes(V["2"])),
                ),
                0.4,
                1,
            ),
            sentence(
                implication(
                    smokes(V["1"]), inheritance(V["1"], prop(S.cancerous))
                ),
                0.6,
                2,
            ),
            sentence(friends(S.Anna, S.Bob), 1.0, 3),
            sentence(friends(S.Anna, S.Edward), 1.0, 4),
            sentence(friends(S.Anna, S.Frank), 1.0, 5),
            sentence(friends(S.Edward, S.Frank), 1.0, 6),
            sentence(friends(S.Gary, S.Helen), 1.0, 7),
            sentence(friends(S.Gary, S.Frank), 0.0, 8),
            sentence(smokes(S.Anna), 1.0, 9),
            sentence(smokes(S.Edward), 1.0, 10),
        )
    )

    # Edward smokes, so Edward is cancerous, and the answer names the five
    # sentences the derivation used.
    # !(test (NARS.Query (kb) (--> Edward ([] cancerous)))
    #        ((stv 0.6 0.48941156079382964) (2 5 6 9 10)))
    assert m.fn["NARS.Query"](
        S.kb(), inheritance(S.Edward, prop(S.cancerous))
    ) == [Expression((S.stv(0.6, 0.48941156079382964), Expression((2, 5, 6, 9, 10))))]
