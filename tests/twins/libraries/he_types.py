"""examples/libraries/he_types.metta in Python: the type judgment, asked directly.

The HE type vocabulary is part of the core engine now, so this file's import is
a no-op and stays only to show that. Its subject is the judgment itself, which
is why every function here is named: `is-function` observes an arrow,
`type-cast` admits or refuses, `match-types` unifies with wildcards, and the
pair accessors and `match-type-or` are the rest of that vocabulary.

`type-cast` takes the space it asks as an ARGUMENT, and a space crosses a term
position as a grounded operand, so the receiver is handed over rather than
named. A declaration is `typed(a, T)`, the `(: a T)` form as data.

`type-cast` is asked through the engine rather than through `m.cast`, and that
is a measured decision, not a habit: `m.cast(S.B, S.type1)` RAISES CastError
where the engine answers B, because an atom nobody declared has type
`%Undefined%`, which the language's own rule treats as a wildcard that matches
any requested type. The divergence is recorded in the residue table.

The refusal is an Error ATOM, and iterating the answer view keeps it as data
where the scalar doors take the loud reading and raise.
"""

from metta import G, S, V, typed

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Observe arrows, cast five atoms, unify four type pairs, take two halves."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    is_function = m.fn.is_function
    assert is_function(S["->"](S.Atom, S.Atom)) == [True]
    assert is_function(S.Atom) == [False]

    # type-cast answers the atom when it has the type and (Error $atom BadType)
    # when it does not. Three ways to have it: the type is the atom's metatype,
    # a declared type matches it, or the atom has no declaration at all, which
    # the engine answers as %Undefined%, a wildcard matching any type.
    m += typed(S.type1, S.Type)
    m += typed(S.A, S.type1)

    cast = m.fn.type_cast
    assert cast(S.A, S.type1, m) == [S.A]
    assert cast(1, S.type1, m) == [S.Error(1, S.BadType)]

    # A metatype counts, so any symbol casts to Symbol and any number to Number.
    assert cast(S.A, S.Symbol, m) == [S.A]
    assert cast(1, S.Number, m) == [1]
    # An atom nobody declared is not the wrong type.
    assert cast(S.B, S.type1, m) == [S.B]

    # match-types is unification with wildcards, Hyperon's own contract:
    # %Undefined% and Atom on EITHER side match anything, and otherwise the two
    # types unify, so a type carrying a variable matches its instance.
    match_types = m.fn.match_types
    matched, missed = G("Matched!"), G("Didn't match")
    assert match_types(S.Atom, S.Atom, matched, missed) == [matched]
    assert match_types(S.Atom, S.Number, matched, missed) == [matched]
    assert match_types(S.Bool, S.Number, matched, missed) == [missed]
    assert match_types(S.List(V.x), S.List(S.Number), matched, missed) == [matched]

    assert m.fn.first_from_pair((S.A, S.B)) == [S.A]
    assert m.fn.second_from_pair((S.A, S.B)) == [S.B]
    assert m.fn.match_type_or(True, S.Number, S.Bool) == [True]  # noqa: FBT003  -- True is the folded accumulator this call carries, an ordinary atom, not a flag
