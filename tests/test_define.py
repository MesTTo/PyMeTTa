"""Purpose: the Python-to-MeTTa compiler: lowerings run against the engine,
refusals name construct and line, and the Python twin agrees with the
equations on ground inputs, property-fuzzed.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import CompileError, S, expr

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402


@pytest.fixture()
def m(metta):
    return metta.fresh_space()


def test_recursion_compiles_and_runs(m):
    @m.define
    def dfact(n):
        if n == 0:
            return 1
        return n * dfact(n - 1)

    assert m.run("!(dfact 5)") == [[120]]
    assert dfact.py(5) == 120
    assert dfact(5) == expr(S.dfact, 5)  # calling the name builds the term
    assert "(= (dfact $n)" in dfact.source()


def test_early_return_reads_as_else(m):
    @m.define
    def dsign(x):
        if x < 0:
            return -1
        if x == 0:
            return 0
        return 1

    for value, expected in [(-3, -1), (0, 0), (9, 1)]:
        assert m.run(f"!(dsign {value})") == [[expected]]


def test_bindings_become_let_star(m):
    @m.define
    def dhyp(a, b):
        aa = a * a
        bb = b * b
        return sqrt_math(aa + bb)  # noqa: F821  engine function

    assert m.run("!(dhyp 3 4)") == [[5.0]]
    assert dhyp.py.__name__ == "dhyp"


def test_true_division_matches_python_exactly(m):
    @m.define
    def dratio(a, b):
        return a / b

    assert m.run("!(dratio 7 2)") == [[3.5]]
    assert m.run("!(dratio 6 2)") == [[3.0]]  # Python answers 3.0, never 3


def test_generator_is_superposition(m):
    @m.define
    def dchoices(n):
        yield n
        yield n + 1
        yield n * 10

    assert m.run("!(collapse (dchoices 5))") == [[expr(5, 6, 50)]]


def test_generator_with_branches(m):
    @m.define
    def dbranch(n):
        if n > 0:
            yield Pos  # noqa: F821  constructor convention
        else:
            yield Neg  # noqa: F821
        yield Always  # noqa: F821

    assert m.run("!(collapse (dbranch 3))") == [[expr(S.Pos, S.Always)]]
    assert m.run("!(collapse (dbranch -3))") == [[expr(S.Neg, S.Always)]]


def test_lambda_is_first_class(m):
    @m.define
    def dapply_twice(x):
        f = lambda v: v + 10  # noqa: E731
        return f(f(x))

    assert m.run("!(dapply_twice 1)") == [[21]]


def test_comprehension_is_map_atom(m):
    @m.define
    def dtens(xs):
        return [x * 10 for x in xs]

    assert m.run("!(dtens (1 2 3))") == [[expr(10, 20, 30)]]


def test_filtered_comprehension_composes_filter_atom(m):
    @m.define
    def dbig(xs):
        return [x for x in xs if x > 2]

    assert m.run("!(dbig (1 2 3 4))") == [[expr(3, 4)]]


def test_match_in_body_binds_pattern_variables(m):
    m.add(S.parent(S.Tom, S.Bob), S.parent(S.Bob, S.Ann))

    @m.define
    def dgrand(gp):
        return match(parent(gp, mid), match(parent(mid, gc), gc))  # noqa: F821

    assert m.run("!(dgrand Tom)") == [[S.Ann]]


def test_short_circuit_and_or(m):
    @m.define
    def dsafe(n):
        return n != 0 and 100 / n > 10  # RHS must not run for 0

    assert m.run("!(dsafe 0)") == [[False]]
    assert m.run("!(dsafe 5)") == [[True]]
    assert dsafe.py(0) is False


def test_constructor_convention_capitalized_names(m):
    @m.define
    def dtag(x):
        return Result(x, Done)  # noqa: F821

    assert m.run("!(dtag 7)") == [[expr(S.Result, 7, S.Done)]]


@pytest.mark.parametrize(
    ("source", "needle"),
    [
        ("def f(x):\n    while x > 0:\n        x = x - 1\n    return x", "recursion"),
        ("def f(x):\n    y = x @ x\n    return y", "matmul"),
        ("def f(x):\n    return {1: x}", "dict"),
        ("def f(x):\n    return f'{x}!'", "f-string"),
        ("def f(x):\n    return unknown_lowercase(x)", "not a parameter"),
        ("def f(x, y=[]):\n    return x", "literal"),
    ],
)
def test_refusals_name_construct_and_line(m, source, needle):
    namespace = {}
    exec(source, namespace)  # noqa: S102  building the test subject
    fn = namespace["f"]
    fn.__source_override = source
    import petta.define as define_module

    with pytest.raises(CompileError) as excinfo:
        # inspect.getsource cannot see exec'd code; compile the AST path the
        # decorator uses by round-tripping through a real file.
        import textwrap, tempfile, importlib.util, pathlib, sys  # noqa: E401

        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "snippet.py"
            p.write_text(textwrap.dedent(source))
            spec = importlib.util.spec_from_file_location("snippet", p)
            module = importlib.util.module_from_spec(spec)
            sys.modules["snippet"] = module
            try:
                spec.loader.exec_module(module)
                m.define(module.f)
            finally:
                sys.modules.pop("snippet", None)
    message = str(excinfo.value)
    assert needle in message
    assert "line" in message


@given(st.integers(min_value=0, max_value=12))
@settings(max_examples=25, deadline=None)
def test_twin_agrees_on_ground_inputs(metta, n):
    """The differential the design promises: equations against the twin."""
    if not hasattr(test_twin_agrees_on_ground_inputs, "_defined"):

        @metta.define
        def dtwin(k):
            if k == 0:
                return 1
            return k * dtwin(k - 1)

        test_twin_agrees_on_ground_inputs._defined = dtwin
    dtwin = test_twin_agrees_on_ground_inputs._defined
    (engine_answer,) = metta.eval(dtwin(n))
    assert engine_answer == dtwin.py(n)


def test_modulo_matches_python_on_signs(metta):
    @metta.define
    def dmod(a, b):
        return a % b

    for a, b in [(-7, 3), (5, -2), (7, 3), (-5, -2)]:
        (engine_answer,) = metta.eval(dmod(a, b))
        assert engine_answer == dmod.py(a, b) == a % b


def test_literal_defaults_are_head_patterns_and_clauses_stack(m):
    """def fib(n=0) is the equation matching 0; definition order is clause
    order; the engine dispatches between the stacked clauses."""

    @m.define
    def dfib(n=0):
        return 0

    @m.define
    def dfib(n=1):  # noqa: F811  stacking is the point
        return 1

    @m.define
    def dfib(n):  # noqa: F811
        return dfib(n - 1) + dfib(n - 2)

    assert m.run("!(dfib 0)") == [[0]]
    assert m.run("!(dfib 1)") == [[1]]
    assert m.run("!(dfib 10)") == [[55]]

    # A literal clause's twin guards its own head; dispatch is the engine's.
    @m.define
    def donly(n=5):
        return 99

    assert donly.py(5) == 99
    assert "(= (donly 5) 99)" == donly.source()
    with pytest.raises(LookupError):
        donly.py(4)


def test_annotations_declare_types_for_defines(m):
    @m.define
    def dtyped(x: int) -> int:
        return x + 1

    assert m.run("!(get-type (dtyped 1))") == [[S.Number]]


def test_engine_functions_feel_like_python(m):
    m.run("(= (dtriple $x) (* $x 3))")
    triple = m.fn("dtriple")
    assert triple(14) == 42
    assert m.fn("superpose").all(expr(1, 2)) == [1, 2]
    with pytest.raises(ValueError):
        m.fn("superpose")(expr(1, 2))  # two answers is not one
