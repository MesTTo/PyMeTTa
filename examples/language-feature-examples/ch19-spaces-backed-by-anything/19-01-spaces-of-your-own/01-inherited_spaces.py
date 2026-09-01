"""Purpose: examples/ch19-spaces-backed-by-anything/19-01-spaces-of-your-own/01-inherited_spaces.metta in Python: child-first reads, front-only writes.

A child space reads through its parent and writes only into itself. One
conjunction joins a parent fact to a child fact, because each conjunct is
matched through the whole read chain; same-shaped facts come back child first;
and neither write reached the parent.

The original names the child `&family-child` so its later forms can address it,
and this writes the same thing: `metta.space(S.family_child, inherits=parent)`.
A name and a MODEL are independent, because the engine's declarations always
took any valid space name and only this door required anonymity. The twin used
to mint an anonymous child and carry the pair as a gap; both are available now,
and the named form is the one the original writes.

One claim keeps the engine's own function. `len(space)` and iterating it both
answer the whole READ CHAIN, six atoms here, where `(space-atom-count ...)`
answers the writable FRONT STORE, three, which is the boundary this example
exists to draw [measured 2026-08-22; filed as residue against P14.10 and
reported to the integrator]. The Python container protocol is self-consistent,
len and iteration agreeing, so the gap is a missing front-store door rather
than a wrong count. PERFECT: `len(child.front)`, or a declared capacity view, so
the question the example is about has a Python spelling. The handle goes into
the call as an ordinary operand.
"""

import metta
from metta import S, V


def twin(m):
    """Fill a parent and a child, then read the chain from both ends."""
    parent = metta.space(S.family_parent)
    parent += S.edge(S.a, S.b)
    parent += S.parent_only(S.kept)
    parent += S.layer(S.parent)

    child = metta.space(S.family_child, inherits=parent)
    child += S.edge(S.b, S.c)
    child += S.child_only(S.local)
    child += S.layer(S.child)

    # One conjunction joins a parent fact to a child fact, because each
    # conjunct is matched through the whole read chain.
    assert [(row.x, row.z) for row in child[S.edge(V.x, V.y), S.edge(V.y, V.z)]] == [
        (S.a, S.c)
    ]

    # Same-shaped facts pin child-first reads without relying on clause order
    # across different arities.
    assert [row.x for row in child[S.layer(V.x)]] == [S.child, S.parent]
    assert m.fn.space_atom_count(child) == [3]

    # Writes never mutate an ancestor: the parent keeps what it had, the child
    # can read it, and the parent cannot read the child.
    assert [row.x for row in parent[S.parent_only(V.x)]] == [S.kept]
    assert [row.x for row in child[S.parent_only(V.x)]] == [S.kept]
    assert not parent[S.child_only(V.x)]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1119 to 1138, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 1138 to 1144, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 1144 to 1111, on the release tree:
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
#: RE-PINNED 2026-08-25, 1111 to 1118, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 1118 to 1142 (+24), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 1142 to 1162 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-31, 1162 to 1193 (+31), the twin now names its spaces,
#: metta.space(S.locked, restricted=True) and metta.space(S.family_child,
#: inherits=parent), which is what the MeTTa original writes; a named space
#: declares its model on a name the caller chose rather than on a pooled
#: anonymous one, and carries its own storage module for the life of the
#: process [measured 2026-08-31: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=41e2cb9862e757dbe066516dab13ae55491f64d3].
#: RE-PINNED 2026-09-01, 1193 to 1284 (+91), one corpus pricing pass on the
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
#: RE-PINNED 2026-09-01, 1284 to 1277 (-7), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 1277 to 1307 (+30), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 1307 to 1325 (+18), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 1325 to 1305 (-20), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-02, 1305 to 1327 (+22), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 1327
