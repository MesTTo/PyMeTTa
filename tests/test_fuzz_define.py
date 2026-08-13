"""Purpose: differential program fuzzing for @m.define, the CSmith recipe on
this compiler: generate random programs INSIDE the compiled subset by
construction, run each program's equations on the engine and its Python twin
on the same ground inputs, and require identical answers. The reassignment
bug this suite was built after (x = x + 1 lowering to a let* that unified a
variable with its own successor, so the engine answered nothing while the
twin answered the value) is exactly the class only this kind of test
catches: every program compiles cleanly, so refusal tests see nothing, and
hand-written examples exercise the spellings their author thought of.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import itertools

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from petta.atoms import Expr, Gnd

_COUNTER = itertools.count()


def _load(tmp_path_factory, source: str, name: str):
    """A real function object whose source inspect.getsource can read: the
    compiler reads syntax from the file, so each program becomes one."""
    path = tmp_path_factory.mktemp("fuzz") / f"{name}.py"
    path.write_text(source)
    namespace: dict = {}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace[name]


def _normalize(value):
    """Engine answers and twin answers into one comparable shape."""
    if isinstance(value, Gnd):
        return _normalize(value.value)
    if isinstance(value, Expr):
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
def int_expr(draw, names: tuple, depth: int = 0):
    if depth >= 3 or draw(st.booleans()):
        leaf = draw(st.sampled_from(("name", "lit")))
        if leaf == "name" and names:
            return draw(st.sampled_from(names))
        return str(draw(st.integers(-9, 9)))
    kind = draw(
        st.sampled_from(
            ("add", "sub", "mul", "mod", "neg", "min", "max", "abs", "ifexp")
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
    test = draw(bool_expr(names, depth + 1))
    return f"({a} if {test} else {b})"


@st.composite
def bool_expr(draw, names: tuple, depth: int = 0):
    kind = draw(st.sampled_from(("cmp", "chain", "and", "or", "not")))
    if depth >= 2:
        kind = "cmp"
    if kind == "cmp":
        op = draw(st.sampled_from(("<", "<=", ">", ">=", "==", "!=")))
        return f"({draw(int_expr(names, depth + 1))} {op} {draw(int_expr(names, depth + 1))})"
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
def statements(draw, names: tuple, indent: str, depth: int = 0):
    """A statement block ending in a return on every path; rebinding is
    weighted up because it is the bug class this suite exists for."""
    lines: list[str] = []
    scope = list(names)
    for _ in range(draw(st.integers(0, 3))):
        rebind = scope and draw(st.integers(0, 2)) > 0
        if rebind:
            target = draw(st.sampled_from(scope))
            if draw(st.booleans()):
                op = draw(st.sampled_from(("+=", "-=", "*=")))
                lines.append(f"{indent}{target} {op} {draw(int_expr(tuple(scope)))}")
                continue
        else:
            target = draw(st.sampled_from(("c", "d", "e")))
        lines.append(f"{indent}{target} = {draw(int_expr(tuple(scope)))}")
        if target not in scope:
            scope.append(target)
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
def programs(draw):
    name = f"fz{next(_COUNTER)}"
    body = draw(statements(("a", "b"), "    "))
    return name, f"def {name}(a, b):\n" + "\n".join(body) + "\n"


@st.composite
def generator_programs(draw):
    """Generator bodies: yields, if-guarded yields, for over a literal tuple,
    and yield from a literal tuple; answers are ordered, so order is part of
    the property."""
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
            elements = ", ".join(
                str(draw(st.integers(-5, 5))) for _ in range(draw(st.integers(2, 4)))
            )
            lines.append(f"    for x in ({elements}):")
            lines.append(f"        yield {draw(int_expr(('a', 'b', 'x')))}")
        else:
            elements = ", ".join(
                str(draw(st.integers(-5, 5))) for _ in range(draw(st.integers(2, 3)))
            )
            lines.append(f"    yield from ({elements})")
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
    }
    picked = [draw(st.sampled_from(sorted(reducers))) for _ in range(2)]
    expression = " + ".join(reducers[p] for p in picked)
    return name, f"def {name}(xs):\n    return {expression}\n"


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=programs(), data=st.data())
def test_engine_and_twin_agree(metta, tmp_path_factory, program, data):
    name, source = program
    fn = _load(tmp_path_factory, source, name)
    defined = metta.define(fn)
    for _ in range(3):
        a = data.draw(st.integers(-9, 9))
        b = data.draw(st.integers(-9, 9))
        engine = metta.eval(defined(a, b))
        twin = defined.py(a, b)
        assert [_normalize(e) for e in engine] == [_normalize(twin)], source


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=generator_programs(), data=st.data())
def test_generator_answers_match_in_order(metta, tmp_path_factory, program, data):
    name, source = program
    fn = _load(tmp_path_factory, source, name)
    defined = metta.define(fn)
    a = data.draw(st.integers(-9, 9))
    b = data.draw(st.integers(-9, 9))
    engine = metta.eval(defined(a, b))
    twin = list(defined.py(a, b))
    assert [_normalize(e) for e in engine] == [_normalize(v) for v in twin], source


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(program=collection_programs(), data=st.data())
def test_collection_bridge_agrees(metta, tmp_path_factory, program, data):
    name, source = program
    fn = _load(tmp_path_factory, source, name)
    defined = metta.define(fn)
    xs = tuple(data.draw(st.integers(-9, 9)) for _ in range(4))
    engine = metta.eval(defined(xs))
    try:
        twin = defined.py(xs)
    except IndexError:
        # A negative-or-large literal index off this tuple: the twin raises,
        # and the engine must answer nothing rather than something.
        assert engine == [], source
        return
    assert [_normalize(e) for e in engine] == [_normalize(twin)], source
