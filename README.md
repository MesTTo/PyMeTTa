# PyMeTTa

MeTTa in Python. Atoms are Python values, spaces are queryable stores,
equations rewrite, and a Python function can be a MeTTa function.

Semantics are PeTTa's. This is a surface onto that engine, not a second
implementation of the language. Pre-1.0: the version is 0.8.0 and the surface
is still moving.

```sh
pip install PyMeTTa
```

```python
from metta import MeTTa

with MeTTa() as m:
    m.self.run("(= (f) 1) !(f) !(+ 1 2)")
    # [[Grounded(1)], [Grounded(3)]]
```

## Atoms: four kinds, no strings

```python
from metta import S, V, G, Expression

S.alice                      # a symbol
V.x                          # a variable, $x
G(3.14)                      # a grounded Python value
S.parent(S.bob, S.alice)     # an expression: (parent bob alice)
```

A string is text, never a name. `S.foo` is the symbol; `"foo"` is a string
atom. Python's casing reaches MeTTa's hyphens: `fn.car_atom` is `car-atom`,
and `m["prime?"]` is the bracket door for a head outside identifier grammar.

## Asking

```python
m.self.run("(= (parent bob alice)) (= (parent alice zoe))")
m.self.run("!(match &self (= (parent $p alice)) $p)")     # [[bob]]

len(m)                       # 6
S.parent(S.bob, S.alice) in m
m[S.parent(V.p, S.alice)]    # pattern indexing
```

- `run` `eval` — evaluate source or a built term
- `match` `add` `remove` — the space doors
- `collapse` `superpose` `once` `chain` `case` — the control forms
- `len`, `in`, `[...]`, iteration — Python's own protocols, on the home space

## Defining: two doors

```python
from metta import equation, rules

equation(S.f(V.x)).to(V.x + 1)          # one equation, built not parsed
m.define(prolog=source, name="p-sum")   # a Prolog predicate as the function

@m.op(effect="pureStructural")          # a Python function IS a MeTTa function
def shout(word: str) -> str:
    return word.upper()

m.self.run('!(shout "hi")')             # [[Grounded('HI')]]
```

`effect=` is required and takes one of `pureStructural`, `readOnlyLookup`,
`nondeterministicReadOnly`, `writesState`, `oracleIO`. Omit it and the call
refuses by name and lists the five. Registering a generator lifts the class to
at least `nondeterministicReadOnly` by itself.

## Spaces

- The home space, plus `new-space` and named spaces.
- **State cells** for mutable values inside a space.
- **Foreign spaces**: anything that answers `match` is a space. A dataframe, a
  key-value store, a vector index, a remote service.
- **Composed spaces** answer a provider; `metta.attach` binds one.
- `metta.spaces.overlay(...)` layers one over another.

## Types

- Declarations, gradual checking, and refinements.
- Tensor shapes, with shape-carrying types.
- `arrow`, `typed`, `convert` on the top-level surface.
- The engine checks; this seat declares.

## Declared algebras

```python
import metta
metta.algebra.counting                  # a shipped carrier
metta.algebra("x", plus=max, times=min) # or declare one
```

Ten carriers ship. The accepted laws are a closed vocabulary the catalog
publishes, so a wrong name refuses and names the set.

## Concurrency, transactions, bounds

```python
with m.transaction():        # rollback and receipts
    ...
m.limits(inferences=10_000)  # a bound the engine enforces
m.stats()                    # deterministic inference counts, not wall clock
```

- `metta.aio` — the async surface.
- Threads, and the engine's own scopes.
- Inference and time limits, with named refusals when they trip.

## Seeing what happened

- `m.stats()` — inferences, cputime, walltime, gc, table bytes, as deltas.
- `m.trace(...)` — the derivation.
- `m.lint()` — findings over a space, silenced per kind with
  `# metta: ok(<kind>)`.
- `metta.testing` — `SpaceMachine` and the compliance suites a provider
  inherits.

## When it refuses

Every deliberate refusal carries `.remedy` and `.ground` beside its message:
the repair as data, and the authority it rests on. `MettaError` is the base,
with `EngineError`, `MettaSyntaxError`, `CastError`, `CompileError`,
`SourceNotFound`, `MettaResultError`, `AssertionFailure`, `TransportFailure`,
`ResourceLimitError` and `Interrupted` under it.

## The ladder, and it never shrinks

Every convenience names its longhand, and the rungs below stay reachable:
built terms, then strings, then Prolog, then C. Nothing forces you up or down.

## The rest of the library

`metta.aio` `metta.algebra` `metta.doors` `metta.foreign` `metta.library`
`metta.lint` `metta.remote` `metta.testing` — 209 names on the top-level
surface, each checked against the live library by the `llms` lane.

Underneath are 62 MeTTa libraries — `lib_math`, `lib_json`, `lib_http`,
`lib_graph`, `lib_pln`, `lib_tabling`, `lib_torch`, `lib_constraints` and the
rest — written in MeTTa over the engine's primitives.

## Integrations live outside this package

PyMeTTa names no third-party library. Integrations are separate distributions
discovered through the `metta.extensions` entry-point group, in
[PyMeTTa-Extensions](https://github.com/MesTTo/PyMeTTa-Extensions):

`metta-pandas` `metta-polars` `metta-duckdb` `metta-sqlite` `metta-numpy`
`metta-arrays` `metta-pyarrow` `metta-nanoarrow` `metta-tables` `metta-faiss`
`metta-graphql` `metta-pydantic` `metta-otel` `metta-live` `metta-remote`
`metta-benchmarking`

Each registers against a declared seam point rather than being named by the
core, which is why the core can be installed without any of them.

## More

`metta.llms()` prints the full cheat sheet the way `help()` does, from an
install as well as a checkout; `python -m metta llms` is the same from a
shell. Every door named there is checked against the live library, so the text
cannot drift from the code.
