"""Purpose: perception that is honestly unsure, a rule that is exact, and a
constraint that propagates backwards to sharpen the perception. DeepProbLog's
canonical task with predictive coding as the perceptron, on someone else's
neural library, with nothing on either side adapted to the other.

A FabricPC network trained by predictive coding reads a noisy observation and
answers a distribution over digits. That belief crosses as ordinary facts, so
every existing symbolic door applies to it without a bridge: a conjunction is
the join over hypothesis pairs, and lib_measure marginalises, because adding
the weight of hypotheses that agree on an outcome is what marginalising means.

The result neither half reaches alone is the last one. Told only what the sum
is, the posterior over the first digit is sharper than the network's own
output, because the constraint eliminates hypothesis pairs the network could
not rule out. The network cannot reason about sums; the reasoner has no eyes.

Guarantees:
  - the network alone is uncertain, and the symbolic constraint raises its
    confidence in the true digit [tested: test_example_runs_and_verifies_itself]
  - the marginal over sums is a distribution, and its mode is the true sum
    [tested: test_example_runs_and_verifies_itself]
  - MeTTa is never called inside the JIT or the differentiated node loop,
    which is FabricPC's own boundary [tested: test_example_runs_and_verifies_itself]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    # A capability check rather than a version one: fabricpc.__version__ reads
    # the installed distribution's metadata, so it reports the installed
    # version even when an earlier sys.path entry supplies different code.
    from fabricpc.training import make_train_step
except ImportError:
    skip("fabricpc 0.5 or newer is not installed (no training.make_train_step)")

import jax
import optax
from fabricpc.core.activations import SigmoidActivation, SoftmaxActivation
from fabricpc.core.energy import CrossEntropyEnergy
from fabricpc.core.inference import InferenceSGD
from fabricpc.core.topology import Edge
from fabricpc.graph_assembly import TaskMap, graph
from fabricpc.graph_initialization import initialize_params
from fabricpc.nodes import IdentityNode, Linear
from metta import Answer, MeTTa, S, V, lib, match

DIGITS, DIM, KNOWN_SUM = 3, 6, 3

# A predictive-coding network, built the way FabricPC's own examples build one.
key = jax.random.PRNGKey(0)
prototype = jax.random.normal(key, (DIGITS, DIM))
draw = jax.random.split(key, 3)
labels = jax.random.randint(draw[0], (256,), 0, DIGITS)
observations = prototype[labels] + 0.35 * jax.random.normal(draw[1], (256, DIM))

sensor = IdentityNode(shape=(DIM,), name="sensor")
hidden = Linear(shape=(16,), activation=SigmoidActivation(), name="hidden")
digit = Linear(
    shape=(DIGITS,),
    activation=SoftmaxActivation(),
    energy=CrossEntropyEnergy(),
    name="digit",
)
structure = graph(
    nodes=[sensor, hidden, digit],
    edges=[
        Edge(source=sensor, target=hidden.slot("in")),
        Edge(source=hidden, target=digit.slot("in")),
    ],
    task_map=TaskMap(x=sensor, y=digit),
    inference=InferenceSGD(eta_infer=0.1, infer_steps=12),
)
params = initialize_params(structure, key)
optimizer = optax.adam(5e-2)
opt_state = optimizer.init(params)
step = make_train_step(structure, optimizer, algorithm="pc")
batch = {"x": observations, "y": jax.nn.one_hot(labels, DIGITS)}
for _ in range(200):
    params, opt_state, metrics, _ = step(params, opt_state, batch, key)
check("predictive coding drove the energy down", float(metrics["energy"]) < 0.01)


def belief(vector):
    """The network's distribution over digits, as (weight digit) pairs."""
    weights = params.nodes
    activation = jax.nn.sigmoid(vector @ weights["hidden"].weights["sensor->hidden:in"])
    scores = jax.nn.softmax(activation @ weights["digit"].weights["hidden->digit:in"])
    return [(round(float(scores[d]), 4), d) for d in range(DIGITS)]


# Two observations noisy enough that the network is honestly unsure.
noise = lambda seed: 1.6 * jax.random.normal(jax.random.PRNGKey(seed), (DIM,))  # noqa: E731 -- one expression, named where it is used
sees_a, sees_b = belief(prototype[1] + noise(7)), belief(prototype[2] + noise(9))
alone = dict((d, w) for w, d in sees_a)
check("the network alone is uncertain about the first digit", alone[1] < 0.9)

m = MeTTa().self
m += lib.measure


# The network is an OPERATION the engine calls, one answer per digit with its
# confidence as the answer's annotation. It reads the trained weights and
# writes nothing, which is what `reads` declares.
def perceive(observation):
    """One answer per digit hypothesis, the network's confidence riding along."""
    seen = sees_a if observation == S.a else sees_b
    for weight, d in seen:
        yield Answer(value=d, k=weight)


m.reads(perceive, name="perceive")
m.annotations("perceive", "ranked")
check("the engine calls the network", int(m.eval(S.collapse(S.top(1, S.perceive(S.a))))[0][0]), 1)

# Perception also enters as ordinary facts, so the rule below can weigh it.
for weight, d in sees_a:
    m += S.sees(S.a, d, weight)
for weight, d in sees_b:
    m += S.sees(S.b, d, weight)


@m.define
def hypothesis(x, y):
    """Every joint hypothesis as (weight sum).

    Two matches in one body ARE the join, and the product and the sum are the
    engine's arithmetic. Nothing here crosses back into Python.
    """
    a = match((S.sees, x, V.da, V.wa), (V.da, V.wa))
    b = match((S.sees, y, V.db, V.wb), (V.db, V.wb))
    return (a[1] * b[1], a[0] + b[0])


@m.define
def consistent_with(x, y, total):
    """The same join, keeping only hypotheses whose sum is `total`, and
    answering what the FIRST observation was under that constraint.
    """
    a = match((S.sees, x, V.da, V.wa), (V.da, V.wa))
    b = match((S.sees, y, V.db, V.wb), (V.db, V.wb))
    if a[0] + b[0] == total:
        return (a[1] * b[1], a[0])
    return ()


pairs = tuple(tuple(row) for row in hypothesis(S.a, S.b))
check("the join enumerates every hypothesis pair", len(pairs), DIGITS * DIGITS)
marginal = m.fn.ws_collapse(pairs).one()
check("the marginal is a distribution", abs(float(m.fn.ws_total(marginal).one()) - 1.0) < 1e-6)
check("its mode is the true sum", int(m.fn.ws_best(marginal).one()), KNOWN_SUM)

# The payoff: told only the sum, the rule keeps the hypotheses that survive it.
kept = tuple(tuple(row) for row in consistent_with(S.a, S.b, KNOWN_SUM) if len(row) == 2)
posterior = m.fn.ws_normalize(m.fn.ws_collapse(kept).one()).one()
sharpened = dict((int(p[1]), float(p[0])) for p in posterior)
check("the constraint picks the true digit", int(m.fn.ws_best(posterior).one()), 1)
check("and is more confident than perception alone", sharpened[1] > alone[1])

print(f"  perception alone : P(a=1) = {alone[1]:.4f}")
print(f"  given sum = {KNOWN_SUM}    : P(a=1) = {sharpened[1]:.4f}")
done("neurosymbolic_addition")
