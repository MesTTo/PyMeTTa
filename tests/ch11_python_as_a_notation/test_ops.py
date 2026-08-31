"""Purpose: engine-backed tests for Python-backed MeTTa functions: kinds,
typing from annotations, defaults as arities, declines, errors, raw mode,
and the py-atom surface where the shim's presence changes the answer.
Guarantees:
  - an Atom annotation preserves the written call while an unconstrained
    parameter receives its reduction [tested:
    test_an_atom_annotation_changes_evaluation_order_as_documented;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - execution modes are scopes, return shapes are invariant, and callable
    policy is reflected by atoms rather than boolean flags [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - implicit operation names map every underscore to a hyphen while an
    explicit name remains exact [tested: test_op_uses_the_define_name_ladder;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - one encoded generator supplies positional and sparse relational rows in
    every binding direction without changing answer multiplicity, and an
    effectful producer runs once per yielded candidate [tested:
    test_relational_tuple_candidates_unify_in_all_directions_without_changing_multiplicity,
    test_sparse_relational_dict_candidates_bind_parameter_names,
    test_effectful_relational_candidates_run_once_per_yield_on_fresh_list;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - coroutine functions, including wrapped and callable forms, register as
    async operations and answer typed future spaces [tested:
    test_register_op_reads_co_flags_and_refuses_or_awaits; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import asyncio
import functools
import inspect
import types
import uuid
from collections import Counter

import pytest

from metta import (
    TRUE,
    UNIT,
    Answer,
    Atom,
    Expression,
    MeTTa,
    NotReducible,
    S,
    Symbol,
    V,
    aio,
    ground,
    reflection,
)
from metta._space import Space
from metta.errors import EngineError, StrictError


def unique(prefix: str) -> str:  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_op_uses_the_define_name_ladder(metta):  # noqa: D103 -- pytest discovers this naming contract by name
    @metta.op(effect="pureStructural")
    def implicit_operation(value):
        return value

    @metta.op(name="exact_operation", effect="pureStructural")
    def explicit_operation(value):
        return value

    try:
        assert metta.eval(S.implicit_operation(7)) == [7]
        assert metta.eval(S["exact_operation"](8)) == [8]
        assert metta.eval(S["implicit_operation"](7)) == [S["implicit_operation"](7)]
    finally:
        for registered_name in ("implicit-operation", "implicit_operation", "exact_operation"):
            try:
                metta.unregister_op(registered_name)
            except KeyError:
                pass


def test_det_op_composes_with_equations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = unique("dbl")

    @metta.op(name=name, effect="pureStructural")
    def double(x: int) -> int:
        return 2 * x

    assert metta.run(f"!({name} 21)") == [[42]]
    quad = unique("quad")
    assert metta.run(f"(= ({quad} $x) ({name} ({name} $x)))\n!({quad} 5)") == [[20]]


def test_an_atom_annotation_changes_evaluation_order_as_documented(metta):
    """An Atom annotation preserves the written call; a bare parameter receives its reduction."""
    atom_name = unique("anyatom")
    value_name = unique("anyval")

    @metta.op(name=atom_name, effect="pureStructural")
    def anyatom(term: Atom) -> Atom:
        return term

    @metta.op(name=value_name, effect="pureStructural")
    def anyval(term):
        return term

    metta.run("(= (p5-side) 42)")
    assert metta.run(f"!({atom_name} (p5-side))") == [[S["p5-side"]()]]
    assert metta.run(f"!({value_name} (p5-side))") == [[42]]


def test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms(
    metta,
):
    """Execution policy scopes compose; callable policy is queryable data."""
    from metta._prelude import NAMES as PRELUDE_NAMES

    for method, removed in (
        (Space.run, {"capture", "atomic", "speculative", "strict", "using"}),
        (Space.eval, {"capture", "residuals"}),
        (Space.op, {"typed", "raw", "pass_atoms", "pure"}),
        (aio.AsyncMeTTa.run, {"capture", "atomic", "speculative", "strict"}),
        (aio.AsyncMeTTa.eval, {"capture", "residuals"}),
        (aio.AsyncMeTTa.op, {"typed", "raw", "pass_atoms", "pure"}),
        (aio.AsyncMeTTa.op, {"typed", "raw", "pass_atoms", "pure"}),
    ):
        assert removed.isdisjoint(inspect.signature(method).parameters)

    with metta.capture() as output:
        groups = metta.run("!(println! p5-captured) !(+ 1 2)")
        answers = metta.eval("(+ 2 3)")
    assert groups == [[TRUE], [3]]
    assert answers == [5]
    assert output.text == "p5-captured\n"

    async def async_capture():
        async with aio.AsyncMeTTa(metta=metta) as asynchronous:
            with asynchronous.capture() as async_output:
                async_groups = await asynchronous.run("!(println! p5-async)")
            return async_groups, async_output.text

    assert asyncio.run(async_capture()) == ([[TRUE]], "p5-async\n")

    with metta.speculative():
        assert metta.run("(p5-speculative fact) !(+ 2 2)") == [[4]]
    assert len(metta.match(Expression(S["p5-speculative"], V.x))) == 0

    with pytest.raises(EngineError):
        with metta.atomic():
            # Integer division by zero answers an Error atom under the P1.34
            # doctrine, so the rollback trigger is a host instantiation fault.
            metta.run("(p5-atomic fact) !(+ $left $right)")
    assert len(metta.match(Expression(S["p5-atomic"], V.x))) == 0

    with pytest.raises(StrictError):
        with metta.strict():
            metta.run("!(p5-does-not-reduce 1)")

    prelude_names = {S[name] for name in PRELUDE_NAMES}
    assert not any(
        isinstance(atom, Expression)
        and atom.head in (S[":"], S["@doc"])
        and atom.args[0] in prelude_names
        for atom in metta.atoms()
    )
    reflection = metta._at("&metta")
    assert {
        row.name
        for row in reflection.match(Expression(S.arguments, V.name, S.atoms))
    } >= prelude_names

    name = unique("p5-policy")
    effect = Expression(S.effect, S[name], S.pureStructural)

    @metta.op(
        name=name,
        transport="raw",
        effect="pureStructural",
    )
    def policy_operation(value):
        return value

    assert [row.kind for row in reflection.match(Expression(S.op, S[name], 1, V.kind))] == [
        S["raw_det"]
    ]
    assert [
        row.effect for row in reflection.match(Expression(S.effect, S[name], V.effect))
    ] == [S.pureStructural]
    assert effect in reflection
    assert metta.run(f"!({name} 7)") == [[7]]

    atoms_name = unique("p5-atoms")
    arguments = Expression(S.arguments, S[atoms_name], S.atoms)
    seen = []

    @metta.op(name=atoms_name, effect="writesState", declarations=[arguments])
    def atom_arguments(value):
        seen.append(value)
        return value

    assert metta.run(f"!({atoms_name} 8)") == [[8]]
    assert isinstance(seen[0], Atom)
    assert [
        row.delivery
        for row in reflection.match(Expression(S.arguments, S[atoms_name], V.delivery))
    ] == [S.atoms]

    refused_name = unique("p5-raw-atoms")
    with pytest.raises(ValueError, match="raw calls do not cross the atom codec"):
        metta.op(
            lambda value: value,
            name=refused_name,
            transport="raw",
            effect="pureStructural",
            declarations=[Expression(S.arguments, S[refused_name], S.atoms)],
        )

    metta.unregister_op(atoms_name)
    metta.unregister_op(name)
    assert not reflection.match(Expression(S.arguments, S[atoms_name], V.delivery))
    assert effect not in reflection


def test_a_python_op_is_a_higher_order_argument(metta):
    """A registered operation reaches the specializer by name, like `(+ 1)`.

    examples/ch05-equations-and-evaluation/05-02-changing-the-equations/04-specialize.metta tests the native partial application
    in this position and nothing tested a Python operation there, so the
    specializer taking one was true and unguarded. What is asserted is the
    equivalence rather than the literal answer, because the claim is that the
    Python operation behaves the same in this position and not merely that it
    works. Both spellings count: the function argument of a user-defined
    recursion, which is where the specializer runs, and the argument of the
    builtin map-atom, which is a different path.
    """
    inc = unique("inc")

    @metta.op(name=inc, effect="pureStructural")
    def increment(x: int) -> int:
        return x + 1

    hof = unique("hof-map")
    metta.run(
        f"(= ({hof} $f ()) ())\n"
        # cons is cons-atom's spelling and both its parameters carry the
        # evaluation mask, so the applied head and the recursive tail are each
        # NAMED before it reads them, left to right.
        f"(= ({hof} $f (cons $x $xs))\n"
        f"   (let $head ($f $x)\n"
        f"     (let $rest ({hof} $f $xs) (cons $head $rest))))"
    )
    native = metta.run(f"!({hof} (+ 1) (1 2 3))")[-1]
    assert native == [Expression(2, 3, 4)]
    assert metta.run(f"!({hof} {inc} (1 2 3))")[-1] == native
    assert metta.run(f"!(map-atom (1 2 3) {inc})")[-1] == native


def test_generator_is_nondeterministic(metta):
    """Each generator yield remains one composable engine answer."""
    name = unique("upto")

    @metta.op(name=name, effect="nondeterministicReadOnly")
    def upto(n: int):
        yield from range(1, n + 1)

    assert metta.run(f"!(collapse ({name} 3))") == [[Expression(1, 2, 3)]]
    # Composes with let and arithmetic like any nondeterministic function.
    assert metta.run(f"!(collapse (let $x ({name} 3) (* $x 10)))") == [[Expression(10, 20, 30)]]


def test_relational_tuple_candidates_unify_in_all_directions_without_changing_multiplicity(
    metta,
) -> None:
    """Each positional row is one candidate parameter binding, duplicates included."""
    name = unique("route")
    candidates = [
        (S.paris, S.lyon),
        (S.paris, S.lyon),
        (S.lyon, S.nice),
    ]

    @metta.op(name=name, effect="nondeterministicReadOnly")
    def route(origin, destination):
        del origin, destination
        yield from candidates

    all_directions = metta.fn[name](V.origin, V.destination)
    assert list(all_directions) == [UNIT, UNIT, UNIT]
    assert Counter((row.origin, row.destination) for row in all_directions.rows) == Counter(
        {
            (S.paris, S.lyon): 2,
            (S.lyon, S.nice): 1,
        }
    )

    forwards = metta.fn[name](S.paris, V.destination)
    assert list(forwards) == [UNIT, UNIT]
    assert Counter(row.destination for row in forwards.rows) == Counter({S.lyon: 2})

    backwards = metta.fn[name](V.origin, S.lyon)
    assert list(backwards) == [UNIT, UNIT]
    assert Counter(row.origin for row in backwards.rows) == Counter({S.paris: 2})

    assert list(metta.fn[name](S.paris, S.lyon)) == [UNIT, UNIT]
    assert list(metta.fn[name](S.paris, S.nice)) == []

    numeric = unique("numeric-relation")

    @metta.op(name=numeric, effect="nondeterministicReadOnly")
    def numeric_relation(value):
        del value
        yield (1,)

    assert list(metta.fn[numeric](1.0)) == [UNIT]


def test_sparse_relational_dict_candidates_bind_parameter_names(metta) -> None:
    """A dict row constrains only the signature positions whose names it carries."""
    name = unique("sparse-route")

    @metta.op(name=name, effect="nondeterministicReadOnly")
    def route(origin, runtime: MeTTa, destination):
        del origin, runtime, destination
        yield {"origin": S.paris, "destination": S.lyon}
        yield {"origin": S.paris, "destination": S.lyon}
        yield {"destination": S.nice}

    all_directions = metta.fn[name](V.origin, V.destination)
    assert list(all_directions) == [UNIT, UNIT, UNIT]
    assert Counter(row.destination for row in all_directions.rows) == Counter(
        {S.lyon: 2, S.nice: 1}
    )

    forwards = metta.fn[name](S.rome, V.destination)
    assert list(forwards) == [UNIT]
    assert forwards.destination == [S.nice]

    backwards = metta.fn[name](V.origin, S.lyon)
    assert list(backwards) == [UNIT, UNIT]
    assert Counter(row.origin for row in backwards.rows) == Counter({S.paris: 2})

    assert list(metta.fn[name](S.rome, S.nice)) == [UNIT]
    assert list(metta.fn[name](S.paris, S.nice)) == [UNIT]
    assert list(metta.fn[name](S.rome, S.lyon)) == []


def test_effectful_relational_candidates_run_once_per_yield_on_fresh_list(metta) -> None:
    """A reverse filter visits each candidate once and answers matching rows."""
    name = unique("effectful-route")
    candidates = [
        (S.paris, S.lyon),
        (S.paris, S.lyon),
        (S.lyon, S.nice),
    ]
    effects: list[tuple[Symbol, Symbol]] = []

    @metta.op(name=name, effect="writesState")
    def route(origin, destination):
        del origin, destination
        for candidate in candidates:
            effects.append(candidate)
            yield candidate

    assert list(metta.fn[name](V.origin, S.lyon)) == [UNIT, UNIT]
    assert effects == candidates


def test_relational_candidate_shape_errors_are_contract_errors(metta) -> None:
    """Malformed rows fail loudly even under operation error-recovery policy."""
    wide = unique("wide-route")
    unknown = unique("unknown-route")
    missing = unique("none-route")
    nested_answer = unique("nested-answer-route")
    repeated = unique("repeated-route")

    @metta.op(name=wide, effect="nondeterministicReadOnly")
    def wide_route(origin, destination):
        del origin, destination
        yield (S.paris, S.lyon, S.nice)

    @metta.op(name=unknown, effect="nondeterministicReadOnly")
    def unknown_route(origin, destination):
        del origin, destination
        yield {"origin": S.paris, "arrival": S.lyon}

    @metta.op(name=missing, effect="nondeterministicReadOnly")
    def missing_route(origin, destination):
        del origin, destination
        yield (None, S.lyon)

    @metta.op(name=nested_answer, effect="nondeterministicReadOnly")
    def nested_answer_route(origin, destination):
        del origin, destination
        yield (Answer(value=S.paris), S.lyon)

    @metta.op(name=repeated, arities=[2], effect="nondeterministicReadOnly")
    def repeated_route(*items):
        del items
        yield {"items": S.paris}

    metta.on_error(wide, S[wide](V.origin, V.destination), "keep")
    metta.on_error(unknown, S[unknown](V.origin, V.destination), "empty")
    metta.on_error(missing, S[missing](V.origin, V.destination), "keep")
    metta.on_error(
        nested_answer,
        S[nested_answer](V.origin, V.destination),
        "empty",
    )
    metta.on_error(repeated, S[repeated](V.left, V.right), "keep")

    with pytest.raises(EngineError, match="yielded a tuple of width 3, but this call takes 2"):
        list(metta.fn[wide](V.origin, V.destination))
    with pytest.raises(EngineError, match=r"yielded unknown parameter key.*arrival"):
        list(metta.fn[unknown](V.origin, V.destination))
    with pytest.raises(EngineError, match=r"yielded None for parameter 'origin'"):
        list(metta.fn[missing](V.origin, V.destination))
    with pytest.raises(EngineError, match=r"yielded Answer for parameter 'origin'"):
        list(metta.fn[nested_answer](V.origin, V.destination))
    with pytest.raises(
        EngineError,
        match=r"repeated variadic parameters; yield a positional tuple of width 2",
    ):
        list(metta.fn[repeated](V.left, V.right))


def test_explicit_answer_value_preserves_generator_tuple_and_dict_results(metta) -> None:
    """Answer(value=...) keeps exact tuple and dict values out of row syntax."""
    tuple_name = unique("tuple-value")
    dict_name = unique("dict-value")
    mapping = {"origin": S.paris, "destination": S.lyon}

    @metta.op(name=tuple_name, effect="nondeterministicReadOnly")
    def tuple_value(_left, _right):
        yield Answer(value=(S.paris, S.lyon))

    @metta.op(name=dict_name, effect="nondeterministicReadOnly")
    def dict_value(_left, _right):
        yield Answer(value=mapping)

    assert list(metta.fn[tuple_name](S.any, S.arguments)) == [
        Expression(S.paris, S.lyon)
    ]
    dict_answers = list(metta.fn[dict_name](S.any, S.arguments))
    assert dict_answers == [ground(mapping)]
    assert dict_answers[0].value is mapping


def test_raw_generators_refuse_relational_rows(metta) -> None:
    """Raw arguments cannot represent unbound positions, so relation rows require the wire."""
    name = unique("raw-route")

    @metta.op(name=name, transport="raw", effect="nondeterministicReadOnly")
    def raw_route(_origin, _destination):
        yield ("paris", "lyon")

    with pytest.raises(EngineError, match="raw generator yielded a relational tuple or dict"):
        list(metta.fn[name](S.paris, S.lyon))


def test_register_op_reads_co_flags_and_refuses_or_awaits(metta):
    """Coroutine functions route to futures; unsupported async shapes refuse."""
    from metta.ops import registered
    from metta.parallel import FutureSpace

    async def coroutine(value):
        return value

    async def async_generator(value):
        yield value

    @types.coroutine
    def iterable_coroutine(value):
        yield value

    class CallableCoroutine:
        async def __call__(self, value):
            return value

    def wrapped(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    accepted = [
        coroutine,
        functools.partial(coroutine),
        CallableCoroutine(),
        wrapped(coroutine),
    ]
    for fn in accepted:
        name = unique("awaitable")
        metta.op(fn, name=name, effect="pureStructural")
        try:
            future = metta.eval(S[name](7))[0]
            assert isinstance(future, FutureSpace)
            assert list(future.wait()) == [7]
            assert metta.type(S[name](7)) == S.SpaceType
            assert registered()[name].kind == "async"
        finally:
            metta.unregister_op(name)

    refused = [
        ("async-generator function", async_generator, "nondeterministicReadOnly"),
        ("generator-based coroutine", iterable_coroutine, "pureStructural"),
    ]
    for expected, fn, effect in refused:
        name = unique("awaitable")
        with pytest.raises(TypeError, match=expected):
            metta.op(fn, name=name, effect=effect)
        assert name not in registered()
        assert not any(
            isinstance(atom, Expression)
            and atom.children[:2] == (S.op, S[name])
            for atom in reflection.atoms()
        ), name

    # Ordinary generators still use the many path after the same flag walk.
    name = unique("ordinary-generator")

    def ordinary(value):
        yield value

    metta.op(ordinary, name=name, effect="nondeterministicReadOnly")
    try:
        assert metta.run(f"!({name} 7)") == [[7]]
        assert registered()[name].kind == "many"
    finally:
        metta.unregister_op(name)


def test_none_and_decline_answer_nothing(metta):
    """Both semidet decline spellings produce no operation answer."""
    evens = unique("evens")
    picky = unique("picky")

    @metta.op(name=evens, effect="pureStructural")
    def only_even(x: int):
        return x if x % 2 == 0 else None

    @metta.op(name=picky, effect="pureStructural")
    def picky_op(x: int):
        if x < 0:
            raise NotReducible
        return x

    r = metta.run(f"!(collapse (superpose (({evens} 1) ({evens} 2) ({evens} 3))))")
    assert r == [[Expression(2)]]
    r = metta.run(f"!(collapse (superpose (({picky} -1) ({picky} 7))))")
    assert r == [[Expression(7)]]


def test_python_exception_is_a_hard_error(metta):
    """An undeclared operation exception crosses as a hard engine error."""
    name = unique("boom")

    @metta.op(name=name, effect="pureStructural")
    def boom(x: int) -> int:  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        msg = "exploded on purpose"
        raise ValueError(msg)

    with pytest.raises(EngineError) as excinfo:
        metta.run(f"!({name} 1)")
    assert "exploded on purpose" in str(excinfo.value)


def test_annotations_declare_types(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = unique("typed")

    @metta.op(name=name, effect="pureStructural")
    def typed_op(x: int) -> int:
        return x

    assert metta.run(f"!(get-type ({name} 1))") == [[S.Number]]


def test_a_variable_crossing_python_comes_back_the_same_variable(metta):
    """A variable that goes into an operation and comes back is the SAME one.

    The boundary encodes a variable by its printed name and the decoder built a
    fresh variable for that name, so identity was lost: a native
    `(= (mcons $h $t) ($h 2 3))` answers an expression whose head IS `$x`, and
    binding the answer to `(9 2 3)` binds `$x` to 9, while the same shape
    through a registered operation answered an unrelated variable that binding
    did nothing to. No relational use of a Python operation could work while
    that held, which is the root of what looked like "inversion does not
    cross".

    The native function is measured alongside rather than assumed, because the
    claim is that the two agree and not that the Python one does something in
    particular.
    """
    op, native = unique("pcons"), unique("mcons")

    @metta.op(name=op, effect="pureStructural")
    def cons(head, tail):
        return (head, *tail)

    metta.run(f"(= ({native} $h $t) ($h 2 3))")
    bind_the_answer = "(let $r ({} $x (2 3)) (let $r (9 2 3) $x))"
    assert metta.run(f"!{bind_the_answer.format(native)}") == [[9]]
    assert metta.run(f"!{bind_the_answer.format(op)}") == [[9]]
    # And a ground call is untouched by any of it.
    assert metta.run(f"!({op} 1 (2 3))") == [[Expression(1, 2, 3)]]


def test_a_registered_operation_runs_backwards(metta):
    """An inverse lets a Python operation stand in a pattern position.

    A foreign function cannot be narrowed, which is why Curry does not invert
    its own `external` functions either, so the backwards direction is
    supplied rather than derived. The mode test compiles INTO the clause, so
    an operation without an inverse keeps the body it had.
    """
    cons = unique("cons")
    metta.op(
        lambda head, tail: (head, *tail),
        name=cons,
        effect="pureStructural",
        inverse=lambda whole: (whole[0], tuple(whole[1:])),
    )
    assert metta.run(f"!({cons} 1 (2 3))") == [[Expression(1, 2, 3)]]
    assert metta.run(f"!(let ({cons} $h $t) (1 2 3) ($h $t))") == [
        [Expression(1, Expression(2, 3))]
    ]

    # An inverse is a RELATION, so it enumerates, and a result with no
    # preimage fails rather than raising, exactly as it would forwards.
    square = unique("sq")

    def roots(value):
        yield (int(value**0.5),)
        yield (-int(value**0.5),)

    metta.op(
        lambda x: x * x,
        name=square,
        effect="nondeterministicReadOnly",
        inverse=roots,
    )
    assert metta.run(f"!(collapse (let ({square} $r) 9 $r))") == [[Expression(3, -3)]]
    assert metta.run(f"!({square} 4)") == [[16]]

    double = unique("double")
    metta.op(
        lambda x: x * 2,
        name=double,
        effect="pureStructural",
        # A bare value at arity one, and None for no preimage.
        inverse=lambda y: None if y % 2 else y // 2,
    )
    assert metta.run(f"!(let ({double} $n) 8 $n)") == [[4]]
    assert metta.run(f"!(collapse (let ({double} $n) 7 $n))") == [[Expression()]]


def test_a_pure_python_operation_can_be_declared_and_cached(metta):
    """An operation could not be declared pure by ANY route, and the refusal
    that said to do it named the bridge instead of the operation.

    Two halves. The refusal read the dispatch goal's functor, so it said
    `metta_py_dispatch_det/3`, which is neither something an author wrote nor
    something a declaration could match. And seam:pure_operation/1 was
    multifile but not dynamic, so a running process could add nothing to it
    even knowing the right name.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(import! &self (library lib_tabling))")
    declared, stateful = unique("psize"), unique("qsize")
    metta.op(
        len,
        name=declared,
        effect="pureStructural",
    )
    calls = []

    def counted_size(value):
        calls.append(value)
        return len(value)

    metta.op(counted_size, name=stateful, effect="writesState")
    metta.run(f"(= (uses-{declared} $k) ({declared} $k))")
    metta.run(f"(= (uses-{stateful} $k) ({stateful} $k))")

    assert metta.run(f"!(tabled (uses-{declared} $k))") == [[True]]

    with pytest.raises(EngineError) as refused:
        metta.run(f"!(tabled (uses-{stateful} $k))")
    message = str(refused.value)
    assert f"{stateful}/1" in message, message
    assert "metta_py_dispatch" not in message, message


def test_registering_an_operation_leaves_the_engines_pure_list_alone(metta):
    """Withdrawing one declaration must not take the engine's list with it.

    A host declaration went into seam:pure_operation/1 itself, and the
    engine's own entries there are RULES with a variable head, so the
    retractall that withdraws one declaration unified with every one of them:
    five clauses to zero, and `+` stopped being pure, from registering any
    operation at all. Host declarations live in their own table now.
    """
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (arith-before $k) (+ $k 1))")
    assert metta.run("!(tabled (arith-before $k))") == [[True]]

    for index in range(3):
        name = unique(f"churn{index}")
        metta.op(
            len,
            name=name,
            effect="pureStructural",
        )

    metta.run("(= (arith-after $k) (+ $k 1))")
    assert metta.run("!(tabled (arith-after $k))") == [[True]], (
        "registering an operation withdrew the engine's own purity list"
    )


def test_a_raw_operation_fails_like_an_encoded_one(metta):
    """Skipping the wire encoding is a decision about ARGUMENTS and results.

    It was never a decision to report failures differently, and it was: a raw
    operation's Python failure reached MeTTa as janus's own term, carrying the
    live exception object, a live traceback and an unbound context, which is
    exactly the defect the encoded paths were fixed for.
    """
    raw, encoded = unique("rboom"), unique("eboom")
    metta.op(lambda x: x // 0, name=raw, transport="raw", effect="pureStructural")
    metta.op(lambda x: x // 0, name=encoded, effect="pureStructural")

    caught = {
        label: str(metta.run(f"!(catch ({name} 1))")[-1][0])
        for label, name in (("raw", raw), ("encoded", encoded))
    }
    for label, rendered in caught.items():
        assert "ZeroDivisionError" in rendered, (label, rendered)
        assert "division by zero" in rendered, (label, rendered)
        assert "0x" not in rendered, (label, rendered)
        assert "python_stack" not in rendered, (label, rendered)
    # Same shape from both doors, with only the operation's own name differing.
    assert caught["raw"].replace(raw, "N") == caught["encoded"].replace(encoded, "N")


def test_a_raw_operations_inverse_crosses_raw_too(metta):
    """One function pair should not see two value conventions.

    A raw operation takes janus's conversions forwards, so a symbol reaches it
    as `str`. Its inverse went through the wire encoding and got `Symbol`, so an
    author writing the pair had to write two different functions to handle one
    value. Both directions now match whichever kind was registered.
    """
    seen: list[tuple[str, str]] = []

    def forwards(value):
        seen.append(("forwards", type(value).__name__))
        return value

    def backwards(value):
        seen.append(("backwards", type(value).__name__))
        return value

    for label, transport in (("raw", "raw"), ("encoded", "encoded")):
        name = unique(label)
        metta.op(
            forwards,
            name=name,
            transport=transport,
            effect="writesState",
            inverse=backwards,
        )
        seen.clear()
        metta.run(f"!({name} sym)")
        metta.run(f"!(let ({name} $n) sym $n)")
        kinds = {kind for _, kind in seen}
        assert len(kinds) == 1, f"{label} saw {seen}"
        assert kinds == ({"str"} if transport == "raw" else {"Symbol"}), (
            f"{label} saw {seen}"
        )


def test_an_inverse_of_the_wrong_width_is_refused(metta):
    """A tuple of the wrong width would unify against nothing and read as
    "this result has no preimage", which is the one answer an inverse is
    entitled to give and the one that would hide the mistake.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = unique("wide")
    metta.op(
        lambda a, b: (a, b),
        name=name,
        effect="pureStructural",
        inverse=lambda _: (1, 2, 3),
    )
    with pytest.raises(EngineError) as refused:
        metta.run(f"!(let ({name} $a $b) (1 2) ($a $b))")
    assert "width 3" in str(refused.value)
    assert "takes 2" in str(refused.value)


def test_an_operation_failure_names_the_metta_call(metta):
    """A registered operation was the one Python caller outside the guard.

    Without it janus's own error term reached MeTTa carrying the live
    exception object and a live traceback object, naming a Python file and
    line and no MeTTa call. That is the defect engine/python.pl fixed for py-call
    and py-atom, and an operation did not get it, so a caught error could not
    be compared or printed after the failure.
    """
    name = unique("boom")

    @metta.op(name=name, effect="pureStructural")
    def boom(x: int) -> int:
        return x // 0

    caught = metta.run(f"!(catch ({name} 1))")[-1]
    assert len(caught) == 1
    rendered = str(caught[0])
    assert "ZeroDivisionError" in rendered
    assert "division by zero" in rendered
    assert f"({name} 1)" in rendered, rendered
    # Nothing in it is a live object, so it survives the failure and prints.
    assert "0x" not in rendered, rendered


def test_an_unbound_argument_is_named_when_python_fails(metta):
    """Naming the position is the difference between a Python internals
    message and knowing that a pattern position was the mistake.

    It is a note on a failure that already happened, not a check before the
    call: an unbound argument is legitimate for an operation written to take a
    pattern apart, so only the operations that cannot serve the position fail,
    and only those get the note.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    one, two = unique("ptail"), unique("pcons")

    @metta.op(name=one, effect="pureStructural")
    def tail(rest):
        return (0, *rest)

    @metta.op(name=two, effect="pureStructural")
    def cons(head, rest):
        return (head, *rest)

    with pytest.raises(EngineError) as singular:
        metta.run(f"!(let ({one} $t) (0 1) $t)")
    assert "argument 1 was unbound" in str(singular.value)
    assert "runs forwards only" in str(singular.value)

    with pytest.raises(EngineError) as plural:
        metta.run(f"!(let ({two} $h $t) (1 2 3) ($h $t))")
    assert "arguments 1, 2 were unbound" in str(plural.value)

    # A failure with every argument bound gets no note, so the note means
    # something when it does appear.
    grounded = unique("plain")

    @metta.op(name=grounded, effect="pureStructural")
    def plain(x: int) -> int:
        return x // 0

    with pytest.raises(EngineError) as bound:
        metta.run(f"!({grounded} 1)")
    assert "unbound" not in str(bound.value)


def test_every_argument_shape_reaches_python_as_its_own_kind(metta):
    """The wire encoder's clauses are mutually exclusive, so their ORDER is a
    pure cost decision, and py_is_object/1 was moved behind the free type
    tests because it is a foreign call into janus that ran on every argument
    and every list element before anything asked whether the value was a
    number.

    The property test in test_properties.py fuzzes that encoder over generated
    atoms, and a generated atom is never a live Python object, which is the
    one clause the move put at the END. So the shapes are pinned here from the
    outside: what each one arrives as in Python is what says the reorder
    changed nothing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = unique("kindof")

    @metta.op(name=name, effect="pureStructural")
    def kind_of(x):
        return type(x).__name__

    shapes = {
        "1": "int",
        "2.5": "float",
        '"txt"': "str",
        "sym": "Symbol",
        "True": "bool",
        "(1 2)": "Expression",
        "()": "Expression",
        "(a (b 1))": "Expression",
        '(py-atom "object()")': "object",
    }
    for source, expected in shapes.items():
        assert metta.run(f"!({name} {source})") == [[expected]], source


def test_annotations_and_explicit_atoms_are_the_two_typing_routes(metta):
    """Annotations derive arrows; an unannotated callable claims no type."""
    annotated, bare, declared = unique("ann"), unique("bare"), unique("declared")

    @metta.op(name=annotated, effect="pureStructural")
    def with_annotations(x: int) -> int:
        return x

    @metta.op(name=bare, effect="pureStructural")
    def without_annotations(x):
        return x

    arrow = Expression(S["->"], S.Number, S.Number)
    metta.op(
        lambda x: x,
        name=declared,
        effect="pureStructural",
        declarations=[Expression(S[":"], S[declared], arrow)],
    )

    assert metta.run(f"!(get-type {annotated})") == [[Expression(S["->"], S.Number, S.Number)]]
    assert metta.run(f"!(get-type {bare})") == [[S["%Undefined%"]]]
    assert metta.run(f"!(get-type {declared})") == [[arrow]]


def test_defaults_register_every_arity(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = unique("greet")

    @metta.op(name=name, effect="pureStructural")
    def greet(who: str, greeting: str = "hello") -> str:
        return f"{greeting}, {who}"

    assert metta.run(f'!({name} "Ada")') == [["hello, Ada"]]
    assert metta.run(f'!({name} "Ada" "hi")') == [["hi, Ada"]]


def test_ops_see_atoms_not_mush(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = unique("peek")
    seen = []

    @metta.op(name=name, effect="writesState")
    def peek(x) -> bool:
        seen.append(x)
        return True

    metta.run(f'!({name} foo)\n!({name} "foo")\n!({name} True)\n!({name} (a 1))')
    sym_arg, str_arg, bool_arg, expr_arg = seen
    assert sym_arg == S.foo and isinstance(sym_arg, Symbol)
    assert str_arg == "foo" and isinstance(str_arg, str)
    assert bool_arg is True
    assert isinstance(expr_arg, Expression) and expr_arg[0] == S.a and expr_arg[1] == 1


def test_atom_annotations_hand_over_atoms(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = unique("atoms")
    seen = []

    @metta.op(name=name, effect="writesState")
    def watch(x: Atom) -> bool:
        seen.append(x)
        return True

    metta.run(f"!({name} 42)")
    assert isinstance(seen[0], Atom) and seen[0] == 42


def test_objects_flow_through_ops_by_identity(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    make = unique("make")
    read = unique("read")

    class Counter:
        def __init__(self):
            self.n = 0

    box = []

    @metta.op(name=make, effect="writesState")
    def make_counter():
        c = Counter()
        box.append(c)
        return ground(c)

    @metta.op(name=read, effect="writesState")
    def read_counter(c) -> int:
        assert c is box[0]
        c.n += 1
        return c.n

    assert metta.run(f"!({read} ({make}))") == [[1]]
    assert box[0].n == 1


def test_raw_mode_for_number_work(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = unique("rawsum")

    @metta.op(name=name, transport="raw", effect="pureStructural")
    def raw_sum(a, b):
        return a + b

    assert metta.run(f"!({name} 20 22)") == [[42]]


def test_operation_registration_names_are_symmetric(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert not hasattr(metta, "register_op")
    assert hasattr(metta, "op")
    assert hasattr(metta, "unregister_op")
    assert metta.op.__func__ is metta.op.__func__
    assert not hasattr(metta, "unregister")

    @metta.op(name="very-unique-op-name-xyz", effect="pureStructural")
    def very_unique_op_name_xyz(x: int) -> int:
        return x

    assert metta.run("!(very-unique-op-name-xyz 9)") == [[9]]
    metta.unregister_op("very-unique-op-name-xyz")
    # Unregistered: the call no longer reduces, the engine leaves it inert.
    r = metta.run("!(very-unique-op-name-xyz 9)")
    assert r == [[Expression(S["very-unique-op-name-xyz"], 9)]]


def test_var_kw_params_are_refused(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError):

        @metta.op(effect="pureStructural")
        def bad(*args):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
            return 0

    with pytest.raises(TypeError):

        @metta.op(effect="pureStructural")
        def bad2(*, key=1):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
            return 0


def test_engine_injection_by_annotation(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # FastAPI's Depends read the house way: a metta.MeTTa annotation is
    # the request, the framework fills it, and the MeTTa call site never
    # sees the slot.
    metta.run("(inj-link a b) (inj-link b c)")

    @metta.op(name="inj-related", effect="nondeterministicReadOnly")
    def inj_related(term, engine: MeTTa):
        for row in engine.self.match(Expression(S["inj-link"], term, V.x)):
            yield row[0]

    try:
        assert metta.run("!(collapse (inj-related a))") == [[Expression(S.b)]]
        # the declared arrow has ONE argument slot: the engine is not a type
        (group,) = metta.run("!(get-type inj-related)")
        assert str(group[0]) == "(-> %Undefined% %Undefined%)"
    finally:
        metta.unregister_op("inj-related")


def test_injection_binds_the_calling_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The engine injects ITSELF bound to the current context's space, the
    # &self reading, so one op behaves per-space without a space argument.
    @metta.op(name="inj-here", effect="readOnlyLookup")
    def inj_here(engine: MeTTa):
        return str(engine.self.name)

    try:
        with metta._new_space() as other:
            other.run("(= (inj-probe) (inj-here))")
            (group,) = other.run("!(inj-probe)")
            assert group[0] == str(other.name)
        (group,) = metta.run("!(inj-here)")
        assert group[0] == "&self"
    finally:
        metta.unregister_op("inj-here")


def test_injection_composes_with_defaults_and_position(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The engine slot may sit anywhere; remaining defaults still ladder
    # the arities, so (inj-mid x) and (inj-mid x y) both serve.
    @metta.op(name="inj-mid", effect="pureStructural")
    def inj_mid(a, engine: MeTTa, b=10):
        assert isinstance(engine, MeTTa)
        return int(a) + int(b)

    try:
        assert metta.run("!(inj-mid 1)") == [[11]]
        assert metta.run("!(inj-mid 1 2)") == [[3]]
    finally:
        metta.unregister_op("inj-mid")


def test_a_name_prolog_owns_registers_and_leaves_prolog_alone(metta):
    """A MeTTa name compiles to a Prolog predicate of one higher arity, and for
    several ordinary words that predicate already belongs to SWI.

    That used to be a refusal, and it had to be: a registered operation's
    clauses went into the module the ENGINE resolves in, so an operation called
    `format` put a format/2 in front of SWI's own and every println! the engine
    ran afterwards reached the operation, printed nothing and raised nothing.
    An operation's clauses go into &self's own module now, where the same
    assert makes a local shadow, so the name is free and the engine's predicate
    goes on answering. Of the 428 names the engine imports, 217 were refused at
    MeTTa arity 1 and 4 are.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for name, arity, call, expected in [
        ("format", 1, "!(format 1)", 1),    # Prolog format/2, a system builtin
        ("print", 1, "!(print 1)", 1),      # print/2, likewise
        ("succ", 1, "!(succ 1)", 1),        # succ/2
        ("between", 2, "!(between 1 2)", 1),  # between/3
        ("digit", 2, "!(digit 1 2)", 1),    # digit/3, from library(dcg/basics)
        ("last", 1, "!(last 1)", 1),        # last/2, from library(lists)
        ("select", 2, "!(select 1 2)", 1),  # select/3, likewise
    ]:
        metta.op(
            lambda *_a: 1,
            name=name,
            effect="pureStructural",
            arities=[arity],
        )
        try:
            assert metta.run(call) == [[expected]], name
        finally:
            metta.unregister_op(name)

    # The engine is untouched: it still prints its own output, which is the
    # half that used to break silently. Containment rather than equality
    # because the fixture is shared and an earlier test may have left the
    # compiled-goal dump on.
    with metta.capture() as output:
        groups = metta.run("!(println! (still here))")
    assert groups == [[TRUE]]
    assert "(still here)\n" in output.text


def test_a_generated_memo_clause_does_not_consume_a_registrable_name(metta):
    """A cached definition's generated replay body must not resolve library
    names in the shared base module. The counted-trie memo's replay clause
    called bare between/3; the module-tier cache asserts into the base tier,
    the first replay resolved between/3 THERE, current_predicate answered
    true from then on, and registering a MeTTa operation named `between`
    refused with metta_op_name_taken for the rest of the process. Found by
    bisecting a serial-order suite failure to
    test_a_cached_definition_memoizes_its_complete_answer_bag
    [measured 2026-08-26]. The generated body now says system:between.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    @metta.cache(name="opsleak-fib", unchecked=True)
    def opsleak_fib(n):
        return n if n < 2 else opsleak_fib(n - 1) + opsleak_fib(n - 2)

    assert opsleak_fib(10) == [55]

    metta.op(lambda *_a: 1, name="between", effect="pureStructural", arities=[2])
    try:
        assert metta.run("!(between 1 2)") == [[1]]
    finally:
        metta.unregister_op("between")


def test_prologs_protected_core_is_still_refused(metta):
    """What is left of the refusal, and it is Prolog's rather than the
    engine's: SWI will not let any module define these, so the assert raises
    wherever the operation's clauses go. call, clause, copy_term and sort are
    the four at MeTTa arity 1 [measured 2026-08-19].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for name, arity in [("sort", 1), ("copy_term", 1), ("call", 1)]:
        with pytest.raises(EngineError) as refused:
            metta.op(
                lambda *_a: 1,
                name=name,
                effect="pureStructural",
                arities=[arity],
            )
        message = str(refused.value)
        assert f"{name}/{arity + 1}" in message, message
        assert "already owns" in message
        assert "name=" in message


def test_a_free_name_that_merely_looks_prolog_still_registers(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # digit/2 is free even though digit/3 is not, so the refusal has to be
    # per arity rather than per name, or it would take names nothing owns.
    name = unique("digit")
    metta.op(lambda _x: 7, name=name, effect="pureStructural", arities=[1])
    try:
        assert metta.run(f"!({name} 1)") == [[7]]
    finally:
        metta.unregister_op(name)


def test_unregistering_a_name_a_system_predicate_shares_does_not_throw(metta):
    """Unregistering asks whether any clause of the name survives, and it
    asked that of every arity of the name, so a name sharing ANY arity with a
    protected system predicate called clause/3 on it and got
    permission_error(access, private_procedure, _) instead of an answer.

    print/6 is free, so this registration is legitimate; print/1 and print/2
    are SWI's and are what the walk trips over. A builtin is never a clause
    of ours, so it is skipped rather than inspected.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.op(
        lambda *_a: 1,
        name="print",
        effect="pureStructural",
        arities=[5],
    )
    try:
        assert metta.run("!(print 1 2 3 4 5)") == [[1]]
    finally:
        metta.unregister_op("print")
    assert metta.run("!(print 1 2 3 4 5)") == [[metta.parse("(print 1 2 3 4 5)")]]


def test_a_tuple_defaults_to_data_and_grounded_retains_a_handle(metta):
    """The default structural answer and explicit host reading are distinct."""
    assert metta.run('!(py-atom "()")') == [[metta.parse("()")]]
    assert metta.run('!((py-atom tuple))') == [[metta.parse("()")]]
    assert metta.run('!(py-atom "(1, 2)")') == [[metta.parse("(1 2)")]]

    ((grounded,),) = metta.run('!(py-atom "(1, 2)" Grounded)')
    assert grounded.metatype == "Grounded"
    assert isinstance(grounded.value, tuple)
    assert grounded.value == (1, 2)
    assert type(grounded.value) is tuple
    # The decoder removes Janus's private carrier before Python sees the value.
    assert metta.run(
        '!(py-dot (py-dot (py-atom "(1, 2)" Grounded) __class__) __name__)'
    ) == [["tuple"]]
    # A returned atom crosses back through Box on public reuse. The bridge
    # removes that transport layer, including inside a container argument.
    with metta.bind(held=grounded):
        assert metta.run("!(car-atom held)") == [[1]]
    with metta.bind(items=Expression(grounded)):
        assert metta.run(
            '!((py-atom "lambda xs: type(xs[0]) is tuple") items)'
        ) == [[True]]
    assert metta.run(
        '!((py-atom "lambda x: x is x[0]") '
        '(py-atom "(lambda x: (x.append(x), x)[1])([])"))'
    ) == [[True]], "checking nested transport must not copy a live cyclic list"
    # the shapes that already worked are untouched
    assert metta.run('!(py-atom "None")') == [[metta.parse("()")]]
    assert metta.run('!(py-atom "[1,2,3]" Expression)') == [[metta.parse("(1 2 3)")]]


def test_a_declared_type_survives_the_library_being_loaded(metta):
    """`(py-atom f Type)` keeps its declaration in the shipped configuration.

    The declaration is published through seam:grounded_extra_type/2, a
    DECLARATION seam, whose every clause is meant to stay reachable
    [source: engine/ext_points.pl, seam:every_clause_runs/1]. It hung off
    the ELSE branch of the ownership seam seam:grounded_type_names/2, and the
    shim answers that one for every Python object, so the whole branch was
    dead here and the declaration was accepted and dropped
    [measured 2026-08-18: `(builtin_function_or_method)` through the
    library against `(builtin_function_or_method (-> Number Number Number))`
    through run.sh].

    This test lives at the LIBRARY door for that reason. The engine-door
    pin, python_surface.plt's a_declared_type_is_reported_beside_the_objects_own,
    was green throughout: plunit loads engine/metta.pl without the shim, so it
    exercises the configuration where the branch is alive. Only the two
    doors together see the defect.
    """
    both = "(builtin_function_or_method (-> Number Number Number))"
    assert metta.run(
        "!(let $f (py-atom math.pow (-> Number Number Number))"
        " (collapse (get-type $f)))"
    ) == [[metta.parse(both)]], "the declared arrow is dropped"
    # A DIFFERENT object, one nothing declares, answers its classes and
    # nothing else, so the union adds no candidate of its own. It has to be
    # a different one: the declaration is keyed on the object and resolving
    # the same name twice resolves to the same object, which is what stops
    # a repeated declaration stacking duplicates.
    assert metta.run("!(let $f (py-atom math.sqrt) (collapse (get-type $f)))") == [
        [metta.parse("(builtin_function_or_method)")]
    ]
