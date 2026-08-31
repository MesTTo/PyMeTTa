"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/05-scallop_readme.metta in Python: the five Scallop README programs.

Transitive paths over edges, stratified even-or-odd through negation, a count
per colour, an argmax per class, and a set-valued animal count. Each is a
handful of facts plus a handful of equations, and each claim is the answer the
Scallop README prints. They are five independent programs, so they are five
functions here, and `twin` runs them in the example's own order.

Almost every definition is compiled, and the Python statements ARE the MeTTa
forms: an assignment is `let`, a statement sequence is `let*`, `if`/`else` and
the conditional expression are `if`, two yields are two coexisting equations,
and bare `match(pattern, template)` is `(match (context-space) ...)`, which is
what `&self` means inside a stored body. A sibling is called by its Python
name, so a hyphenated head is never spelled to reach one.

Three things the surface still makes the twin say the long way, each measured
rather than assumed:

- The example inlines a `let` under each `collapse`. The twin NAMES that
  intermediate instead, which the lane's contract allows and the checklist
  asks for, and leaves `collapse` itself mentioned, because the dissolution
  table sends it to `list()` and a compiled body has no lowering for that.
- `sc-odd?` is the one relation that must stay TWO coexisting equations. Its
  literal head `(sc-odd? 1)` beside the variable head is what `not-provable`
  builds its dual from; folding them into one guarded body compiles, answers
  correctly on a direct call, and then fails the negation with
  ``Type error: `integer' expected, found `Empty'``. So it is a `@m.rules`
  bundle, and a rules body EXECUTES, which is why its `let` and `match` are
  built by naming their heads.
- `foldall` and `not-provable` are named through `S` rather than `fn`, because
  a compiled body resolves `fn` against the space's catalog and neither head
  is in it (friction, P14.4).
"""

from metta import TRUE, Expression, G, S, V, equation, fn, match, superpose

#: The odd-number relation, whose name carries a `?` no Python identifier can.
ODD = S["sc-odd?"]

#: The colours, the grades and the taxonomy the last three programs work over.
COLOURS = ((0, G("blue")), (1, G("green")), (2, G("blue")))
GRADES = ((0, G("tom"), 50), (0, G("jerry"), 70), (0, G("alice"), 60),
          (1, G("bob"), 80), (1, G("sherry"), 90), (1, G("frank"), 30))
KINDS = ((S.giraffe, S.mammal), (S.tiger, S.mammal), (S.mammal, S.animal))
NAMES = ((1, S.giraffe), (1, S.tiger), (2, S.giraffe), (2, S.tiger))


def paths(m):
    """Transitive paths over two edges. README result {(0,1), (0,2), (1,2)}."""
    # (sc-edge 0 1) (sc-edge 1 2)
    m += S.sc_edge(0, 1)
    m += S.sc_edge(1, 2)

    @m.define
    def sc_edge_to(node):
        """(= (sc-edge-to $a) (match (context-space) (sc-edge $a $b) $b))."""
        return match(S.sc_edge(node, V.b), V.b)

    @m.define
    def sc_path_to(node):
        """(= (sc-path-to $a) (sc-edge-to $a)), and the recursive alternative."""
        yield sc_edge_to(node)
        yield sc_path_to(sc_edge_to(node))

    @m.define
    def sc_path_pair():
        """One (from to) pair per path; the example inlines this binding."""
        start = match(S.sc_edge(V.a, V._), V.a)
        return (start, sc_path_to(start))

    @m.define
    def sc_paths():
        """(= (sc-paths) (collapse ...))."""
        return S.collapse(sc_path_pair())  # rung: `collapse` is list(), which a compiled body has no lowering for (P14.4)

    # !(test (sc-paths) ((0 1) (0 2) (1 2)))
    assert sc_paths() == [Expression(((0, 1), (0, 2), (1, 2)))]


def evens(m):
    """Stratified even-or-odd: negation sees the finite number relation whole."""
    # (sc-number 0) ... (sc-number 10)
    m += [S.sc_number(number) for number in range(11)]

    @m.rules
    def parity(x, step):
        """One is odd, and anything two above an odd number is odd."""
        # (= (sc-odd? 1) True)
        yield equation(ODD(1)).to(TRUE)
        # (= (sc-odd? $x)
        #    (let $n (match (context-space) (sc-number $x) $x) (sc-odd? (- $n 2))))
        yield equation(ODD(x)).to(
            S.let(step, S.match(S.context_space(), S.sc_number(x), x), ODD(step - 2))  # rung: a rules body EXECUTES, so a stored `let` over a stored `match` is built by naming both heads (P14.4)
        )

    @m.define
    def sc_even_number():
        """One answer per number nothing proves odd."""
        y = match(S.sc_number(V.y), V.y)
        return y if S.not_provable(S["sc-odd?"](y)) else superpose()

    @m.define
    def sc_evens():
        """(= (sc-evens) (collapse ...))."""
        return S.collapse(sc_even_number())  # rung: the same `collapse` (P14.4)

    # !(test (sc-evens) (0 2 4 6 8 10))
    assert sc_evens() == [Expression((0, 2, 4, 6, 8, 10))]


def colour_counts(m):
    """A count per colour, through the general fold rather than a counter."""
    # (sc-object-color 0 "blue") (sc-object-color 1 "green") (sc-object-color 2 "blue")
    m += [S.sc_object_color(obj, colour) for obj, colour in COLOURS]

    @m.define
    def sc_one_color(colour):
        """(= (sc-one-color $c) (let $o (match ...) 1)): one answer per object."""
        _object = match(S.sc_object_color(V.o, colour), V.o)
        return 1

    @m.define
    def sc_color_count(colour):
        """(= (sc-color-count $c) (foldall + (sc-one-color $c) 0))."""
        return S.foldall(S.add, sc_one_color(colour), 0)

    @m.define
    def sc_color_pair():
        """One (colour count) pair per colour; the example inlines this binding."""
        colour = superpose("blue", "green")
        return (colour, sc_color_count(colour))

    @m.define
    def sc_color_counts():
        """(= (sc-color-counts) (collapse ...))."""
        return S.collapse(sc_color_pair())  # rung: the same `collapse` (P14.4)

    # !(test (sc-color-counts) (("blue" 2) ("green" 1)))
    assert sc_color_counts() == [Expression(((G("blue"), 2), (G("green"), 1)))]


def class_tops(m):
    """An argmax per class, through an open reducer rather than a closed list."""
    # (sc-class-student-grade 0 "tom" 50), and five more
    m += [
        S.sc_class_student_grade(klass, student, grade)
        for klass, student, grade in GRADES
    ]

    @m.define
    def sc_pick_max(left, right):
        """(= (sc-pick-max $a $b) (if (> $a $b) $a $b))."""
        return left if left > right else right  # noqa: FURB136  -- max(right, left) compiles to (max $b $a), a different equation from the example's

    @m.define
    def sc_class_max(klass):
        """(= (sc-class-max $c) (foldall sc-pick-max (match ...) -1))."""
        return S.foldall(
            S.sc_pick_max,
            match(S.sc_class_student_grade(klass, V._, V.g), V.g),
            -1,
        )

    @m.define
    def sc_class_pair():
        """One (class student) pair per class; the example inlines these bindings."""
        klass = superpose(0, 1)
        top = sc_class_max(klass)
        return (klass, match(S.sc_class_student_grade(klass, V.s, top), V.s))

    @m.define
    def sc_class_top():
        """(= (sc-class-top) (collapse ...))."""
        return S.collapse(sc_class_pair())  # rung: the same `collapse` (P14.4)

    # !(test (sc-class-top) ((0 "jerry") (1 "sherry")))
    assert sc_class_top() == [Expression(((0, G("jerry")), (1, G("sherry"))))]


def animal_count(m):
    """The animal count as a SET: four raw derivations become Scallop's two."""
    # (sc-is-a giraffe mammal) ... (sc-name 2 tiger)
    m += [S.sc_is_a(kind, parent) for kind, parent in KINDS]
    m += [S.sc_name(obj, kind) for obj, kind in NAMES]

    @m.define
    def sc_parent_kind(kind):
        """(= (sc-parent-kind $x) (match (context-space) (sc-is-a $x $y) $y))."""
        return match(S.sc_is_a(kind, V.y), V.y)

    @m.define
    def sc_ancestor_kind(kind):
        """(= (sc-ancestor-kind $x) (sc-parent-kind $x)), and the recursion."""
        yield sc_parent_kind(kind)
        yield sc_ancestor_kind(sc_parent_kind(kind))

    @m.define
    def sc_animal_object():
        """Every named object whose kind reaches `animal`."""
        named = match(S.sc_name(V.o, V.kind), (V.o, V.kind))
        ancestor = sc_ancestor_kind(named[1])
        return named[0] if ancestor == S.animal else superpose()

    @m.define
    def sc_one_animal():
        """(= (sc-one-animal) (let $o (unique (sc-animal-object)) 1))."""
        _object = fn.unique(sc_animal_object())
        return 1

    @m.define
    def sc_animal_count():
        """(= (sc-animal-count) (foldall + (sc-one-animal) 0))."""
        return S.foldall(S.add, sc_one_animal(), 0)

    # !(test (sc-animal-count) 2)
    assert sc_animal_count() == [2]


def twin(m):
    """Five README programs, and the five answers Scallop prints for them."""
    paths(m)
    evens(m)
    colour_counts(m)
    class_tops(m)
    animal_count(m)


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 129083 to 129626, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 129626 to 129381, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 129381 to 129321, on the release tree:
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
#: RE-PINNED 2026-08-25, 129321 to 129267, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 129267 to 132823 (+3556), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 132823 to 132703 (-120), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 132703 to 132575 (-128), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-09-01, 132575 to 83537 (-49038), one corpus pricing pass on
#: the merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 83537
