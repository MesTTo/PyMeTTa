"""Purpose: examples/ch07-control-flow/07-05-recursion/06-peano.metta in Python: growing a space 300 times.

Each round reads every `(num $t)` in the space and writes `(num (S $t))` back,
refusing a duplicate, so 300 rounds leave 301 atoms. The claim is that count,
and Python counts it: `collapse` is `list()` and `length` is `len()`, and a
lazy answer view counts through the engine without pulling an atom into Python.

All four definitions are compiled now, and each one is the Python statement its
MeTTa form already was. An assignment is `let`; a statement sequence is `let*`;
`if`/`else` is the conditional; a `case` with one capturing arm is an ordinary
binding. Only `collapse` still declares a rung, because the dissolution table
sends it to `list()` and a compiled body has no lowering for that.

`&self` inside a stored body is the ambient space, and bare `match(pattern,
template)` is what reads it: the one-pattern form lowers to
`(match (context-space) ...)`. Where the example passes `&self` as an ARGUMENT
the handle itself crosses, because a space is a grounded atom wherever a term
wants one.

`expandK` keeps its camelCase head through the explicit `name=`, because the
implicit name is the mechanical image and `def expand_k` would install
`expand-k`, a different head from the one the example makes matchable.
"""

from metta import S, V, fn, match, superpose


def twin(m):
    """Expand the space 300 times, then count what is in it."""

    @m.define
    def add_atom_no_duplicate(space, atom):
        """Write the atom unless the space already answers a match for it."""
        # (= (add-atom-no-duplicate $Space $Atom)
        #    (if (== () (collapse (once (match $Space $Atom $Atom))))
        #        (add-atom $Space $Atom)
        #        (empty)))
        seen = S.collapse(
            S.once(match(space, atom, atom))
        )  # rung: `collapse` is list(), which a compiled body has no lowering for (P14.4)
        if fn.eq(seen, ()):  # seen comes from a match, so its type is unknown
            return fn.add_atom(space, atom)
        return superpose()

    @m.define
    def expand_once():
        """For every existing (num $t), add (num (S $t))."""
        # (= (expand-once)
        #    (case (match &self (num $t) $t)
        #          (($x (add-atom-no-duplicate &self (num (S $x)))))))
        found = match(S.num(V.t), V.t)
        return add_atom_no_duplicate(m, S.num(S.S(found)))

    @m.define(name="expandK")
    def expand_k(n: int):
        """Run expand-once n times, then answer done."""
        # (= (expandK $n)
        #    (if (== $n 0) done (let $temp1 (expand-once) (expandK (- $n 1)))))
        if fn.eq(n, 0):  # engine equality is intentional
            return S.done
        _round = expand_once()
        return expand_k(n - 1)

    @m.define
    def demo_peano(k):
        """Seed the space with Z, expand it k times, and read every number."""
        # (= (demo-peano $K)
        #    (let* (($s (add-atom &self (num Z))) ($g (expandK $K)))
        #          (match &self (num $1) $1)))
        _seeded = fn.add_atom(m, S.num(S.Z))
        _grown = expand_k(k)
        return match(S.num(V.stored), V.stored)

    # !(test (length (collapse (demo-peano 300))) 301)
    assert len(demo_peano(300)) == 301


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2027861 to 2027880, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 2027880 to 2027886, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2027886 to 2027853, on the release tree:
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
#: RE-PINNED 2026-08-25, 2027853 to 2027858, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 2027858 to 2396413 (+368555): 6917bef7's relational
#: candidate rows, measured 2,027,856 to 2,394,524 at the exact pair;
#: ai-brief-p14-relational-ops-fastpath carries the follow-up [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 2396413 to 2396435 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 2396435 to 2394988 (-1447), by the specializer
#: argument-walk fix.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-08-26, 2396435 to 2033218 (-363217, -15.2%). `len(...)` on
#: this effect-bearing goal used to encode and cross all 301 answers to reach
#: one number, and these answers are deep Peano numerals, so the encoding cost
#: by term size: 2,029,719 inferences counting without it, 2,392,138 counting
#: with it, 2,393,864 for the full materializing pass. The count and the
#: values now come from ONE evaluation holding its answers unencoded
#: [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-relational-fastpath off 694c12f7 with engine/reader.so and the MORK artefact; commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
#: RE-PINNED 2026-08-26, at the relational-counting merge: 2031806.
#: Both parents re-pinned this budget and neither number survives the
#: merge, so it is re-measured here rather than resolved to a side.
#: The two mechanisms above COMPOSE, and the world-admission merge's
#: admission guard lands on top of them: this lineage read 2394988,
#: the counting branch read 2033218 against its own base, and the
#: merged tree reads 2031806
#: [measured: min-of-3 serial fresh processes on the resolved merge
#: tree; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 3 ../../examples/<this example>;
#: fixture=engine/reader.so and the MORK artefact present;
#: commit=58d0332489da668251edcd52ccc5cb42ba2e57bb].
#: RE-PINNED 2026-09-01, 2031806 to 1745696 (-286110), the compiled-language
#: batch: try/raise on the error algebra, dict-space literals with lib_dict
#: auto-import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 1745696 to 1745675 (-21), the subtract-atom primitive
#: and the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 1745675 to 1474885 (-270790), generic Python operators
#: now dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 1474885 to 1476216 (+1331), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 1476216 to 1476476 (+260), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 1476476 to 1476494 (+18), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 1476494 to 1476504 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
BUDGET = 1476504
