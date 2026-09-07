# Examples by topic

Every example asserts its own outputs. `extensions/python/tests/repository/test_examples.py`
discovers them recursively and excludes the shared `_common.py` and the
language-feature corpus below, so a stopped example fails the build. Run any
example from the repository root:

    PYTHONPATH=extensions/python/examples python extensions/python/examples/basics/first_steps.py

The examples keep `from _common import ...` uniform. The test runner and the
command above add the examples root to Python's module search path; `_common.py`
then locates the repository by its project markers instead of assuming a fixed
folder depth.

Examples with optional dependencies such as DuckDB, NumPy, and PyTorch skip
with a message when the dependency is absent.

## Language features

`language-feature-examples/` is the other half of this folder and the larger
one: the whole shipped MeTTa corpus written again in Python, one file per
example, its directories mirroring `examples/` so a file is addressed by
transforming the path of the program it answers. Read it for how a given MeTTa
construct is spelled in Python.

These are the same kind of thing as the topical examples above and a different
shape. Each defines `twin(m)` rather than running itself, because the corpus is
driven by `extensions/python/tools/twin_coverage.py`, which passes the handle,
compares the answers against the original's alpha-equal multiset, and holds
each file to the inference budget pinned at its foot. That is why the runner
above skips this directory: a file here verifies nothing when executed on its
own.

## Basics

| example | what it shows |
|---|---|
| [`basics/first_steps.py`](basics/first_steps.py) | run, atoms, unification/substitution, joined queries, eval, and proof trees |

## Operations

| example | what it shows |
|---|---|
| [`operations/python_definitions.py`](operations/python_definitions.py) | `@m.define`: Python compiled to equations, plus class accessor and method exposure controls |
| [`operations/annotation_contracts.py`](operations/annotation_contracts.py) | annotations as evaluation contracts, local type claims, and source-derived definition facts |
| [`operations/concurrency_handles.py`](operations/concurrency_handles.py) | multi-argument engine-pool work and nonblocking channel reads |
| [`operations/engine_controls.py`](operations/engine_controls.py) | per-call and scoped time, inference, and stack bounds, engine stats, captured output, and DataFrame conversion |
| [`operations/error_handling.py`](operations/error_handling.py) | structured assertion failures and the explicit row-data-to-exception bridge |
| [`operations/explaining_a_query.py`](operations/explaining_a_query.py) | `explain()`: the join the matcher will run, the explanation as storable atoms, `analyze=` and its refusal |
| [`operations/property_instances.py`](operations/property_instances.py) | ground Hypothesis instances that preserve named and anonymous variable laws |
| [`operations/runtime_configuration.py`](operations/runtime_configuration.py) | inspected process settings, pre-start configuration, and the startup freeze |
| [`operations/saga_compensation.py`](operations/saga_compensation.py) | committed effect receipts and reverse-order compensation on exceptional exit |

## Data

| example | what it shows |
|---|---|
| [`data/array_interop.py`](data/array_interop.py) | NumPy and PyTorch through one DLPack operation set |

## Integration

| example | what it shows |
|---|---|
| [`integration/python_objects.py`](integration/python_objects.py) | registered and class-owned `__metta__`/`__from_metta__` conversion, plus `py-field` reasoning |
| [`integration/registration_lifecycle.py`](integration/registration_lifecycle.py) | unloaded entry-point discovery and exact cleanup of process-wide integration hooks |
| [`integration/duckdb_space.py`](integration/duckdb_space.py) | DuckDB tables as a matchable space with `WHERE` pushdown |
| [`integration/sqlite_space.py`](integration/sqlite_space.py) | Declared table shapes, transactional writes, and opaque or transparent SQL BLOB images |
| [`integration/persistent_migration.py`](integration/persistent_migration.py) | One-open journal schema migration through the public space factory |
| [`integration/provider_policy.py`](integration/provider_policy.py) | structural provider capabilities, per-request policy, and refusal reasons |
| [`integration/provider_worlds.py`](integration/provider_worlds.py) | exact bound pushdown and provider-owned immutable-world snapshots and commits |
| [`integration/remote_controls.py`](integration/remote_controls.py) | remote authorization, capability discovery, and cursor resource ceilings |
| [`integration/routing_equations.py`](integration/routing_equations.py) | dispatch as equations, with the catch-all as the 404 |
| [`integration/web_routes.py`](integration/web_routes.py) | FastAPI-shaped routing: the table is facts and dispatch is unification |
| [`integration/multishot_solving.py`](integration/multishot_solving.py) | clingo-shaped multi-shot solving: parts ground incrementally and externals toggle |
| [`integration/networkx_space.py`](integration/networkx_space.py) | a space's links as a networkx graph, an nx answer written back as atoms, one projection rule for n-ary links |
| [`integration/cmetta_space.py`](integration/cmetta_space.py) | a sibling MeTTa implementation as a matcher behind the same provider seam |

## Reasoning

| example | what it shows |
|---|---|
| [`reasoning/evolutionary_search.py`](reasoning/evolutionary_search.py) | a population as a space and generations as rewriting |
| [`reasoning/pln_uncertain_reasoning.py`](reasoning/pln_uncertain_reasoning.py) | the engine's PLN library driven from Python |
| [`reasoning/custom_matchers.py`](reasoning/custom_matchers.py) | grounded values with their own matching logic inside unify |
| [`reasoning/literature_discovery.py`](reasoning/literature_discovery.py) | an embedding decides what unifies, the engine decides what follows, and the answer carries its sources |
| [`reasoning/neurosymbolic_addition.py`](reasoning/neurosymbolic_addition.py) | a predictive-coding network perceives, a symbolic constraint sharpens what it saw |

## Live systems

| example | what it shows |
|---|---|
| [`live/standing_queries.py`](live/standing_queries.py) | actors and pub-sub, including inspection of the space's live event folds |

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
