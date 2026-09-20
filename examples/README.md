# PyMeTTa by example

Every example runs and asserts its own output, so nothing here is aspirational.

```sh
PYTHONPATH=extensions/python/examples \
  python extensions/python/examples/basics/first_steps.py
```

## Start here

- **`basics/first_steps`** — the five-minute surface: run MeTTa source, build
  atoms in Python, query with joins, evaluate.

## Spaces backed by something else

- **`integration/sqlite_space`** — the standard-library SQL instance of the
  bridge: declarations relate edge and domain tables to MeTTa heads.
- **`integration/duckdb_space`** — a database as a space, built on the public
  integration interface alone.
- **`integration/networkx_space`** — the metagraph reading made executable: a
  space's expressions over a graph library.
- **`integration/cmetta_space`** — a space whose matching runs in CMeTTa, a C
  runtime, reached as a subprocess.
- **`integration/persistent_migration`** — migrating a persistent space's
  schema through the public factory.
- **`integration/provider_policy`** — request-specific policy at a foreign
  space boundary, through `can_run`.
- **`integration/provider_worlds`** — a foreign provider receiving bounds and
  committing immutable worlds.
- **`integration/registration_lifecycle`** — discovering integrations without
  loading them, and undoing global hooks.
- **`integration/remote_controls`** — authorization and finite cursor
  ownership on a remote space.
- **`integration/python_objects`** — the two-way translator: an Enum becomes
  symbols, a dataclass becomes an expression.
- **`integration/multishot_solving`** — clingo's multi-shot solving on the
  lingua-franca reading.
- **`integration/web_routes`** — the Express/FastAPI route example, built on
  the core surface.
- **`integration/routing_equations`** — the subsumption frame on the smallest
  case: an app is a space, a route is an equation.
- **`data/array_interop`** — one operation set for every DLPack library, so
  NumPy flows through the same MeTTa function.

## Defining and running

- **`operations/python_definitions`** — the `@define` path: write Python, get
  MeTTa.
- **`operations/annotation_contracts`** — annotations controlling evaluation
  and becoming facts derived from a contract.
- **`operations/effect_ranks`** — classifying an operation with a decorator,
  and reading the rank it carries.
- **`operations/property_instances`** — ground property-test instances
  generated from a symbolic pattern.
- **`operations/engine_controls`** — the engine-control surface on one page:
  per-call time and inference bounds, scoped settings.
- **`operations/runtime_configuration`** — process-wide runtime and
  presentation settings as `(limit ...)` rows.
- **`operations/error_handling`** — classifying a false MeTTa claim separately
  from an engine fault.
- **`operations/explaining_a_query`** — EXPLAIN over the engine's own
  decisions: which join the matcher will run.
- **`operations/concurrency_handles`** — multi-argument pool work and
  nonblocking mailbox reads.
- **`operations/saga_compensation`** — recovering committed external-style
  steps through saga receipts.

## Reasoning

- **`reasoning/pln_uncertain_reasoning`** — the engine's PLN library from
  Python: implications with truth values and evidence.
- **`reasoning/neurosymbolic_addition`** — perception that is honestly unsure,
  a rule that is exact, a constraint that propagates.
- **`reasoning/custom_matchers`** — custom matching as a property of grounded
  atoms, on the public surface.
- **`reasoning/evolutionary_search`** — an evolutionary loop where the
  population is a space and a generation is space rewriting.
- **`reasoning/literature_discovery`** — literature-based discovery as one
  neurosymbolic query: a hypothesis no paper states.

## Larger pieces

- **`gallery/family_algebras`** — one family relation run in every logical
  direction under every carrier.
- **`gallery/ecosystem_graph`** — a NetworkX shortest-path algorithm expressed
  as one MeTTa operation.
- **`gallery/git_like_worlds`** — branch, diff and commit immutable worlds
  like local repository heads.
- **`gallery/journaled_observed_store`** — validate, transact, observe, close
  and replay a journaled fact store.
- **`gallery/linda_coordination`** — one deterministic Linda tuple through
  watch, peek and take.
- **`gallery/symbolic_tensors`** — lowering a symbolic tensor identity to one
  numeric GEMM.
- **`live/standing_queries`** — actors and pub-sub as spaces: a mailbox is a
  space, a subscription is a standing query.

## Every language construct, in Python

`language-feature-examples/` is the whole shipped MeTTa corpus written again in
Python, one file per example, mirroring the MeTTa tree. Read it when you know
the MeTTa spelling and want the Python one.

## How these stay honest

Each example asserts its own outputs, and `tests/repository/test_examples.py`
runs all of them, so a broken one fails the build. Ones needing an optional
dependency skip with a message naming it.
