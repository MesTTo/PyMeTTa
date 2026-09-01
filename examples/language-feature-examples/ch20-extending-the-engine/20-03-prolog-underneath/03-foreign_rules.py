"""examples/ch20-extending-the-engine/20-03-prolog-underneath/03-foreign_rules.metta in Python: a foreign space holding RULES.

In MeTTa a space is BOTH a data source and where the program lives, so an
equation added to a foreign space has to evaluate rather than sit there inert.
A provider says it holds equations by declaring the `rules` capability, and
nothing else about it changes: the engine compiles the equation, so a rule in a
foreign space is the same compiled clause a native one is.

That is why this twin writes those rules the way it would write any others.
`@demo.define` compiles into the provider's space, the recursion and the nested
body come out of Python's own syntax, a body that is a bare lowercase symbol is
the `S` factory, and the two equations that share a head are two yields, since
each independent yield stores one equation.

Evaluating IN a space is the space handle's own `eval`, which is what
`(metta $atom %Undefined% &space)` says: a rule belongs to the space that holds
it, so calling `(fdouble 21)` from `&self` would find nothing.

The provider's space is reached by ATOM, `metta.space(S["rule_demo"])`, because
a space name is a symbol and never text and its MeTTa name really has an
underscore, so the bracket spells it exactly. The provider itself arrives
through the handle's own door, `m.register_prolog(path=PROVIDER)`, which is
what `import_prolog_functions_from_file` names in MeTTa.
"""

from pathlib import Path

import metta
from metta import S, V, lib

#: The provider under test, thirteen lines. Its whole contribution is declaring
#: the `rules` capability beside match, enumerate, add and remove. A path is
#: a Path, never text.
PROVIDER = Path("./examples/ch20-extending-the-engine/20-03-prolog-underneath/_fixtures/rule_provider.pl")


def twin(m):
    """Put five rules and one fact in a foreign space, then evaluate them there."""
    m += lib["lib_import"]
    m.register_prolog(path=PROVIDER)

    demo = metta.space(S["rule_demo"])

    # A rule, added to the foreign space, evaluating.
    @demo.define
    def fdouble(x):
        # (= (fdouble $x) (* 2 $x))
        return 2 * x

    assert demo.eval(S.fdouble(21)) == [42]

    # Several equations for one name are an answer SET, which is what MeTTa
    # promises, and two yields are those two equations. Sorted, because a set
    # has no order.
    @demo.define
    def fpick():
        yield S.one
        yield S.two

    assert sorted(demo.eval(S.fpick())) == [S.one, S.two]

    # A body that is not a call IS the answer, the way a native equation with a
    # bare atom body behaves.
    @demo.define
    def fplain():
        return S.settled

    assert demo.eval(S.fplain()) == [S.settled]

    # A body is evaluated FURTHER, so a nested call is evaluated inside out.
    # Reading evaluation as "match for (= (f Args) $body) and reduce $body" is
    # the naive reading, and here that shows up as (* 2 3) reaching + as a list
    # instead of as 6.
    @demo.define
    def fnest():
        return 1 + 2 * 3

    assert demo.eval(S.fnest()) == [7]

    # Recursion, and `if` evaluating only the branch it takes.
    @demo.define
    def ffact(x):
        return x * ffact(x - 1) if x > 0 else 1

    assert demo.eval(S.ffact(5)) == [120]

    # And the space is still a data source. Holding rules is an addition, not a
    # replacement, which is the whole of what "both" means.
    demo += S.edge(S.a, S.b)
    assert [(row.x, row.y) for row in demo[S.edge(V.x, V.y)]] == [(S.a, S.b)]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 37512 to 37965, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 37965 to 37986, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 37986 to 37617, on the release tree:
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
#: RE-PINNED 2026-08-25, 37617 to 37627, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 37627 to 36811 (-816), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 36811 to 36833 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 36833 to 30823 (-6010), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 30823 to 30800 (-23), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 30800
