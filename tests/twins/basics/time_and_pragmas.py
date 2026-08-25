"""Purpose: examples/basics/time_and_pragmas.metta in Python: bounds, time and pragmas.

Three of the four bounding forms have a Python door and take it. `timeout` and
`inferences` are per-call keywords, so `(timeout 30 (spin 100))` is
`m.eval(S.spin(100), timeout=30)`; `with-pragma!` scopes settings to a region,
so it is `with m.limits(...)`, which is the same shape and the same undo. The
fourth, `pragma!`, sets a process-wide interpreter setting and is the bound
`m.fn.pragma` effect call. `car-atom` dissolves as well:
`elapsed` answers `(Value Seconds)` and Python reads the value as `[0]`.

`metta/3` takes the space as an operand and a space HANDLE is a grounded atom,
so the handle goes straight in and no `&self` symbol appears; `evalc` is
`m.eval` on the same handle, which is why the two forms sit side by side here.

`spin` is an ordinary decorated function now: its body answers the lowercase
symbol `done`, and `S.done` is the mention door for exactly that, a lowercase
name a compiled body reads as data rather than as a call it cannot resolve.

`bounded-factorial` needs the definitional door that derives NO first-match
guard: its two clauses are non-exclusive and both apply at 0, which is what
makes the runaway branch reachable at all. `@m.define` would emit
`(if (== $n 0) (empty) ...)` and prune it, so `@m.rules` is the door, and the
bound decorator writes the bundle and lands it in one act.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import UNIT, S, V, equation, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 47686 to 48047, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 48047 to 48058, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 48058 to 48026, on the release tree:
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
#: RE-PINNED 2026-08-25, 48026 to 48036, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 48036


def twin(m):
    """Bound four evaluations, set seven pragmas, then invert arithmetic."""

    @m.define
    def spin(n):
        # (= (spin $n) (if (> $n 0) (spin (- $n 1)) done))
        return spin(n - 1) if n > 0 else S.done

    # A bound that is not reached is invisible.
    assert m.eval(S.spin(100), timeout=30) == [S.done]
    assert m.eval(S.add(1, 2), timeout=30) == [3]

    # Bounding an expression does NOT collapse it to one answer: the whole
    # answer set computes under the bound.
    assert m.eval(S.superpose((1, 2, 3)), timeout=30) == [1, 2, 3]

    # elapsed answers (Value Seconds), so timing a call does not mean writing
    # the clock by hand. Only the value is asserted; the duration is real but
    # not reproducible enough to assert on.
    assert m.answers(S.elapsed(S.spin(100))).one()[0] == S.done

    # sleep answers True, so it sequences with anything else.
    assert m.fn.sleep(0.01).one() is True

    # metta/3 interprets an atom in a space it is HANDED; PeTTa's evalc
    # already is that, since PeTTa's eval is full evaluation rather than one
    # rewriting step, so the two agree.
    assert m.eval(S.metta(S.add(1, 2), S["%Undefined%"], m)) == [3]
    assert m.eval(S.add(1, 2)) == [3]

    # Pragmas. Each answers the unit value, the way add-atom and print do.
    # Every key must be in the interpreter registry, and a bound's value is
    # checked before it replaces a working setting.
    pragma = m.fn.pragma
    assert pragma(S.max_time, 30) == [UNIT]
    assert pragma(S.max_inferences, 100_000_000) == [UNIT]
    # Passing none clears a bound again.
    assert pragma(S.max_time, S.none) == [UNIT]
    assert pragma(S.max_inferences, S.none) == [UNIT]

    # max-stack-depth answers its own error rather than raising: the count it
    # requires is checked in the answer, so the program that wrote it runs on.
    assert pragma(S.max_stack_depth, 0) == [UNIT]
    assert pragma(S.max_stack_depth, -1) == [
        S.Error(fn.pragma(S.max_stack_depth, -1), S.UnsignedIntegerIsExpected)
    ]
    assert pragma(S.max_stack_depth, S.none) == [UNIT]

    # A positive stack-depth setting caps the evaluator's branch-local fuel,
    # and a finite sibling survives when an overlapping recursive branch runs
    # out.
    pragma(S.max_stack_depth, 20).one()

    @m.rules
    def bounded_factorial(n):
        # (= (bounded-factorial 0) 1)
        yield equation(S.bounded_factorial(0)).to(1)
        # (= (bounded-factorial $n) (* $n (bounded-factorial (- $n 1))))
        yield equation(S.bounded_factorial(n)).to(n * S.bounded_factorial(n - 1))

    assert m.eval(S.bounded_factorial(5)) == [120, S.Error(-3, S.StackOverflow)]

    pragma(S.max_stack_depth, S.none).one()

    # (inferences $n $expr) is timeout's deterministic twin: the bound stops
    # at the same step on every machine, and it is the same keyword.
    assert m.eval(S.spin(100), inferences=100000) == [S.done]
    assert m.eval(S.superpose((1, 2, 3)), inferences=100000) == [1, 2, 3]

    # with-pragma! scopes settings to ONE expression; a with-block scopes them
    # to a region, and the previous values come back on every exit path.
    with m.limits(inferences=100000):
        assert m.eval(S.add(20, 22)) == [42]
    with m.limits(timeout=30, inferences=100000):
        assert m.eval(S.spin(100)) == [S.done]
    assert m.eval(S.spin(2000)) == [S.done]

    # Relational integer arithmetic: one unbound argument among integers
    # solves for it. Exactness is honest, so a branch with no integer answer
    # answers nothing rather than something approximate.
    assert m.solve(4, V.x - 1).x == 5
    assert m.solve(10, V.x + 3).x == 7
    assert m.solve(6, V.x * 2).x == 3
    assert m.solve(3, V.x / 2).x == 6
    assert m.solve(7, V.x * 2).x == []
