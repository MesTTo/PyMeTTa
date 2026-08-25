"""Purpose: spell the cyclic higher-order specialization example in Python.

Two mutually recursive pairs, each carrying the function it was called with.
The pairs are the reason both take the `@m.rules` shape of the definitional
decorator rather than `@m.define`: `f1`'s body calls `f2` and `f2`'s body
calls `f1`, and a compiled body resolves a free name against what the engine
knows AT DECORATION TIME, so whichever is written first cannot name the other.
At the rule door both are ordinary built terms and the cycle closes when the
bundle lands.

Assumes:
  - the four equations and two runnable claims mirror
    examples/functions/specializecyclic.metta in source order
    [source: examples/functions/specializecyclic.metta lines 1-15; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Guarantees:
  - twin installs every equation and proves both runnable claims
    [tested: test_a_shipped_twin_agrees_with_its_example_end_to_end; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, equation, if_

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships.
#: Before the wave this file carried an EMPIRICAL envelope rather than a point,
#: minimum 26325, maximum 26409 over 28 observations under
#: `full-lane/218/workers=32`, because its cost moves with the scheduler; the
#: re-pin pass has to give it an envelope again rather than a point
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 81920 to 81962, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 81962 to 81979, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 81979 to 81971, on the release tree:
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
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
BUDGET = {
    "minimum": 81967,
    "maximum": 82019,
    "observations": 20,
    "protocol": "full-lane/219/workers=32",
}


def twin(m):
    """Install both cycles and ask each one through the same function value."""

    @m.rules
    def cyclic(f, a, n):
        """The mutually recursive equations, admitted as one rule bundle."""
        # (= (f1 $f $a) (if (< $a 0) ($f nevercalled 42)
        #                   (if (== $a 0) (f2 $f (- $a 1)) finish)))
        #
        yield equation(S.f1(f, a)).to(
            if_(
                S.lt(a, 0),
                Expression((f, S.nevercalled, 42)),
                if_(S.eq(a, 0), S.f2(f, a - 1), S.finish),
            )
        )
        # (= (f2 $f $a) (if (< $a 0) ($f nevercalled 42) (f1 $f $a)))
        yield equation(S.f2(f, a)).to(
            if_(S.lt(a, 0), Expression((f, S.nevercalled, 42)), S.f1(f, a))
        )
        # (= (f3 $f $n) (if (== $n 0) finish (f4 $f $n)))
        yield equation(S.f3(f, n)).to(if_(S.eq(n, 0), S.finish, S.f4(f, n)))
        # (= (f4 $f $n) (f3 $f (- $n 1)))
        yield equation(S.f4(f, n)).to(S.f3(f, n - 1))

    assert m.eval(S.f1(S.add, 2)) == [S.finish]
    assert m.eval(S.f3(S.add, 1)) == [S.finish]
