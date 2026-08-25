"""Purpose: examples/types/types.metta in Python: what a type is and where it lives.

Three groups of claims. Concrete types are declarations about SYMBOLS, so they
are atoms written into the space: there is no Python signature that says
`(: a A)`, because `a` is not a function, and `typed(x, T)` is the builder for
that declaration term. Function types are arrows, and the type variable in
`(-> $a $a)` is what Python's own type parameter says, so `mid` and `testf` are
ordinary generic functions and `@m.define` publishes the arrow their signatures
name.

`space.type(atom)` is the get-type accessor and answers the FIRST type, which
is every claim here but one: `x` is declared twice, and the whole answer set is
the form itself, evaluated.

Both function bodies select on a STRUCTURE, and Python's `match` statement is
MeTTa's own `case`: `mid` keeps only an argument shaped `(a b)` and `testf`
keeps only the symbol `at`. Measured on this engine, `case` unifies both ways,
so `mid(($a b))` answers `(a b)` exactly as the original's `let` does.
"""

from metta import Expression, S, V, Variable, arrow, ground, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11902 to 15626, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 15626 to 15639, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 15639 to 15569, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
BUDGET = 15569

#: The unconstrained type. Python's grammar cannot spell `%Undefined%`, so the
#: name takes the bracket; `Any` is its image in a DECLARING position, where
#: `typed` and `arrow` read it through the annotation table.
#:
#: The table is one-way, which is friction against P14.9: a twin comparing an
#: ANSWER against a type atom has no Python-type spelling for it, so the marked
#: name is written out. It should read `assert m.type(S.c) == Any`, with the
#: same table reading `Any` on the right of an equality as it already reads it
#: inside `arrow(...)` and `typed(...)`.
UNDEFINED = S["%Undefined%"]


def twin(m):
    """Declare, then ask, then declare a function and ask about its answers."""
    # Concrete types. Each declaration is a fact about a symbol.
    # (: a A) (: b B) (: A Type) (: x Letter) (: x Buchstabe)
    m += typed(S.a, S.A)
    m += typed(S.b, S.B)
    m += typed(S.A, S.Type)
    m += typed(S.x, S.Letter)
    m += typed(S.x, S.Buchstabe)

    # The type of an unbound variable is itself unknown: another variable.
    # !(test (get-type $a) $z)
    assert type(m.type(V.a)) is Variable
    # !(test (get-type a) A)
    assert m.type(S.a) == S.A
    # !(test (get-type b) B)
    assert m.type(S.b) == S.B
    # !(test (get-type c) %Undefined%)
    assert m.type(S.c) == UNDEFINED
    # !(test (get-type A) Type)
    assert m.type(S.A) == S.Type
    # !(test (get-type B) %Undefined%)
    assert m.type(S.B) == UNDEFINED

    # An expression's type is the expression of its parts' types, and a ground
    # value carries its own.
    # !(test (get-type (a b)) (A B))
    assert m.type(S.a(S.b)) == S.A(S.B)
    # !(test (get-type 42) Number)
    assert m.type(42) == S.Number
    # !(test (get-type "42") String)
    assert m.type(ground("42")) == S.String

    # Two declarations, two answers, so this one calls the relation: the
    # accessor answers the first type and the example collapses every one.
    # !(test (collapse (get-type x)) (Letter Buchstabe))
    assert m.fn.get_type(S.x) == [S.Letter, S.Buchstabe]

    @m.define
    def mid[T](x: T) -> T:
        """(: mid (-> $a $a)), and a body that keeps only an `(a b)`."""
        match x:
            case (S.a, S.b):
                return x

    # !(test (mid ($a b)) (a b))
    assert mid(Expression((V.a, S.b))) == [S.a(S.b)]

    # `testx` is a declaration and nothing else: no equation defines it, so
    # the arrow is the whole of what the file says about it.
    # (: testx (-> $a $b $a))
    m += typed(S.testx, arrow(V.a, V.b, V.a))
    # !(test (get-type (testx 1 "f")) Number)
    assert m.type(S.testx(1, ground("f"))) == S.Number

    # Nondeterministic types: `at` is both an A and a T, so a function
    # declared (-> $a $a) accepts it and answers a T.
    # (: at A) (: at T) (: t T)
    m += typed(S.at, S.A)
    m += typed(S.at, S.T)
    m += typed(S.t, S.T)

    @m.define
    def testf[T](x: T) -> T:
        """(: testf (-> $a $a)), and a body that answers only for `at`."""
        match x:
            case S.at:
                return S.t

    # !(test (testf at) t)
    assert testf(S.at) == [S.t]
