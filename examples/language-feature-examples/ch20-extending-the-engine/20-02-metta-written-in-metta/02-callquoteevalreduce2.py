"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/02-callquoteevalreduce2.metta in Python: four ways to not reduce.

One inner term, `(fib (myfunc))`, under four wrappers. `call`, `eval` and
`reduce` all get to 5; `quote` holds the term as it was written. Each claim
wraps the answer in a symbol of its own so the comparison sees what came back
rather than what it would reduce to next.

Everything here compiles. `fib` and `myfunc` are ordinary functions, and the
four wrappers are ordinary functions whose bodies mention a translator form:
`call`, `quote`, `eval` and `reduce` are forms the compiler reads rather than
functions the catalog holds, so a body names them at the `S` door and hands
them a call built out of the two Python names beside it.

The outer wrappers in the claims are not functions at all. `fib-call` has no
equation, so evaluating `(fib-call (call-fib))` reduces what is inside it and
leaves the wrapper standing, which is exactly what the claim is measuring; that
makes each one a term to evaluate rather than a call to make.
"""

from metta import S


def twin(m):
    """Wrap one term four ways, and see which of them reduce."""

    @m.define
    def fib(n: int) -> int:              # (= (fib $N) (if (< $N 2) $N
        if n < 2:                        #     (+ (fib (- $N 1)) (fib (- $N 2)))))
            return n
        return fib(n - 1) + fib(n - 2)

    @m.define
    def myfunc():                        # (= (myfunc) 5)
        return 5

    @m.define
    def call_fib():                      # (= (call-fib) (call (fib (myfunc))))
        return S.call(fib(myfunc()))

    @m.define
    def quote_fib():                     # (= (quote-fib) (quote (fib (myfunc))))
        return S.quote(fib(myfunc()))

    @m.define
    def eval_fib():                      # (= (eval-fib) (eval (fib (myfunc))))
        return S.eval(fib(myfunc()))

    @m.define
    def reduce_fib():                    # (= (reduce-fib) (reduce (fib (myfunc))))
        return S.reduce(fib(myfunc()))

    inner = S.fib(S.myfunc())
    assert m.answers(S.fib_call(S.call_fib())) == [S.fib_call(5)]
    # The quote BARRIER dissolves and hands over its payload unevaluated,
    # (myfunc) included.
    assert m.answers(S.fib_quote(S.quote_fib())) == [S.fib_quote(inner)]
    assert m.answers(S.fib_eval(S.eval_fib())) == [S.fib_eval(5)]
    assert m.answers(S.fib_reduce(S.reduce_fib())) == [S.fib_reduce(5)]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 49843 to 49790, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 49790 to 49720, on the release tree:
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
#: RE-PINNED 2026-08-25, 49720 to 49714, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 49714 to 52919 (+3205), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 52919 to 52891 (-28), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 52891 to 52859 (-32), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 52859 to 38665 (-14194), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 38665 to 38620 (-45), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 38620 to 39435 (+815), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 39435 to 43783 (+4348), exact numeric annotations
#: retain native operator heads, publish MeTTa type declarations, and leave
#: relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 43783 to 44235 (+452), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 44235 to 44357 (+122), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 44357 to 44367 (+10), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 44367 to 43022 (-1345), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 43022 to 43396 (+374), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 43396 to 43491 (+95), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
BUDGET = 43491

#: OVERRUN 2026-09-07, 1500: it names the six wrappers as definitions where the
#: example writes one inner term under four of them. Measured 43396 against a
#: ceiling of 41922; a minimal twin of this example costs 29827, inside the
#: ceiling's 41922, so the distance is this twin's own program [measured
#: 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-08, 1600: the same program, priced on the tree that merged
#: the twins burn-down after the catalog-types merge, reads 43491 against a
#: ceiling of 41968, 23 past the 1500 above; the ceiling moved +46 with the
#: re-derived authoring constants (1406 once plus 1309 each for six
#: definitions) and the twin +95 with the definition-time delivery check and
#: the lookup step every twin pays; the minimal twin costs 29826, inside the
#: ceiling, so the distance is still this twin's own program [measured
#: 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
OVERRUN = 1600

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 1 atom the example does not (1 :): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "230acfc89f628d20a71888230be17b02c8e79d3d49807890dd7a1a8027f3b30c"
