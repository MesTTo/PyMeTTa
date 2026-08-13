"""Purpose: the predictive-coding functor, run against FabricPC. PC is the
deepest ML fit for a rule engine yet: unlike backprop's global tape, its
inference and learning are LOCAL, per node, from quantities a fact can carry,
so the whole dynamics lands as space rewriting. The mapping exercised here:
topology as facts rules traverse; a settle step as an operation that rewrites
per-node energy facts; the convergence loop as MeTTa equations, control
symbolic while numerics stay JAX's; error-gated attention as a match over
energy facts, precision-weighting as a rule; and JAX arrays flowing through
the same DLPack array layer as NumPy and torch, a third library with zero
new code.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os

import pytest

os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
os.environ.setdefault("JAX_PLATFORMS", "cpu")

jax = pytest.importorskip("jax")
fabricpc = pytest.importorskip("fabricpc")

import jax.numpy as jnp  # noqa: E402

from fabricpc.core.inference import InferenceSGD  # noqa: E402
from fabricpc.core.topology import Edge  # noqa: E402
from fabricpc.graph_assembly import TaskMap, graph  # noqa: E402
from fabricpc.graph_initialization import initialize_params  # noqa: E402
from fabricpc.graph_initialization.state_initializer import (  # noqa: E402
    initialize_graph_state,
)
from fabricpc.nodes import Linear  # noqa: E402

import pettorch  # noqa: E402
from petta import S, V, decode, expr, val  # noqa: E402
from petta import integrate as pi  # noqa: E402


@pytest.fixture(scope="module")
def pc(metta):
    """A tiny supervised PCN and its whole MeTTa image, built once."""
    pettorch.install(metta)
    space = metta.fresh_space()

    layer_in = Linear(shape=(4,), name="sense")
    layer_mid = Linear(shape=(3,), name="hidden")
    layer_out = Linear(shape=(2,), name="belief")
    structure = graph(
        nodes=[layer_in, layer_mid, layer_out],
        edges=[
            Edge(source=layer_in, target=layer_mid.slot("in")),
            Edge(source=layer_mid, target=layer_out.slot("in")),
        ],
        task_map=TaskMap(x=layer_in, y=layer_out),
        inference=InferenceSGD(eta_infer=0.05, infer_steps=20),
    )
    key = jax.random.PRNGKey(0)
    params = initialize_params(structure, key)
    clamps = {
        "sense": jnp.asarray([[1.0, 0.5, -0.5, 0.25]]),
        "belief": jnp.asarray([[1.0, 0.0]]),
    }
    holder = {
        "state": initialize_graph_state(
            structure, 1, jax.random.PRNGKey(1), clamps=clamps, params=params
        )
    }

    # ----- topology as facts, through the public bulk loader
    pi.facts(
        space,
        (
            expr(S["pc-node"], S[name], S[type(node).__name__], expr(*node.node_info.shape))
            for name, node in structure.nodes.items()
        ),
    )
    pi.facts(
        space,
        (
            expr(S["pc-edge"], S[info.source], S[info.target])
            for info in structure.edges.values()
        ),
    )

    # ----- dynamics as operations, through the public op interface
    def total_energy() -> float:
        state = holder["state"]
        return float(
            sum(
                jnp.sum(state.nodes[n].energy)
                for n in structure.nodes
                if structure.nodes[n].node_info.in_degree > 0
            )
        )

    def pc_energy() -> float:
        return total_energy()

    def pc_step() -> float:
        holder["state"] = InferenceSGD.inference_step(
            params,
            holder["state"],
            clamps,
            structure,
            structure.config["inference"].config,
        )
        return total_energy()

    def pc_state(node):
        name = node.name if hasattr(node, "name") else str(node)
        return val(holder["state"].nodes[name].z_latent)

    space.op(pc_energy, name="pc-energy", raw=True, typed=False)
    space.op(pc_step, name="pc-step!", raw=True, typed=False)
    space.op(pc_state, name="pc-state", raw=False, typed=False, pass_atoms=True)

    def node_energies():
        state = holder["state"]
        for n in structure.nodes:
            if structure.nodes[n].node_info.in_degree > 0:
                yield expr(S[n], round(float(jnp.sum(state.nodes[n].energy)), 8))

    space.op(node_energies, name="pc-node-energies", raw=False, typed=False)

    # ----- the convergence loop as MeTTa source: control symbolic, numerics JAX
    space.run(
        "(= (settle-until $eps $max)\n"
        "   (if (<= $max 0)\n"
        "       (Settled max-steps (pc-energy))\n"
        "       (let* (($before (pc-energy))\n"
        "              ($after (pc-step!)))\n"
        "             (if (< (- $before $after) $eps)\n"
        "                 (Settled converged $after)\n"
        "                 (settle-until $eps (- $max 1))))))\n"
        "(= (anxious $threshold)\n"
        "   (let ($node $e) (pc-node-energies)\n"
        "        (if (> $e $threshold) $node (empty))))"
    )
    return space, structure, holder


def test_topology_is_facts_rules_traverse(pc):
    space, structure, _holder = pc
    rows = space.query("(pc-node $n $type $shape)")
    assert {str(r.n) for r in rows} == {"sense", "hidden", "belief"}
    # The prediction path, derived by a rule over edge facts:
    space.run(
        "(= (feeds $a $b) (match (context-space) (pc-edge $a $b) True))\n"
        "(= (feeds $a $b) (let $m (match (context-space) (pc-edge $a $m0) $m0)"
        " (feeds $m $b)))"
    )
    assert space.run("!(feeds sense belief)") == [[True]]


def test_jax_flows_through_the_same_array_layer(pc):
    space, _structure, holder = pc
    (group,) = space.run("!(t-shape (pc-state sense))")
    assert group == [expr(1, 4)]
    (types,) = space.run("!(collapse (get-type (pc-state hidden)))")
    assert S.DLTensor in list(types[0])


def test_settling_is_energy_descent_in_the_space(pc):
    space, _structure, _holder = pc
    (before,) = space.run("!(pc-energy)")[0]
    for _ in range(5):
        space.run("!(pc-step!)")
    (after,) = space.run("!(pc-energy)")[0]
    assert float(after) < float(before)


def test_the_convergence_loop_is_metta_source(pc):
    space, _structure, _holder = pc
    (group,) = space.run("!(settle-until 0.0001 200)")
    (settled,) = group
    assert settled[0] == S.Settled
    assert str(settled[1]) in ("converged", "max-steps")
    assert float(settled[2].value if hasattr(settled[2], "value") else settled[2]) >= 0.0


def test_precision_gating_is_a_rule_over_error_facts(pc):
    """The symbolic payoff: per-node energies are facts each step, so which
    node deserves attention is a match, not a hook into a framework."""
    space, _structure, _holder = pc
    (all_nodes,) = space.run("!(collapse (anxious -1.0))")
    assert {str(a) for a in all_nodes[0]} == {"hidden", "belief"}
    (calm,) = space.run("!(collapse (anxious 999999.0))")
    assert list(calm[0]) == []
