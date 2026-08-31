"""Purpose: examples/ch09-types/11-subtyping.metta in Python: `:<` widens, it does not decide.

Two things surprise people about subtyping here. The spelling is `:<` and it
points from the subtype UP, so `(:< Dog Animal)` reads "Dog is below Animal".
And nothing DECIDES whether one type is below another while checking an
argument: declaring an edge WIDENS a value's type list, and the ordinary check
then runs unchanged against the wider list. `get-type` is where the whole
feature is visible, which is why every claim here reads it, and reads the whole
answer set rather than the accessor's first type.

`speak` asks for an Animal, and Python's own class is how an annotation names
that type: `def speak(a: Animal) -> str` IS `(: speak (-> Animal String))`.
The edge itself still has to be written as an atom, because a Python subclass
declares no `:<` (friction, P14.9, and it is the natural door).
"""

from metta import S, V, arrow, ground, typed

#: The subtype edge. `:<` is a declaration head like `:` and `->`, and the one
#: of the three with no exported builder, so it takes the quoted-name rung.
BELOW = S[":<"]


class Animal:
    """The MeTTa type `Animal`, as a Python class so an annotation can say it."""


def twin(m):
    """Declare edges, then watch what each value's type list becomes."""
    kind = m.fn.get_type

    # (: Rex Dog) (:< Dog Animal)
    m += typed(S.Rex, S.Dog)
    m += BELOW(S.Dog, S.Animal)

    # One value, two types now, in declaration order and then supertype order.
    # !(test (collapse (get-type Rex)) (Dog Animal))
    assert kind(S.Rex) == [S.Dog, S.Animal]

    @m.define
    def speak(a: Animal) -> str:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        """(: speak (-> Animal String)), (= (speak $a) "some noise")."""
        return "some noise"

    # Which is what makes the argument acceptable: speak asks for an Animal
    # and Rex is a Dog, and Animal is in Rex's widened list.
    # !(test (speak Rex) "some noise")
    assert speak(S.Rex) == [ground("some noise")]

    # Transitive, because widening repeats over what the previous round added.
    # (:< Animal LivingThing)
    # !(test (collapse (get-type Rex)) (Dog Animal LivingThing))
    m += BELOW(S.Animal, S.LivingThing)
    assert kind(S.Rex) == [S.Dog, S.Animal, S.LivingThing]

    # Two things are NOT widened, both deliberately: a grounded literal's
    # built-in type, and the return type of an application.
    # (:< Number Countable)
    # !(test (collapse (get-type 1)) (Number))
    m += BELOW(S.Number, S.Countable)
    assert kind(1) == [S.Number]

    # (: half (-> Number Fraction)) (:< Fraction Rational)
    # !(test (collapse (get-type (half 3))) (Fraction))
    m += typed(S.half, arrow(int, S.Fraction))
    m += BELOW(S.Fraction, S.Rational)
    assert kind(S.half(3)) == [S.Fraction]

    # A diamond answers its join TWICE, and that is not a bug to report:
    # widening checks against the list as it stood when the round BEGAN, so
    # both parents reach the join in the same round and both append it.
    # (:< Bat Bird) (:< Bat Mammal) (:< Bird Animal2) (:< Mammal Animal2)
    # (: Stellaluna Bat)
    # !(test (collapse (get-type Stellaluna)) (Bat Bird Mammal Animal2 Animal2))
    m += BELOW(S.Bat, S.Bird)
    m += BELOW(S.Bat, S.Mammal)
    m += BELOW(S.Bird, S.Animal2)
    m += BELOW(S.Mammal, S.Animal2)
    m += typed(S.Stellaluna, S.Bat)
    assert kind(S.Stellaluna) == [
        S.Bat, S.Bird, S.Mammal, S.Animal2, S.Animal2,
    ]

    # An edge whose subtype side is a PATTERN contributes an instance, because
    # the lookup is the ordinary two-sided matcher, not a table of symbols.
    # (:< (Boxed $t) Container) (: crate (Boxed Apple))
    # !(test (collapse (get-type crate)) ((Boxed Apple) Container))
    m += BELOW(S.Boxed(V.t), S.Container)
    m += typed(S.crate, S.Boxed(S.Apple))
    assert kind(S.crate) == [S.Boxed(S.Apple), S.Container]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6045 to 8572, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8572 to 8583, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8583 to 8515, on the release tree:
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
#: RE-PINNED 2026-08-25, 8515 to 8528, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 8528 to 8671 (+143), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 8671 to 8691 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 8691 to 10043 (+1352), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 10043
