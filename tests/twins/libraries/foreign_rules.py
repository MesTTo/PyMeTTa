"""examples/libraries/foreign_rules.metta in Python: a foreign space holding RULES.

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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
BUDGET = 37617

#: The provider under test, thirteen lines. Its whole contribution is declaring
#: the `rules` capability beside match, enumerate, add and remove. A path is
#: a Path, never text.
PROVIDER = Path("./examples/libraries/_fixtures/rule_provider.pl")


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
    assert [(row.x, row.y) for row in demo.match(S.edge(V.x, V.y))] == [(S.a, S.b)]
