"""examples/ch06-many-answers/09-streamops.metta in Python: the same algebra over ANSWERS.

`superpose` fans an expression out into one answer per element, and the four
operations here work over those answers rather than over children. In Python
that difference disappears: the answers of a superposition of a literal ARE
that literal's members, an answer set is an iterable, `list()` of it is what
`collapse` spells, and the multiset algebra is `collections.Counter` again,
exactly as it was over children in the sibling `multiset_operations`.

So each claim holds three things to one answer: the Python spelling over the
members, the engine's own stream operation over the superposition terms, and
the expected list.
"""

from collections import Counter

from metta import Expression, S


def twin(m):
    """Fan out four streams, then fold them back both ways."""

    def fan(members):
        """The term whose answers are `members`, one each."""
        return S.superpose(Expression(members))

    def kept(left, budget):
        """`left`'s answers in their own order, while each budget lasts."""
        out = []
        for atom in left:
            if budget[atom]:
                budget[atom] -= 1
                out.append(atom)
        return out

    letters = (S.a, S.b, S.c, S.d, S.d)
    left, right = (S.a, S.b, S.b, S.c), (S.b, S.c, S.c, S.d)
    wide, wider = (S.a, S.b, S.c, S.c), (S.b, S.c, S.c, S.c, S.d)

    # (collapse (unique (superpose (a b c d d)))) -> (a b c d)
    assert list(dict.fromkeys(letters)) == m.fn.unique(fan(letters)) == [S.a, S.b, S.c, S.d]

    # (collapse (union ...)) -> (a b b c b c c d): every copy from both sides
    assert [*left, *right] == m.fn.union(fan(left), fan(right)) == [
        S.a, S.b, S.b, S.c, S.b, S.c, S.c, S.d]

    # (collapse (intersection ...)) -> (b c c): as many copies as both afford
    assert kept(wide, Counter(wide) & Counter(wider)) == m.fn.intersection(
        fan(wide), fan(wider)) == [S.b, S.c, S.c]

    # (collapse (subtraction ...)) -> (a b)
    assert kept(left, Counter(left) - Counter(right)) == m.fn.subtraction(
        fan(left), fan(right)) == [S.a, S.b]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 4740 to 4741, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 4741 to 4743, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 4743 to 4715 (-28), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 4715 to 4997 (+282), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 4997 to 4989 (-8), the subtract-atom primitive and the
#: Counter grain for -=: a new engine head shifts every twin's load structure,
#: and the removal doors changed meaning where a twin spells one [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 4989
