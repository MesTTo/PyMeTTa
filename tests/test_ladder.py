"""Purpose: the ladder's sugar tier: the module-level functions over the
default engine (M1), scoped limits (M3), into= row shaping (M4), the batch
block (M5), the shipped pytest fixtures (M6), and the exported strategies
(L4). Every rung is tested as sugar for the rung below.
Guarantees:
  - module define/cache/stats/limits/strict/trace verbs defer to one lazy
    default engine [tested: test_module_tier_exposes_the_mode_and_definition_family;
    commit=WORKTREE]
  - scoped stack bounds retain an explicit byte count for
    ``petta_py_limited/6`` [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=WORKTREE]
  - class declarations are context-relative through ``Space.define`` and the
    retired root ``record`` door is not used [tested:
    test_define_wires_the_declarative_dance and
    test_define_refuses_an_unregistrable_class; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - a batch discards on exception and refuses remove/clear inside its own
    block, the stated edges [tested test_batch_edges_are_enforced]
  - query(into=) and Rows.build rebuild a complete constructor expression,
    while cast returns the admitted atom [tested:
    test_a_constructor_expression_rebuilds_through_the_query_door;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
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

import petta
from petta import PettaError, S, V
from petta._space_objects import _apply_limited, _limits
from petta.errors import InferenceLimitError


def test_module_tier_is_sugar_over_one_default_engine():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert petta.engine() is petta.engine()
    scratch = petta.space()
    scratch.add(S.ml(1))
    assert len(scratch.query(S.ml(V.x))) == 1
    # The module functions and the instance touch the same engine.
    petta.run("(= (ml-fn $x) (+ $x 1))")
    assert petta.eval("(ml-fn 4)") == [5]
    assert petta.engine().self.fn.ml_fn(9).one() == 10
    assert petta.space("&ml-named").name == "&ml-named"
    assert importlib.util.find_spec("petta.space") is None
    assert callable(petta.space)


def test_module_tier_exposes_the_mode_and_definition_family() -> None:
    """The guide's root verbs are self-space methods with lazy engine creation."""

    @petta.define
    def module_tier_increment(n):
        return n + 1

    @petta.cache
    def module_tier_square(n):
        return n * n

    assert module_tier_increment(4) == [5]
    assert module_tier_square(3) == [9]
    with petta.stats() as measured:
        assert petta.eval(S.module_tier_increment(8)) == [9]
    assert measured.inferences > 0
    with petta.limits(inferences=100_000), petta.strict():
        assert petta.eval(S.module_tier_square(4)) == [16]
    events = petta.trace("!(module-tier-increment 1)")
    assert events
    assert callable(petta.trace)


def test_module_tier_verbs_are_inert_until_called() -> None:
    """Naming every PEP 562-era root verb does not start the default engine."""
    root = Path(__file__).parents[3]
    source = (
        "from petta import _engine\n"
        "import petta\n"
        "assert not _engine.started()\n"
        "assert all(callable(getattr(petta, name)) for name in "
        "('define', 'cache', 'stats', 'limits', 'strict', 'trace'))\n"
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
    """Exercise the sibling engine seam when this worktree contains it."""
    if not metta._rt.once("current_predicate(petta_py_limited/6)"):
        pytest.skip("petta_py_limited/6 is supplied by the sibling engine job")
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
    edges = m.query(S.edge(V.a, V.b), into=_Edge)
    assert edges == [_Edge("x", "y"), _Edge("y", "z")]
    m.add(S.pair(S.k, 7))
    assert m.query(S.pair(V.a, V.n), into=_Pair) == [_Pair("k", 7)]
    # A missing column is an error at the door.
    with pytest.raises(TypeError, match="needs column"):
        m.query(S.edge(V.a, V.other), into=_Edge)
    # A primitive annotation is checked, not assumed.
    with pytest.raises(TypeError, match="not int"):
        m.query(S.edge(V.a, V.n), into=_Pair)


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
        rows = space.query(V.constructor)
        assert rows.build(P5Constructor) == [P5Constructor("bolts", 4)]
        assert space.query(V.constructor, into=P5Constructor) == [
            P5Constructor("bolts", 4)
        ]
        assert space.cast(atom, P5Constructor) is atom


def test_batch_crosses_once_and_reads_see_the_pre_batch_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta._new_space()
    with m.batch() as batch:
        for n in range(10):
            m.add(S.bt(n))
        assert len(batch) == 10
        assert len(m.query(S.bt(V.n))) == 0  # the stated edge: reads pre-batch
    assert len(m.query(S.bt(V.n))) == 10


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
    assert len(m.query(S.bt(V.n))) == 0
    # Same-space batches do not nest; different spaces batch independently.
    other = metta._new_space()
    with m.batch():
        with pytest.raises(PettaError, match="nest"):
            with m.batch():
                pass
        with other.batch():
            other.add(S.ob(1))
        assert len(other.query(S.ob(V.x))) == 1


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
    assert len(m.query(S.tx(V.n))) == 0


def test_shipped_plugin_provides_the_fixtures(tmp_path: Path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A bare test file with no conftest gets metta and scratch_space from
    # the plugin module itself; -p loads it exactly as the pytest11 entry
    # point does in an installed environment.
    test_file = tmp_path / "test_plugin_probe.py"
    test_file.write_text(
        "from petta import S\n"
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
            "petta.pytest_plugin",
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
    assert data["project"]["entry-points"]["pytest11"]["petta"] == "petta.pytest_plugin"


@given(petta.testing.patterns(max_leaves=4))
def test_patterns_strategy_always_carries_a_variable(pattern):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert pattern.vars


@given(petta.testing.ground_atoms(max_leaves=4))
def test_ground_atoms_strategy_is_ground(atom):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert not atom.vars


def test_ladder_rungs_cross_the_async_seam(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import asyncio

    from petta import aio

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
                assert len(await am.query(S.ab(V.n))) == 0
            assert len(await am.query(S.ab(V.n))) == 5
            # into= crosses too.
            rows = await am.query(S.ab(V.n), into=_Count)
            assert sorted(row.n for row in rows) == [0, 1, 2, 3, 4]
            return True

    assert asyncio.run(go())


class _Count(NamedTuple):
    n: int


def test_define_wires_the_declarative_dance(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from dataclasses import dataclass

    @metta.define
    @dataclass
    class LadderEdge:
        a: str
        b: str

    declared = metta.query("(: LadderEdge $t)")
    assert [str(row[0]) for row in declared] == ["(-> String String LadderEdge)"]
    # cast narrows against the landed declaration ...
    atom = petta.parse('(LadderEdge "x" "y")')
    assert metta.cast(atom, LadderEdge) is atom
    # ... conversion runs both ways ...
    projected = petta.convert.project(LadderEdge("p", "q"))
    assert str(projected.atom) == '(LadderEdge "p" "q")'
    assert petta.convert.build(projected.atom, LadderEdge) == LadderEdge("p", "q")
    # ... and the class serves as an into= target.
    sp = metta._new_space()
    sp.add(projected.atom)
    assert sp.query("(LadderEdge $a $b)", into=LadderEdge) == [LadderEdge("p", "q")]


def test_define_refuses_an_unregistrable_class(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="default image"):

        @metta.define
        class Plain:
            pass
