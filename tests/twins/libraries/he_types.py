"""examples/libraries/he_types.metta in Python: the type judgment, asked directly.

The HE type vocabulary is part of the core engine now, so this file's import is
a no-op and stays only to show that. Its subject is the judgment itself, which
is why every function here is named: `is-function` observes an arrow,
`type-cast` admits or refuses, `match-types` unifies with wildcards, and the
pair accessors and `match-type-or` are the rest of that vocabulary.

`type-cast` is asked through the engine rather than through `m.cast`, and that
is a measured decision, not a habit: `m.cast(S.B, S.type1)` RAISES CastError
where the engine answers B, because an atom nobody declared has type
`%Undefined%`, which the language's own rule treats as a wildcard that matches
any requested type. The divergence is recorded in the residue table.

The refusal is an Error ATOM, so it comes back through `m.eval`, which hands
error answers over as data where the cardinality doors raise on them.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 18997 to 11268, -7729 (-40.69%), by the idiomatic
#: rewrite: fourteen `test` wrappers left the engine for `assert`; the five
#: casts, four match-types, two pair halves and match-type-or are what
#: remains. Measured min-of-three with the MORK backend linked into this
#: worktree, which the earlier figure may not have been. Prior: 18997 was the
#: last figure for the generator twin that yielded `m.eval(S.test(...))` once
#: per runnable form.
BUDGET = 11268


def twin(m):
    """Observe arrows, cast five atoms, unify four type pairs, take two halves."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    is_function = m.fn("is-function")
    assert is_function(S["->"](S.Atom, S.Atom)) is True
    assert is_function(S.Atom) is False

    # type-cast answers the atom when it has the type and (Error $atom BadType)
    # when it does not. Three ways to have it: the type is the atom's metatype,
    # a declared type matches it, or the atom has no declaration at all, which
    # the engine answers as %Undefined%, a wildcard matching any type.
    m += S[":"](S.type1, S.Type)
    m += S[":"](S.A, S.type1)

    cast = m.fn("type-cast")
    assert cast(S.A, S.type1, S["&self"]) == S.A  # rung: the space is type-cast's own ARGUMENT, and m.cast diverges from it on undeclared atoms, so the engine is asked directly
    assert m.eval(S["type-cast"](1, S.type1, S["&self"])) == [S.Error(1, S.BadType)]  # rung: as above, and the answer is an error ATOM, which only m.eval hands over as data

    # A metatype counts, so any symbol casts to Symbol and any number to Number.
    assert cast(S.A, S.Symbol, S["&self"]) == S.A  # rung: as above
    assert cast(1, S.Number, S["&self"]) == 1  # rung: as above
    # An atom nobody declared is not the wrong type.
    assert cast(S.B, S.type1, S["&self"]) == S.B  # rung: as above

    # match-types is unification with wildcards, Hyperon's own contract:
    # %Undefined% and Atom on EITHER side match anything, and otherwise the two
    # types unify, so a type carrying a variable matches its instance.
    match_types = m.fn("match-types")
    matched, missed = val("Matched!"), val("Didn't match")
    assert match_types(S.Atom, S.Atom, matched, missed) == matched
    assert match_types(S.Atom, S.Number, matched, missed) == matched
    assert match_types(S.Bool, S.Number, matched, missed) == missed
    assert match_types(S.List(V.x), S.List(S.Number), matched, missed) == matched

    assert m.fn("first-from-pair")((S.A, S.B)) == S.A
    assert m.fn("second-from-pair")((S.A, S.B)) == S.B
    assert m.fn("match-type-or")(True, S.Number, S.Bool) is True  # noqa: FBT003  -- True is the folded accumulator this call carries, an ordinary atom, not a flag
