"""The Python twin of examples/libraries/he_types.metta.

The type surface: arrow recognition, checked casting, and wildcard type matching.

The HE vocabulary is part of the core engine now, so the import stays only to
show it remains a no-op. The two declarations are written as the atoms they
are, at the `S[":"]` door, because `:` is not a name Python can spell as an
attribute and because they declare DATA the file goes on to cast, not a Python
function whose annotation could emit them.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 18997 to 18997, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 18997 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 18997

#: The two answers match-types gives, spelled once because the file asserts them
#: four times and only the arguments move.
MATCHED, UNMATCHED = val("Matched!"), val("Didn't match")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # !(test (is-function (-> Atom Atom)) True)
    yield m.eval(S.test(S["is-function"](S["->"](S.Atom, S.Atom)), TRUE))
    # !(test (is-function Atom) False)
    yield m.eval(S.test(S["is-function"](S.Atom), FALSE))

    # type-cast answers the atom when it has the type and (Error $atom BadType)
    # when it does not. Three ways to have it: the type is the atom's metatype,
    # a declared type matches it, or the atom has no declaration at all, which
    # the engine answers as %Undefined%, a wildcard that matches any type.
    # (: type1 Type)
    m += S[":"](S.type1, S.Type)
    # (: A type1)
    m += S[":"](S.A, S.type1)

    # !(test (type-cast A type1 &self) A)
    yield m.eval(S.test(S["type-cast"](S.A, S.type1, S["&self"]), S.A))
    # !(test (type-cast 1 type1 &self) (Error 1 BadType))
    yield m.eval(
        S.test(S["type-cast"](1, S.type1, S["&self"]), S.Error(1, S.BadType))
    )

    # A metatype counts, so any symbol casts to Symbol and any number to Grounded.
    # !(test (type-cast A Symbol &self) A)
    yield m.eval(S.test(S["type-cast"](S.A, S.Symbol, S["&self"]), S.A))
    # !(test (type-cast 1 Number &self) 1)
    yield m.eval(S.test(S["type-cast"](1, S.Number, S["&self"]), 1))

    # An atom nobody declared is not the wrong type.
    # !(test (type-cast B type1 &self) B)
    yield m.eval(S.test(S["type-cast"](S.B, S.type1, S["&self"]), S.B))

    # match-types is unification with wildcards: %Undefined% and Atom on EITHER
    # side match anything, and otherwise the two types unify.
    # !(test (match-types Atom Atom "Matched!" "Didn't match") "Matched!")
    yield m.eval(
        S.test(S["match-types"](S.Atom, S.Atom, MATCHED, UNMATCHED), MATCHED)
    )
    # !(test (match-types Atom Number "Matched!" "Didn't match") "Matched!")
    yield m.eval(
        S.test(S["match-types"](S.Atom, S.Number, MATCHED, UNMATCHED), MATCHED)
    )
    # !(test (match-types Bool Number "Matched!" "Didn't match") "Didn't match")
    yield m.eval(
        S.test(S["match-types"](S.Bool, S.Number, MATCHED, UNMATCHED), UNMATCHED)
    )
    # !(test (match-types (List $x) (List Number) "Matched!" "Didn't match") "Matched!")
    yield m.eval(
        S.test(
            S["match-types"](S.List(V.x), S.List(S.Number), MATCHED, UNMATCHED),
            MATCHED,
        )
    )

    # !(test (first-from-pair (A B)) A)
    yield m.eval(S.test(S["first-from-pair"]((S.A, S.B)), S.A))
    # !(test (second-from-pair (A B)) B)
    yield m.eval(S.test(S["second-from-pair"]((S.A, S.B)), S.B))

    # !(test (match-type-or True Number Bool) True)
    yield m.eval(S.test(S["match-type-or"](TRUE, S.Number, S.Bool), TRUE))
