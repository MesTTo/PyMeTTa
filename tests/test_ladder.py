"""Purpose: the ladder's sugar tier: the module-level functions over the
default engine (M1), scoped limits (M3), into= row shaping (M4), the batch
block (M5), the shipped pytest fixtures (M6), and the exported strategies
(L4). Every rung is tested as sugar for the rung below.
Guarantees:
  - module define/cache/op/stats/limits/strict/trace verbs defer to one lazy
    default engine, and op forwards its receiver result without another
    wrapper [tested: test_module_tier_exposes_the_mode_and_definition_family,
    test_module_tier_op_forwards_identity_to_the_default_receiver;
    commit=WORKTREE]
  - scoped stack bounds retain an explicit byte count for
    ``petta_py_limited/6`` [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - class declarations are context-relative through ``Space.define`` and the
    retired root ``record`` door is not used [tested:
    test_define_wires_the_declarative_dance and
    test_define_refuses_an_unregistrable_class; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - a batch discards on exception and refuses remove/clear inside its own
    block, the stated edges [tested test_batch_edges_are_enforced]
  - match(into=) and Rows.build rebuild a complete constructor expression,
    while cast returns the admitted atom [tested:
    test_a_constructor_expression_rebuilds_through_the_query_door;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``metta.speculate()`` is the exact lazy module-tier spelling for the
    default receiver's discarded execution scope [tested:
    test_module_tier_speculate_discards_default_space_writes; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import pytest
from hypothesis import given

import metta
from metta import PettaError, S, V
from metta._space_objects import _apply_limited, _limits
from metta.errors import InferenceLimitError


def test_module_tier_is_sugar_over_one_default_engine():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert metta.engine() is metta.engine()
    scratch = metta.space()
    scratch.add(S.ml(1))
    assert len(scratch.match(S.ml(V.x))) == 1
    # The module functions and the instance touch the same engine.
    metta.run("(= (ml-fn $x) (+ $x 1))")
    assert metta.eval("(ml-fn 4)") == [5]
    assert metta.engine().self.fn.ml_fn(9).one() == 10
    assert metta.space("&ml-named").name == "&ml-named"
    assert importlib.util.find_spec("metta.space") is None
    assert callable(metta.space)


def test_module_tier_exposes_the_mode_and_definition_family() -> None:
    """The guide's root verbs are self-space methods with lazy engine creation."""

    @metta.define
    def module_tier_increment(n):
        return n + 1

    @metta.cache
    def module_tier_square(n):
        return n * n

    assert module_tier_increment(4) == [5]
    assert module_tier_square(3) == [9]
    with metta.stats() as measured:
        assert metta.eval(S.module_tier_increment(8)) == [9]
    assert measured.inferences > 0
    with metta.limits(inferences=100_000), metta.strict():
        assert metta.eval(S.module_tier_square(4)) == [16]
    events = metta.trace("!(module-tier-increment 1)")
    assert events
    assert callable(metta.trace)


def test_module_tier_op_forwards_identity_to_the_default_receiver(monkeypatch) -> None:
    """The root door returns exactly what the default receiver returns."""
    sentinel = object()
    calls = []

    class Receiver:
        def op(self, *args, **kwargs):
            calls.append((args, kwargs))
            return sentinel

    class Context:
        self = Receiver()

    monkeypatch.setattr(metta, "engine", Context)

    def host(value):
        return value

    assert metta.op(host, name="root-op-forwarding", effect="pureStructural") is sentinel
    assert calls == [
        ((host,), {"name": "root-op-forwarding", "effect": "pureStructural"})
    ]


def test_module_tier_op_registration_precedes_definition_compilation() -> None:
    """A root operation is known when the following root definition compiles."""

    @metta.op(name="root-op-definition-order", effect="pureStructural")
    def root_op_definition_order(value):
        return value * 2

    try:

        @metta.define
        def root_definition_after_op(value):
            return root_op_definition_order(value) + 1

        assert root_definition_after_op(4) == [9]
        assert root_op_definition_order.__wrapped__(4) == 8
    finally:
        metta.engine().self.unregister_op("root-op-definition-order")


def test_module_tier_op_requires_effect_before_registration() -> None:
    """The root door inherits the receiver's required effect metadata."""

    def root_op_without_effect(value):
        return value

    with pytest.raises(TypeError, match=r"requires effect=.*pureStructural.*oracleIO"):
        metta.op(root_op_without_effect, name="root-op-without-effect")
    assert metta.run(
        "!(match &petta (op root-op-without-effect $arity $kind) $kind)"
    ) == [[]]


def test_module_tier_speculate_discards_default_space_writes() -> None:
    """The guide-exact root spelling is sugar over the default receiver."""
    with metta.speculate():
        metta.run("!(add-atom &self (root-speculate-p14 1))")
        assert list(metta.match(S.root_speculate_p14(V.n))) == []
    assert list(metta.match(S.root_speculate_p14(V.n))) == []


def test_module_tier_verbs_are_inert_until_called() -> None:
    """Naming every PEP 562-era root verb does not start the default engine."""
    root = Path(__file__).parents[3]
    source = (
        "from metta import _engine\n"
        "import metta\n"
        "assert not _engine.started()\n"
        "assert all(callable(getattr(metta, name)) for name in "
        "('define', 'cache', 'op', 'stats', 'limits', 'strict', 'speculate', 'trace'))\n"
        "assert not _engine.started()\n"
    )
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env=os.environ | {"PYTHONPATH": str(root / "bindings" / "python")},
        check=True,
    )


def test_stack_limit_is_carried_to_the_limited_six_seam(metta) -> None:
    """The scoped value reaches the contract even before the sibling seam lands."""

    class RecordingRuntime:
        def __init__(self) -> None:
            self.call = ()

        def apply_must(self, *args):
            self.call = args
            return "answered"

    with metta.limits(stack=4_000_000):
        bounded = _limits(None, None)
        assert bounded == (-1.0, -1, 4_000_000)
        runtime = RecordingRuntime()
        assert _apply_limited(runtime, bounded, "petta_py_eval_all", ["&self", []]) == (
            "answered"
        )
    assert runtime.call == (
        "petta_py_limited",
        -1.0,
        -1,
        4_000_000,
        "petta_py_eval_all",
        ["&self", []],
    )


def test_stack_limit_through_petta_py_limited_6(metta) -> None:
    """Exercise the merged sibling engine seam through the public block."""
    with metta.limits(stack=4_000_000):
        assert metta.eval(S["+"](1, 2)) == [3]


def test_scoped_limits_apply_and_per_call_overrides(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta._new_space()
    m.run("(= (ll-spin $n) (if (== $n 0) done (ll-spin (- $n 1))))")
    with m.limits(inferences=60):
        with pytest.raises(InferenceLimitError):
            m.eval("(ll-spin 100000)")
        # The per-call kwarg still overrides the scoped default.
        assert str(m.eval("(ll-spin 3)", inferences=100_000)[0]) == "done"
    # Outside the block the default is gone.
    assert str(m.eval("(ll-spin 50)")[0]) == "done"


def test_scoped_limits_validate_at_the_block(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="positive"):
        metta.limits(inferences=-1)
    with pytest.raises(TypeError, match="seconds"):
        metta.limits(timeout="soon")


@dataclass
class _Edge:
    a: str
    b: str


class _Pair(NamedTuple):
    a: str
    n: int


def test_query_into_shapes_rows(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta._new_space()
    m.add(S.edge(S.x, S.y), S.edge(S.y, S.z))
    edges = m.match(S.edge(V.a, V.b), into=_Edge)
    assert edges == [_Edge("x", "y"), _Edge("y", "z")]
    m.add(S.pair(S.k, 7))
    assert m.match(S.pair(V.a, V.n), into=_Pair) == [_Pair("k", 7)]
    # A missing column is an error at the door.
    with pytest.raises(TypeError, match="needs column"):
        m.match(S.edge(V.a, V.other), into=_Edge)
    # A primitive annotation is checked, not assumed.
    with pytest.raises(TypeError, match="not int"):
        m.match(S.edge(V.a, V.n), into=_Pair)


def test_a_constructor_expression_rebuilds_through_the_query_door(metta):
    """Rows.build and into= rebuild the constructor expression; cast returns the admitted atom."""

    @metta.define
    @dataclass
    class P5Constructor:
        label: str
        count: int

    atom = S.P5Constructor("bolts", 4)
    with metta._new_space() as space:
        space.add(atom)
        rows = space.match(V.constructor)
        assert rows.build(P5Constructor) == [P5Constructor("bolts", 4)]
        assert space.match(V.constructor, into=P5Constructor) == [
            P5Constructor("bolts", 4)
        ]
        assert space.cast(atom, P5Constructor) is atom


def test_batch_crosses_once_and_reads_see_the_pre_batch_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta._new_space()
    with m.batch() as batch:
        for n in range(10):
            m.add(S.bt(n))
        assert len(batch) == 10
        assert len(m.match(S.bt(V.n))) == 0  # the stated edge: reads pre-batch
    assert len(m.match(S.bt(V.n))) == 10


def test_batch_edges_are_enforced(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta._new_space()
    m.add(S.keep(1))
    with pytest.raises(PettaError, match="batch"):
        with m.batch():
            m.remove(S.keep(1))
    with pytest.raises(PettaError, match="batch"):
        with m.batch():
            m.clear()
    # An exception discards the pending adds rather than landing writes
    # the code after the raise never saw.
    with pytest.raises(RuntimeError):
        with m.batch():
            m.add(S.bt(1))
            msg = "boom"
            raise RuntimeError(msg)
    assert len(m.match(S.bt(V.n))) == 0
    # Same-space batches do not nest; different spaces batch independently.
    other = metta._new_space()
    with m.batch():
        with pytest.raises(PettaError, match="nest"):
            with m.batch():
                pass
        with other.batch():
            other.add(S.ob(1))
        assert len(other.match(S.ob(V.x))) == 1


def test_batch_composes_with_transaction(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta._new_space()

    def work():
        with m.batch():
            m.add(S.tx(1), S.tx(2))
        msg = "roll it back"
        raise ValueError(msg)

    with pytest.raises(ValueError):
        m.transaction(work)
    # The batch flushed inside the transaction, and the transaction
    # rolled the flushed writes back: economy composed with atomicity.
    assert len(m.match(S.tx(V.n))) == 0


def test_shipped_plugin_provides_the_fixtures(tmp_path: Path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A bare test file with no conftest gets metta and scratch_space from
    # the plugin module itself; -p loads it exactly as the pytest11 entry
    # point does in an installed environment.
    test_file = tmp_path / "test_plugin_probe.py"
    test_file.write_text(
        "from metta import S\n"
        "def test_probe(metta, scratch_space):\n"
        "    scratch_space.add(S.pp(1))\n"
            "    assert len(scratch_space) == 1\n"
        "    assert scratch_space.name != metta.name\n"
    )
    import os

    environment = dict(os.environ)
    package_root = str(Path(__file__).resolve().parents[1])
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{package_root}{os.pathsep}{existing}" if existing else package_root
    )
    # One registration path in every environment: with the entry point
    # installed, autoload plus -p would register the module twice.
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-p",
            "metta.pytest_plugin",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=240,
        cwd=tmp_path,
        env=environment,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "1 passed" in done.stdout


def test_the_entry_point_is_declared():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import tomllib

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    assert data["project"]["entry-points"]["pytest11"]["metta"] == "metta.pytest_plugin"


@given(metta.testing.patterns(max_leaves=4))
def test_patterns_strategy_always_carries_a_variable(pattern):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert pattern.vars


@given(metta.testing.ground_atoms(max_leaves=4))
def test_ground_atoms_strategy_is_ground(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert not atom.vars


def test_ladder_rungs_cross_the_async_seam(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import asyncio

    from metta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=metta._new_space()) as am:
            await am.run("(= (al-spin $n) (if (== $n 0) done (al-spin (- $n 1))))")
            # limits() is an ordinary with even in async code, and the
            # scope crosses the thread hop with each awaited call.
            with am.limits(inferences=60):
                with pytest.raises(InferenceLimitError):
                    await am.eval("(al-spin 100000)")
            assert str((await am.eval("(al-spin 3)"))[0]) == "done"
            # The async batch collects through awaited adds and flushes
            # once on the worker at exit.
            async with am.batch() as batch:
                for n in range(5):
                    await am.add(S.ab(n))
                assert len(batch) == 5
                assert len(await am.match(S.ab(V.n))) == 0
            assert len(await am.match(S.ab(V.n))) == 5
            # into= crosses too.
            rows = await am.match(S.ab(V.n), into=_Count)
            assert sorted(row.n for row in rows) == [0, 1, 2, 3, 4]
            return True

    assert asyncio.run(go())


class _Count(NamedTuple):
    n: int


def test_define_wires_the_declarative_dance(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from dataclasses import dataclass

    from metta import convert

    @metta.define
    @dataclass
    class LadderEdge:
        a: str
        b: str

    declared = metta.match("(: LadderEdge $t)")
    assert [str(row[0]) for row in declared] == ["(-> String String LadderEdge)"]
    # cast narrows against the landed declaration ...
    atom = metta.parse('(LadderEdge "x" "y")')
    assert metta.cast(atom, LadderEdge) is atom
    # ... conversion runs both ways ...
    projected = convert.project(LadderEdge("p", "q"))
    assert str(projected.atom) == '(LadderEdge "p" "q")'
    assert convert.build(projected.atom, LadderEdge) == LadderEdge("p", "q")
    # ... and the class serves as an into= target.
    sp = metta._new_space()
    sp.add(projected.atom)
    assert sp.match("(LadderEdge $a $b)", into=LadderEdge) == [LadderEdge("p", "q")]


def test_define_refuses_an_unregistrable_class(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="default image"):

        @metta.define
        class Plain:
            pass


def test_current_space_leaves_every_root_verb_in_place():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # current_space() once popped the hidden implementation-module names
    # with no replacement, so metta.define and five siblings vanished from
    # the package for the life of the process; the failure only surfaced
    # when another test in the same worker had called it first.
    metta.current_space()
    for verb in ("define", "answer", "errors", "ops", "results", "atoms"):
        if verb in metta._ROOT_IMPLEMENTATION_VERBS:
            assert getattr(metta, verb) is metta._ROOT_IMPLEMENTATION_VERBS[verb]
