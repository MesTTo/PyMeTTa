"""Purpose: prove the networkx example: a space's expressions read as a
graph on the public surface alone, the projection rule refuses to guess
an n-ary reading, and the whole example file runs green end to end.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
from importlib import util as _importlib_util
from pathlib import Path

import pytest

import metta

nx = pytest.importorskip("networkx")

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "examples" / "integration" / "networkx_space.py"
)


def _module():
    examples_root = str(_MODULE_PATH.parents[1])
    sys.path.insert(0, examples_root)
    try:
        specification = _importlib_util.spec_from_file_location(
            "petta_example_networkx_space", _MODULE_PATH
        )
        module = _importlib_util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(examples_root)


@pytest.fixture
def scratch(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_to_graph_reads_links_as_edges_of_atom_nodes(scratch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module = _module()
    scratch.run("(nxe a b) (nxe b c)")
    graph = module.to_graph(scratch, "(nxe $x $y)")
    assert graph.number_of_edges() == 2
    assert metta.parse("a") in graph  # nodes ARE atoms, not strings
    assert nx.shortest_path(graph, metta.parse("a"), metta.parse("c")) == [
        metta.parse("a"),
        metta.parse("b"),
        metta.parse("c"),
    ]


def test_an_nary_shape_refuses_to_guess_and_takes_either_reading(scratch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module = _module()
    scratch.run("(nxt s v o)")
    with pytest.raises(ValueError, match=r"no default graph reading"):
        module.to_graph(scratch, "(nxt $s $v $o)")
    chain = module.to_graph(scratch, "(nxt $s $v $o)", projection="pairwise")
    assert chain.number_of_edges() == 2
    stars = module.to_graph(scratch, "(nxt $s $v $o)", projection="bipartite")
    # the link itself is a node, the hypergraph-faithful reading
    assert metta.parse("(nxt s v o)") in stars
    assert stars.number_of_edges() == 3
    with pytest.raises(ValueError, match=r"at least two argument"):
        module.to_graph(scratch, "(solo $x)")


def test_the_example_runs_whole():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    examples_root = str(_MODULE_PATH.parents[1])
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{examples_root}{os.pathsep}{existing}" if existing else examples_root
    )
    finished = subprocess.run(
        [sys.executable, str(_MODULE_PATH)],
        capture_output=True,
        text=True,
        timeout=240,
        env=environment,
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    assert "OK networkx_space" in finished.stdout
