"""Purpose: spell the admission-pool differential specification in Python.

`(admits <pool> <type>)` and `(capacity <pool> <n>)` are data, and a pool is a
space whose write door is claimed by a judge over them. The engine ships that
judge as a Prolog-bodied builtin; this file is its executable specification,
the same judge written in the surface language, claimed through the same
general hook, refusing and accepting the same atoms, with a differential
asserting the two agree verdict for verdict.

The whole judge is ordinary Python now. Every part of the original's chain has
a spelling inside a compiled body: `if`/`else` for the branches, `==` for the
empty test, `types[0]` and `types[1:]` for `car-atom` and `cdr-atom`, `<` for
the bound, `match(space, pattern, template)` for the two catalog reads, and
`accept`/`refuse` for the verdicts. The four definitions are written
bottom-upwards, because a compiled body calls a sibling by the Python name it
is already bound to and a name has to exist before it is called.

The Atom masks are the annotations. `atom: Atom` emits
`(: metta-admission-typed (-> %Undefined% Atom %Undefined% %Undefined%))`, the
declaration the original writes by hand, and it is load-bearing: it keeps the
offered atom unreduced the whole way down, so a pool judges the atom AS ITSELF
[measured 2026-08-24: the annotation's own emission read back from the space;
commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].

Both spaces the judge talks about are HANDLES, in the stored equations as well
as at the call sites: a space is an ordinary term operand, and a compiled body
carries one the way a term does. The contract rows go into the reflection space
through `+=` rather than through `pool.admits(...)`, because the receiver
method also CLAIMS the pool's write door for the shipped builtin, which is the
one thing this example may not do: the claim under test is its own.

Assumes:
  - the custom judge, pool setup, and seven claims mirror the source example
    [source: examples/ch15-writing-transactions-and-worlds/04-admission_pools.metta lines 9-72; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Guarantees:
  - the custom and builtin judges agree before, at, and after the declared
    capacity boundary [measured 2026-08-24: the twin runs to completion under
    the lane, which is what proves every assert it states;
    command=python extensions/python/tools/twin_coverage.py
    examples/ch15-writing-transactions-and-worlds/04-admission_pools.metta; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import Atom, S, V, accept, fn, match, refuse, typed


def twin(m):
    """Install the surface-written judge, claim one pool, and compare verdicts."""
    reflection = metta.reflection
    pool = metta.space(S.metta_pool)

    # space-atom-count is the store's own clause bookkeeping, a property read
    # per add rather than an enumeration of everything the pool holds.
    @m.define
    def metta_admission_within(pool_, limits):
        if limits == ():
            return accept()
        if fn.space_atom_count(pool_) < limits[0]:
            return accept()
        return refuse(S.pool_at_capacity(limits[0]))

    @m.define
    def metta_admission_bounded(pool_):
        return metta_admission_within(pool_, S.collapse(match(reflection, S.capacity(pool_, V.limit), V.limit)))  # rung: a compiled body has no spelling for list()

    # Every declared admits type must be carried, the witness reading: an atom
    # whose type nothing declares is not evidence that it is one of these, and
    # a judge that let it in would admit everything a program never got round
    # to declaring.
    @m.define
    def metta_admission_typed(pool_, atom: Atom, types):
        if types == ():
            return metta_admission_bounded(pool_)
        if fn.has_declared_type(atom, types[0]):
            return metta_admission_typed(pool_, atom, types[1:])
        return refuse(S.does_not_carry(types[0]))

    @m.define
    def metta_admission_verdict(pool_, atom: Atom):
        return metta_admission_typed(pool_, atom, S.collapse(match(reflection, S.admits(pool_, V.type), V.type)))  # rung: as above

    # Contract atoms for one pool: Ticket-typed members, at most two of them.
    reflection += S.admits(pool, S.Ticket)
    reflection += S.capacity(pool, 2)
    m += typed(S.ticket(S.a), S.Ticket)
    m += typed(S.ticket(S.b), S.Ticket)

    # The guard is one line, and the claim is the ordinary general hook:
    # nothing about admission is special-cased in the engine's write path.
    @pool.pre_add
    @m.define
    def metta_pool_guard(incoming):
        return metta_admission_verdict(pool, incoming)

    # A typed atom enters; an untyped one is refused naming the missing type.
    pool += S.ticket(S.a)
    assert [row.x for row in pool[S.ticket(V.x)]] == [S.a]

    stowaway = S.stowaway(1)
    assert m.eval(fn.catch(fn.add_atom(pool, stowaway))) == [  # rung: catch keeps this failure as aggregate data, which is what the example claims about
        S.Error(
            S["metta_add_refused"](pool, stowaway, S.does_not_carry(S.Ticket)),
            S.none,
        )
    ]

    # The bound holds: the second ticket fills the pool and the third is
    # refused.
    pool += S.ticket(S.b)
    assert m.eval(fn.catch(fn.add_atom(pool, S.ticket(S.a)))) == [  # rung: as above
        S.Error(
            S["metta_add_refused"](pool, S.ticket(S.a), S.pool_at_capacity(2)),
            S.none,
        )
    ]

    # The differential, across the judge's three verdict classes: the shipped
    # builtin and the surface-written chain answer the same verdict for the
    # same pool and atom, which is what licenses the Prolog body as an
    # implementation choice.
    builtin = m.fn.space_admission_verdict
    assert builtin(pool, stowaway).one() == metta_admission_verdict(pool, stowaway).one()
    assert builtin(pool, S.ticket(S.a)).one() == metta_admission_verdict(pool, S.ticket(S.a)).one()

    reflection -= S.capacity(pool, 2)
    assert builtin(pool, S.ticket(S.a)).one() == metta_admission_verdict(pool, S.ticket(S.a)).one()
    assert builtin(pool, S.ticket(S.a)) == [S.accept()]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. This file's previous pin was an empirical envelope rather than a
#: point, because its judge runs engine-time matching whose count moves with
#: the lane's own scheduling; the re-pin pass owns that decision too
#: [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 48023 to 48089, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 48089 to 48105, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 48105 to 48002, on the release tree:
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
#: RE-PINNED 2026-08-25, 48002 to 48029, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 48029 to 50201 (+2172), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 50201 to 50407 (+206), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 50407 to 48928 (-1479), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 48928
