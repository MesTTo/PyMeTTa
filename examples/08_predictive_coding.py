"""Purpose: predictive coding through FabricPC: topology as facts, one
settle step as an operation, the convergence loop as MeTTa source, and
which node deserves attention as a rule over energy facts.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os

os.environ.setdefault("JAX_PLATFORMS", "cpu")

from _common import check, done, skip

try:
    import jax
    import jax.numpy as jnp
    from fabricpc.core.inference import InferenceSGD
    from fabricpc.core.topology import Edge
    from fabricpc.graph_assembly import TaskMap, graph
    from fabricpc.graph_initialization import initialize_params
    from fabricpc.graph_initialization.state_initializer import initialize_graph_state
    from fabricpc.nodes import Linear
except ImportError:
    skip("fabricpc (and jax) are not installed")

import pettorch
from petta import MeTTa, S, expr
from petta import integrate as pi

m = MeTTa().fresh_space()
pettorch.install(m)

sense, hidden, belief = Linear(shape=(4,), name="sense"), Linear(shape=(3,), name="hidden"), Linear(shape=(2,), name="belief")
structure = graph(
    nodes=[sense, hidden, belief],
    edges=[Edge(source=sense, target=hidden.slot("in")),
           Edge(source=hidden, target=belief.slot("in"))],
    task_map=TaskMap(x=sense, y=belief),
    inference=InferenceSGD(eta_infer=0.05, infer_steps=20),
)
params = initialize_params(structure, jax.random.PRNGKey(0))
clamps = {"sense": jnp.asarray([[1.0, 0.5, -0.5, 0.25]]), "belief": jnp.asarray([[1.0, 0.0]])}
holder = {"state": initialize_graph_state(structure, 1, jax.random.PRNGKey(1), clamps=clamps, params=params)}

pi.facts(m, (expr(S["pc-edge"], S[i.source], S[i.target]) for i in structure.edges.values()))


def energy() -> float:
    s = holder["state"]
    return float(sum(jnp.sum(s.nodes[n].energy) for n in structure.nodes
                     if structure.nodes[n].node_info.in_degree > 0))


def step() -> float:
    holder["state"] = InferenceSGD.inference_step(
        params, holder["state"], clamps, structure, structure.config["inference"].config)
    return energy()


m.op(energy, name="pc-energy", raw=True, typed=False)
m.op(step, name="pc-step!", raw=True, typed=False)
m.run("""
(= (settle-until $eps $max)
   (if (<= $max 0)
       (Settled max-steps (pc-energy))
       (let* (($before (pc-energy)) ($after (pc-step!)))
             (if (< (- $before $after) $eps)
                 (Settled converged $after)
                 (settle-until $eps (- $max 1))))))
""")
step()  # one warm step, so the baseline is inside the descent
baseline = energy()
(group,) = m.run("!(settle-until 0.0001 200)")
(settled,) = group
check("settled symbolically", settled[0], S.Settled)
check("settling did not climb", energy() <= baseline + 1e-6)
check("a settled state is a fixed point", abs(step() - energy()) < 1e-6)
done("08_predictive_coding")
