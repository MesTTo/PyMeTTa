"""Purpose: examples/ch19-spaces-backed-by-anything/19-01-spaces-of-your-own/02-restricted_spaces.metta in Python: a curated execution base.

A restricted space keeps ordinary computation and its own equations, refuses
anything its base does not publish, and gains a capability only when the
capability is granted at creation.

`metta.space(S.locked, restricted=True)` and
`metta.space(S.reader, restricted=True, grants=[SpaceCapability.file])` are
those two spaces, named exactly as `!(new-space &locked (restricted))` and
`!(new-space &reader (restricted (grants file)))` name them. A name and a MODEL
are independent.

A path crosses as the `pathlib.Path` it is and a capability as the vocabulary
value it is, so neither is quoted into text.
"""

from pathlib import Path

import metta
from metta import S
from metta.errors import SpaceCapabilityError
from metta.vocabularies import SpaceCapability

#: The file the example asks about: a path, which is what pathlib is for.
SOURCE = Path(
    "examples/ch19-spaces-backed-by-anything/19-01-spaces-of-your-own/02-restricted_spaces.metta"
)


def twin(m):  # noqa: ARG001  -- both spaces are created here; the default handle stays untouched
    """Lock a space, watch it refuse a file read, then grant the capability."""
    # The original NAMES its spaces, `!(new-space &locked (restricted))`, and
    # the answer of that form IS the name it created. This is that call: a name
    # and a MODEL are independent, because metta_declare_restricted_space/2
    # always took any valid space name and only the Python door required
    # anonymity.
    locked = metta.space(S.locked, restricted=True)

    @locked.define
    def double(x: int) -> int:
        return x * 2

    # A restricted space retains ordinary computation and its own equations.
    assert locked.eval(S.double(21)) == [42]

    # A path crosses the call door as the atom its codec makes of it, so
    # nothing quotes it into a string first.
    asked = S["exists_file"](SOURCE)

    # The file operation reaches a refusal that names what is missing.
    refusal = None
    try:
        locked.eval(asked)
    except SpaceCapabilityError as error:
        refusal = error
    assert refusal is not None

    # A capability is granted explicitly when the space is created, as the
    # vocabulary's own value rather than as the word for it.
    reader = metta.space(S.reader, restricted=True, grants=[SpaceCapability.file])
    assert reader.eval(asked) == [True]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 52818 to 52949, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 52949 to 52946, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 52946 to 53023, on the release tree:
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
#: RE-PINNED 2026-08-25, 53023 to 53120, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 53120 to 56077 (+2957), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 56077 to 56803 (+726), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 56803 to 56798 (-5), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-31, 56798 to 61560 (+4762), the twin now names its spaces,
#: metta.space(S.locked, restricted=True) and metta.space(S.family_child,
#: inherits=parent), which is what the MeTTa original writes; a named space
#: declares its model on a name the caller chose rather than on a pooled
#: anonymous one, and carries its own storage module for the life of the
#: process [measured 2026-08-31: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=41e2cb9862e757dbe066516dab13ae55491f64d3].
#: RE-PINNED 2026-09-01, 61560 to 61707 (+147), one corpus pricing pass on the
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
#: RE-PINNED 2026-09-01, 61707 to 62169 (+462), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 62169 to 62273 (+104), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 62273 to 62711 (+438), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 62711 to 63647 (+936), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 63647 to 64200 (+553), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
#: RE-PINNED 2026-09-02, 64200 to 64349 (+149), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-02, 64349 to 64390 (+41), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 64390
