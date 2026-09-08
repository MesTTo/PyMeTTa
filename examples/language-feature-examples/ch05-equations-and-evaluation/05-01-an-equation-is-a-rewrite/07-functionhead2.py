"""Purpose: examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/07-functionhead2.metta in Python: a relational constraint, chained.

`animal` keeps whatever is living AND a being; `cat` takes what `animal`
produces and keeps whatever is also small. `small` is put under a
`NoMatchFail` dispatch policy first, so asking `small` about something it has
no fact for FAILS the relation instead of answering the unreduced call, which
is what makes `cat` a filter rather than a producer of residual terms.

The ten facts are a TABLE, so they are written as one: a dict from each animal
to the relations that hold of it, and a comprehension turning each pair into
its equation. That preserves the original's own reading order and says the
shape of the knowledge once instead of ten times. They cannot be decorated
functions: each head fixes a SYMBOL (`(living garfield)`), a stacked clause
fixes a head position with a literal DEFAULT, and a literal is a bool, int,
float or str, never a symbol.

The three relations that follow are ordinary decorated functions. `only`
forces its constraint with an ordinary assignment, which the compiler stores
as a `let*`; `cat` uses relational `let`, where `$X` is the hole unification
fills. The fact relations are explicit symbol calls because they are data
heads in this file, not Python definitions.

The claim dissolves twice over: `collapse` is the list an evaluation already
answers, and `msort` is Python's own `sorted`.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import TRUE, S, V, equation
from metta.vocabularies import NoMatchEnum

#: The knowledge, as the table it is: each animal and what holds of it, in the
#: original's own order.
FACTS = {
    S.garfield: (S.living, S.being, S.small),
    S.snoopy: (S.living, S.being),
    S.roomba: (S.being, S.small),
    S.cat42: (S.living, S.being, S.small),
}


def twin(m):
    """Filter ten facts through two chained relations."""
    metta.reflection += S.dispatch_policy(
        S.small, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
    )

    # (= (living garfield) True) ... (= (small cat42) True)
    # rung: each head fixes a SYMBOL, and a stacked clause's literal default is a
    #   bool, int, float or str (residue, P14.4)
    m += [equation(rel(who)).to(TRUE) for who, rels in FACTS.items() for rel in rels]

    @m.define
    def only(c, x):
        # (= (only $C $X) (let* (($constraint $C)) $X))
        _constraint = c
        return x

    @m.define
    def animal(x):
        # (= (animal $X) (only ((living $X) (being $X)) $X))
        return only((S.living(x), S.being(x)), x)

    @m.define
    def cat(a):
        # (= (cat $A) (let $A (animal $X) (only (small $X) $X)))
        return S.let(  # rung: solve(pattern, subject) has no expression-position form inside a compiled body
            a, animal(V.x), only(S.small(V.x), V.x)
        )

    assert sorted(m.eval(S.cat(V.X))) == [S.cat42, S.garfield]


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 25419 to 25438, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 25438 to 25271, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 25271 to 25175, on the release tree:
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
#: RE-PINNED 2026-08-25, 25175 to 25151, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 25151 to 25655 (+504), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 25655 to 25568 (-87), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 25568 to 25525 (-43), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 25525 to 13805 (-11720), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 13805 to 13778 (-27), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 13778 to 13752 (-26), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 13752 to 14244 (+492), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 14244 to 14239 (-5), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 14239 to 13212 (-1027), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 13212 to 13554 (+342), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 13554 to 13618 (+64), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 13618 to 13374 (-244), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 13374 to 13400 (+26), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 13400 to 13453 (+53), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
BUDGET = 13453

#: DIVERGED 2026-09-07, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 1 atom the example does not (1 =): the twin is an ordinary Python
#: program and its body lowers to the engine's own forms: a match statement is
#: ONE equation whose body is a case tower where the example writes one clause
#: per arm, a named intermediate is a let* the original does not have, a Python
#: truth test wraps its condition in py-truthy, and the annotations and
#: docstrings that come with it are stored beside them [measured 2026-09-07:
#: the two stored-atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "45f33941ab23ce785d3f3c847146e14a22a9fc0c3c92538db86181edf3c74153"
