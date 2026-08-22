"""The Python twin of examples/types/recursive_types2.metta: Peano numbers.

`Z` is zero and `S` is successor, so `(S (S Z))` is two, and `Greater` decides
between two of them by peeling one constructor off each until one of them runs
out. The three equations are the whole definition and they are recursion over
STRUCTURE rather than over a value.

None of the three compiles, because their heads match a CONSTRUCTOR:
`(Greater (S $x) Z)` fixes the shape of an argument, and a compiled head takes
plain parameters or literal patterns, not a structural pattern. Python's own
construct for that is the `match` statement, which the compiled subset has no
lowering for yet; the residue table records it against P14.4. They are one
definition, so `@rules` writes them as a group and `$x` and `$y` are its
parameters rather than two more `V.` reads.

`SUCC` names the successor because the successor's MeTTa name is `S`, and `S`
is already the name of the symbol factory this module builds every atom with.
"""

from petta import S, equation, rules, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: every head matches a CONSTRUCTOR, `(Greater (S $x) Z)`, and a compiled head takes
#: plain parameters or literal defaults, so `@rules` writes the three clauses with their two
#: variables scoped to its parameters; the `(: ...)` declarations have no `typed(x, T)` builder.
RUNG = "@rules: every head matches a constructor a compiled head cannot spell, and (: ...) has no typed(x, T) builder"

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9191 to 9213, +22, by lifting the 3-clause equation set from
#: repeated `m += equation(...).to(...)` to `@rules` plus one `m.add(*group)`. The whole of the
#: increase is the multi-atom add path, not the decorator: `rules` builds its equations in
#: Python and spends nothing on the engine, and one `m.add` of n atoms costs 13 + 3n inferences
#: more than n separate `m +=` calls (measured over three fresh processes each: 673 against 692
#: at two atoms, 1042 against 1064 at three, 0.0000% spread). Prior: #: RE-PINNED 2026-08-22, 8923 to 9191, +268, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 8923 by 47554fc's control/types twin baseline.
BUDGET = 9213

#: The successor constructor, whose MeTTa name is the single letter S.
SUCC = S.S


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: Z Nat)
    m += S[":"](S.Z, S.Nat)
    # (: S (-> Nat Nat))
    m += S[":"](SUCC, S["->"](S.Nat, S.Nat))
    # (: Greater (-> Nat Nat Bool))
    m += S[":"](S.Greater, S["->"](S.Nat, S.Nat, S.Bool))

    @rules
    def greater(x, y):
        # (= (Greater (S $x) Z) True)
        yield equation(S.Greater(SUCC(x), S.Z)).to(TRUE)
        # (= (Greater Z $x) False)
        yield equation(S.Greater(S.Z, x)).to(FALSE)
        # (= (Greater (S $x) (S $y)) (Greater $x $y))
        yield equation(S.Greater(SUCC(x), SUCC(y))).to(S.Greater(x, y))

    m.add(*greater)

    # !(test (Greater (S Z) (S Z)) false)
    yield m.eval(S.test(S.Greater(SUCC(S.Z), SUCC(S.Z)), FALSE))
    # !(test (Greater (S (S Z)) (S Z)) true)
    yield m.eval(S.test(S.Greater(SUCC(SUCC(S.Z)), SUCC(S.Z)), TRUE))
