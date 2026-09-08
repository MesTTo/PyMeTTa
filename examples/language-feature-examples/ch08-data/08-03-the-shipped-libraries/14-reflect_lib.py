"""examples/ch08-data/08-03-the-shipped-libraries/14-reflect_lib.metta in Python: the engine's own surface as data.

Every enumeration answers a name per solution, so a Python list IS the
collapse and `len` is the count. The `engine-` predicates under the MeTTa
names are the same operations, and the claims that pair them are what says
so.

`surface-counts` moves as libraries are imported, so what is pinned here is
the SHAPE rather than the numbers.

An extension point's name keeps its underscore, `foreign_space`, so that one
comes through the exact subscript door where every other name here takes the
host-convention map.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib


def twin(m):
    """Ask what the engine knows, where a name came from, and how many."""
    m += lib.reflect

    @m.define
    def mine(x):
        # (= (mine $x) $x)
        return x

    knows, arity = m.fn["knows?"], m.fn["arity-of"]
    origin = m.fn["origin-of"]

    assert knows(S.car_atom) == [True]
    assert knows(S.mine) == [True]
    assert knows(S.no_such_name_anywhere) == [False]

    # A registered arity counts the ANSWER position, so `car-atom` takes one
    # argument and is registered at 2.
    assert arity(S.car_atom) == [2]
    assert arity(S.cons_atom) == [3]
    assert arity(S.no_such_name_anywhere) == []

    # Where a name comes from, which a flat list of names cannot say.
    assert origin(S.car_atom) == [(S.builtin,)]
    assert origin(S.mine)[0][0] == S.equation
    assert origin(S.case) == [(S.special_form,)]

    # The four enumerations. `special-forms` is what the translator COMPILES
    # and so appears in no registry.
    builtins, special = m.fn["builtins"], m.fn["special-forms"]
    functions, mine_only = m.fn["functions"], m.fn["user-functions"]
    assert len(builtins()) > 100
    assert len(special()) > 10
    assert S.mine in mine_only()
    assert S.car_atom not in mine_only()
    assert S.car_atom in functions()
    assert S.case not in builtins()
    assert S.case in special()
    # `let` is in BOTH, which is what a name with a registered implementation
    # and a compiled form looks like.
    assert S.let in builtins()
    assert S.let in special()

    # The seam catalogue, one (name arity kind) per point.
    points = m.fn["extension-points"]
    assert len(points()) > 3
    assert S["foreign_space"](1, S.ownership) in points()

    # The cheap health check: four pairs rather than four enumerations.
    counts = m.fn["surface-counts"]()[0]
    assert len(counts) == 4
    assert counts[0][0] == S.builtins

    # The whole thing as JSON, which is what an outside tool consumes.
    surface = str(m.fn["surface-json"]()[0].value)
    assert len(surface) > 1000
    assert surface[0] == "{"

    # Every name above has a Prolog rung under it, and the MeTTa name is one
    # equation over it.
    assert m.fn["engine-arity"](S.car_atom) == arity(S.car_atom)
    assert m.fn["engine-knows"](S.car_atom) == [True]
    assert m.fn["engine-knows"](S.no_such_name_anywhere) == [False]
    assert m.fn["engine-origin"](S.car_atom) == [(S.builtin,)]
    assert m.fn["engine-surface-counts"]() == m.fn["surface-counts"]()
    assert len(m.fn["engine-builtin"]()) == len(builtins())
    assert len(m.fn["engine-special-form"]()) == len(special())
    assert len(m.fn["engine-function"]()) == len(functions())
    assert len(m.fn["engine-user-function"]()) == len(mine_only())
    assert len(m.fn["engine-extension-point"]()) == len(points())


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 161415 inferences, 1.0621x the example's 151980; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 161415 to 161491 (+76), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 161491 to 161419 (-72), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 161419 to 161350 (-69), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 161350 to 161489 (+139), boot content moved: the
#: refusal table and the typing point are modules this package did not have,
#: three convert doors became one, per-library faces are projections, and the
#: engine gained a catalog watch point, and SWI clause-indexing shape shifts a
#: twin count by tens whenever boot content moves, the mechanism every earlier
#: entry in these chains names. The watch point itself is one inference per
#: &metta write, which a twin that defines a function pays three of (2239
#: against 2236 on ch03 01-comments with the two announcement clauses taken
#: out), and the (limit ...) rows it exists for cost nothing at all: 2239
#: either way with every row-backed bound removed, because boot seeds the
#: mirror those bounds are read from [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 161350 to 166460 (+5110), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 166460 to 166470 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 166470 to 167727 (+1257), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 167727 to 167755 (+28), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 167755
