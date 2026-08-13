# Examples: the integrations, each one runnable and self-verifying

Every example asserts its own outputs, so a printout here is a checked claim
rather than something to trust; the test suite runs them all
(`python/tests/test_examples.py`), which is what keeps them true. Run one
from the repository root:

    python python/examples/01_first_steps.py

Examples with optional dependencies (duckdb, numpy, torch, fabricpc) skip
with a message when the dependency is absent.

| example | what it shows |
|---|---|
| 01_first_steps | run, atoms, joined queries, eval, proof trees |
| 02_write_metta_in_python | @m.define: Python compiled to equations, stacked clauses, generators, match |
| 03_objects_both_ways | the four-image translator and py-field reasoning |
| 04_sql_is_a_space | DuckDB tables as a matchable space with WHERE pushdown |
| 05_one_array_layer | NumPy and torch through one DLPack operation set |
| 06_torch_deep | rules routing between models; equations trained by torch.optim |
| 07_attention_is_matching | the KV cache as a space; attention equals torch's |
| 08_predictive_coding | FabricPC settling driven by a symbolic convergence loop |
| 09_the_routing_frame | dispatch as equations, the catch-all as the 404 |
| 10_evolution_in_a_space | a population as a space; generations as rewriting |
| 11_pln_uncertain_reasoning | the engine's PLN library driven from Python |
| 12_standing_queries | actors and pub-sub: mailboxes as spaces, delivery inside the write |
| 13_custom_matchers | fuzzy and semantic matchers feeding the measure algebra |
| 14_soft_unification | Sessa's weak unification and goal-directed soft proving over terms |
| 15_web_routes | FastAPI's routing semantics: the table is facts, dispatch is unification |

The frame behind the folder: MeTTa's semantics subsume the concepts these
systems are made of. Functions are grounded functions and a call is a
reduction; stateful objects are grounded atoms with identity; tables,
caches and populations are spaces and a query is a match; dispatch is
equations with the catch-all last; generators, search and retrieval are
nondeterminism; schemas are constructors with declarations; structure is
facts rules match over; subscriptions are standing queries; closeness of
any kind is a matcher whose answers carry a measure. An integration maps a
library onto that, and the toolkit in `petta.integrate` makes the mapping
a page of code.
