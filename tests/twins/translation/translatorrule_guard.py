"""The Python twin of examples/translation/translatorrule_guard.metta.

A translator rule's head is a PATTERN, so a rule can carry a guard: it names
the shape it rewrites and a call of another shape falls through to ordinary
dispatch. The example walks that from both sides, and adds the other half a
head shape cannot say, which is that a rule's BODY is its condition too: a
clause whose body has no answer declines and the next clause is tried.

Every definition here stays at the container door, and the reasons are the
compiled subset's own. `add-pairs`, `hold-pairs`, `pick` and `only-a` select
on head PATTERNS, `(pair $a $b)` and the symbol `a`, where a compiled head
pattern is a literal default and reaches neither a structure nor a symbol.
`holds-a-miss` names the hyphenated `add-pairs`, which a compiled body cannot
resolve because it resolves a free name exactly. `pick` and `both-ways` answer
LOWERCASE SYMBOLS as data, `(picked $x)` and `bw-one`, and a lowercase free
name in a compiled body is looked up as a function while a capitalised one
would be a different atom. All three are recorded against P14.4.

What the rewrite does reach is the term door, where every form below is one
call over data: a symbol calls to build, and a plain Python tuple is the
expression its arguments are.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17296 to 17296, +0, by the wave-4 idiom rewrite:
#: every form is the same term built at the same door, so the rewrite is a
#: SPELLING change and the counter says so.
BUDGET = 17296


def pair_sum(head):
    """`(= (head (pair $a $b) (pair $c $d)) (noeval (pair (+ $a $c) (+ $b $d))))`,
    the guarded clause both `add-pairs` and `hold-pairs` are written from.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return equation(head(S.pair(V.a, V.b), S.pair(V.c, V.d))).to(
        S.noeval(S.pair(V.a + V.c, V.b + V.d))
    )


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    an `add-atom` or `add-translator-rule!` form answers what it added.
    """
    # !(add-atom &petta (dispatch-policy add-pairs NoMatchEnum NoMatchFail))
    yield m.eval(
        S["add-atom"](
            S["&petta"],
            S["dispatch-policy"](
                S["add-pairs"], S.NoMatchEnum, S.NoMatchFail
            ),
        )
    )

    # This one rewrites a pair addition only when both arguments are pairs.
    # (: add-pairs (-> Atom Atom %Undefined%))
    m += S[":"](S["add-pairs"], S["->"](S.Atom, S.Atom, S["%Undefined%"]))
    # (= (add-pairs (pair $a $b) (pair $c $d))
    #    (noeval (pair (+ $a $c) (+ $b $d))))
    m += pair_sum(S["add-pairs"])
    # !(add-translator-rule! add-pairs)
    yield m.eval(S["add-translator-rule!"](S["add-pairs"]))

    # !(test (add-pairs (pair 1 2) (pair 10 20)) (pair 11 22))
    yield m.eval(
        S.test(
            S["add-pairs"](S.pair(1, 2), S.pair(10, 20)), S.pair(11, 22)
        )
    )

    # A call the rule does not match carries on to ordinary dispatch, so a
    # miss has no answer rather than bringing the translation down.
    # !(test (collapse (add-pairs 1 2)) ())
    yield m.eval(S.test(S.collapse(S["add-pairs"](1, 2)), ()))

    # (= (holds-a-miss) (add-pairs 1 2))
    m += equation(S["holds-a-miss"]()).to(S["add-pairs"](1, 2))
    # !(test (collapse (holds-a-miss)) ())
    yield m.eval(S.test(S.collapse(S["holds-a-miss"]()), ()))

    # To hand a miss back as DATA instead, write the identity as a second
    # equation; noeval stops the expansion from going round again.
    # (: hold-pairs (-> Atom Atom %Undefined%))
    m += S[":"](S["hold-pairs"], S["->"](S.Atom, S.Atom, S["%Undefined%"]))
    # (= (hold-pairs (pair $a $b) (pair $c $d))
    #    (noeval (pair (+ $a $c) (+ $b $d))))
    m += pair_sum(S["hold-pairs"])
    # (= (hold-pairs $a $b) (noeval (noeval (hold-pairs $a $b))))
    m += equation(S["hold-pairs"](V.a, V.b)).to(
        S.noeval(S.noeval(S["hold-pairs"](V.a, V.b)))
    )
    # !(add-translator-rule! hold-pairs)
    yield m.eval(S["add-translator-rule!"](S["hold-pairs"]))

    # !(test (hold-pairs (pair 1 2) (pair 10 20)) (pair 11 22))
    yield m.eval(
        S.test(
            S["hold-pairs"](S.pair(1, 2), S.pair(10, 20)), S.pair(11, 22)
        )
    )
    # !(test (hold-pairs 1 2) (hold-pairs 1 2))
    yield m.eval(
        S.test(S["hold-pairs"](1, 2), S["hold-pairs"](1, 2))
    )

    # The engine's own stream operations are written that way.
    # !(test (collapse (union (superpose (1 2)) (superpose (2 3)))) (1 2 2 3))
    yield m.eval(
        S.test(
            S.collapse(S.union(S.superpose((1, 2)), S.superpose((2, 3)))),
            (1, 2, 2, 3),
        )
    )
    # !(test (union foo bar) (union foo bar))
    yield m.eval(S.test(S.union(S.foo, S.bar), S.union(S.foo, S.bar)))

    # A RULE'S BODY IS ITS CONDITION: a body with no answer declines, and the
    # next clause is tried.
    # (: pick (-> Atom %Undefined%))
    m += S[":"](S.pick, S["->"](S.Atom, S["%Undefined%"]))
    # (= (pick a) (empty))
    m += equation(S.pick(S.a)).to(S.empty())
    # (= (pick $x) (noeval (picked $x)))
    m += equation(S.pick(V.x)).to(S.noeval(S.picked(V.x)))
    # !(add-translator-rule! pick)
    yield m.eval(S["add-translator-rule!"](S.pick))

    # !(test (pick a) (picked a))
    yield m.eval(S.test(S.pick(S.a), S.picked(S.a)))
    # !(test (pick b) (picked b))
    yield m.eval(S.test(S.pick(S.b), S.picked(S.b)))

    # And when NO clause applies, the whole rule declines and the call carries
    # on to ordinary dispatch.
    # (: only-a (-> Atom %Undefined%))
    m += S[":"](S["only-a"], S["->"](S.Atom, S["%Undefined%"]))
    # (= (only-a a) (empty))
    m += equation(S["only-a"](S.a)).to(S.empty())
    # !(add-translator-rule! only-a)
    yield m.eval(S["add-translator-rule!"](S["only-a"]))

    # !(test (collapse (only-a a)) ())
    yield m.eval(S.test(S.collapse(S["only-a"](S.a)), ()))

    # A rule is DETERMINISTIC in a way the function of the same equations is
    # not: written as a plain function the same two equations answer twice.
    # (= (both-ways $x) bw-one)
    m += equation(S["both-ways"](V.x)).to(S["bw-one"])
    # (= (both-ways $x) bw-two)
    m += equation(S["both-ways"](V.x)).to(S["bw-two"])
    # !(test (collapse (both-ways q)) (bw-one bw-two))
    yield m.eval(
        S.test(
            S.collapse(S["both-ways"](S.q)), (S["bw-one"], S["bw-two"])
        )
    )
