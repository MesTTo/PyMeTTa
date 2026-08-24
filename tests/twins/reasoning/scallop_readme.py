"""Purpose: examples/reasoning/scallop_readme.metta in Python: the five Scallop README programs.

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

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
BUDGET = 1


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
    for number in range(11):
        m += S.sc_number(number)

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
    for obj, colour in COLOURS:
        m += S.sc_object_color(obj, colour)

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
    for klass, student, grade in GRADES:
        m += S.sc_class_student_grade(klass, student, grade)

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
    for kind, parent in KINDS:
        m += S.sc_is_a(kind, parent)
    for obj, kind in NAMES:
        m += S.sc_name(obj, kind)

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
