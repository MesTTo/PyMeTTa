"""Purpose: examples/ch19-spaces-backed-by-anything/19-01-spaces-of-your-own/03-parametric_spaces.metta in Python: a space named by an expression.

`(cache &primary-kb 100)` is a ground expression used as a SPACE NAME, so two
instances of the same shape are two isolated spaces, and the same equation in
each reads its own parameters back out of `context-space`. Pattern
destructuring is the parameter surface, which is why no parameter builtin
exists.

Every door here is the container door now. `metta.space(name)` takes an ATOM as
the name, so a parameterised space has a handle like any other space and `+=`,
`space[pattern]`, `space.eval(term)` and `space.type(atom)` all work here
exactly as they work everywhere else
[measured 2026-08-24: `metta.space(S.cache(S["&primary-kb"], 100))` answers a
handle whose two instances stay isolated; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. The two base names
stay symbols because that is what they are: `&primary-kb` is a PARAMETER of the
space's name and never denotes a space of its own in this program.

The equation is the one thing still written as a term: its body binds by
DESTRUCTURING a pattern, `(let (cache $base $limit) (context-space) ...)`, and
Python's own assignment is what `let` becomes only when the target is a name
(residue, P14.4). PERFECT: `solve(S.cache(V.base, V.limit), fn.context_space())`
inside a compiled body, the expression-position function the guide rules for
exactly this case; measured 2026-08-24, a body naming `solve` is refused,
"'solve' is not a parameter of cache-config, not a function the engine knows"
[commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
"""

import metta
from metta import S, V, equation, fn

#: The two base names, which are parameters of a space's name rather than
#: spaces: nothing in the program ever writes to `&primary-kb` itself.
PRIMARY, SECONDARY = S["&primary-kb"], S["&secondary-kb"]  # rung: a parameter of a space name, not a space


def twin(m):
    """Make two instances of one cache shape, and read each one's parameters."""
    primary = metta.space(S.cache(PRIMARY, 100))
    secondary = metta.space(S.cache(SECONDARY, 10))

    # The same equation reads the identifier of whichever instance owns it.
    config = equation(S.cache_config()).to(
        S.let(S.cache(V.base, V.limit), fn.context_space(), S.config(V.base, V.limit))  # rung: a let that DESTRUCTURES has no assignment spelling
    )
    primary += config
    secondary += config

    primary += S.entry(S.primary)
    secondary += S.entry(S.secondary)

    assert primary.eval(S.cache_config()) == [S.config(PRIMARY, 100)]
    assert secondary.eval(S.cache_config()) == [S.config(SECONDARY, 10)]

    assert [row.which for row in primary[S.entry(V.which)]] == [S.primary]
    assert [row.which for row in secondary[S.entry(V.which)]] == [S.secondary]

    assert m.type(primary) == S.SpaceType


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 9055 to 9128, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 9128 to 9111, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 9111 to 9115, on the release tree:
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
#: RE-PINNED 2026-08-25, 9115 to 9110, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 9110 to 9046 (-64), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 9046 to 9031 (-15), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 9031 to 9026 (-5), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 9026 to 4463 (-4563), one corpus pricing pass on the
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
#: RE-PINNED 2026-09-01, 4463 to 4452 (-11), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 4452
