# Examples by topic

Every example asserts its own outputs. `bindings/python/tests/test_examples.py`
discovers them recursively and excludes only the shared `_common.py`, so a
stopped example fails the build. Run any example from the repository root:

    PYTHONPATH=bindings/python/examples python bindings/python/examples/basics/first_steps.py

The examples keep `from _common import ...` uniform. The test runner and the
command above add the examples root to Python's module search path; `_common.py`
then locates the repository by its project markers instead of assuming a fixed
folder depth.

Examples with optional dependencies such as DuckDB, NumPy, and PyTorch skip
with a message when the dependency is absent.

## Basics

| example | what it shows |
|---|---|
| [`basics/first_steps.py`](basics/first_steps.py) | run, atoms, joined queries, eval, and proof trees |

## Operations

| example | what it shows |
|---|---|
| [`operations/python_definitions.py`](operations/python_definitions.py) | `@m.define`: Python compiled to equations, stacked clauses, generators, and match |
| [`operations/annotation_contracts.py`](operations/annotation_contracts.py) | annotations as evaluation contracts, local type claims, and source-derived definition facts |
| [`operations/engine_controls.py`](operations/engine_controls.py) | per-call time and inference bounds, engine stats, captured output, and DataFrame conversion |

## Data

| example | what it shows |
|---|---|
| [`data/array_interop.py`](data/array_interop.py) | NumPy and PyTorch through one DLPack operation set |

## Integration

| example | what it shows |
|---|---|
| [`integration/python_objects.py`](integration/python_objects.py) | Python object projection, reconstruction, and `py-field` reasoning |
| [`integration/duckdb_space.py`](integration/duckdb_space.py) | DuckDB tables as a matchable space with `WHERE` pushdown |
| [`integration/sqlite_space.py`](integration/sqlite_space.py) | Declared table shapes, transactional writes, and opaque or transparent SQL BLOB images |
| [`integration/routing_equations.py`](integration/routing_equations.py) | dispatch as equations, with the catch-all as the 404 |
| [`integration/web_routes.py`](integration/web_routes.py) | FastAPI-shaped routing: the table is facts and dispatch is unification |
| [`integration/multishot_solving.py`](integration/multishot_solving.py) | clingo-shaped multi-shot solving: parts ground incrementally and externals toggle |
| [`integration/networkx_space.py`](integration/networkx_space.py) | a space's links as a networkx graph, an nx answer written back as atoms, one projection rule for n-ary links |

## Reasoning

| example | what it shows |
|---|---|
| [`reasoning/evolutionary_search.py`](reasoning/evolutionary_search.py) | a population as a space and generations as rewriting |
| [`reasoning/pln_uncertain_reasoning.py`](reasoning/pln_uncertain_reasoning.py) | the engine's PLN library driven from Python |
| [`reasoning/custom_matchers.py`](reasoning/custom_matchers.py) | grounded values with their own matching logic inside unify |

## Live systems

| example | what it shows |
|---|---|
| [`live/standing_queries.py`](live/standing_queries.py) | actors and pub-sub: mailboxes as spaces and delivery inside the write |

## Executable gallery

Every gallery claim is followed by a checked `# ->` MeTTa translation and
checked `# =>` output. The `gallery` gate runs all six programs and verifies
each emitted `@example` through both its MeTTa definition and Python twin.

| example | what it shows |
|---|---|
| [`gallery/family_algebras.py`](gallery/family_algebras.py) | all four family-relation directions under counting, tropical, provenance, ranking, and probability |
| [`gallery/journaled_observed_store.py`](gallery/journaled_observed_store.py) | validation, transactional post-commit observation, and journal replay |
| [`gallery/linda_coordination.py`](gallery/linda_coordination.py) | deterministic watch, peek, and consuming take over a tuple space |
| [`gallery/git_like_worlds.py`](gallery/git_like_worlds.py) | immutable branches, multiset diff, and one observed commit |
| [`gallery/symbolic_tensors.py`](gallery/symbolic_tensors.py) | a symbolic double-transpose lowering to one GEMM result under the tropical carrier |
| [`gallery/ecosystem_graph.py`](gallery/ecosystem_graph.py) | NetworkX expressed as a read-only MeTTa operation whose result returns as knowledge |

The torch examples formerly numbered 06 to 08 live in the sibling `pettorch`
repository. The former soft-unification example 14 lives in the sibling
`pettaprove` repository.

MeTTa's semantics subsume the concepts these systems are made of. Functions
are grounded functions and a call is a reduction. Stateful objects are
grounded atoms with identity. Tables, caches, and populations are spaces, and
a query is a match. Dispatch is equations with the catch-all last. Generators,
search, and retrieval are nondeterminism. Schemas are constructors with
declarations. Structure is facts that rules match over. Subscriptions are
standing queries. Closeness of any kind is matching logic a grounded value
owns, its degrees riding as answer annotations. An integration maps a library onto those forms, and the toolkit in
`metta.integrate` supports that mapping.
