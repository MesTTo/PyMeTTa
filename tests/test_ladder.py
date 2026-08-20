"""Purpose: the ladder's sugar tier: the module-level functions over the
default engine (M1), scoped limits (M3), into= row shaping (M4), the batch
block (M5), the shipped pytest fixtures (M6), and the exported strategies
(L4). Every rung is tested as sugar for the rung below.
Guarantees:
  - a batch discards on exception and refuses remove/clear inside its own
    block, the stated edges [tested test_batch_edges_are_enforced]
  - query(into=) and Rows.build rebuild a complete constructor expression,
    while cast returns the admitted atom [tested:
    test_a_constructor_expression_rebuilds_through_the_query_door;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import pytest
from hypothesis import given

import petta
from petta import InferenceLimitError, PettaError, S, V


def test_module_tier_is_sugar_over_one_default_engine():
    assert petta.default_engine() is petta.default_engine()
    scratch = petta.default_engine().new_space()
    scratch.add(S.ml(1))
    assert len(scratch.query(S.ml(V.x))) == 1
    # The module functions and the instance touch the same engine.
    petta.run("(= (ml-fn $x) (+ $x 1))")
    assert petta.eval("(ml-fn 4)") == [5]
    assert petta.fn("ml-fn").one(9) == 10
    assert petta.default_engine().space("&ml-named").space_name == "&ml-named"
    # petta.space stays the MODULE, a public import target the ladder
    # deliberately does not clobber.
    import petta.space as space_module

    assert petta.space is space_module


def test_scoped_limits_apply_and_per_call_overrides(metta):
    m = metta.new_space()
    m.run("(= (ll-spin $n) (if (== $n 0) done (ll-spin (- $n 1))))")
    with m.limits(inferences=60):
        with pytest.raises(InferenceLimitError):
            m.eval("(ll-spin 100000)")
        # The per-call kwarg still overrides the scoped default.
        assert str(m.eval("(ll-spin 3)", inferences=100_000)[0]) == "done"
    # Outside the block the default is gone.
    assert str(m.eval("(ll-spin 50)")[0]) == "done"


def test_scoped_limits_validate_at_the_block(metta):
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


def test_query_into_shapes_rows(metta):
    m = metta.new_space()
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
    @petta.record
    @dataclass
    class P5Constructor:
        label: str
        count: int

    atom = S.P5Constructor("bolts", 4)
    with metta.new_space() as space:
        space.add(atom)
        rows = space.query(V.constructor)
        assert rows.build(P5Constructor) == [P5Constructor("bolts", 4)]
        assert space.query(V.constructor, into=P5Constructor) == [
            P5Constructor("bolts", 4)
        ]
        assert space.cast(atom, P5Constructor) is atom


def test_batch_crosses_once_and_reads_see_the_pre_batch_space(metta):
    m = metta.new_space()
    with m.batch() as batch:
        for n in range(10):
            m.add(S.bt(n))
        assert len(batch) == 10
        assert len(m.query(S.bt(V.n))) == 0  # the stated edge: reads pre-batch
    assert len(m.query(S.bt(V.n))) == 10


def test_batch_edges_are_enforced(metta):
    m = metta.new_space()
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
            raise RuntimeError("boom")
    assert len(m.query(S.bt(V.n))) == 0
    # Same-space batches do not nest; different spaces batch independently.
    other = metta.new_space()
    with m.batch():
        with pytest.raises(PettaError, match="nest"):
            with m.batch():
                pass
        with other.batch():
            other.add(S.ob(1))
        assert len(other.query(S.ob(V.x))) == 1


def test_batch_composes_with_transaction(metta):
    m = metta.new_space()

    def work():
        with m.batch():
            m.add(S.tx(1), S.tx(2))
        raise ValueError("roll it back")

    with pytest.raises(ValueError):
        m.transaction(work)
    # The batch flushed inside the transaction, and the transaction
    # rolled the flushed writes back: economy composed with atomicity.
    assert len(m.query(S.tx(V.n))) == 0


def test_shipped_plugin_provides_the_fixtures(tmp_path: Path):
    # A bare test file with no conftest gets metta and scratch_space from
    # the plugin module itself; -p loads it exactly as the pytest11 entry
    # point does in an installed environment.
    test_file = tmp_path / "test_plugin_probe.py"
    test_file.write_text(
        "from petta import S\n"
        "def test_probe(metta, scratch_space):\n"
        "    scratch_space.add(S.pp(1))\n"
        "    assert scratch_space.count() == 1\n"
        "    assert scratch_space.space_name != metta.space_name\n"
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


def test_the_entry_point_is_declared():
    import tomllib

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    assert data["project"]["entry-points"]["pytest11"]["petta"] == "petta.pytest_plugin"


@given(petta.testing.patterns(max_leaves=4))
def test_patterns_strategy_always_carries_a_variable(pattern):
    from petta.atoms import is_ground

    assert not is_ground(pattern)


@given(petta.testing.ground_atoms(max_leaves=4))
def test_ground_atoms_strategy_is_ground(atom):
    from petta.atoms import is_ground

    assert is_ground(atom)


def test_ladder_rungs_cross_the_async_seam(metta):
    import asyncio

    from petta import aio

    async def go():
        async with aio.AsyncMeTTa(metta=metta.new_space()) as am:
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


def test_record_wires_the_declarative_dance(metta):
    # In-process: the classes declare on the next engine touch (the
    # engine exists here already, so immediately).
    from dataclasses import dataclass

    @petta.record
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
    sp = metta.new_space()
    sp.add(projected.atom)
    assert sp.query("(LadderEdge $a $b)", into=LadderEdge) == [LadderEdge("p", "q")]


def test_record_before_any_engine_defers_without_booting():
    import os
    import subprocess

    code = (
        "import sys\n"
        "from dataclasses import dataclass\n"
        "import petta\n"
        "@petta.record\n"
        "@dataclass\n"
        "class PreBoot:\n"
        "    n: int\n"
        "assert 'janus_swi' not in sys.modules, 'record booted the engine'\n"
        "m = petta.MeTTa()\n"
        "rows = m.query('(: PreBoot $t)')\n"
        "assert [str(r[0]) for r in rows] == ['(-> Number PreBoot)'], rows\n"
        "print('deferred ok')\n"
    )
    environment = dict(os.environ)
    package_root = str(Path(__file__).resolve().parents[1])
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{package_root}{os.pathsep}{existing}" if existing else package_root
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=240,
        env=environment,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "deferred ok" in done.stdout


def test_record_refuses_an_unregistrable_class():
    with pytest.raises(TypeError, match="default image"):

        @petta.record
        class Plain:
            pass
