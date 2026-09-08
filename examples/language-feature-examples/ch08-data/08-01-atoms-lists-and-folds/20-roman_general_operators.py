"""examples/ch08-data/08-01-atoms-lists-and-folds/20-roman_general_operators.metta in Python: three set operations with the comparison passed in.

The nine fixed spellings `15-roman.metta` uses are one call each to these
three with an equality supplied, so this file supplies one of its own. The
operator names are punctuation Python's grammar will not take, so all three
come through the exact subscript door, which is rung 5.

`close-enough` is an ordinary compiled definition, and the operators take its
NAME rather than a call, which is what makes them higher-order. Its comparison
is built by its WORD, `fn.lt(...)`, because `<` is not one of the five number
operators a compiled body lowers natively and `a < b` would store
`(py-operator lt ...)` where the original stores `(< ...)`.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, fn, lib

#: The two collections every claim is about.
LEFT = (1, 5, 9)
RIGHT = (2, 100)


def twin(m):
    """Intersection, subtraction and union under a comparison of our own."""
    m += lib.roman

    @m.define
    def close_enough(a: int, b: int) -> bool:
        # (= (close-enough $a $b) (< (abs-math (- $a $b)) 2))
        return fn.lt(fn.abs_math(a - b), 2)

    near = S.close_enough
    intersect, subtract, union = m.fn["/?\\"], m.fn["\\?"], m.fn["\\?/"]

    # `/?\` keeps the elements of the left the comparison relates to
    # something on the right.
    assert intersect(near, LEFT, RIGHT) == [(1,)]
    assert intersect(near, LEFT, ()) == [()]

    # `\?` is the other half: the elements with no relative on the right.
    assert subtract(near, LEFT, RIGHT) == [(5, 9)]
    assert subtract(near, LEFT, ()) == [LEFT]

    # `\?/` is the union built out of that subtraction.
    assert union(near, LEFT, RIGHT) == [(5, 9, 2, 100)]
    assert union(near, (), RIGHT) == [RIGHT]

    # Passing `==` back in reproduces the fixed spelling exactly, which is
    # what makes the nine sugar over three operations.
    equals = S["=="]
    assert intersect(equals, (1, 2, 3), (2, 3, 4)) == m.fn["/==\\"]((1, 2, 3), (2, 3, 4))
    assert subtract(equals, (1, 2, 3), (2, 3, 4)) == m.fn["\\=="]((1, 2, 3), (2, 3, 4))
    assert union(equals, (1, 2, 3), (2, 3, 4)) == m.fn["\\==/"]((1, 2, 3), (2, 3, 4))

    # `fst` and `snd` read a two-element expression, and `cns` is the pair
    # reading of `cons`.
    assert m.fn.fst((S.a, S.b)) == [S.a]
    assert m.fn.snd((S.a, S.b)) == [S.b]
    assert m.fn.cns((1, (2, 3))) == [(1, 2, 3)]
    assert m.fn.cns((S.f(1), ())) == [(S.f(1),)]

    # The two tracing helpers print and answer their subject unchanged.
    assert m.fn.traceid(42) == [42]
    assert m.fn.tracem(G("the answer"), 42) == [42]
    assert m.answers(1 + S.traceid(41)) == [42]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 132148 inferences, 1.0705x the example's 123442; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 132148 to 132187 (+39), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 132187 to 132056 (-131), metta_substitute_self/3
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
#: RE-PINNED 2026-09-08, 132056 to 130302 (-1754), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 130302 to 130321 (+19), boot content moved: the
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
#: RE-PINNED 2026-09-08, 130302 to 130866 (+564), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 130866 to 130876 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 130876 to 131119 (+243), the module boundary merged
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
#: RE-PINNED 2026-09-08, 131119 to 131192 (+73), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 131192 to 131230 (+38), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
BUDGET = 131230
