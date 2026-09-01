"""examples/ch08-data/08-01-atoms-lists-and-folds/10-multiset_operations.metta in Python: Counter is the algebra.

Every one of these operations is MULTISET, not set: `(a a a)` minus `(a)` is
`(a a)`, and an intersection keeps as many copies as both sides can afford.
`collections.Counter` is exactly that algebra, `&` and `-` included, so each
Python spelling is one line over it plus a walk that renders the result in the
left side's own order, which is the order the answers come back in.

Each claim says two things at once: what the operation answers, and that the
Python spelling and the engine's own `-atom` operation agree on it. The second
half is why the dissolution is safe to teach.
"""

from collections import Counter

from metta import Expression, S


def twin(m):
    """Run each multiset operation both ways and hold them to one answer."""

    def kept(left, budget):
        """`left`'s atoms in their own order, while the budget for each lasts."""
        out = []
        for atom in left:
            if budget[atom]:
                budget[atom] -= 1
                out.append(atom)
        return Expression(out)

    def common(left, right):
        """Multiset intersection: Counter's `&`, in the left side's order."""
        return kept(left, Counter(left) & Counter(right))

    def without(left, right):
        """Multiset difference: Counter's `-`, in the left side's order."""
        return kept(left, Counter(left) - Counter(right))

    def joined(left, right):
        """Multiset union: every copy from both sides, which is concatenation."""
        return Expression((*left, *right))

    def once_each(items):
        """Duplicates dropped, first occurrence kept: dict.fromkeys is that."""
        return Expression(dict.fromkeys(items))

    repeated = S.a(S.b, S.c, S.d, S.d)
    left, right = S.a(S.b, S.b, S.c), S.b(S.c, S.c, S.d)
    wide, wider = S.a(S.b, S.c, S.c), S.b(S.c, S.c, S.c, S.d)
    narrow = S.b(S.c, S.d)
    thrice, once = S.a(S.a, S.a), S.a()
    nothing = Expression(())

    assert once_each(repeated) == m.fn.unique_atom(repeated).one() == S.a(S.b, S.c, S.d)
    assert joined(left, right) == m.fn.union_atom(left, right).one() == S.a(
        S.b, S.b, S.c, S.b, S.c, S.c, S.d)
    assert common(wide, wider) == m.fn.intersection_atom(wide, wider).one() == S.b(S.c, S.c)
    assert without(left, right) == m.fn.subtraction_atom(left, right).one() == S.a(S.b)
    assert common(wide, narrow) == m.fn.intersection_atom(wide, narrow).one() == S.b(S.c)
    assert common(thrice, once) == m.fn.intersection_atom(thrice, once).one() == S.a()
    assert without(thrice, once) == m.fn.subtraction_atom(thrice, once).one() == S.a(S.a)
    assert common(S.a(S.b), nothing) == m.fn.intersection_atom(
        S.a(S.b), nothing).one() == nothing


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 4756 to 4908, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 4908 to 4909, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 4909 to 4925, on the release tree:
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
#: RE-PINNED 2026-08-25, 4925 to 4927, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 4927 to 4903 (-24), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 4903 to 6835 (+1932), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 6835 to 6819 (-16), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 6819 to 6858 (+39), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = 6858
