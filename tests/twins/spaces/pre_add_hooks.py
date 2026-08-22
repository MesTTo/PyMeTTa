"""The Python twin of examples/spaces/pre_add_hooks.metta: arbitrary MeTTa at the write door.

A pre-add hook claims one space's write door for one function of one argument,
and the handler answers one of four verdicts: `(accept)` lets the atom in as
offered, `(accept <atom>)` lets a transformed one in, `(refuse <words>)` throws
carrying the handler's own sentence, and `(drop)` skips the write while the
caller sees success. An atom the handler's equations do not cover is a stuck
state that says so, and a second claimant is refused when the claim is made.

The four ordinary writes go through `pool += atom`, and that IS the point being
made: the hook fires on the write door, not on a particular spelling of it, so
the transform, the drop and the plain accept all happen under `+=` exactly as
they happen under `add-atom`.

The five equations are written at the container door for two reasons at once:
their heads carry a nested literal PATTERN (`(guard (secret $x))`), which the
compiled subset spells only as a literal default, and their bodies name `refuse`,
`accept`, `drop` and `cooked`, lowercase symbols that a compiled body resolves as
functions rather than reading as data (residue, P14.4). The hook claim and its
release stay terms because there is no Python door for them yet; §9j's
`@space.pre_add` is the designed one and the residue names it against P14.10.
"""

from petta import S, V, equation, expr, val

#: The answer group a write form contributes: `add-atom` answers the unit,
#: which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10531 to 9549, -982 (-9.3%), by the P14 twin-style
#: rewrite, and the whole delta is the four writes: each moved from evaluating
#: an (add-atom &pool ...) term to `pool += atom`, 246 a write, inside the
#: 239-to-311 band this folder measures for a plain-atom write; the claimed
#: hook runs on either door, so it is in both figures. The five equations still
#: enter at the container door and the eight assertions are unchanged terms.
#: Prior: ADDED 2026-08-22 at 10531 by the wave-3 spaces baseline.
BUDGET = 9549


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    pool = m.space("&pool")
    here = S[pool.space_name]

    # The four verdicts, one equation each, in first-match order.
    # (= (guard (secret $x)) (refuse "no secrets in this pool"))
    m += equation(S.guard(S.secret(V.x))).to(
        S.refuse(val("no secrets in this pool"))
    )
    # (= (guard (raw $x)) (accept (cooked $x)))
    m += equation(S.guard(S.raw(V.x))).to(S.accept(S.cooked(V.x)))
    # (= (guard (dup $x)) (drop))
    m += equation(S.guard(S.dup(V.x))).to(S.drop())
    # (= (guard (plain $x)) (accept))
    m += equation(S.guard(S.plain(V.x))).to(S.accept())

    # !(declare-pre-add! &pool guard)
    yield m.eval(S["declare-pre-add!"](here, S.guard))

    # An accepted atom lands as offered.
    # !(add-atom &pool (plain 1))
    pool += (S.plain, 1)
    yield WROTE
    # !(test (match &pool (plain $x) $x) 1)
    yield m.eval(S.test(S.match(here, S.plain(V.x), V.x), 1))

    # A transformed atom lands in the handler's chosen form, and is not
    # re-asked: one decision per request.
    # !(add-atom &pool (raw 7))
    pool += (S.raw, 7)
    yield WROTE
    # !(test (match &pool (cooked $x) $x) 7)
    yield m.eval(S.test(S.match(here, S.cooked(V.x), V.x), 7))

    # A dropped atom is skipped and the caller sees success, which is how set
    # semantics is written as a rule.
    # !(add-atom &pool (dup 3))
    pool += (S.dup, 3)
    yield WROTE
    # !(test (collapse (match &pool (dup $x) $x)) ())
    yield m.eval(S.test(S.collapse(S.match(here, S.dup(V.x), V.x)), ()))

    # A refusal carries the handler's own sentence to the caller.
    # !(test (repr (catch (add-atom &pool (secret 1))))
    #        "(Error (petta_add_refused &pool (secret 1) \"no secrets in this pool\") none)")
    yield m.eval(
        S.test(
            S.repr(S.catch(S["add-atom"](here, S.secret(1)))),
            val(
                '(Error (petta_add_refused &pool (secret 1) '
                '"no secrets in this pool") none)'
            ),
        )
    )

    # A claimed handler whose equations do not cover the atom is a stuck state
    # that names the space, the slot, the handler and the atom.
    # !(test (repr (catch (add-atom &pool (uncovered 9))))
    #        "(Error (petta_hook_stuck &pool pre-add guard (uncovered 9)) none)")
    yield m.eval(
        S.test(
            S.repr(S.catch(S["add-atom"](here, S.uncovered(9)))),
            val(
                "(Error (petta_hook_stuck &pool pre-add guard "
                "(uncovered 9)) none)"
            ),
        )
    )

    # One claimant per name, checked when the claim is made.
    # (= (other-guard $a) (accept))
    m += equation(S["other-guard"](V.a)).to(S.accept())
    # !(test (repr (catch (declare-pre-add! &pool other-guard)))
    #        "(Error (petta_hook_conflict &pool pre-add guard other-guard) none)")
    yield m.eval(
        S.test(
            S.repr(
                S.catch(S["declare-pre-add!"](here, S["other-guard"]))
            ),
            val(
                "(Error (petta_hook_conflict &pool pre-add guard "
                "other-guard) none)"
            ),
        )
    )

    # Undeclaring is explicit and frees the claim; the space is direct again.
    # !(undeclare-pre-add! &pool)
    yield m.eval(S["undeclare-pre-add!"](here))
    # !(add-atom &pool (uncovered 10))
    pool += (S.uncovered, 10)
    yield WROTE
    # !(test (match &pool (uncovered $x) $x) 10)
    yield m.eval(S.test(S.match(here, S.uncovered(V.x), V.x), 10))
