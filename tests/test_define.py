"""Purpose: the Python-to-MeTTa compiler: lowerings run against the engine,
refusals name construct and line, helper-bearing redefinitions replace as a
unit, and guarded Python twins agree with equations on ground inputs.
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

    # One naming policy across both decorators: underscores read as hyphens.
    assert m.run("!(dapply-twice 1)") == [[21]]


def test_underscore_rename_is_exposed_and_diagnosed(m):
    @m.define
    def add_one(value):
        return value + 1

    assert m.run("!(add-one 5)") == [[6]]
    assert m.run("!(add_one 5)") == [[S.add_one(5)]]
    explanation = m.why(S.add_one(5))
    assert "did you mean add-one?" in explanation
    assert "underscores as hyphens" in explanation


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
        ("def f(x):\n    while x > 0:\n        break\n    return x", "test"),
        ("def f(x):\n    y = x @ x\n    return y", "matmul"),
        ("def f(x):\n    return {1: x}", "dict"),
        ("def f(x, w):\n    return f'{x:{w}}'", "f-string"),
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


def test_while_becomes_a_tail_recursive_helper(m):
    @m.define
    def dgcd(a, b):
        while b != 0:
            t = b
            b = a % b
            a = t
        return a

    assert m.run("!(dgcd 48 36)") == [[12]]
    assert dgcd.py(48, 36) == 12
    # The helper is an ordinary equation, visible in the space.
    helpers = [x for x in m.atoms() if str(x).startswith("(= (dgcd--loop")]
    assert len(helpers) == 1


def test_nested_loops_carry_the_outer_state(m):
    @m.define
    def dtriangles(n):
        total = 0
        i = 0
        while i < n:
            j = 0
            while j < i:
                total += j
                j += 1
            i += 1
        return total

    assert m.run("!(dtriangles 5)") == [[10]]
    assert dtriangles.py(5) == 10


def test_for_peels_with_decons_and_early_return_searches(m):
    @m.define
    def dfind(xs, target):
        i = 0
        while i < len(xs):
            if xs[i] == target:
                return i
            i += 1
        return -1

    assert m.run("!(dfind (a b c) b)") == [[1]]
    assert m.run("!(dfind (a b c) z)") == [[-1]]

    @m.define
    def dpositive(xs):
        acc = 0
        for x in xs:
            if x > 0:
                acc += x
        return acc

    assert m.run("!(dpositive (3 -1 4 -1 5))") == [[12]]
    assert dpositive.py((3, -1, 4, -1, 5)) == 12


def test_nested_defs_lift_with_their_closure(m):
    @m.define
    def douter(x, y):
        def scaled(v):
            return v * 2 + y

        return scaled(x) + scaled(y)

    assert m.run("!(douter 3 4)") == [[22]]
    assert douter.py(3, 4) == 22


def test_loops_run_in_constant_stack(m):
    """Two million rounds through the compiled helper: last-call optimized,
    so the loop runs in constant stack, the mark of a real loop rather than
    recursion wearing one's clothes."""

    @m.define
    def dcountdown(n):
        while n > 0:
            n -= 1
        return n

    assert m.run("!(dcountdown 2000000)") == [[0]]


def test_loop_variable_read_after_for_is_refused(m):
    with pytest.raises(CompileError) as excinfo:

        @m.define
        def dleak(xs):
            for x in xs:
                pass
            return x  # noqa: F821

    assert "after the loop" in str(excinfo.value) or "no MeTTa equivalent" in str(
        excinfo.value
    )


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
    from petta import EngineError

    with pytest.raises(EngineError):
        m.fn("superpose")(expr(1, 2))  # two answers is not one


def test_boolean_operators_answer_the_operand(m):
    """3 or 7 is 3, 0 or 7 is 7, 3 and 7 is 7: Python's own reading,
    truthiness deciding and the operand answering."""

    @m.define
    def dpick(a, b):
        return a or b

    @m.define
    def dboth(a, b):
        return a and b

    assert m.run("!(dpick 3 7)") == [[3]]
    assert m.run("!(dpick 0 7)") == [[7]]
    assert m.run("!(dboth 3 7)") == [[7]]
    assert m.run("!(dboth 0 7)") == [[0]]
    assert dpick.py(0, 7) == 7 and dboth.py(3, 7) == 7


def test_truthiness_decides_tests(m):
    """A bare value as the test reads by bool(), zero and empty the only
    falsehoods, exactly Python."""

    @m.define
    def dclassify(n):
        if n:
            return Some  # noqa: F821
        return Nothing  # noqa: F821

    assert m.run("!(dclassify 7)") == [[S.Some]]
    assert m.run("!(dclassify 0)") == [[S.Nothing]]
    # Constructors exist only in the engine; the twin says so.
    with pytest.raises(RuntimeError):
        dclassify.py(7)


def test_mixed_numeric_equality_and_membership(m):
    @m.define
    def dsame(a, b):
        return a == b / 1

    @m.define
    def dhas(x, xs):
        return x in xs

    assert m.run("!(dsame 4 4)") == [[True]]
    assert m.run("!(dhas 2 (1 2 3))") == [[True]]
    assert m.run("!(dhas 9 (1 2 3))") == [[False]]
    assert m.run('!(dhas "ell" "hello")') == [[True]]


def test_fstrings_str_round_range_slices(m):
    @m.define
    def dlabel(x):
        return f"v={x:03d}!"

    @m.define
    def dtext(x):
        return str(x)

    @m.define
    def dbank(x):
        return round(x)

    @m.define
    def dspan(n):
        return sum(range(n))

    @m.define
    def dcut(xs):
        return xs[1:-1]

    assert m.run("!(dlabel 7)") == [["v=007!"]]
    assert m.run("!(dtext 42)") == [["42"]]
    # Banker's rounding, not half-away: Python's own round.
    assert m.run("!(dbank 2.5)") == [[2]]
    assert m.run("!(dbank 3.5)") == [[4]]
    assert m.run("!(dspan 5)") == [[10]]
    assert m.run("!(dcut (a b c d))") == [[expr(S.b, S.c)]]
    assert dlabel.py(7) == "v=007!" and dcut.py(("a", "b", "c", "d")) == ("b", "c")
    assert "py-str-join" in dlabel.runtime_ops


def test_host_bindings_refuse_the_constructor_reading(m):
    with pytest.raises(CompileError) as caught:

        @m.define
        def dthreshold(x):
            return x + Threshold  # noqa: F821

    assert "module binding" in str(caught.value)


Threshold = 5


def test_twin_refuses_engine_only_bodies(m):
    m.add(expr(S.fact9, 9))

    @m.define
    def dseek():
        return match(fact9(v), v)  # noqa: F821

    assert m.run("!(dseek)") == [[9]]
    with pytest.raises(RuntimeError) as caught:
        dseek.py()
    assert "match against the space" in str(caught.value)


def test_same_head_redefinition_replaces(m):
    @m.define
    def dvalue():
        return 1

    assert m.run("!(dvalue)") == [[1]]

    @m.define
    def dvalue():
        return 2

    # The notebook reading: one head, the newest body, exactly one answer.
    assert m.run("!(collapse (dvalue))") == [[expr(2)]]
    assert dvalue.py() == 2


def test_helper_only_redefinition_replaces_main_and_aux_equations(m):
    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 1
            n -= 1
        return total

    assert m.value(daux_replace(3)) == 3

    @m.define
    def daux_replace(n):  # noqa: F811
        total = 0
        while n > 0:
            total += 2
            n -= 1
        return total

    assert m.value(daux_replace(3)) == 6
    assert daux_replace.py(3) == 6

    @m.define
    def daux_replace(n):  # noqa: F811
        total = 0
        while n > 0:
            total += 2
            n -= 1
        return total

    assert m.value(daux_replace(3)) == 6
    assert daux_replace.py(3) == 6
    helpers = [
        atom for atom in m.atoms() if str(atom).startswith("(= (daux-replace--loop")
    ]
    assert len(helpers) == 1


def test_later_literal_head_subsumed_by_earlier_head_is_refused(m):
    @m.define
    def dsubsumed(x, y=0):
        return 10

    with pytest.raises(CompileError, match="earlier clause already answers"):

        @m.define
        def dsubsumed(x=1, y=0):  # noqa: F811
            return 20

    assert m.run("!(collapse (dsubsumed 1 0))") == [[expr(10)]]
    assert dsubsumed.py(1, 0) == 10


def test_nonmatching_hazardous_twin_dispatches_to_the_next_clause(m):
    @m.define
    def dhazard_guard(n=0):
        return match(Fact(x), x)  # noqa: F821

    @m.define
    def dhazard_guard(n):  # noqa: F811
        return n + 1

    assert m.run("!(dhazard-guard 2)") == [[3]]
    assert dhazard_guard.py(2) == 3
    with pytest.raises(RuntimeError, match="match against the space"):
        dhazard_guard.py(0)


def test_define_refuses_callable_objects(m):
    class CallableObject:
        def __call__(self, value):
            return value

    with pytest.raises(TypeError, match="define expects a Python function"):
        m.define(CallableObject())
