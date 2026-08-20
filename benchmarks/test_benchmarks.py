"""Purpose: calibrated Python-surface performance cases with exact units.
Guarantees:
  - compared cases use identical corpus sizes, limits, and operation units
    [tested benchmark baseline]
  - every mutable engine case receives a fresh space outside its measured
    window [tested benchmark_case]
  - raw and encoded operation cases select one named transport mode [tested:
    test_raw_operation, test_encoded_operation; commit=6fbd5872cc0ff7abf9c99b90f915f8a31470a861]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from tempfile import TemporaryDirectory

from benchmarks.engine_workloads import (
    ALPHA_TERMS,
    DIGEST_ATOMS,
    LET_ITERATIONS,
    LET_SLOPE_SMALL,
    METHOD_CALLS,
    SORT_TERMS,
    SOURCE_FORMS,
    SPACE_NAME_CALLS,
    TYPED_CALLS,
    TYPED_SLOPE_SMALL,
    alpha_unique_case,
    close_engine_case,
    digest_case,
    let_heavy,
    let_space,
    py_method_case,
    sort_atom_case,
    source_load_case,
    space_name_case,
    typed_call,
    typed_space,
)
from benchmarks.workloads import (
    JSON_TRIPS,
    TERM_COUNT,
    WIRE_TRIPS,
    json_payload,
    json_wire,
    term_operators,
    wire_atom,
    wire_codec,
)
from petta import Answer, MeTTa, S, V, expr
from petta.testing import benchmark_case, benchmark_counter_slope, count_atoms

_ROWS = 2_000


def _empty_space():
    return MeTTa().new_space()


def _drop(space):
    space.drop()


def _engine_workload_case(
    benchmark,
    baseline,
    *,
    name,
    unit,
    operations,
    factory,
):
    return benchmark_case(
        benchmark,
        baseline,
        name=name,
        unit=unit,
        operations=operations,
        operation=lambda state: state[1](),
        setup=factory,
        teardown=close_engine_case,
        engine=lambda state: state[0],
        rounds=3,
        warmup_rounds=1,
    )


def _space_with_edges():
    space = _empty_space()
    space.add(*(S.edge(i, i + 1) for i in range(_ROWS)))
    return space


def test_add_single(benchmark, inference_baseline):
    def operation(space):
        for index in range(_ROWS):
            space.add(S.n(index))
        return _ROWS

    benchmark_case(
        benchmark,
        inference_baseline,
        name="add-single",
        unit="atoms",
        operations=_ROWS,
        operation=operation,
        setup=_empty_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_add_batch(benchmark, inference_baseline):
    def operation(space):
        space.add(*(S.n(index) for index in range(_ROWS)))
        return _ROWS

    benchmark_case(
        benchmark,
        inference_baseline,
        name="add-batch",
        unit="atoms",
        operations=_ROWS,
        operation=operation,
        setup=_empty_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_query_rows(benchmark, inference_baseline):
    repeats = 20

    def operation(space):
        return sum(len(space.query(S.edge(V.a, V.b))) for _ in range(repeats))

    benchmark_case(
        benchmark,
        inference_baseline,
        name="query-2k-rows",
        unit="rows",
        operations=repeats * _ROWS,
        operation=operation,
        setup=_space_with_edges,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_eval_arithmetic(benchmark, inference_baseline):
    def operation(space):
        for index in range(_ROWS):
            space.eval(expr(S["+"], index, 1))
        return _ROWS

    benchmark_case(
        benchmark,
        inference_baseline,
        name="eval-arith",
        unit="evaluations",
        operations=_ROWS,
        operation=operation,
        setup=_empty_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def _operation_space(name, *, transport):
    space = _empty_space()

    @space.register_op(name=name, transport=transport)
    def addition(left, right):
        return left + right

    return space


def _drop_operation_space(name):
    def teardown(space):
        space.unregister_op(name)
        space.drop()

    return teardown


def _eval_registered(space, name):
    for index in range(_ROWS):
        space.eval(expr(S[name], index, 1))
    return _ROWS


def test_raw_operation(benchmark, inference_baseline):
    name = "benchmark-raw-operation"
    benchmark_case(
        benchmark,
        inference_baseline,
        name="op-raw",
        unit="evaluations",
        operations=_ROWS,
        operation=lambda space: _eval_registered(space, name),
        setup=lambda: _operation_space(name, transport="raw"),
        teardown=_drop_operation_space(name),
        engine=lambda space: space,
    )


def test_encoded_operation(benchmark, inference_baseline):
    name = "benchmark-encoded-operation"
    benchmark_case(
        benchmark,
        inference_baseline,
        name="op-encoded",
        unit="evaluations",
        operations=_ROWS,
        operation=lambda space: _eval_registered(space, name),
        setup=lambda: _operation_space(name, transport="encoded"),
        teardown=_drop_operation_space(name),
        engine=lambda space: space,
    )


def _countdown_space():
    space = _empty_space()
    space.run("(= (benchmark-countdown $n) (if (> $n 0) (benchmark-countdown (- $n 1)) done))")
    return space


def test_loop_million(benchmark, inference_baseline):
    def operation(space):
        assert space.run("!(benchmark-countdown 1000000)") == [[S.done]]
        return 1_000_000

    benchmark_case(
        benchmark,
        inference_baseline,
        name="loop-1m",
        unit="iterations",
        operations=1_000_000,
        operation=operation,
        setup=_countdown_space,
        teardown=_drop,
        engine=lambda space: space,
        rounds=3,
        warmup_rounds=1,
    )


def test_let_heavy(benchmark, inference_baseline):
    benchmark_case(
        benchmark,
        inference_baseline,
        name="let-heavy",
        unit="iterations",
        operations=LET_ITERATIONS,
        operation=let_heavy,
        setup=let_space,
        teardown=_drop,
        engine=lambda space: space,
        rounds=3,
        warmup_rounds=1,
    )
    benchmark_counter_slope(
        inference_baseline,
        name="let-heavy",
        unit="iterations",
        small_operations=LET_SLOPE_SMALL,
        small_operation=lambda space: let_heavy(space, LET_SLOPE_SMALL),
        large_operations=LET_ITERATIONS,
        large_operation=let_heavy,
        setup=let_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_typed_call(benchmark, inference_baseline):
    """Pin the typed call in BOTH units, because only one of them can see it.

    The inference row here is real and it is not the point: a specialised type
    check compiles to a VM instruction SWI does not count, so this workload's
    inference count is identical with the specialisation and without it. The
    instruction ceiling in benchmarks/baseline.json is what actually gates the
    check, and it is the reason this case exists.
    """
    benchmark_case(
        benchmark,
        inference_baseline,
        name="typed-call",
        unit="calls",
        operations=TYPED_CALLS,
        operation=typed_call,
        setup=typed_space,
        teardown=_drop,
        engine=lambda space: space,
        rounds=3,
        warmup_rounds=1,
    )
    benchmark_counter_slope(
        inference_baseline,
        name="typed-call",
        unit="calls",
        small_operations=TYPED_SLOPE_SMALL,
        small_operation=lambda space: typed_call(space, TYPED_SLOPE_SMALL),
        large_operations=TYPED_CALLS,
        large_operation=typed_call,
        setup=typed_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_wire_codec(benchmark, inference_baseline):
    operations = WIRE_TRIPS * count_atoms(wire_atom())

    benchmark_case(
        benchmark,
        inference_baseline,
        name="wire-codec",
        unit="atom round-trips",
        operations=operations,
        operation=wire_codec,
        setup=wire_atom,
        teardown=lambda _atom: None,
        engine=None,
    )


def test_json_wire(benchmark, inference_baseline):
    benchmark_case(
        benchmark,
        inference_baseline,
        name="json-wire",
        unit="payload round-trips",
        operations=JSON_TRIPS,
        operation=json_wire,
        setup=json_payload,
        teardown=lambda _payload: None,
        engine=None,
    )


def test_run_source(benchmark, inference_baseline):
    repeats = 1_000

    def operation(space):
        for _ in range(repeats):
            space.run("!(+ 1 2)")
        return repeats

    benchmark_case(
        benchmark,
        inference_baseline,
        name="run-source",
        unit="directives",
        operations=repeats,
        operation=operation,
        setup=_empty_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_term_operators(benchmark, inference_baseline):
    benchmark_case(
        benchmark,
        inference_baseline,
        name="term-operators",
        unit="terms",
        operations=TERM_COUNT,
        operation=lambda _state: term_operators(),
        setup=lambda: None,
        teardown=lambda _state: None,
        engine=None,
    )


def _people_space():
    space = _empty_space()
    space.add(*(S.person(S[f"p{i}"], i % 90) for i in range(_ROWS)))
    return space


def test_query_where(benchmark, inference_baseline):
    repeats = 20
    expected_rows = 508
    guard = (V.age >= 18) & (V.age <= 40)

    def operation(space):
        return sum(len(space.query(S.person(V.name, V.age), where=guard)) for _ in range(repeats))

    benchmark_case(
        benchmark,
        inference_baseline,
        name="query-where",
        unit="rows",
        operations=repeats * expected_rows,
        operation=operation,
        setup=_people_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def _prepared_join_space():
    space = _space_with_edges()
    return space, space.prepare(S.edge(V.a, V.b), S.edge(V.b, V.c))


def _drop_pair(state):
    state[0].drop()


def _prepared_join(state, repeats):
    _space, prepared = state
    return sum(len(prepared.solve()) for _ in range(repeats))


def test_prepared_join(benchmark, inference_baseline):
    repeats = 5
    rows = _ROWS - 1

    benchmark_case(
        benchmark,
        inference_baseline,
        name="prepared-join",
        unit="rows",
        operations=repeats * rows,
        operation=lambda state: _prepared_join(state, repeats),
        setup=_prepared_join_space,
        teardown=_drop_pair,
        engine=lambda state: state[0],
    )
    benchmark_counter_slope(
        inference_baseline,
        name="prepared-join",
        unit="rows",
        small_operations=rows,
        small_operation=lambda state: _prepared_join(state, 1),
        large_operations=25 * rows,
        large_operation=lambda state: _prepared_join(state, 25),
        setup=_prepared_join_space,
        teardown=_drop_pair,
        engine=lambda state: state[0],
    )


def _direct_join(space, repeats):
    return sum(len(space.query(S.edge(V.a, V.b), S.edge(V.b, V.c))) for _ in range(repeats))


def test_direct_join(benchmark, inference_baseline):
    repeats = 5
    rows = _ROWS - 1

    benchmark_case(
        benchmark,
        inference_baseline,
        name="direct-join",
        unit="rows",
        operations=repeats * rows,
        operation=lambda space: _direct_join(space, repeats),
        setup=_space_with_edges,
        teardown=_drop,
        engine=lambda space: space,
    )
    benchmark_counter_slope(
        inference_baseline,
        name="direct-join",
        unit="rows",
        small_operations=rows,
        small_operation=lambda space: _direct_join(space, 1),
        large_operations=25 * rows,
        large_operation=lambda space: _direct_join(space, 25),
        setup=_space_with_edges,
        teardown=_drop,
        engine=lambda space: space,
    )


def _limited_query(space, *, guarded):
    kwargs = {"timeout": 30.0, "inferences": 50_000_000} if guarded else {}
    return len(space.query(S.edge(V.a, V.b), limit=50, **kwargs))


def _query_limit_case(benchmark, baseline, *, name, guarded):
    repeats = 100

    def operation(space):
        return sum(_limited_query(space, guarded=guarded) for _ in range(repeats))

    return benchmark_case(
        benchmark,
        baseline,
        name=name,
        unit="rows",
        operations=repeats * 50,
        operation=operation,
        setup=_space_with_edges,
        teardown=_drop,
        engine=lambda space: space,
    )


def test_query_limit_plain(benchmark, inference_baseline):
    _query_limit_case(
        benchmark,
        inference_baseline,
        name="query-limit-plain",
        guarded=False,
    )


def test_query_limit_guarded(benchmark, inference_baseline):
    _query_limit_case(
        benchmark,
        inference_baseline,
        name="query-limit-guarded",
        guarded=True,
    )


def test_add_table_rows(benchmark, inference_baseline):
    rows = [(index, index + 1) for index in range(_ROWS)]

    def operation(space):
        return space.add_table("edge", rows)

    benchmark_case(
        benchmark,
        inference_baseline,
        name="add-table-rows",
        unit="rows",
        operations=_ROWS,
        operation=operation,
        setup=_empty_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def _weighted_space():
    space = _empty_space()

    def mood(_day, _class=None):
        yield Answer(value=S.calm, k=0.25)
        yield Answer(value=S.tense, k=0.75)

    space.register_op(mood, name="benchmark-mood")
    space.declare_annotations("benchmark-mood", "prob")
    return space


def _drop_weighted(space):
    space.unregister_op("benchmark-mood")
    space.drop()


def test_annotated_relation(benchmark, inference_baseline):
    repeats = 500

    def operation(space):
        for _ in range(repeats):
            space.run("!(collapse (top 1 (benchmark-mood today)))")
        return repeats

    benchmark_case(
        benchmark,
        inference_baseline,
        name="annotated-relation",
        unit="evaluations",
        operations=repeats,
        operation=operation,
        setup=_weighted_space,
        teardown=_drop_weighted,
        engine=lambda space: space,
    )


def test_register_operation(benchmark, inference_baseline):
    registrations = 100

    def operation(space):
        for index in range(registrations):
            name = f"benchmark-register-{index}"

            def identity(value: int) -> int:
                return value

            space.register_op(identity, name=name)
            space.unregister_op(name)
        return registrations

    benchmark_case(
        benchmark,
        inference_baseline,
        name="register-op",
        unit="registrations",
        operations=registrations,
        operation=operation,
        setup=_empty_space,
        teardown=_drop,
        engine=lambda space: space,
    )


def _subscribed_spaces():
    watched = _empty_space()
    target = _empty_space()
    subscription = watched.subscribe(S.never(V.x))
    return target, watched, subscription


def _drop_subscribed(state):
    target, watched, subscription = state
    subscription.cancel()
    target.drop()
    watched.drop()


def test_subscription_tax(benchmark, inference_baseline):
    def operation(state):
        target, _watched, _subscription = state
        target.add(*(S.n(index) for index in range(_ROWS)))
        return _ROWS

    benchmark_case(
        benchmark,
        inference_baseline,
        name="subscribe-tax",
        unit="atoms",
        operations=_ROWS,
        operation=operation,
        setup=_subscribed_spaces,
        teardown=_drop_subscribed,
        engine=lambda state: state[0],
    )


def test_alpha_unique(benchmark, inference_baseline):
    _engine_workload_case(
        benchmark,
        inference_baseline,
        name="alpha-unique",
        unit="terms",
        operations=ALPHA_TERMS,
        factory=alpha_unique_case,
    )


def test_space_digest(benchmark, inference_baseline):
    _engine_workload_case(
        benchmark,
        inference_baseline,
        name="space-digest",
        unit="atoms",
        operations=DIGEST_ATOMS,
        factory=digest_case,
    )


def test_py_method_call(benchmark, inference_baseline):
    _engine_workload_case(
        benchmark,
        inference_baseline,
        name="py-method-call",
        unit="calls",
        operations=METHOD_CALLS,
        factory=py_method_case,
    )


def test_sort_atom(benchmark, inference_baseline):
    _engine_workload_case(
        benchmark,
        inference_baseline,
        name="sort-atom",
        unit="terms",
        operations=SORT_TERMS,
        factory=sort_atom_case,
    )


def test_source_load(benchmark, inference_baseline):
    _engine_workload_case(
        benchmark,
        inference_baseline,
        name="source-load",
        unit="forms",
        operations=SOURCE_FORMS,
        factory=source_load_case,
    )


def test_space_name(benchmark, inference_baseline):
    _engine_workload_case(
        benchmark,
        inference_baseline,
        name="space-name",
        unit="calls",
        operations=SPACE_NAME_CALLS,
        factory=space_name_case,
    )


def _save_state(format):
    directory = TemporaryDirectory(prefix="petta-benchmark-")
    source = _empty_space()
    target = _empty_space()
    source.add(*(S["benchmark-save-node"](i, i + 1) for i in range(20_000)))
    source.run("(= (benchmark-save-next $x) (+ $x 1))")
    return directory, source, target, f"{directory.name}/roundtrip.{format}", format


def _drop_save_state(state):
    directory, source, target, _path, _format = state
    source.drop()
    target.drop()
    directory.cleanup()


def _save_load(state):
    _directory, source, target, path, format = state
    saved = source.save(path, format=format)
    groups = target.load(path)
    if saved != 20_001 or groups or target.count() != 20_001:
        raise AssertionError(f"{format} did not round-trip 20,001 atoms")
    if target.run("!(benchmark-save-next 41)") != [[42]]:
        raise AssertionError(f"{format} lost the stored equation")
    return saved


def _save_case(benchmark, baseline, format):
    return benchmark_case(
        benchmark,
        baseline,
        name=f"save-load-{format}",
        unit="atoms",
        operations=20_001,
        operation=_save_load,
        setup=lambda: _save_state(format),
        teardown=_drop_save_state,
        engine=lambda state: state[1],
        rounds=3,
        warmup_rounds=1,
    )


def _file_load_state():
    directory = TemporaryDirectory(prefix="petta-benchmark-")
    source = _empty_space()
    source.add(*(S["benchmark-load-node"](i, i + 1) for i in range(20_000)))
    source.run("(= (benchmark-load-next $x) (+ $x 1))")
    path = f"{directory.name}/loader.metta"
    source.save(path, format="metta")
    target = _empty_space()
    return directory, source, target, path


def _drop_file_load_state(state):
    directory, source, target, _path = state
    source.drop()
    target.drop()
    directory.cleanup()


def _file_load(state):
    """Price the loader itself, both doors, no save in the loop.

    `target.load` replaces the file's previous contribution every round, so
    each measured round pays withdrawal plus re-add plus the content digest,
    the loader's whole path. The `import!` that follows hits the other
    branch, an unchanged file's skip, one read and one hash; its answer
    shape is not asserted because that surface is its own tests' business.
    """
    _directory, _source, target, path = state
    groups = target.load(path)
    if groups or target.count() != 20_001:
        raise AssertionError("load did not carry 20,001 atoms")
    target.run(f'!(import! &self "{path}")')
    return 20_001


def test_file_load(benchmark, inference_baseline):
    benchmark_case(
        benchmark,
        inference_baseline,
        name="file-load",
        unit="atoms",
        operations=20_001,
        operation=_file_load,
        setup=_file_load_state,
        teardown=_drop_file_load_state,
        engine=lambda state: state[1],
        rounds=3,
        warmup_rounds=1,
    )


def test_save_load_metta(benchmark, inference_baseline):
    _save_case(benchmark, inference_baseline, "metta")


def test_save_load_fast(benchmark, inference_baseline):
    _save_case(benchmark, inference_baseline, "fast")


def _provider_space():
    """A minimal in-process provider, so the case prices the seam's own
    dispatch and nothing else: no SQL, no wire, no subprocess."""
    from petta.foreign import SpaceProvider

    class Rows(SpaceProvider):
        def __init__(self):
            space = _empty_space()
            self.stored = [space.parse("(edge a b)"), space.parse("(edge a c)")]
            self.space = space

        def atoms(self):
            return iter(self.stored)

        def match(self, pattern):
            return iter(self.stored)

    provider = Rows()
    provider.space.register_space(provider, "&bench-provider")
    return provider.space


def _drop_provider(space):
    space.unregister_space("&bench-provider")
    space.drop()


def test_foreign_match(benchmark, inference_baseline):
    """The foreign-space seam priced per query: provider dispatch, the
    candidate crossing, and the engine's own binding of each answer."""
    repeats = 2_000

    def operation(space):
        result = None
        for _ in range(repeats):
            result = space.run("!(collapse (match &bench-provider (edge a $x) $x))")
        (group,) = result
        assert sorted(str(atom) for atom in group[0]) == ["b", "c"]
        return repeats

    benchmark_case(
        benchmark,
        inference_baseline,
        name="foreign-match",
        unit="queries",
        operations=repeats,
        operation=operation,
        setup=_provider_space,
        teardown=_drop_provider,
        engine=lambda space: space,
    )


def _bridge_space():
    """The derived table bridge over stdlib SQLite, the schema one MeTTa
    declaration, so the case prices the whole derivation live."""
    import sqlite3

    from petta.tables import TableBridge

    space = _empty_space()
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE edges (a TEXT, b TEXT)")
    provider = TableBridge(
        space.parse,
        connection,
        "(bridge (edge $a $b) (row edges (a $a) (b $b)))",
    )
    provider.add(space.parse("(edge a b)"))
    provider.add(space.parse("(edge a c)"))
    space.register_space(provider, "&bench-bridge")
    return space


def _drop_bridge(space):
    space.unregister_space("&bench-bridge")
    space.drop()


def test_table_bridge_match(benchmark, inference_baseline):
    repeats = 2_000

    def operation(space):
        result = None
        for _ in range(repeats):
            result = space.run("!(collapse (match &bench-bridge (edge a $x) $x))")
        (group,) = result
        assert sorted(str(atom) for atom in group[0]) == ["b", "c"]
        return repeats

    benchmark_case(
        benchmark,
        inference_baseline,
        name="table-bridge-match",
        unit="queries",
        operations=repeats,
        operation=operation,
        setup=_bridge_space,
        teardown=_drop_bridge,
        engine=lambda space: space,
    )


def _handle_space():
    from pathlib import Path

    import pytest

    library = (
        Path(__file__).resolve().parents[3]
        / "examples"
        / "integration"
        / "c_extension"
        / "handle.so"
    )
    if not library.is_file():
        pytest.skip("handle.so is not built; see examples/integration/c_extension")
    space = _empty_space()
    space.register_foreign_library(
        library,
        entry="install_handle",
        names=["vector-new", "vector-nth", "vector-bump", "vector-length"],
    )
    return space


def test_handle_round_trip(benchmark, inference_baseline):
    """A native handle out and back per operation: the ["h"] wire form,
    the registry keep, the resolve, and one C accessor through it."""
    repeats = 2_000

    def operation(space):
        value = None
        for _ in range(repeats):
            (row,) = space.run("!(vector-new 4)")
            with row[0] as handle:
                value = space.run("!(vector-nth h 3)", using={"h": handle})[0][0]
        assert str(value) == "3"
        return repeats

    benchmark_case(
        benchmark,
        inference_baseline,
        name="handle-round-trip",
        unit="round trips",
        operations=repeats,
        operation=operation,
        setup=_handle_space,
        teardown=_drop,
        engine=lambda space: space,
    )
