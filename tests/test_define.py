"""Purpose: the Python-to-MeTTa compiler: lowerings run against the engine,
refusals name construct and line, helper-bearing redefinitions replace as a
unit, and guarded Python twins agree with equations on ground inputs.
Owns:
  - test_define_from_two_threads_is_serialized joins both definition workers
    before examining their equations [tested test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib.util
import sys
import tempfile
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from petta import CompileError, EngineError, S, expr

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta.new_space()


def twin_base_probe(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return value + 1


def twin_base_replacement(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return value + 10


def twin_user_probe(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return twin_base_probe(value) * 2


def test_define_from_two_threads_is_serialized(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def thread_left(value):
        return value + 1

    def thread_right(value):
        return value * 2

    with ThreadPoolExecutor(max_workers=2) as workers:
        left, right = workers.map(m.define, (thread_left, thread_right))

    assert m.eval(left(4)) == [5]
    assert m.eval(right(4)) == [8]


def test_existing_twin_sees_later_redefinition(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.define(twin_base_probe)
    twin_user = m.define(twin_user_probe)
    assert twin_user.py(3) == 8

    original_name = twin_base_replacement.__name__
    twin_base_replacement.__name__ = twin_base_probe.__name__
    try:
        m.define(twin_base_replacement)
    finally:
        twin_base_replacement.__name__ = original_name

    assert twin_user.py(3) == 26


def test_recursion_compiles_and_runs(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dfact(n):
        if n == 0:
            return 1
        return n * dfact(n - 1)

    assert m.run("!(dfact 5)") == [[120]]
    assert dfact.py(5) == 120
    assert dfact(5) == expr(S.dfact, 5)  # calling the name builds the term
    assert "(= (dfact $n)" in dfact.source()


def test_early_return_reads_as_else(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dsign(x):
        if x < 0:
            return -1
        if x == 0:
            return 0
        return 1

    for value, expected in [(-3, -1), (0, 0), (9, 1)]:
        assert m.run(f"!(dsign {value})") == [[expected]]


def test_bindings_become_let_star(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A body calls engine functions by the name it writes, and Python cannot
    # spell a hyphen, so the engine's sqrt-math is reached through an alias
    # the body CAN write. Explicit, one line, and visible in the space; the
    # compiler no longer retries a hyphenated spelling behind the author.
    m.run("(= (sqrt_math $x) (sqrt-math $x))")

    @m.define
    def dhyp(a, b):
        aa = a * a
        bb = b * b
        return sqrt_math(aa + bb)  # noqa: F821  engine function

    assert m.run("!(dhyp 3 4)") == [[5.0]]
    assert dhyp.py.__name__ == "dhyp"


def test_true_division_matches_python_exactly(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dratio(a, b):
        return a / b

    assert m.run("!(dratio 7 2)") == [[3.5]]
    assert m.run("!(dratio 6 2)") == [[3.0]]  # Python answers 3.0, never 3


def test_generator_is_superposition(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dchoices(n):
        yield n
        yield n + 1
        yield n * 10

    assert m.run("!(collapse (dchoices 5))") == [[expr(5, 6, 50)]]


def test_generator_with_branches(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dbranch(n):
        if n > 0:
            yield Pos  # noqa: F821  constructor convention
        else:
            yield Neg  # noqa: F821
        yield Always  # noqa: F821

    assert m.run("!(collapse (dbranch 3))") == [[expr(S.Pos, S.Always)]]
    assert m.run("!(collapse (dbranch -3))") == [[expr(S.Neg, S.Always)]]


def test_lambda_is_first_class(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dapply_twice(x):
        f = lambda v: v + 10  # noqa: E731
        return f(f(x))

    # One naming policy across both decorators: the Python name, verbatim.
    assert m.run("!(dapply_twice 1)") == [[21]]


def test_the_python_name_is_the_metta_name_and_name_asks_for_another(m):
    """No implicit rewriting. The identifier in the source is the name in
    the space, and the hyphenated spelling MeTTa prefers is asked for.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    @m.define
    def add_one(value):
        return value + 1

    assert m.run("!(add_one 5)") == [[6]]
    assert m.run("!(add-one 5)") == [[S["add-one"](5)]]

    @m.define(name="add-two")
    def add_two(value):
        return value + 2

    assert m.run("!(add-two 5)") == [[7]]
    assert m.run("!(add_two 5)") == [[S.add_two(5)]]
    assert add_two.py(5) == 7


def test_comprehension_is_map_atom(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dtens(xs):
        return [x * 10 for x in xs]

    assert m.run("!(dtens (1 2 3))") == [[expr(10, 20, 30)]]


def test_filtered_comprehension_composes_filter_atom(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dbig(xs):
        return [x for x in xs if x > 2]

    assert m.run("!(dbig (1 2 3 4))") == [[expr(3, 4)]]


def test_match_in_body_binds_pattern_variables(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.parent(S.Tom, S.Bob), S.parent(S.Bob, S.Ann))

    @m.define
    def dgrand(gp):
        return match(parent(gp, mid), match(parent(mid, gc), gc))  # noqa: F821

    assert m.run("!(dgrand Tom)") == [[S.Ann]]


def test_short_circuit_and_or(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dsafe(n):
        return n != 0 and 100 / n > 10  # RHS must not run for 0

    assert m.run("!(dsafe 0)") == [[False]]
    assert m.run("!(dsafe 5)") == [[True]]
    assert dsafe.py(0) is False


def test_constructor_convention_capitalized_names(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
def test_refusals_name_construct_and_line(m, source, needle):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    namespace = {}
    exec(source, namespace)
    fn = namespace["f"]
    fn.__source_override = source

    with pytest.raises(CompileError) as excinfo:
        # inspect.getsource cannot see exec'd code; compile the AST path the
        # decorator uses by round-tripping through a real file.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "snippet.py"
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


def test_modulo_matches_python_on_signs(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @metta.define
    def dmod(a, b):
        return a % b

    for a, b in [(-7, 3), (5, -2), (7, 3), (-5, -2)]:
        (engine_answer,) = metta.eval(dmod(a, b))
        assert engine_answer == dmod.py(a, b) == a % b


def test_literal_defaults_are_head_patterns_and_clauses_stack(m):
    """Def fib(n=0) is the equation matching 0; definition order is clause
    order; the engine dispatches between the stacked clauses.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    @m.define
    def dfib(n=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return 0

    @m.define
    def dfib(n=1):  # noqa: ARG001, F811  -- stacked definitions are the overload behavior under test; the test reflects this callable signature, so every declared parameter must remain visible
        return 1

    @m.define
    def dfib(n):  # noqa: F811
        return dfib(n - 1) + dfib(n - 2)

    assert m.run("!(dfib 0)") == [[0]]
    assert m.run("!(dfib 1)") == [[1]]
    assert m.run("!(dfib 10)") == [[55]]

    # A literal clause's twin guards its own head; dispatch is the engine's.
    @m.define
    def donly(n=5):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return 99

    assert donly.py(5) == 99
    assert "(= (donly 5) 99)" == donly.source()
    with pytest.raises(LookupError):
        donly.py(4)


def test_while_becomes_a_tail_recursive_helper(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_nested_loops_carry_the_outer_state(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_nested_for_loops_resume_the_outer_sequence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dgrid(rows):
        out = 0
        for row in rows:
            for cell in row:
                out += cell
            out += 100
        return out

    @m.define
    def dcube(grid):
        out = 0
        for plane in grid:
            for row in plane:
                for cell in row:
                    out += cell
        return out

    # A for carries the sequence it has left to peel. Held as a fixed
    # variable rather than as loop state, the inner loop's exit read that
    # name in its own equation, where it is the inner loop's tail, and the
    # outer loop resumed on it.
    assert m.run("!(dgrid ((1 2) (3)))") == [[206]]
    assert dgrid.py([[1, 2], [3]]) == 206
    assert m.run("!(dgrid ((5)))") == [[105]]
    assert m.run("!(dgrid ())") == [[0]]
    assert m.run("!(dcube (((1 2) (3)) ((4))))") == [[10]]
    assert dcube.py([[[1, 2], [3]], [[4]]]) == 10


def test_for_peels_with_decons_and_early_return_searches(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_nested_defs_lift_with_their_closure(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
    recursion wearing one's clothes.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    @m.define
    def dcountdown(n):
        while n > 0:
            n -= 1
        return n

    assert m.run(
        "!(with-pragma! ((max-stack-depth 10000000)) (dcountdown 2000000))"
    ) == [[0]]


def test_loop_variable_read_after_for_is_refused(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(CompileError) as excinfo:

        @m.define
        def dleak(xs):
            for _x in xs:
                pass
            return _x

    assert "after the loop" in str(excinfo.value) or "no MeTTa equivalent" in str(
        excinfo.value
    )


def test_annotations_declare_types_for_defines(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dtyped(x: int) -> int:
        return x + 1

    assert m.run("!(get-type (dtyped 1))") == [[S.Number]]


def test_engine_functions_feel_like_python(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (dtriple $x) (* $x 3))")
    triple = m.fn("dtriple")
    assert triple(14) == 42
    assert m.fn("superpose").all(expr(1, 2)) == [1, 2]
    with pytest.raises(EngineError):
        m.fn("superpose")(expr(1, 2))  # two answers is not one


def test_boolean_operators_answer_the_operand(m):
    """3 or 7 is 3, 0 or 7 is 7, 3 and 7 is 7: Python's own reading,
    truthiness deciding and the operand answering.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

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
    falsehoods, exactly Python.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

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


def test_mixed_numeric_equality_and_membership(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_fstrings_str_round_range_slices(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_host_bindings_refuse_the_constructor_reading(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(CompileError) as caught:

        @m.define
        def dthreshold(x):
            return x + Threshold

    assert "module binding" in str(caught.value)


Threshold = 5


def test_twin_refuses_engine_only_bodies(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(expr(S.fact9, 9))

    @m.define
    def dseek():
        return match(fact9(v), v)  # noqa: F821

    assert m.run("!(dseek)") == [[9]]
    with pytest.raises(RuntimeError) as caught:
        dseek.py()
    assert "match against the space" in str(caught.value)


def test_same_head_redefinition_replaces(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def install_first_definition():
        @m.define
        def dvalue():
            return 1

        return dvalue

    install_first_definition()
    assert m.run("!(dvalue)") == [[1]]

    def install_replacement_definition():
        @m.define
        def dvalue():
            return 2

        return dvalue

    dvalue = install_replacement_definition()
    # The notebook reading: one head, the newest body, exactly one answer.
    assert m.run("!(collapse (dvalue))") == [[expr(2)]]
    assert dvalue.py() == 2


def test_helper_only_redefinition_replaces_main_and_aux_equations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 1
            n -= 1
        return total

    assert m.one(daux_replace(3)) == 3

    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 2
            n -= 1
        return total

    assert m.one(daux_replace(3)) == 6
    assert daux_replace.py(3) == 6

    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 2
            n -= 1
        return total

    assert m.one(daux_replace(3)) == 6
    assert daux_replace.py(3) == 6
    helpers = [
        atom for atom in m.atoms() if str(atom).startswith("(= (daux_replace--loop")
    ]
    assert len(helpers) == 1


def test_later_literal_head_subsumed_by_earlier_head_is_refused(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dsubsumed(x, y=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return 10

    with pytest.raises(CompileError, match="earlier clause already answers"):

        @m.define
        def dsubsumed(x=1, y=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
            return 20

    assert m.run("!(collapse (dsubsumed 1 0))") == [[expr(10)]]
    assert dsubsumed.py(1, 0) == 10


def test_nonmatching_hazardous_twin_dispatches_to_the_next_clause(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dhazard_guard(n=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return match(Fact(x), x)  # noqa: F821

    @m.define
    def dhazard_guard(n):  # noqa: F811
        return n + 1

    assert m.run("!(dhazard_guard 2)") == [[3]]
    assert dhazard_guard.py(2) == 3
    with pytest.raises(RuntimeError, match="match against the space"):
        dhazard_guard.py(0)


def test_define_refuses_callable_objects(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class CallableObject:
        def __call__(self, value):
            return value

    with pytest.raises(TypeError, match="define expects a Python function"):
        m.define(CallableObject())


# M2: rewriting a defined function in Prolog for speed used to mean deleting
# the Python, and the differential oracle went with it. The two are declared
# together instead, and testing.check_twin runs the pair.
FAST_PROLOG = """
:- metta_extension(define_twin_demo, [version('0.1.0')]).
:- metta_export("(: dt-dot (-> Expression Expression Number))").
'dt-dot'(A, B, Out) :- dt_dot_(A, B, 0, Out).
dt_dot_([], [], Acc, Acc).
dt_dot_([X|Xs], [Y|Ys], Acc0, Out) :- Acc is Acc0 + X * Y, dt_dot_(Xs, Ys, Acc, Out).
"""


@pytest.fixture(scope="module")
def fast_file(tmp_path_factory):
    """One file for the whole module, deliberately.

    Registration ownership is process-wide and by SOURCE, so a per-test copy
    at a different path is a SECOND library claiming 'dt-dot', which the
    engine refuses by design. Re-registering the same file is replacement.
    """
    source = tmp_path_factory.mktemp("define_twin") / "dt_fast.pl"
    source.write_text(FAST_PROLOG)
    return source


def test_a_definition_may_be_written_in_prolog_with_the_python_as_reference(m, fast_file):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define(prolog=fast_file, name="dt-dot")
    def dt_dot(a, b):
        """The readable reference."""
        return sum(x * y for x, y in zip(a, b, strict=True))

    # The engine answers from the Prolog, and the Python is still callable.
    assert m.eval(dt_dot((1, 2, 3), (4, 5, 6))) == [32]
    assert dt_dot.py((1, 2, 3), (4, 5, 6)) == 32
    assert dt_dot.name == "dt-dot"
    # There is no compiled equation to print, so source() says where it came from.
    assert str(fast_file) in dt_dot.source()
    assert "python twin as .py" in repr(dt_dot)


def test_the_prolog_twin_is_checked_against_its_reference(m, fast_file):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from petta import testing

    @m.define(prolog=fast_file, name="dt-dot")
    def dt_dot(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    ran = testing.check_twin(dt_dot, [((1, 2, 3), (4, 5, 6)), ((0,), (9,)), ((), ())])
    assert len(ran) == 3


def test_a_prolog_twin_that_disagrees_is_caught(m, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from petta import testing

    source = tmp_path / "dt_wrong.pl"
    source.write_text(
        ':- metta_extension(dt_wrong, [version("0.1")]).\n'
        ':- metta_export("(: dt-sum (-> Number Number Number))").\n'
        "'dt-sum'(A, B, Out) :- Out is A + B + 1.\n"
    )

    @m.define(prolog=source, name="dt-sum")
    def dt_sum(a, b):
        return a + b

    with pytest.raises(AssertionError, match="the engine answered"):
        testing.check_twin(dt_sum, [(1, 2)])


def test_a_prolog_file_that_does_not_register_the_name_is_refused(m, fast_file):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(CompileError, match="does not register"):

        @m.define(prolog=fast_file)
        def dt_absent(a, b):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
            return a


def test_a_twin_of_the_wrong_shape_is_refused(m, fast_file):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # dt-dot/3 is two inputs and one output; a one-parameter twin would need
    # arity 2, and a caller is the only thing that would ever find that out.
    with pytest.raises(CompileError, match="Python twin takes 1"):

        @m.define(prolog=fast_file, name="dt-dot")
        def dt_dot(a):
            return a


def test_define_needs_a_function_or_prolog_and_then_one(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="takes a function"):
        m.define()



# The space-hook door and the define door compose (P12.3). A hook body is
# arbitrary MeTTa, and the Python that @m.define compiles participates on
# both sides of a verdict: a comparison the engine evaluates decides
# admission, and a constructor-minting transform names the granted form.
# The mechanism itself is tested in tests/prolog/hooks.plt; this witnesses
# that "write the policy in Python" is registration plus the existing door,
# not a second mechanism.
def test_a_hook_body_is_arbitrary_metta_and_python_compiles_to_it(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def budget_allows(count):
        return count * 2 <= 6

    @m.define
    def stamp(item):
        return Stamped(item)  # noqa: F821  constructor convention

    m.run(
        '(= (p12-witness-guard (secret $x))'
        ' (refuse "a python-compiled policy refuses secrets"))'
    )
    m.run("(= (p12-witness-guard (raw $x)) (accept (stamp $x)))")
    m.run(
        "(= (p12-witness-guard (count $n))"
        ' (if (budget_allows $n) (accept) (refuse "the python budget said no")))'
    )
    m.run("!(declare-pre-add! &p12-witness-pool p12-witness-guard)")
    try:
        # The granted form is the Python transform's constructor, not the
        # offered atom.
        m.run("!(add-atom &p12-witness-pool (raw 7))")
        assert m.run("!(match &p12-witness-pool (Stamped $x) $x)") == [[7]]
        assert (
            m.run("!(collapse (match &p12-witness-pool (raw $x) $x))")
            == [[expr()]]
        )

        # The Python comparison decides admission in both directions.
        m.run("!(add-atom &p12-witness-pool (count 3))")
        assert m.run("!(match &p12-witness-pool (count $n) $n)") == [[3]]
        with pytest.raises(EngineError, match="the python budget said no"):
            m.run("!(add-atom &p12-witness-pool (count 4))")
        assert m.run("!(match &p12-witness-pool (count $n) $n)") == [[3]]

        # A refusal carries the handler's own sentence to the Python caller.
        with pytest.raises(EngineError, match="refuses secrets"):
            m.run("!(add-atom &p12-witness-pool (secret 1))")
        assert (
            m.run("!(collapse (match &p12-witness-pool (secret $x) $x))")
            == [[expr()]]
        )
    finally:
        m.run("!(undeclare-pre-add! &p12-witness-pool)")
