# PyMeTTa

MeTTa in Python. Atoms are Python values, spaces are queryable stores,
equations rewrite, and a Python function can be a MeTTa function.

Semantics are PeTTa's. This is a surface onto that engine, not a second
implementation of the language.

```sh
pip install .
```

```python
from metta import MeTTa

with MeTTa() as m:
    m.self.run("(= (f) 1) !(f) !(+ 1 2)")
    # [[Grounded(1)], [Grounded(3)]]
```

## Query a space

```python
m.self.run("(= (parent bob alice)) (= (parent alice zoe))")
m.self.run("!(match &self (= (parent $p alice)) $p)")
# [[bob]]

len(m)          # 6
```

## A Python function IS a MeTTa function

```python
@m.op(effect="pureStructural")
def shout(word: str) -> str:
    return word.upper()

m.self.run('!(shout "hi")')
# [[Grounded('HI')]]
```

`effect=` is required and takes one of `pureStructural`, `readOnlyLookup`,
`nondeterministicReadOnly`, `writesState`, `oracleIO`. Omit it and the call
refuses by name and lists the five.

## Build terms instead of strings

```python
from metta import S, V, equation

equation(S.f(V.x)).to(V.x + 1)     # one equation, built not parsed
S.parent(S.bob, S.alice)           # (parent bob alice)
```

A name reaches MeTTa through Python's own casing: `fn.car_atom` is
`car-atom`, and `m["prime?"]` is the door for a head outside identifier
grammar.

## What is here

- **Spaces** — `match`, `add`, `remove`, state cells, `new-space`, and the
  collection protocols, so `len(m)`, `atom in m` and `m[pattern]` read the
  home space.
- **Evaluation** — `run`, `eval`, `collapse`, `superpose`, `once`, `chain`,
  `case`, and the stream forms.
- **Types** — declarations, gradual checking, refinements, and tensor shapes.
- **Nondeterminism** — answers are sequences; `Answers` and `Rows` carry them
  with `.column()`, `.index()` and the usual iteration.
- **Transactions** — `m.transaction()`, with rollback and receipts.
- **Limits** — `m.limits(inferences=...)`, and `m.stats()` for deterministic
  inference counts.
- **Prolog underneath** — `m.define(prolog=source, name=...)` when a predicate
  is the clearest way to say it.
- **Foreign spaces** — a provider answers `match` and becomes a space:
  dataframes, key-value stores, anything queryable.
- **Refusals carry repairs** — every deliberate refusal has `.remedy` and
  `.ground` beside its message.

## More

`metta.llms()` prints the full cheat sheet the way `help()` does, from an
install as well as a checkout. `python -m metta llms` is the same from a
shell. Every door named there is checked against the live library by the
`llms` lane, so the text cannot drift from the code.
