"""Purpose: the Python-to-MeTTa compiler: lowerings run against the engine,
refusals name construct and line, helper-bearing redefinitions replace as a
unit, and guarded Python twins agree with equations on ground inputs.
Guarantees:
  - one source docstring reaches Defined.doc, help(), and the definition
    space's @doc atom [tested:
    test_one_docstring_reaches_help_dot_doc_and_get_doc;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a local annotated assignment emits and enforces its in-place type claim
    without reinterpreting source-level colon data [tested:
    test_an_annotated_binding_emits_its_claim,
    translator_typed_let:a_source_colon_pair_stays_a_pattern;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every definition derives source, documentation, captures, and purity from
    its AST and retires stale reflection on replacement and clear [tested:
    test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - implicit definition names apply the underscore-to-hyphen map and explicit
    name= remains exact [tested:
    test_the_implicit_name_is_mapped_and_name_is_exact; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - the public twin oracle preserves grounded scalar species while comparing
    engine and Python answers [tested:
    test_check_twin_distinguishes_integer_float_and_boolean_answers;
    commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a]
  - compiled for statements iterate every Python iterable with the same
    element count as their twin [tested:
    test_for_statement_uses_python_iteration_for_every_grounded_iterable;
    commit=cf1963fa03f91c1d9721636cb6f05c6cfc362819]
  - generic compiled operators invoke Python's live protocols, while exact
    int/float annotations retain pure engine heads; typing.no_type_check can
    keep that syntax proof without publishing a source-absent arrow [tested:
    test_compiled_operators_follow_python_protocols_and_result_species,
    test_no_type_check_keeps_annotations_as_a_compile_proof_only;
    commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301]
Owns:
  - test_define_from_two_threads_is_serialized joins both definition workers
    before examining their equations [tested test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib.util
import inspect
import pydoc
import sys
import tempfile
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from metta import Expression, S, Space, V, parse
from metta.errors import CompileError, EngineError
from metta.vocabularies import EffectClass

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


def twin_base_probe(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return value + 1


def twin_base_replacement(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return value + 10


def twin_user_probe(value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return twin_base_probe(value) * 2


def p5_documented_greeting(value: str) -> str:
    """Return a defined greeting."""
    return f"Hello, {value}."


def test_define_from_two_threads_is_serialized(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def thread_left(value):
        return value + 1

    def thread_right(value):
        return value * 2

    with ThreadPoolExecutor(max_workers=2) as workers:
        left, right = workers.map(m.define, (thread_left, thread_right))

    assert left(4) == [5]
    assert right(4) == [8]


def test_existing_twin_sees_later_redefinition(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.define(twin_base_probe, name="twin_base_probe")
    twin_user = m.define(twin_user_probe, name="twin_user_probe")
    assert twin_user.py(3) == 8

    original_name = twin_base_replacement.__name__
    twin_base_replacement.__name__ = twin_base_probe.__name__
    try:
        m.define(twin_base_replacement, name="twin_base_probe")
    finally:
        twin_base_replacement.__name__ = original_name

    assert twin_user.py(3) == 26


def test_one_docstring_reaches_help_dot_doc_and_get_doc(m):
    """One source docstring reaches Defined.doc, help(), and get-doc."""
    documented = m.define(p5_documented_greeting)
    expected = inspect.getdoc(p5_documented_greeting)
    assert documented.doc == expected
    assert expected in pydoc.render_doc(documented)
    docs = m.run(f"!(get-doc {documented.name})")
    assert len(docs) == 1 and expected in str(docs[0][0])
    assert expected in pydoc.render_doc(m.fn[documented.name])


def test_recursion_compiles_and_runs(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dfact(n):
        if n == 0:
            return 1
        return n * dfact(n - 1)

    assert m.run("!(dfact 5)") == [[120]]
    assert dfact.py(5) == 120
    assert dfact(5) == [120]
    assert S.dfact(5) == Expression(S.dfact, 5)  # the S door stages explicitly
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


def test_an_annotated_binding_emits_its_claim(m):
    """A local annotated assignment emits and enforces its in-place type claim."""

    @m.define
    def annotated_binding(value):
        result: int = value
        return result

    assert "(: $result Number)" in str(annotated_binding.body)
    assert m.run("!(annotated-binding 7)") == [[7]]
    assert m.run('!(annotated-binding "nope")') == [[]]

    @m.define
    def annotated_generator(value):
        result: int = value
        yield result

    assert "(: $result Number)" in str(annotated_generator.body)
    assert m.run("!(annotated-generator 8)") == [[8]]


def test_each_ast_derived_fact_replaces_the_flag_it_supersedes(m, monkeypatch):
    """Every AST-derived fact replaces the decorator flag it supersedes."""

    @m.define
    def ast_helper(value):
        return value

    def ast_observed(value):
        """Documentation derived from the parsed function body."""
        return ast_helper(value)

    ast_observed.__doc__ = "A mutable runtime attribute is not the source fact."
    observed = m.define(ast_observed)

    assert observed.doc == "Documentation derived from the parsed function body."
    assert observed.source_span.path == str(Path(__file__).resolve())
    assert observed.source_span.start_line == inspect.getsourcelines(ast_observed)[1]
    assert observed.free_variables == ("ast_helper",)
    assert observed.pure is True
    assert observed.effect is EffectClass.pureStructural
    assert "pure" not in inspect.signature(m.define).parameters

    reflection = m._at("&metta")
    source_rows = reflection.match(parse("(source-span $space ast-observed $path $sl $sc $el $ec)"))
    assert len(source_rows) == 1
    source_row = source_rows[0]
    assert source_row.space == m
    assert source_row.path.value == str(Path(__file__).resolve())
    source_fact = Expression(
        S["source-span"],
        source_row.space,
        S["ast-observed"],
        source_row.path,
        source_row.sl,
        source_row.sc,
        source_row.el,
        source_row.ec,
    )
    free_fact = parse("(free-variable " + m.name + " ast-observed ast_helper)")
    effect_fact = parse("(effect ast-observed pureStructural)")
    assert free_fact in reflection
    assert effect_fact in reflection
    assert reflection.run(f"!(get-type (defined {m.name} ast-observed))") == [[S.DefinitionFact]]
    assert reflection.run(f"!(get-type {source_fact})") == [[S.DefinitionFact]]
    assert reflection.run(f"!(get-type {free_fact})") == [[S.DefinitionFact]]
    assert reflection.run(f"!(get-type {effect_fact})") == [[S.EffectDecl]]
    assert "Documentation derived from the parsed function body." in str(
        m.run("!(get-doc ast-observed)")
    )

    m.run("(= (ast_effect $value) (println! $value))")

    def ast_observed(value):
        """Replacement documentation from the replacement AST."""
        return ast_effect(value)  # noqa: F821

    replacement = m.define(ast_observed)
    assert replacement.pure is False
    assert replacement.effect is EffectClass.oracleIO
    assert effect_fact not in reflection
    assert parse("(effect ast-observed oracleIO)") in reflection
    assert (
        len(reflection.match(parse("(source-span $space ast-observed $path $sl $sc $el $ec)"))) == 1
    )
    assert "Replacement documentation from the replacement AST." in str(
        m.run("!(get-doc ast-observed)")
    )

    old_source = list(
        reflection.match(parse("(source-span $space ast-observed $path $sl $sc $el $ec)"))
    )

    def ast_observed(value):
        """A fact publication failure must not install this clause."""
        return value + 1

    runtime_type = type(m.runtime)
    real_must = runtime_type.must
    failed = False

    def fail_reflection(runtime, goal, **inputs):
        nonlocal failed
        if not failed and goal == "metta_py_add(Space, W)" and inputs.get("Space") == "&metta":
            failed = True
            msg = "forced definition-fact failure"
            raise EngineError(msg)
        return real_must(runtime, goal, **inputs)

    monkeypatch.setattr(runtime_type, "must", fail_reflection)
    with pytest.raises(EngineError, match="forced definition-fact failure"):
        m.define(ast_observed)
    monkeypatch.setattr(runtime_type, "must", real_must)
    assert (
        list(reflection.match(parse("(source-span $space ast-observed $path $sl $sc $el $ec)")))
        == old_source
    )
    assert "Replacement documentation from the replacement AST." in str(
        m.run("!(get-doc ast-observed)")
    )

    m.clear()
    assert not reflection.match(parse("(source-span $space ast_observed $path $sl $sc $el $ec)"))
    assert free_fact not in reflection


def test_true_division_matches_python_exactly(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dratio(a, b):
        return a / b

    assert m.run("!(dratio 7 2)") == [[3.5]]
    assert m.run("!(dratio 6 2)") == [[3.0]]  # Python answers 3.0, never 3


def test_flat_generator_emits_one_equation_per_yield(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def mycalc(x, y):
        yield x + y
        yield x - y

    equations = m.fn.mycalc.equations
    assert len(equations) == 2
    assert all(equation.children[0] == S["="] for equation in equations)
    assert mycalc(1, 2) == [3, -1]


def test_generator_with_branches(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dbranch(n):
        if n > 0:
            yield Pos  # noqa: F821  constructor convention
        else:
            yield Neg  # noqa: F821
        yield Always  # noqa: F821

    assert m.run("!(collapse (dbranch 3))") == [[Expression(S.Pos, S.Always)]]
    assert m.run("!(collapse (dbranch -3))") == [[Expression(S.Neg, S.Always)]]
    (equation,) = m.fn.dbranch.equations
    assert "superpose" in str(equation.children[2])


def test_loop_yields_remain_one_superpose_equation(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dloop(values):
        for value in values:  # noqa: UP028 -- the explicit loop is the compiler shape under test
            yield value

    (equation,) = m.fn.dloop.equations
    assert "superpose" in str(equation.children[2])
    assert dloop((1, 2, 3)) == [1, 2, 3]


def test_lambda_is_first_class(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dapply_twice(x):
        f = lambda v: v + 10  # noqa: E731
        return f(f(x))

    assert m.run("!(dapply-twice 1)") == [[21]]


def test_the_implicit_name_is_mapped_and_name_is_exact(m):
    """Implicit names transliterate; name= is the exact-name escape."""

    @m.define
    def add_one(value):
        return value + 1

    assert m.run("!(add-one 5)") == [[6]]
    assert m.run("!(add_one 5)") == [[S["add_one"](5)]]

    @m.define(name="add_two")
    def add_two(value):
        return value + 2

    assert m.run("!(add_two 5)") == [[7]]
    assert m.run("!(add-two 5)") == [[S["add-two"](5)]]
    assert add_two.py(5) == 7


def test_comprehension_is_map_atom(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dtens(xs):
        return [x * 10 for x in xs]

    assert m.run("!(dtens (1 2 3))") == [[Expression(10, 20, 30)]]


def test_filtered_comprehension_composes_filter_atom(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dbig(xs):
        return [x for x in xs if x > 2]

    assert m.run("!(dbig (1 2 3 4))") == [[Expression(3, 4)]]


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

    assert m.run("!(dtag 7)") == [[Expression(S.Result, 7, S.Done)]]


@pytest.mark.parametrize(
        ("source", "needle"),
        [
            ("def f(x):\n    while x > 0:\n        break\n    return x", "test"),
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
    (engine_answer,) = dtwin(n)
    assert engine_answer == dtwin.py(n)


def test_modulo_matches_python_on_signs(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @metta.define
    def dmod(a, b):
        return a % b

    for a, b in [(-7, 3), (5, -2), (7, 3), (-5, -2)]:
        (engine_answer,) = dmod(a, b)
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


def test_for_statement_uses_python_iteration_for_every_grounded_iterable(m):
    """Strings, bytes, and mappings follow iter(), like lists and tuples."""

    @m.define
    def diterable_count(values):
        count = 0
        for _value in values:
            count += 1
        return count

    cases = (
        ("abc", 3),
        ("", 0),
        (b"xy", 2),
        (b"", 0),
        ({"left": 1, "right": 2}, 2),
        ({}, 0),
        ([1, 2, 3], 3),
        ((1, 2), 2),
    )
    for value, expected in cases:
        assert diterable_count.py(value) == expected
        assert list(diterable_count(value)) == [expected]


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

    assert m.run("!(with-pragma! ((max-stack-depth 10000000)) (dcountdown 2000000))") == [[0]]


def test_loop_variable_read_after_for_is_refused(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(CompileError) as excinfo:

        @m.define
        def dleak(xs):
            for _x in xs:
                pass
            return _x

    assert "after the loop" in str(excinfo.value) or "no MeTTa equivalent" in str(excinfo.value)


def test_annotations_declare_types_for_defines(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dtyped(x: int) -> int:
        return x + 1

    assert m.run("!(get-type (dtyped 1))") == [[S.Number]]


def test_no_type_check_keeps_annotations_as_a_compile_proof_only(m):
    """A source-exact or multi-arity twin can keep proof without an arrow."""
    from typing import no_type_check

    @m.define
    @no_type_check
    def dnative_only(x: int) -> int:
        """Add one.

        Args:
            x: the input

        Returns:
            the result
        """
        return x + 1

    assert str(dnative_only.body) == "(+ $x 1)"
    assert list(m.match(S[":"](S.dnative_only, V.type))) == []
    documentation = str(m.run("!(get-doc dnative-only)")[0][0])
    assert documentation.count("(@type %Undefined%)") == 2

    @m.define
    @no_type_check
    def dshared(x: int) -> int:
        return x + 1

    @m.define(name="dshared")
    @no_type_check
    def dshared_2(x: int, y: int) -> int:
        return x + y

    assert dshared(3) == [4]
    assert dshared_2(3, 4) == [7]
    assert list(m.match(S[":"](S.dshared, V.type))) == []


def test_engine_functions_feel_like_python(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (dtriple $x) (* $x 3))")
    triple = m.fn.dtriple
    assert triple(14) == [42]
    assert m.fn.superpose(Expression(1, 2)) == [1, 2]
    with pytest.raises(EngineError):
        m.fn.superpose(Expression(1, 2)).one()


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
    assert m.run("!(dcut (a b c d))") == [[Expression(S.b, S.c)]]
    assert dlabel.py(7) == "v=007!" and dcut.py(("a", "b", "c", "d")) == ("b", "c")
    assert "py-str-join" in dlabel.runtime_ops


def test_host_bindings_read_as_implicit_islands(m):
    """A capitalized module binding is not data: it reads the live value.

    Refusing it was the old law; under the fallback law the name islands,
    so the equation reads the module's binding at application time and a
    rebind is visible on the next call.
    """

    @m.define
    def dthreshold(x):
        return x + Threshold

    assert list(dthreshold(4)) == [9]


Threshold = 5


def test_twin_refuses_engine_only_bodies(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(Expression(S.fact9, 9))

    @m.define
    def dseek():
        return match(fact9(v), v)  # noqa: F821

    assert m.run("!(dseek)") == [[9]]
    with pytest.raises(RuntimeError) as caught:
        dseek.py()
    assert "match against the space" in str(caught.value)
    assert "calling it evaluates through its space" in str(caught.value)


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
    assert m.run("!(collapse (dvalue))") == [[Expression(2)]]
    assert dvalue.py() == 2


def test_same_head_redefinition_replaces_the_whole_yield_unit(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dyield_unit(value):
        yield value
        yield value + 1

    assert dyield_unit(3) == [3, 4]
    assert len(m.fn["dyield-unit"].equations) == 2

    @m.define
    def dyield_unit(value):
        yield value * 10
        yield value * 100

    assert dyield_unit(3) == [30, 300]
    assert len(m.fn["dyield-unit"].equations) == 2


def test_helper_only_redefinition_replaces_main_and_aux_equations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 1
            n -= 1
        return total

    assert daux_replace(3) == [3]

    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 2
            n -= 1
        return total

    assert daux_replace(3) == [6]
    assert daux_replace.py(3) == 6

    @m.define
    def daux_replace(n):
        total = 0
        while n > 0:
            total += 2
            n -= 1
        return total

    assert daux_replace(3) == [6]
    assert daux_replace.py(3) == 6
    helpers = [atom for atom in m.atoms() if str(atom).startswith("(= (daux-replace--loop")]
    assert len(helpers) == 1


def test_later_literal_head_subsumed_by_earlier_head_is_refused(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dsubsumed(x, y=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return 10

    with pytest.raises(CompileError, match="earlier clause already answers"):

        @m.define
        def dsubsumed(x=1, y=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
            return 20

    assert m.run("!(collapse (dsubsumed 1 0))") == [[Expression(10)]]
    assert dsubsumed.py(1, 0) == 10


def test_nonmatching_hazardous_twin_dispatches_to_the_next_clause(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def dhazard_guard(n=0):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return match(Fact(x), x)  # noqa: F821

    @m.define
    def dhazard_guard(n):  # noqa: F811
        return n + 1

    assert m.run("!(dhazard-guard 2)") == [[3]]
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
    assert dt_dot((1, 2, 3), (4, 5, 6)) == [32]
    assert dt_dot.py((1, 2, 3), (4, 5, 6)) == 32
    assert dt_dot.name == "dt-dot"
    # There is no compiled equation to print, so source() says where it came from.
    assert str(fast_file) in dt_dot.source()
    assert "python twin as .py" in repr(dt_dot)


def test_the_prolog_twin_is_checked_against_its_reference(m, fast_file):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import testing

    @m.define(prolog=fast_file, name="dt-dot")
    def dt_dot(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    ran = testing.check_twin(dt_dot, [((1, 2, 3), (4, 5, 6)), ((0,), (9,)), ((), ())])
    assert len(ran) == 3


def test_a_prolog_twin_that_disagrees_is_caught(m, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import testing

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


def test_check_twin_distinguishes_integer_float_and_boolean_answers(m):
    """Python's equal numeric scalars remain different MeTTa groundings."""
    from metta import Grounded, testing

    @m.define
    def dt_reciprocal(value):
        return value**-1

    testing.check_twin(dt_reciprocal, [(1,), (-1,)])
    assert type(dt_reciprocal(1)[0].value) is float

    class DeliberatelyWrongScalarTwin:
        name = "dt-bool-species"

        def __call__(self):
            return [Grounded(1)]

        @staticmethod
        def py():
            return True

    with pytest.raises(AssertionError, match="the engine answered"):
        testing.check_twin(DeliberatelyWrongScalarTwin(), [()])


def test_compiled_operators_follow_python_protocols_and_result_species(m):  # noqa: C901 -- one protocol matrix must exercise every operator family through the same differential oracle
    """Every lowered operator agrees with the live Python data model."""
    from metta import fn, testing

    @m.define
    def dt_add(left, right):
        return left + right

    @m.define
    def dt_native_add(left: int, right: int) -> int:
        return left + right

    @m.define
    def dt_sub(left, right):
        return left - right

    @m.define
    def dt_native_sub(left: int, right: int) -> int:
        return left - right

    @m.define
    def dt_mul(left, right):
        return left * right

    @m.define
    def dt_native_mul(left: int, right: int) -> int:
        return left * right

    @m.define
    def dt_div(left, right):
        return left / right

    @m.define
    def dt_native_div(left: float, right: float) -> float:
        return left / right

    @m.define
    def dt_floor(left, right):
        return left // right

    @m.define
    def dt_native_floor(left: float, right: float) -> float:
        return left // right

    @m.define
    def dt_mod(left, right):
        return left % right

    @m.define
    def dt_native_mod(left: int, right: int) -> int:
        return left % right

    @m.define
    def dt_band(left, right):
        return left & right

    @m.define
    def dt_bor(left, right):
        return left | right

    @m.define
    def dt_bxor(left, right):
        return left ^ right

    @m.define
    def dt_order(left, right):
        return left < right

    @m.define
    def dt_native_order(left: int, right: int) -> bool:
        return left < right

    @m.define
    def dt_greater(left, right):
        return left > right

    @m.define
    def dt_native_greater(left: int, right: int) -> bool:
        return left > right

    @m.define
    def dt_at_most(left, right):
        return left <= right

    @m.define
    def dt_native_at_most(left: int, right: int) -> bool:
        return left <= right

    @m.define
    def dt_at_least(left, right):
        return left >= right

    @m.define
    def dt_native_at_least(left: int, right: int) -> bool:
        return left >= right

    @m.define
    def dt_annotated_equal(left: int, right: float) -> bool:
        return left == right

    @m.define
    def dt_annotated_float_equal(left: float, right: float) -> bool:
        return left == right

    @m.define
    def dt_builtins(values):
        return sum(values), min(values), max(values), sorted(values)

    @m.define
    def dt_reciprocal_species(value):
        return value**-1

    @m.define
    def dt_literal_set():
        return {1, 2, 3} - {2}

    @m.define
    def dt_set_comprehension(values):
        return {value % 3 for value in values}

    class Reflected:
        def __radd__(self, _left):
            return "radd"

        def __rsub__(self, _left):
            return "rsub"

        def __rmul__(self, _left):
            return "rmul"

        def __rtruediv__(self, _left):
            return "rtruediv"

        def __rfloordiv__(self, _left):
            return "rfloordiv"

        def __rmod__(self, _left):
            return "rmod"

        def __rpow__(self, _left):
            return "rpow"

        def __rmatmul__(self, _left):
            return "rmatmul"

        def __rlshift__(self, _left):
            return "rlshift"

        def __rrshift__(self, _left):
            return "rrshift"

        def __rand__(self, _left):
            return "rand"

        def __ror__(self, _left):
            return "ror"

        def __rxor__(self, _left):
            return "rxor"

        def __gt__(self, _left):
            return "reflected-lt"

        def __ge__(self, _left):
            return "reflected-le"

        def __lt__(self, _left):
            return "reflected-gt"

        def __le__(self, _left):
            return "reflected-ge"

    @m.define
    def dt_reflected(value):
        return (
            1 + value,
            1 - value,
            2 * value,
            8 / value,
            8 // value,
            8 % value,
            2**value,
            2 @ value,
            1 << value,
            8 >> value,
            6 & value,
            6 | value,
            6 ^ value,
            1 < value,
            1 <= value,
            1 > value,
            1 >= value,
        )

    class Unary:
        def __neg__(self):
            return "neg"

        def __pos__(self):
            return "pos"

        def __invert__(self):
            return "invert"

        def __abs__(self):
            return "abs"

    @m.define
    def dt_unary(value):
        return -value, +value, ~value, abs(value)

    checks = (
        (dt_add, (("ab", "cd"), ([1, 2], [3, 4]), ((1, 2), (3, 4)))),
        (dt_native_add, ((5, 2), (-5, 2))),
        (dt_sub, ((5, 2),)),
        (dt_native_sub, ((5, 2), (-5, 2))),
        (dt_mul, (("ab", 2), ([1, 2], 2), ((1, 2), 2))),
        (dt_native_mul, ((5, 2), (-5, 2))),
        (dt_div, ((5.0, 2.0), (-5.0, 2.0))),
        (dt_native_div, ((5.0, 2.0), (-5.0, 2.0))),
        (dt_floor, ((5.0, 2.0), (-5.0, 2.0))),
        (dt_native_floor, ((5.0, 2.0), (-5.0, 2.0))),
        (dt_mod, (("%03d", 7),)),
        (dt_native_mod, ((5, 2), (-5, 2))),
        (dt_band, ((6, 3), (True, False))),
        (dt_bor, ((6, 3), (True, False))),
        (dt_bxor, ((6, 3), (True, False))),
        (dt_order, (("alpha", "beta"),)),
        (dt_native_order, ((1, 2), (2, 1))),
        (dt_greater, ((2, 1), (1, 2))),
        (dt_native_greater, ((2, 1), (1, 2))),
        (dt_at_most, ((1, 2), (2, 1))),
        (dt_native_at_most, ((1, 2), (2, 1))),
        (dt_at_least, ((2, 1), (1, 2))),
        (dt_native_at_least, ((2, 1), (1, 2))),
        (dt_annotated_equal, ((1, 1.0),)),
        (dt_annotated_float_equal, ((float("nan"), float("nan")), (-0.0, 0.0))),
        (dt_builtins, (((True, False, True),), ((3, 1, 2),))),
        (dt_reciprocal_species, ((1,), (-1,))),
        (dt_reflected, ((Reflected(),),)),
        (dt_unary, ((Unary(),),)),
    )
    for defined, cases in checks:
        testing.check_twin(defined, cases)

    dynamic_set = list(dt_sub({1, 2, 3}, {2}))
    assert len(dynamic_set) == 1 and dynamic_set[0].value == {1, 3}
    assert dt_band({1, 2}, {2, 3})[0].value == {2}
    assert dt_bor({1}, {2})[0].value == {1, 2}
    assert dt_bxor({1, 2}, {2, 3})[0].value == {1, 3}
    protocol_heads = {
        dt_add: "add",
        dt_sub: "sub",
        dt_mul: "mul",
        dt_div: "truediv",
        dt_floor: "floordiv",
        dt_mod: "mod",
        dt_order: "lt",
        dt_greater: "gt",
        dt_at_most: "le",
        dt_at_least: "ge",
    }
    for defined, selector in protocol_heads.items():
        assert str(defined.body) == f"(py-operator {selector} $left $right)"

    native_heads = {
        dt_native_add: "(+ $left $right)",
        dt_native_sub: "(- $left $right)",
        dt_native_mul: "(* $left $right)",
        dt_native_div: "(/ (* 1.0 $left) $right)",
        dt_native_floor: "(floor-div $left $right)",
        dt_native_mod: "(% $left $right)",
        dt_native_order: "(< $left $right)",
        dt_native_greater: "(> $left $right)",
        dt_native_at_most: "(<= $left $right)",
        dt_native_at_least: "(>= $left $right)",
    }
    for defined, expected in native_heads.items():
        assert str(defined.body) == expected
        assert "py-operator" not in str(defined.body)

    assert type(dt_native_add(5, 2)[0].value) is int
    assert type(dt_native_sub(5, 2)[0].value) is int
    assert type(dt_native_mul(5, 2)[0].value) is int
    assert type(dt_native_div(5.0, 2.0)[0].value) is float
    assert type(dt_native_floor(5.0, 2.0)[0].value) is float
    assert type(dt_native_mod(5, 2)[0].value) is int
    for native_compare in (
        dt_native_order,
        dt_native_greater,
        dt_native_at_most,
        dt_native_at_least,
    ):
        assert type(native_compare(1, 2)[0].value) is bool
    assert dt_annotated_equal(1, 1.0) == [True]
    assert dt_annotated_float_equal(float("nan"), float("nan")) == [False]
    assert dt_annotated_float_equal(-0.0, 0.0) == [True]
    assert m.eval(fn.eq(1, 1.0)) == [False]
    assert m.eval(fn.eq(float("nan"), float("nan"))) == [True]
    assert m.eval(fn.eq(-0.0, 0.0)) == [False]
    assert str(dt_annotated_equal.body) == "(py-operator eq $left $right)"
    assert str(dt_annotated_float_equal.body) == "(py-operator eq $left $right)"

    def members(answer):
        return {
            pair.children[0].value
            for pair in answer.atoms()
            if isinstance(pair, Expression) and len(pair.children) == 2
        }

    assert members(next(iter(dt_literal_set()))) == {1, 3}
    assert members(next(iter(dt_set_comprehension((1, 2, 3, 4))))) == {0, 1, 2}


def test_compiled_rich_comparisons_truth_test_only_in_boolean_contexts(m):
    """A rich comparison's object survives until Python syntax tests it."""
    calls = []

    class Verdict:
        def __init__(self, name, truth):
            self.name = name
            self.truth = truth

        def __bool__(self):
            calls.append(("bool", self.name))
            return self.truth

    direct = Verdict("direct", truth=False)
    final = Verdict("final", truth=True)

    class Left:
        def __lt__(self, _other):
            calls.append("lt")
            return direct

        def __ne__(self, _other):
            calls.append("ne")
            return direct

    class Middle:
        def __lt__(self, _other):
            calls.append("middle-lt")
            return final

    left = Left()
    middle = Middle()

    @m.define
    def dt_direct_compare(a, b):
        return a < b

    @m.define
    def dt_not_equal(a, b):
        return a != b

    @m.define
    def dt_compare_test(a, b):
        if a < b:
            return "truthy"
        return "falsy"

    @m.define
    def dt_native_compare_test(a: int, b: int) -> str:
        if a < b:
            return "truthy"
        return "falsy"

    @m.define
    def dt_compare_chain(a, b, c):
        return a < b < c

    answer = dt_direct_compare(left, middle)[0]
    assert answer.value is direct
    assert calls == ["lt"]

    calls.clear()
    answer = dt_not_equal(left, middle)[0]
    assert answer.value is direct
    assert calls == ["ne"]

    calls.clear()
    assert dt_compare_test(left, middle) == ["falsy"]
    assert calls == ["lt", ("bool", "direct")]
    assert "(py-truthy (py-operator lt $a $b))" in str(dt_compare_test.body)
    assert "(< $a $b)" in str(dt_native_compare_test.body)
    assert "py-truthy" not in str(dt_native_compare_test.body)
    assert dt_native_compare_test(1, 2) == ["truthy"]
    assert dt_native_compare_test(2, 1) == ["falsy"]

    direct.truth = True
    calls.clear()
    answer = dt_compare_chain(left, middle, object())[0]
    assert answer.value is final
    assert calls == ["lt", ("bool", "direct"), "middle-lt"]


def test_compiled_augassign_uses_in_place_protocol(m):
    """Non-space ``op=`` invokes __iop__ once and rebinds its result."""

    class InPlace:
        def __init__(self):
            self.calls = []

        def __iadd__(self, other):
            self.calls.append(("iadd", other))
            return "in-place-result"

        def __add__(self, other):
            self.calls.append(("add", other))
            return "binary-result"

        def __imatmul__(self, other):
            self.calls.append(("imatmul", other))
            return "in-place-matmul"

    @m.define
    def dt_in_place(value):
        value += 3
        return value

    @m.define
    def dt_in_place_matmul(value):
        value @= 4
        return value

    @m.define
    def dt_list_in_place():
        values = [1]
        values += [2]
        return values

    @m.define
    def dt_set_in_place():
        values = {1}
        values |= {2}
        return values

    value = InPlace()
    assert dt_in_place(value) == ["in-place-result"]
    assert value.calls == [("iadd", 3)]
    assert dt_in_place_matmul(value) == ["in-place-matmul"]
    assert value.calls[-1] == ("imatmul", 4)
    assert dt_list_in_place() == [Expression(1, 2)]
    set_answer = dt_set_in_place()[0]
    assert {pair.children[0].value for pair in set_answer.atoms()} == {1, 2}


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
# The mechanism itself is tested in tests/prolog/suites/spaces/hooks.plt; this witnesses
# that "write the policy in Python" is registration plus the existing door,
# not a second mechanism.
def test_a_hook_body_is_arbitrary_metta_and_python_compiles_to_it(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @m.define
    def budget_allows(count):
        return count * 2 <= 6

    @m.define
    def stamp(item):
        return Stamped(item)  # noqa: F821  constructor convention

    m.run('(= (p12-witness-guard (secret $x)) (refuse "a python-compiled policy refuses secrets"))')
    m.run("(= (p12-witness-guard (raw $x)) (accept (stamp $x)))")
    m.run(
        "(= (p12-witness-guard (count $n))"
        ' (if (budget-allows $n) (accept) (refuse "the python budget said no")))'
    )
    m.run("!(declare-pre-add! &p12-witness-pool p12-witness-guard)")
    try:
        # The granted form is the Python transform's constructor, not the
        # offered atom.
        m.run("!(add-atom &p12-witness-pool (raw 7))")
        assert m.run("!(match &p12-witness-pool (Stamped $x) $x)") == [[7]]
        assert m.run("!(collapse (match &p12-witness-pool (raw $x) $x))") == [[Expression()]]

        # The Python comparison decides admission in both directions.
        m.run("!(add-atom &p12-witness-pool (count 3))")
        assert m.run("!(match &p12-witness-pool (count $n) $n)") == [[3]]
        with pytest.raises(EngineError, match="the python budget said no"):
            m.run("!(add-atom &p12-witness-pool (count 4))")
        assert m.run("!(match &p12-witness-pool (count $n) $n)") == [[3]]

        # A refusal carries the handler's own sentence to the Python caller.
        with pytest.raises(EngineError, match="refuses secrets"):
            m.run("!(add-atom &p12-witness-pool (secret 1))")
        assert m.run("!(collapse (match &p12-witness-pool (secret $x) $x))") == [[Expression()]]
    finally:
        m.run("!(undeclare-pre-add! &p12-witness-pool)")


def test_augmented_assignment_on_a_space_is_the_write_door(metta):
    """+= and -= on a space-bound local compile to add-atom and remove-atom.

    The miscompile this pins against stored (+ $s atom), answered True and
    wrote nothing, silently. Space provenance follows context-space and
    new-space bindings and plain aliases; the space name keeps its binding
    while the write executes under a throwaway one.
    """
    import pytest

    from metta import S, V
    from metta.errors import CompileError

    with metta._new_space() as m:

        @m.define
        def note(tag):
            space = S.context_space()
            space += S.ran(tag)
            return True

        assert "(add-atom $space (ran $tag))" in str(note.bodies[0])
        assert m.eval("(note logged)") == [True]
        assert [str(r.t) for r in m.match(S.ran(V.t))] == ["logged"]

        @m.define
        def unnote(tag):
            space = S.context_space()
            also = space
            also -= S.ran(tag)
            return True

        assert m.eval("(unnote logged)") == [True]
        assert not list(m.match(S.ran(V.t)))

        @m.define
        def accumulate(x):
            total = 0
            total += x
            return total

        assert m.eval("(accumulate 5)") == [5]

        with pytest.raises(CompileError, match="has no space meaning"):

            @m.define
            def scaled(tag):
                space = S.context_space()
                space *= S.ran(tag)
                return True

        # A nested-function local: += makes the name local (Python's own
        # rule), so no closure cell exists and the generic refusal is the
        # honest one.
        outside = m
        with pytest.raises(CompileError, match="augmented before it is bound"):

            @m.define
            def closured(x):
                outside += S.saw(x)  # noqa: F823, F841  -- the unbound augmentation IS the scenario
                return x

        # A module-global space IS visible to the compiler, so the refusal
        # names the space and the write door.
        globals()["outside_space"] = m
        try:
            with pytest.raises(CompileError, match="held outside this body"):

                @m.define
                def closured_global(x):
                    outside_space += S.saw(x)  # noqa: F821, F841  -- planted module global, removed below; the refused write is the scenario
                    return x
        finally:
            del globals()["outside_space"]


def test_walrus_bindings_hoist_as_let(metta):
    """`name := value` is Python's own let expression and compiles as one.

    PEP 572 binds to the enclosing function scope, which is a let* chain
    around the statement's continuation: nesting binds inner-first,
    siblings bind left to right, and an if-test walrus stays visible in
    both branches. A while-test walrus (per-iteration rebinding) and a
    walrus inside a nested scope refuse with their remedies.
    """
    import pytest

    from metta.errors import CompileError

    with metta._new_space() as m:

        @m.define
        def wsq(x):
            return (y := x * x) + y

        assert str(wsq.bodies[0]) == (
            "(let* (($y (py-operator mul $x $x))) (py-operator add $y $y))"
        )
        assert m.eval("(wsq 3)") == [18]

        @m.define
        def native_wsq(x: int) -> int:
            return (y := x * x) + y

        assert str(native_wsq.bodies[0]) == "(let* (($y (* $x $x))) (+ $y $y))"

        @m.define
        def native_guard(n: int) -> int:
            if (half := n // 2) < 10:
                return half
            return 0

        assert "py-operator" not in str(native_guard.bodies[0])
        assert "py-truthy" not in str(native_guard.bodies[0])

        @m.define
        def nested(x):
            return (y := (z := x + 1) * 2) + z + y

        assert m.eval("(nested 3)") == [20]

        @m.define
        def sibs(a):
            return (p := a + 1) * (q := p + 1) + q

        assert m.eval("(sibs 1)") == [9]

        @m.define
        def guard(n):
            if (doubled := n * 2) > 5:
                return doubled
            return 0

        assert m.eval("(guard 4)") == [8]
        assert m.eval("(guard 1)") == [0]

        with pytest.raises(CompileError, match="while test"):

            @m.define
            def bad_while(n):
                total = 0
                while (k := n) > 0:
                    total += k
                    n = n - 1
                return total

        with pytest.raises(CompileError, match="nested scope"):

            @m.define
            def bad_comp(xs):
                return [(w := v) for v in xs]  # noqa: F841  -- the refused binding IS the scenario

        # A walrus inside a BUILT TERM is data the term carries: hoisting
        # it into an evaluating let ran (+ $x 1) with $x unbound (the
        # spaces twins agent measured the engine refusing "+ ran
        # backwards"), so the boundary refuses with the remedy.
        with pytest.raises(CompileError, match="built term"):

            @m.define
            def bad_term(x):
                return S.cnt(inc := x + 1)  # noqa: F841  -- the refused binding IS the scenario


def test_a_pep695_type_parameter_resolves_in_annotations(m):
    """``def mid[T](x: T) -> T`` compiles: ``T`` lives in ``__type_params__``.

    The type-parameter scope sits between the closure and the locals and
    appears in neither ``__globals__`` nor ``__closure__``; leaving it out
    of the annotation namespace made the eager space-parameter probe refuse
    every generic definition with "the local annotation name 'T' is not
    available".
    """

    @m.define
    def generic_mid[T](x: T) -> T:
        return x

    assert list(generic_mid(S.a)) == [S.a]


def test_an_unresolvable_annotation_is_not_a_space_parameter(m):
    """A structured annotation the resolver cannot name is not a space handle.

    A subscripted domain builder used to refuse the whole definition through
    the eager probe; the strict refusal belongs only where an annotation is
    consumed as a type. A bare NAME that resolves nowhere keeps refusing
    loudly, because ``target: Space`` with the import missing must not
    silently turn the body's removal into arithmetic. The positive control
    keeps the probe honest: a resolvable ``Space`` parameter still enters
    statement lowering as a space handle.
    """
    domain_builder = {"rows": object()}

    @m.define
    def carries(x: domain_builder["rows"]):  # noqa: F821  -- the subscripted domain builder IS the scenario
        return x

    assert list(carries(S.b)) == [S.b]

    with pytest.raises(CompileError, match="not available"):

        @m.define
        def typo(target: SpaceHandle, atom):  # noqa: F821  -- the unresolvable bare name IS the scenario
            target -= atom
            return S.done

    @m.define
    def removes(target: Space, atom):
        target -= atom
        return S.done

    held = m.metta.space()
    held += S.marker(1)
    assert list(removes(held, S.marker(1))) == [S.done]
    assert list(held[S.marker(V.n)]) == []
