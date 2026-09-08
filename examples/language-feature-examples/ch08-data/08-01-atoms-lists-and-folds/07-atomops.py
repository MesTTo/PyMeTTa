"""examples/ch08-data/08-01-atoms-lists-and-folds/07-atomops.metta in Python: structure, and what refuses.

The file has three parts and each belongs on its own rung.

Taking apart an expression that IS an expression is Python's own work and costs
no engine at all: `e[0]` is the head, `e[1:]` is the rest, `e[i]` is a position,
and `Expression((0, *e))` builds a new one around it. Those claims are written
that way and nothing crosses.

The second part is about what the operations do with an argument they cannot
use, and Python cannot say it: `e[5]` raises IndexError where `index-atom`
answers `()`, and `len(5)` raises TypeError where `size-atom` answers `()`.
ANSWERING rather than raising is the claim, so those go to the operations
themselves, named through `m.fn.<name>` where rung 4's map turns each
underscore back into the hyphen the engine holds. Two of them answer an
`(Error ...)` atom instead, which is data in aggregation, so those two are read
by iterating rather than through the scalar door, which raises on an error.

The third part is sharper still. An unbound VARIABLE is not a value Python has,
and handing one where an expression is expected used to be answered rather than
refused: `(car-atom $u)` unified its argument with a fresh cons cell and
answered the head it had just invented. Each of those claims names its own
operation, because the refusal belongs to that operation.
"""

from metta import UNIT, Expression, S, V


def twin(m):
    """Take an expression apart, then ask what refuses and how."""

    def guarded(call):
        """Whether an operation refuses a call or answers it.

        Most of these calls carry an unbound variable, and the call answers the
        verdict all the same: the bindings those variables took are the
        parallel row face on the same view.
        """
        return m.fn.if_error(S.catch(call), S.refused, S.answered).one()

    e = Expression((1, 2, 3))
    pair = S.A(S.B)
    nothing = Expression(())

    # Structure, in Python, with no crossing at all.
    assert Expression((0, *e)) == Expression((0, 1, 2, 3))   # (cons-atom 0 (1 2 3))
    assert e[0] == 1                                          # (car-atom (1 2 3))
    assert list(e[1:]) == [2, 3]                              # (cdr-atom (1 2 3))
    assert e[1] == 2                                          # (index-atom (1 2 3) 1)

    assert m.fn.id(5) == [5]
    assert S.Father(V.X).alpha_eq(S.Father(V.Y))              # (=alpha ...) is True
    assert not S.Father(V.X).alpha_eq(S.Son(V.X))
    assert m.fn.first_from_pair(pair) == [S.A]
    assert m.fn.second_from_pair(pair) == [S.B]

    # An argument the operation cannot use is ANSWERED, not raised.
    assert m.fn.index_atom(e, 5) == [nothing]   # past the end
    assert m.fn.index_atom(e, S.a) == [nothing]   # not an index at all
    assert m.fn.size_atom(5) == [nothing]
    assert m.fn.sort_atom(5) == [nothing]
    assert m.fn.unique_atom(5) == [nothing]
    assert m.fn.alpha_unique_atom(5) == [nothing]
    assert m.fn.intersection_atom(5, S.a()) == [nothing]

    # A non-expression operand answers UNIT, the empty expression itself.
    # !(test (min-atom 5) ())
    assert m.fn.min_atom(5) == [UNIT]
    assert m.fn.max_atom(5) == [UNIT]

    # An unbound variable is a program error, and every guarded position
    # refuses it by name rather than solving for it.
    assert guarded(S.car_atom(V.unbound)) == S.refused
    assert guarded(S.size_atom(V.unbound)) == S.refused
    assert guarded(S.sort_atom(V.unbound)) == S.refused
    assert guarded(S.index_atom(V.unbound, 0)) == S.refused
    assert guarded(S.subtraction_atom(V.unbound, S.a(S.b))) == S.refused

    # A bound argument is untouched, which is the half that makes the refusal
    # worth anything.
    assert guarded(S.car_atom(Expression((1, 2)))) == S.answered
    assert Expression((1, 2))[0] == 1

    # The refusal is narrow: index-atom's SECOND argument is relational by
    # design, so an unbound index still enumerates every position in turn.
    assert m.fn.index_atom(S.a(S.b, S.c), V.i) == [S.a, S.b, S.c]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 26270 to 26631, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 26631 to 26632, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 26632 to 26670, on the release tree:
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
#: RE-PINNED 2026-08-25, 26670 to 26678, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 26678 to 24000 (-2678), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 24000 to 48677 (+24677), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 48677 to 48635 (-42), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 48635 to 48729 (+94), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 48729 to 49237 (+508), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 49237 to 49245 (+8), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 49245 to 47118 (-2127), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 47118 to 11194 (-35924), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 11194 to 11138 (-56), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 11138 to 11476 (+338), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 11476 to 11748 (+272), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 11748 to 11736 (-12), Compile shipped typing decisions
#: and initial vocabulary facts, index vocabulary membership, and reuse the
#: first Python variable binding before indexing additional names; retain type,
#: transaction and variable-identity checks [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 11736
