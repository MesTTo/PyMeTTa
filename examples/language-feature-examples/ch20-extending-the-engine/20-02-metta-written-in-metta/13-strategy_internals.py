"""Purpose: examples/ch20-extending-the-engine/20-02-metta-written-in-metta/13-strategy_internals.metta in Python: lib_strategy from the inside.

A strategy is a NAME, so `S.mark` is what every operation here is handed:
applying one lowers to a MeTTa call and never installs a host callback, which
is the library's whole claim and the reason a Python callable would be the
wrong argument.

The typed operations take a SORT, so the declarations below are the ordinary
`typed` and `arrow` doors and the term's own type is what decides whether the
strategy runs.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, arrow, lib, typed


def declined(answers):
    """Whether a strategy answered nothing, `Empty` being how it says so."""
    return [answer for answer in answers if answer != S.Empty] == []


def twin(m):
    """Application, the two traversals, and the three typed operations."""
    m += lib.strategy

    @m.define
    def mark(x):
        # (= (mark $x) (marked $x))
        return S.marked(x)

    evaluate, everywhere = m.fn["strategy-eval"], m.fn["strategy-all"]
    tail, one = m.fn["strategy-all-tail"], m.fn["strategy-one"]

    # Application itself: a strategy NAME and a term. Every combinator
    # bottoms out here.
    assert evaluate(S.mark, S.a) == [S.marked(S.a)]
    assert evaluate(S.id, S.a) == [S.a]
    assert evaluate(S.mark, S.a) == m.fn["strategy-apply"](S.mark, S.a)

    # `all`: the strategy at every immediate child, INCLUDING the written
    # expression head, because a head is a child in MeTTa's flat term model.
    assert everywhere(S.mark, S.h(S.a, S.b)) == [
        Expression((S.marked(S.h), S.marked(S.a), S.marked(S.b)))
    ]
    assert everywhere(S.mark, S.leaf) == [S.leaf]
    assert everywhere(S.mark, ()) == [()]

    # The recursion inside it: `strategy-all` takes the head off and hands
    # the TAIL to this one, so the two agree on an expression and differ on
    # everything else.
    assert tail(S.mark, (S.a, S.b)) == [(S.marked(S.a), S.marked(S.b))]
    assert tail(S.mark, ()) == [()]
    assert tail(S.mark, (S.a, S.b)) == [everywhere(S.mark, S.h(S.a, S.b))[0][1:]]
    assert declined(tail(S.mark, S.leaf))
    assert everywhere(S.mark, S.leaf) == [S.leaf]

    # `one`: every successful single-child rewrite, left to right, as
    # separate answers rather than one term with every child rewritten.
    # The `Empty` a declining position answers is a sentinel the original's
    # `collapse` prunes; a Python answer list keeps it, so it is filtered by
    # name rather than pretended away.
    rewrites = [answer for answer in one(S.mark, S.h(S.a)) if answer != S.Empty]
    assert rewrites == [Expression((S.marked(S.h), S.a)), S.h(S.marked(S.a))]
    assert declined(one(S.mark, S.leaf))

    # The three typed operations under the application operator. A
    # type-preserving strategy has the same sort on both sides, and
    # `strategy-typed-tp` finds that sort by MATCHING the declaration.
    m += typed(S.DA, S.Type)
    m += typed(S.DS, S.Type)
    m += typed(S.da, S.DA)
    m += typed(S.preserve, arrow(S.DA, S.DA))

    @m.define
    def preserve(x):
        # (= (preserve $x) (kept $x))
        return S.kept(x)

    assert m.fn["strategy-typed-tp"](S.preserve, S.da) == [S.kept(S.da)]
    assert declined(m.fn["strategy-typed-tp"](S.preserve, 1))

    # The type-unifying scheme takes the RESULT sort instead.
    m += typed(S.summarize, arrow(S.DA, S.DS))

    @m.define
    def summarize(x):
        # (= (summarize $x) (sum $x))
        return S.sum(x)

    assert m.fn["strategy-typed-tu"](S.summarize, S.DS, S.da) == [S.sum(S.da)]
    assert declined(m.fn["strategy-typed-tu"](S.summarize, S.DA, S.da))

    # Both hand the sort they selected to the one gradual type check.
    apply_typed = m.fn["strategy-typed-apply"]
    assert apply_typed(S.preserve, S.DA, S.da) == [S.kept(S.da)]
    assert declined(apply_typed(S.preserve, S.DA, 1))
    assert apply_typed(S.preserve, S.DA, S.da) == m.fn["◁"](S.preserve, S.TP, S.da)

    # An ill-typed subject reports its OWN error rather than being silently
    # declined, so a term that cannot be typed at all is a different answer
    # from a term whose type does not fit.
    assert apply_typed(S.preserve, S.DA, S.undeclared_name()) == [
        S.kept(S.undeclared_name())
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 422964 inferences, 0.9520x the example's 444306; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 422964 to 423043 (+79), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 423043 to 422924 (-119), metta_substitute_self/3
#: probes the term for the text &self before walking it, one C write and one C
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
#: RE-PINNED 2026-09-08, 422924 to 421170 (-1754), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 421170 to 421193 (+23), boot content moved: the
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
#: RE-PINNED 2026-09-08, 421170 to 425614 (+4444), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 425614 to 425624 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 425624 to 425932 (+308), the module boundary merged
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
#: RE-PINNED 2026-09-08, 421193 to 421228 (+35), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 421228 to 425952 (+4724), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 425952 to 426388 (+436), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 425932 to 431866 (+5934), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 431866 to 431806 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 431806 to 432307 (+501), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=WORKTREE].
BUDGET = 432307
