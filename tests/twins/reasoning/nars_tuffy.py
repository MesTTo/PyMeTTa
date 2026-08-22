"""The Python twin of examples/reasoning/nars_tuffy.metta: the Tuffy smokers KB.

The knowledge base is ONE equation whose body is a ten-element expression, so
it is written as data: a Python tuple of ten `sentence(...)` calls. NARS spells
four things with punctuation the term door reaches only by name, so each is
named once and the ten rows then read as the logic they are: `-->` is
inheritance, `==>` implication, `[] p` the property `p`, and U+00D7 the
product of two terms. That last head is written as the escape
`\N{MULTIPLICATION SIGN}` and quoted as `multiplication-sign` in the
comments, because a bare one is a confusable ruff refuses.

`kb` stays at the container door because its body is DATA rather than a
computation: a compiled body's free names must be parameters, functions the
engine knows by exactly that name, or capitalised constructors, and `-->`,
`==>` and the product head are none of the three.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 16271945 across the rewrite: the named NARS constructors
#: and the tuple rows build the same two atoms the hand-nested `expr` calls
#: built, which the atom-level differential confirms byte-for-byte. Prior: ADDED
#: 2026-08-22 at 16271945 by the wave-3 twin baseline.
BUDGET = 16271945


def inheritance(subject, predicate):
    """`(--> subject predicate)`, NARS inheritance."""
    return S["-->"](subject, predicate)


def implication(premise, conclusion):
    """`(==> premise conclusion)`, NARS implication."""
    return S["==>"](premise, conclusion)


def product(left, right):
    """`(multiplication-sign left right)`, the NARS product of two terms."""
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
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_nars))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_nars)))

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

    # !(test (NARS.Query (kb)
    #                    (--> Edward ([] cancerous)))
    #        ((stv 0.6 0.48941156079382964) (2 5 6 9 10)))
    yield m.eval(
        S.test(
            S["NARS.Query"](
                S.kb(), inheritance(S.Edward, prop(S.cancerous))
            ),
            (S.stv(0.6, 0.48941156079382964), (2, 5, 6, 9, 10)),
        )
    )
