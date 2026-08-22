"""examples/control/and_then_or_else.metta in Python: short-circuiting.

`and-then` and `or-else` are the short-circuiting boolean connectives. They
are special forms rather than functions, which is the whole point: a
function's arguments are evaluated before the call, so a function could not
skip its second one.

Python's own `and` and `or` are those two forms exactly. Inside a compiled
body they lower to a binding plus a test that answers the DECIDING OPERAND,
so `a and b` is `(and-then $a $b)` down to which value comes back, and the
argument that is not chosen is never evaluated, because a compiled body's
arguments are syntax rather than calls.

They are not a second spelling of `and` and `or`. Those are RELATIONAL: they
evaluate both sides and can solve for an unbound argument. Python has no
relational `and`, so that one keeps MeTTa's name, and so does the `if` in the
last claim, which is there only to expose the bindings a solved answer would
carry.

The original opens a second space to keep its two experiments apart. Python
keeps them apart with a slice of the first, so `note2` records into the same
space `note` does and the two equations really are the same equation twice,
which is what the original's two are once the space is factored out.
"""

from petta import Atom, S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11903 to 16522, +4619 (+38.8%), by the twin contract
#: change: six definitions ENTERED the engine, `note`, `note2`, `both`,
#: `either`, `gated` and `fallback`, where the old twin stated every
#: connective as a term, so the short circuit and the skipping now run as
#: compiled equations and each definition pays `@m.define`'s fixed
#: registration; the nine `test` wrappers and two `get-atoms` collapses LEFT
#: for `assert` and `list`, which is the smaller half. Measured min-of-3 over
#: fresh processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 23624 the ratio is 0.6994. Prior: 11903,
#: the transliterated twin this replaces.
BUDGET = 16522


def twin(m):
    """Skip a branch, take a branch, and prove which one ran."""
    ran = m.space("&ran")

    @m.op
    def record(tag: Atom) -> bool:
        """Write the tag and answer True: `space += atom` is add-atom's door."""
        ran.add(S.ran(tag))
        return True

    @m.define
    def note(tag):
        # (= (note $tag) (let $_ (add-atom &ran (ran $tag)) True))
        return record(tag)

    @m.define
    def note2(tag):
        # (= (note2 $tag) (let $_ (add-atom &ran2 (ran $tag)) True))
        return record(tag)

    @m.define
    def both(a, b):
        # (and-then $a $b)
        return a and b

    @m.define
    def either(a, b):
        # (or-else $a $b)
        return a or b

    # !(test (and-then True yes) yes)
    assert both(TRUE, S.yes) == [S.yes]
    # !(test (and-then False yes) False)
    assert both(FALSE, S.yes) == [False]
    # !(test (or-else True no) True)
    assert either(TRUE, S.no) == [True]
    # !(test (or-else False fallback) fallback)
    assert either(FALSE, S.fallback) == [S.fallback]

    # They take expressions, not just literals. An argument that is a term
    # reduces on the way in, which is what the original's do too.
    # !(test (and-then (> 2 1) (> 3 2)) True)
    assert both(S[">"](2, 1), S[">"](3, 2)) == [True]
    # !(test (or-else (> 1 2) (> 3 2)) True)
    assert either(S[">"](1, 2), S[">"](3, 2)) == [True]

    @m.define
    def gated(flag, tag):
        # (and-then $flag (note $tag)): the note is a call the body COMPILES,
        # so whether it runs is the engine's decision, not Python's
        return flag and note(tag)

    @m.define(name="fallback")
    def fell_back(flag, tag):
        # (or-else $flag (note $tag))
        return flag or note(tag)

    # !(and-then False (note skipped-by-and-then))
    gated(FALSE, S["skipped-by-and-then"])
    # !(or-else True (note skipped-by-or-else))
    fell_back(TRUE, S["skipped-by-or-else"])
    # !(and-then True (note taken-by-and-then))
    gated(TRUE, S["taken-by-and-then"])
    # !(or-else False (note taken-by-or-else))
    fell_back(FALSE, S["taken-by-or-else"])

    # !(test (collapse (get-atoms &ran))
    #        ((ran taken-by-and-then) (ran taken-by-or-else)))
    assert list(ran) == [S.ran(S["taken-by-and-then"]), S.ran(S["taken-by-or-else"])]

    # The contrast, in one place: `and` does NOT skip, so its second argument
    # runs even though the first is False. Both forms are written the same way
    # so the pair stays comparable.
    already = len(ran)
    # !(and False (note2 and-runs-it))
    m.eval(S["and"](FALSE, S.note2(S["and-runs-it"])))
    # !(and-then False (note2 and-then-skips-it))
    m.eval(S["and-then"](FALSE, S.note2(S["and-then-skips-it"])))

    # !(test (collapse (get-atoms &ran2)) ((ran and-runs-it)))
    assert list(ran)[already:] == [S.ran(S["and-runs-it"])]

    # And the other side of the trade: and-then cannot be solved backwards,
    # where `and` can.
    # !(test (collapse (if (and-then (or-else $p True) $q) ($p $q))) ())
    unsolved = S["and-then"](S["or-else"](V.p, TRUE), V.q)
    assert m.eval(S["if"](unsolved, (V.p, V.q))) == []  # rung: the `if` is what exposes the bindings, and a two-argument `if` has no Python conditional to be
