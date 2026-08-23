"""Purpose: differential program fuzzing for @m.define, the CSmith recipe on
this compiler: generate random programs INSIDE the compiled subset by
construction, run each program's equations on the engine and its Python twin
on the same ground inputs, and require identical answers. The reassignment
bug this suite was built after (x = x + 1 lowering to a let* that unified a
variable with its own successor, so the engine answered nothing while the
twin answered the value) is exactly the class only this kind of test
catches: every program compiles cleanly, so refusal tests see nothing, and
hand-written examples exercise the spellings their author thought of.
Guarantees:
  - every generated program compiles, so a red run is a lowering defect and
    not a refusal [tested test_engine_and_twin_agree, test_nested_loops_agree]
  - a loop whose body holds another loop is generated, in both the `for` and
    the `while` spelling [tested test_the_fuzzer_reaches_a_loop_inside_a_loop]
  - that shape catches a continuation resolving a loop's remaining sequence
    in the wrong equation [measured 2026-08-18: with _define_loops.py reverted
    to 9190bbd^, test_nested_loops_agree fails in 5 of 5 seeded runs and
    test_engine_and_twin_agree in 4 of 5, where this file's own previous
    version passed 5 of 5 against the same broken compiler]
  - MAX_LOOP_NEST's depth cap keeps loop_block's recursion bounded rather
    than runaway [measured 2026-08-18: recursion the only variable held
    constant, the shared test_engine_and_twin_agree (60 examples) moved from
    a 0.48s to a 0.71s min-of-3; the file's own min-of-3 moved from 0.77s (3
    tests, no loop nesting reachable) to 1.28s (these 5 tests)]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import ast
import itertools

import pytest
from hypothesis import HealthCheck, Phase, find, given, settings
from hypothesis import strategies as st

from metta.atoms import Expression, Grounded

_COUNTER = itertools.count()


def _tuple_literal(draw, lowest: int, highest: int) -> str:
    """A Python tuple literal of small ints; the one-element spelling needs
    its trailing comma, or (5) is just 5.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    values = [
        str(draw(st.integers(-5, 5)))
        for _ in range(draw(st.integers(lowest, highest)))
    ]
    if len(values) == 1:
        return f"({values[0]},)"
    return "(" + ", ".join(values) + ")"


def _load(tmp_path_factory, source: str, name: str):
    """A real function object whose source inspect.getsource can read: the
    compiler reads syntax from the file, so each program becomes one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    path = tmp_path_factory.mktemp("fuzz") / f"{name}.py"
    path.write_text(source)
    namespace: dict = {}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace[name]


def _normalize(value):
    """Engine answers and twin answers into one comparable shape."""
    if isinstance(value, Grounded):
        return _normalize(value.value)
    if isinstance(value, Expression):
        return tuple(_normalize(c) for c in value)
    if isinstance(value, (list, tuple)):
        return tuple(_normalize(v) for v in value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return value


# ------------------------------------------------------- program generation
#
# Programs are built as source text, by construction inside the subset:
# integer expressions over the parameters and bound names, boolean tests,
# assignments with deliberate REBINDING, augmented assignment, if/else with
# early returns, and chained comparisons. Divisors are nonzero literals.


@st.composite
def int_expr(draw, names: tuple, depth: int = 0):  # noqa: C901, D103  -- int_expr keeps the recursive expression generator together so its branches share one state; pytest discovers or injects this callable; its descriptive name states the contract
    if depth >= 3 or draw(st.booleans()):
        leaf = draw(st.sampled_from(("name", "lit")))
        if leaf == "name" and names:
            return draw(st.sampled_from(names))
        return str(draw(st.integers(-9, 9)))
    kind = draw(
        st.sampled_from(
            ("add", "sub", "mul", "mod", "neg", "min", "max", "abs",
             "ifexp", "or", "and", "truthytest")
        )
    )
    a = draw(int_expr(names, depth + 1))
    if kind == "neg":
        return f"(-{a})"
    if kind == "abs":
        return f"abs({a})"
    b = draw(int_expr(names, depth + 1))
    if kind == "add":
        return f"({a} + {b})"
    if kind == "sub":
        return f"({a} - {b})"
    if kind == "mul":
        return f"({a} * {b})"
    if kind == "mod":
        divisor = draw(st.sampled_from((-3, -2, -1, 1, 2, 3)))
        return f"({a} % {divisor})"
    if kind in ("min", "max"):
        return f"{kind}({a}, {b})"
    if kind in ("or", "and"):
        # Python answers the deciding OPERAND, an int here, not a boolean.
        return f"({a} {kind} {b})"
    if kind == "truthytest":
        # A bare int as the test: truthiness, zero the only falsehood.
        return f"({a} if {b} else {draw(int_expr(names, depth + 1))})"
    test = draw(bool_expr(names, depth + 1))
    return f"({a} if {test} else {b})"


@st.composite
def bool_expr(draw, names: tuple, depth: int = 0):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    kind = draw(st.sampled_from(("cmp", "chain", "and", "or", "not")))
    if depth >= 2:
        kind = "cmp"
    if kind == "cmp":
        op = draw(st.sampled_from(("<", "<=", ">", ">=", "==", "!=")))
        left = draw(int_expr(names, depth + 1))
        right = draw(int_expr(names, depth + 1))
        if op in ("==", "!=") and draw(st.integers(0, 3)) == 0:
            # Mixed numeric equality: Python says 4 == 4.0; so must the
            # compiled form, through py-eq. The operand is a fresh SMALL
            # literal rather than an arbitrary expression, because the two
            # executors genuinely part company past binary64: the engine's
            # division saturates to the IEEE infinity while plain Python
            # raises OverflowError converting the huge int, so an unbounded
            # operand made the twin die on its own arithmetic instead of
            # reporting a disagreement (Hypothesis found it, 8/8
            # reproductions; the boundary itself is pinned two-sidedly in
            # test_the_define_twin_survives_integer_division_past_the_float_range).
            # Small literals exercise the py-eq mixed-equality path fully.
            right = f"({draw(st.integers(-9, 9))} / 1)"
        return f"({left} {op} {right})"
    if kind == "chain":
        op1, op2 = draw(st.sampled_from(("<", "<="))), draw(st.sampled_from(("<", "<=")))
        parts = [draw(int_expr(names, depth + 1)) for _ in range(3)]
        return f"({parts[0]} {op1} {parts[1]} {op2} {parts[2]})"
    if kind == "not":
        return f"(not {draw(bool_expr(names, depth + 1))})"
    joiner = " and " if kind == "and" else " or "
    return "(" + joiner.join(
        draw(bool_expr(names, depth + 1)) for _ in range(2)
    ) + ")"


@st.composite
def assignments(draw, scope: list, indent: str, count: int, protected: tuple = ()):
    """Count assignment lines over (and into) scope; rebinding weighted up
    because it is the bug class this suite exists for. protected names stay
    readable but never assigned: clobbering a loop counter would generate a
    genuinely nonterminating program, in Python exactly as compiled.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    lines: list[str] = []
    assignable = [n for n in scope if n not in protected]
    for _ in range(count):
        rebind = assignable and draw(st.integers(0, 2)) > 0
        if rebind:
            target = draw(st.sampled_from(tuple(assignable)))
            if draw(st.booleans()):
                op = draw(st.sampled_from(("+=", "-=", "*=")))
                lines.append(f"{indent}{target} {op} {draw(int_expr(tuple(scope)))}")
                continue
        else:
            target = draw(st.sampled_from(("c", "d", "e")))
        lines.append(f"{indent}{target} = {draw(int_expr(tuple(scope)))}")
        if target not in scope:
            scope.append(target)
            assignable.append(target)
    return lines


# The deepest loop nest generated here. programs() stops one short of it;
# nested_loop_programs spends the whole budget, since three levels is where
# two enclosing loops each have a remaining sequence to carry into the
# innermost equation.
MAX_LOOP_NEST = 3


@st.composite
def loop_nest(draw, minimum: int = 1, maximum: int = MAX_LOOP_NEST - 1):
    """The kinds of one loop nest, outermost first."""
    return tuple(
        draw(st.sampled_from(("while", "for")))
        for _ in range(draw(st.integers(minimum, maximum)))
    )


@st.composite
def loop_block(draw, scope: list, indent: str, nest: tuple, protected: tuple = ()):
    """A terminating loop: a bounded while over a fresh counter, or a for
    over a literal tuple, each mutating accumulators from the scope.

    `nest` holds the kinds still to place, outermost first, and every loop
    but the last one holds the next in its body. Recursing on nest[1:]
    bounds the depth by the tuple's length rather than by a coin, and the
    tuple comes from loop_nest, which draws at most MAX_LOOP_NEST kinds.

    A loop that holds another runs at least once, or the nested shape is
    generated and never executed. That shape is the one a fixed
    continuation variable got wrong: a nested construct compiles into its
    own equation with a fresh variable namespace, so the outer loop's
    remaining sequence resolved there to the INNER loop's tail and the
    outer loop resumed on the wrong list [source
    bindings/python/metta/_define_loops.py:116-123].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    kind, deeper = nest[0], nest[1:]
    counter = draw(st.sampled_from(("i", "j", "k")))
    while counter in scope:
        counter += "x"
    lines: list[str] = []
    inner = indent + "    "
    if kind == "while":
        bound = draw(st.integers(1, 3)) if deeper else draw(st.integers(0, 4))
        lines.append(f"{indent}{counter} = 0")
        scope.append(counter)
        lines.append(f"{indent}while {counter} < {bound}:")
        # A name FIRST bound inside the body may be unbound after a loop
        # that never ran (Python's UnboundLocalError; the compiler's named
        # refusal), so only body-local or pre-bound names appear, and body
        # additions do not escape into the outer scope.
        body_scope = list(scope)
        # Clobbering any enclosing counter, not just this loop's own, would
        # generate a genuinely nonterminating program.
        body_protected = (*protected, counter)
    else:
        source = _tuple_literal(draw, 1, 3) if deeper else _tuple_literal(draw, 0, 4)
        lines.append(f"{indent}for {counter} in {source}:")
        body_scope = [*list(scope), counter]
        # Neither the loop variable nor a body-first binding survives the
        # loop: reading either after it is refused (or unbound in Python).
        # The target itself stays assignable, since the next round rebinds it.
        body_protected = protected
    lines.extend(
        draw(assignments(body_scope, inner, draw(st.integers(1, 2)), body_protected))
    )
    if deeper:
        lines.extend(draw(loop_block(body_scope, inner, deeper, body_protected)))
        lines.extend(
            draw(assignments(body_scope, inner, draw(st.integers(0, 2)), body_protected))
        )
    if draw(st.integers(0, 3)) == 0:
        lines.append(f"{inner}if {draw(bool_expr(tuple(body_scope), 1))}:")
        lines.append(f"{inner}    return {draw(int_expr(tuple(body_scope)))}")
    if kind == "while":
        lines.append(f"{inner}{counter} += 1")
    return lines


@st.composite
def statements(draw, names: tuple, indent: str, depth: int = 0):
    """A statement block ending in a return on every path."""
    lines: list[str] = []
    scope = list(names)
    lines.extend(draw(assignments(scope, indent, draw(st.integers(0, 3)))))
    if draw(st.integers(0, 2)) == 0:
        lines.extend(draw(loop_block(scope, indent, draw(loop_nest()))))
    if depth < 2 and draw(st.integers(0, 2)) == 0:
        test = draw(bool_expr(tuple(scope)))
        then = draw(statements(tuple(scope), indent + "    ", depth + 1))
        lines.append(f"{indent}if {test}:")
        lines.extend(then)
        if draw(st.booleans()):
            otherwise = draw(statements(tuple(scope), indent + "    ", depth + 1))
            lines.append(f"{indent}else:")
            lines.extend(otherwise)
        else:
            lines.extend(draw(statements(tuple(scope), indent, depth + 1)))
        return lines
    lines.append(f"{indent}return {draw(int_expr(tuple(scope)))}")
    return lines


@st.composite
def programs(draw):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = f"fz{next(_COUNTER)}"
    body = draw(statements(("a", "b"), "    "))
    return name, f"def {name}(a, b):\n" + "\n".join(body) + "\n"


@st.composite
def nested_loop_programs(draw):
    """Programs whose loop body holds another loop, every example.

    programs() reaches this shape too, in 35.6% of 2000 generated programs
    [measured 2026-08-18], which leaves the class to chance at a budget of
    60. It deserves its own budget because it is silent everywhere else:
    the program compiles clean, and the engine then resumes the outer loop
    on the wrong remaining sequence, so it answers nothing (or something
    else) while the twin answers the value.
    """
    name = f"fz{next(_COUNTER)}"
    scope = ["a", "b"]
    lines = draw(assignments(scope, "    ", draw(st.integers(0, 2))))
    nest = draw(loop_nest(minimum=2, maximum=MAX_LOOP_NEST))
    lines.extend(draw(loop_block(scope, "    ", nest)))
    lines.append(f"    return {draw(int_expr(tuple(scope)))}")
    return name, f"def {name}(a, b):\n" + "\n".join(lines) + "\n"


def _nested_loop_kinds(source: str) -> set[str]:
    """The kinds of every loop whose body holds another loop, so the empty
    set means the program has no loop inside a loop at all.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    kinds = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.For, ast.While)) and any(
            isinstance(sub, (ast.For, ast.While))
            for statement in node.body
            for sub in ast.walk(statement)
        ):
            kinds.add("for" if isinstance(node, ast.For) else "while")
    return kinds


@st.composite
def generator_programs(draw):
    """Generator bodies: yields, if-guarded yields, for over a literal tuple,
    and yield from a literal tuple; answers are ordered, so order is part of
    the property.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = f"fz{next(_COUNTER)}"
    names = ("a", "b")
    lines: list[str] = []
    for _ in range(draw(st.integers(1, 4))):
        kind = draw(st.sampled_from(("yield", "ifyield", "for", "from")))
        if kind == "yield":
            lines.append(f"    yield {draw(int_expr(names))}")
        elif kind == "ifyield":
            lines.append(f"    if {draw(bool_expr(names))}:")
            lines.append(f"        yield {draw(int_expr(names))}")
        elif kind == "for":
            lines.append(f"    for x in {_tuple_literal(draw, 1, 4)}:")
            lines.append(f"        yield {draw(int_expr(('a', 'b', 'x')))}")
        else:
            lines.append(f"    yield from {_tuple_literal(draw, 1, 3)}")
    return name, f"def {name}(a, b):\n" + "\n".join(lines) + "\n"


@st.composite
def collection_programs(draw):
    """Programs over one tuple parameter: the builtin bridge and indexing."""
    name = f"fz{next(_COUNTER)}"
    reducers = {
        "len": "len(xs)",
        "sum": "sum(xs)",
        "min": "min(xs)",
        "max": "max(xs)",
        "first-sorted": "sorted(xs)[0]",
        "index": f"xs[{draw(st.integers(-4, 3))}]",
        "comprehension": "sum([x * x for x in xs if x > 0])",
        "pairs": "len([(x, y) for x in xs for y in xs if x < y])",
        "member": "(1 if 3 in xs else 0)",
        "slice": f"sum(xs[{draw(st.integers(-3, 2))}:{draw(st.integers(-2, 4))}])",
        "range": "sum(range(len(xs)))",
        "fstring": "len(f'{xs[0]}:{xs[1]:04d}')",
        "text": "len(str(sorted(xs)))",
    }
    picked = [draw(st.sampled_from(sorted(reducers))) for _ in range(2)]
    expression = " + ".join(reducers[p] for p in picked)
    return name, f"def {name}(xs):\n    return {expression}\n"


def _answers_agree(metta, tmp_path_factory, program, data, rounds: int) -> None:
    """The differential itself: one two-parameter program, its equations on
    the engine and its Python twin on the same ground inputs, `rounds` fresh
    pairs of them, and the two answer lists required identical.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name, source = program
    fn = _load(tmp_path_factory, source, name)
    defined = metta.define(fn)
    for _ in range(rounds):
        a = data.draw(st.integers(-9, 9))
        b = data.draw(st.integers(-9, 9))
        engine = defined(a, b)
        twin = defined.py(a, b)
        assert [_normalize(e) for e in engine] == [_normalize(twin)], source


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=programs(), data=st.data())
def test_engine_and_twin_agree(metta, tmp_path_factory, program, data):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _answers_agree(metta, tmp_path_factory, program, data, rounds=3)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=nested_loop_programs(), data=st.data())
def test_nested_loops_agree(metta, tmp_path_factory, program, data):
    """A loop inside a loop, every example. Each loop compiles to its own
    equation, so the continuation the outer loop hands its body is closed
    over in the inner loop's namespace; anything it holds as a fixed
    variable instead of resolving through the scope means the outer loop
    resumes on the inner loop's state. Two rounds rather than three: a
    nested program costs more to run and the shape is what matters here.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    _answers_agree(metta, tmp_path_factory, program, data, rounds=2)


def test_the_fuzzer_reaches_a_loop_inside_a_loop():
    """The shape this suite exists to reach, asserted rather than hoped for.
    loop_block once took no depth and never recursed, so no generated
    program held a loop inside a loop and the differential above proved
    nothing about that class.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    # Generate only: find would otherwise shrink each witness to its minimal
    # form, which answers a question nobody asked and cost 13.12s of the
    # suite's 14.55s [measured 2026-08-18].
    reachable = settings(max_examples=200, deadline=None, phases=[Phase.generate])
    for kind in ("for", "while"):
        find(
            nested_loop_programs(),
            lambda program, kind=kind: kind in _nested_loop_kinds(program[1]),
            settings=reachable,
        )


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=generator_programs(), data=st.data())
def test_generator_answers_match_in_order(metta, tmp_path_factory, program, data):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, source = program
    fn = _load(tmp_path_factory, source, name)
    defined = metta.define(fn)
    a = data.draw(st.integers(-9, 9))
    b = data.draw(st.integers(-9, 9))
    engine = defined(a, b)
    twin = list(defined.py(a, b))
    assert [_normalize(e) for e in engine] == [_normalize(v) for v in twin], source


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=collection_programs(), data=st.data())
def test_collection_bridge_agrees(metta, tmp_path_factory, program, data):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, source = program
    fn = _load(tmp_path_factory, source, name)
    defined = metta.define(fn)
    xs = tuple(data.draw(st.integers(-9, 9)) for _ in range(4))
    engine = defined(xs)
    try:
        twin = defined.py(xs)
    except IndexError:
        # A negative-or-large literal index off this tuple: the twin raises,
        # and the engine must answer nothing rather than something.
        assert engine == [], source
        return
    assert [_normalize(e) for e in engine] == [_normalize(twin)], source


def test_the_define_twin_survives_integer_division_past_the_float_range(
    metta, tmp_path_factory
):
    """The committed Hypothesis example: huge int meets /, both sides pinned.

    The generator once grew a value past binary64 and divided it by 1 for
    the mixed-equality probe; the engine saturates that division to the
    IEEE infinity (the numeric-boundary rule its own suite pins) while
    plain Python raises OverflowError converting the huge int, so the
    differential died on the twin's arithmetic instead of reporting a
    disagreement. The boundary is genuinely twin-inexpressible: every
    int-to-float conversion on such a value raises in Python. This pins
    BOTH true behaviors, the way the tuple-index case above pins its
    raise, and the generator now keeps its mixed-equality operand small.
    """
    source = (
        "def grown_mix(a, b):\n"
        "    acc = 10 + abs(a)\n"
        "    for _ in range(200):\n"
        "        acc = acc * 1000\n"
        "    return a if (b == (acc / 1)) else b\n"
    )
    fn = _load(tmp_path_factory, source, "grown_mix")
    defined = metta.define(fn)
    engine = defined(3, 4)
    assert [_normalize(e) for e in engine] == [4], (
        "the engine saturates acc / 1 to inf, 4 == inf is False, so the "
        "else branch answers"
    )
    with pytest.raises(OverflowError):
        fn(3, 4)
