# Door-order contract

The gate certifies the published **partial** ranking of every declared door.
It checks complete row coverage, rank equations, door-cycle witnesses, blocked
dependencies, contract sites and freshness of both generated tables.

| Source finding | Published rank |
| --- | --- |
| Closed host work with no door dependency | 0 |
| A native crossing with no door composition or supplied contract call | 1 |
| Closed door composition | `1 + max(callee ranks)` |
| Mixed crossings, recursion, open dispatch or an unordered dependency | Unnumbered, with its findings retained |

`python tools/doororder.py` checks this contract from the Python component.
`sh tools/check.sh door-order` runs it from the superproject. `--write` updates
the generated verdict and typeshed invocation tables. It does not assign numbers
to unresolved results. Consumers that need finite orders use
`--require-ordered DOOR [DOOR ...]`; a missing or unnumbered key fails even with
`--write`.

## Why the gate changed

The former predicate required the mixed, recursive and defect-open lists to be
empty. It failed on the shipped implementation before this change. A strict
rank satisfies `rank(caller) > rank(callee)`. Following a call cycle would require
`rank(f) > rank(f)`, a contradiction. Real recursive helpers such as
`metta._atoms.model._operator_form` recursively lower nested tuples; removing
their call edges would change the claim being checked. The inherited
`SpaceHandle._space` liveness crossing independently makes many compositions
mixed. Ignoring helper crossings also fails the planted inherited-property
constructor control.

The gate now decides whether the source-derived partial ranking and published
table agree with the rules above. It no longer decides that every shipped door
has a finite order. It does not prove termination, eliminate dynamic dispatch,
or certify a client's finite-order requirement unless that requirement is named.
This is a deliberate specification change, recorded under
`door-analysis-certificates` and `i10` in the repository record.

The default gate remains falsifiable: dropping a declared row, inventing a rank
or door-cycle witness, or changing a door without updating its verdict fails.
The tests also plant an unresolved implementation and require its finite order;
regenerating the table cannot make that requirement pass.

## Precision and value-flow equality

Concrete type declarations already refine instance and container alternatives.
They now apply the same rule to known functions, bound methods, class objects
and generators. `Callable`, `Any` and `type[C]` retain their distinct meanings.
An incompatible-only actual remains visible, so an invalid call cannot become
valid by deleting its only receiver. Missing function attributes produce an
unresolved witness instead of a fabricated host-only call.

The measured amplification starts in `metta.algebra._catalog_declaration`:
`getattr(match, field)` encounters foreign containers and produces their bound
methods, including `extend`. These methods formerly survived concrete `Atom`
declarations and reached callable collection in `expand_positional`. The
attribution found 367 introduced container methods and 916,234 reference-pair
writes in that collector. The tuple tree walk was previously ruled out and was
not changed.

`CopyGraph` records only unfiltered identity inclusions `values(a) <= values(b)`.
Mutual reachability proves equality at a fixed point, allowing those cells to
share storage and readers. Equality of their current sets alone proves nothing
about future writes. Imports, annotations, narrowing and other transformations
are not identity edges. Call-graph SCCs retain their recursive findings.
This separation follows the copy-edge restriction in
[SVF's Andersen solver](https://github.com/SVF-tools/SVF/blob/f3f095033ac117c9b4ab576410d2326807e6ee31/svf/lib/WPA/AndersenSFR.cpp#L35-L48).

For an isolated cycle of `n` copy cells, storing a later set of `p` values changes
from `n` cells and `n` copy edges to one cell and no internal edges. Value unions
cost `Theta(p)` after quotienting, versus `Theta(n*p)` before. Notifying `r`
distinct readers still costs `Theta(r)`. Computing the quotient costs
`O(V log V + E)` including deterministic member sorting, with `O(V+E)` space.
Other transfer functions keep their existing costs.

## Measurements

The initial attribution used component `e407647c06cf2fcf4223458a3de72c268bad7586`.
The revised attribution used frozen snapshot
`961e52f73de778c6a5ad9f2c87fb754d8401be6a`. The new solver module accounts for
the extra module. These are stored reference pairs, not physical heap objects;
hash consing already shares equal immutable sets.

| Corpus | Before modules | Before references | After modules | After references |
| --- | ---: | ---: | ---: | ---: |
| All sources | 178 | 3,177,078 | 179 | 1,130,997 |
| Without `metta.algebra` | 177 | 1,272,822 | 178 | 802,711 |

The traced full-run CPU measurements were 126.05 seconds before and 33.39 seconds
after. These include attribution overhead and concurrent workstation activity;
the reference counts establish the precision reduction without treating those
times as an instruction benchmark.

The quotient merges only `metta._atoms.templates._spans`'s `scan` and `index`
cells in this corpus. Disabling collapse yields identical call facts and
identical live sets after normalizing allocation-order literal-key IDs. Raw
stores differ in 23 cells only by `unreachable` bottom markers. The large
reduction is due to declaration precision; no corpus speedup is claimed for SCC
collapse. Generated constraint graphs check arbitrary late writes and edges
against an independent unquotiented solver, and a cycle-size sweep checks the
one-cell result while preserving every reader.

## Change record

2026-09-23: Replace the impossible universal-order predicate with the partial
ranking contract and explicit finite-order obligations. Refine callable species
at concrete declarations, retain invalid function-member witnesses, and collapse
proven identity-copy SCCs. Include both solver modules in the persisted-core
fingerprint and keep extension copies isolated. Regenerate the verdict table.

Verification on frozen snapshot `187a1ce379126250e894de8c02934fa2148813cb`:
`HYPOTHESIS_PROFILE=ci sh tools/check.sh door-order door-order-selftest` exits 0;
145 tests pass. Ruff passes all five changed handwritten Python files. Mypy
passes the three solver modules. jscpd reports no clones in the changed code.
The report contains 227 doors: 30 order 0, 16 order 1, two order 2 and 179
unnumbered, retaining 113 mixed, 108 recursive and 155 defect-open findings.

Adding `space:planted-order` with `registry.current()` produces an unresolved
external-call witness and a stale-table exit of 1. Running
`--write --require-ordered space:planted-order` still exits 1 with no table drift
and `required_unordered = ["space:planted-order"]`. Substituting that dispatch
in the existing alias/helper test fails with `AssertionError: assert None == 1`.
Both planted changes were removed before the passing verification.

An extra standalone mypy invocation over `tools/doororder.py` exposed existing
`import-not-found` diagnostics for `doorgen` and `mypy`, plus `_shipped`'s
string/tuple variable-reuse errors. The configured mypy surface is `metta` and
`ext`, not the tools scripts; those six diagnostics are outside this gate's
verification claim. The introduced optional-rank arithmetic diagnostic was
fixed and the solver-module check passes.
