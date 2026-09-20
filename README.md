<!--
Purpose: teach the Python seat through its public doors and runnable example idioms.
Assumes: Python 3.12+, SWI-Prolog 9.3+, and janus_swi linked to that SWI.
Decides: examples use define for lowered equations and named effect decorators
  for Python callbacks; optional integrations are identified at their use sites.
-->

# PyMeTTa

MeTTa in Python: build terms, query spaces, lower Python functions into equations, and let the engine call Python libraries.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    m.run("(= (double $x) (* 2 $x))")
    assert m.eval(S.double(21)) == [42]

    m.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann))
    rows = m.match(S.Parent(V.gp, V.p), S.Parent(V.p, V.gc))
    assert rows.to_dicts() == [{"gp": "Tom", "p": "Bob", "gc": "Ann"}]
```

The engine supplies MeTTa semantics; Python supplies values, functions, storage providers, and application control.

## Installation

Install the distribution into a Python environment with a matching SWI-Prolog and Janus installation.

```sh
pip install PyMeTTa
python -m metta --version
python -m metta llms
```

A checkout can select its engine through `METTA_PATH`, while the installed distribution carries its runtime.

```sh
# From the workspace root:
pip install -e extensions/python
export METTA_PATH="$PWD"
python -m metta run examples/your-program.metta
```

Optional integrations are separate distributions, installed only for the doors your application uses.

| Extra | Use |
|---|---|
| `pymetta[arrays]` | Array API and DLPack integration |
| `pymetta[dataframes]` | pandas and Polars result conversions |
| `pymetta[arrow]` | Arrow producers and consumers |
| `pymetta[sql]` | SQL integrations |
| `pymetta[graphql]` | GraphQL request execution |
| `pymetta[live]` | The materialized-view accessor |
| `pymetta[remote]` | The remote accessor |
| `pymetta[models]` | Model conversion integration |
| `pymetta[otel]` | OpenTelemetry integration |

[llms.txt](llms.txt) is the compact reference; [examples](examples/README.md) contains programs that check their own results.

## The surface

The root module exports 104 names, grouped here without requiring a wildcard import.

| Feature | Doors |
|---|---|
| Context and space types | `MeTTa`, `Space`, `SpaceLike`, `SpaceProvider` |
| Atom classes | `Atom`, `Symbol`, `Variable`, `Grounded`, `Expression`, `Handle`, `Undefined` |
| Factories and constants | `S`, `V`, `G`, `ground`, `fresh`, `seg`, `TRUE`, `FALSE`, `UNIT` |
| Answer types | `Answer`, `Answers`, `Bindings`, `Rows` |
| Built control terms | `and_`, `or_`, `not_`, `if_`, `in_`, `superpose` |
| Reading and substitution | `parse`, `forms`, `render`, `unify` |
| Type declarations | `arrow`, `typed` |
| Evaluation and queries | `run`, `eval`, `match`, `solve`, `fn` |
| Space selection and writes | `engine`, `space`, `current_space`, `attach`, `drop`, `add`, `remove`, `view` |
| Definitions | `define`, `Defined`, `equation`, `rules`, `py` |
| Python operations | `op`, `pure`, `reads`, `writes`, `io`, `registered`, `withdraw` |
| Write judgments | `accept`, `refuse` |
| Mutable cells | `State` |
| Algebra selection | `under`, `current_algebra` |
| Shipped carriers | `set`, `bag`, `bool`, `counting`, `tropical`, `prob`, `ranked`, `prov`, `budget`, `amplitude` |
| Concurrent work | `spawn`, `par_map`, `race`, `every`, `channel`, `scope`, `move_on_after` |
| Bounds and speculation | `limits`, `speculate` |
| Observation | `stats`, `trace`, `doc`, `catalog`, `reflection` |
| Libraries and deployment | `lib`, `Library`, `boot`, `Lock`, `Drift` |
| Runtime configuration | `config`, `Config` |
| Refusals | `MettaError`, `NotReducible`, `Timeout`, `is_transport_failure` |
| Reference and tooling | `llms`, `stubs`, `__version__` |

Public modules and packages have their own contracts; this checkout contains 27 non-underscore top-level entries.

| Module | Doors and purpose |
|---|---|
| `metta.aio` | `AsyncMeTTa`, `connect`: worker-owned asynchronous calls |
| `metta.algebra` | Carriers, declarations, tagged answers, retained derivations, law checking |
| `metta.cli` | The installed CLI launcher |
| `metta.convert` | `encode`, `decode`, `project`, `build`: host and atom representations |
| `metta.derivation` | Proof objects and rendering |
| `metta.doors` | Declared operation contracts and `table()` |
| `metta.events` | `Event`, `EventStream`, `Fold`: writes and commit boundaries |
| `metta.foreign` | Storage capability protocols and `SpaceProvider` |
| `metta.importing` | `install`, `installed`: import MeTTa source as Python modules |
| `metta.integrate` | Entry-point discovery, conversion, representation, and reflection registration |
| `metta.ipython` | Line and cell magics; `use` selects their space |
| `metta.library` | Library roster, declaration rows, cards, digests, and locks |
| `metta.lint` | Findings, file diagnostics, and machine-applicable repairs |
| `metta.live` | `Live`, `Delta`, `Changes`: maintained query answers |
| `metta.manifest` | Application assembly through `boot` |
| `metta.parallel` | Futures, scopes, channels, thread pools, and process pools |
| `metta.paths` | `path`, `Attr`, `Key`: lazy paths inside live values |
| `metta.pytest_plugin` | The `metta` and `scratch_space` fixtures |
| `metta.remote` | `serve`, `connect`, `Gateway`, `RemoteSpace`, `RemoteCursor` |
| `metta.seam` | Declared extension points and registered rows |
| `metta.spaces` | Unions, overlays, read-only spaces, mapped spaces, and object views |
| `metta.structures` | Alpha sets, pattern maps, indexes, and maintained views |
| `metta.subscribe` | Callback and queued standing queries |
| `metta.tables` | Tabular ingestion, declarative SQL bridges, and SQL functions |
| `metta.testing` | Strategies, answer assertions, and provider compliance suites |
| `metta.typing` | Declared shape rules and their equations |
| `metta.vocabularies` | Named engine vocabularies, including `EffectClass` |

Import carriers explicitly because `set` and `bool` also name Python builtins.

```python
import metta

carrier = metta.counting
assert carrier is not None
assert len(metta.__all__) == 104
```

## Contexts and spaces

`MeTTa()` owns a context, `m.self` is its home space, and evaluation doors on the context forward home.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    kb = m.space()
    try:
        kb.add(S.person(S.Ada, 36))
        assert kb.match(S.person(V.name, V.age)).to_dicts() == [
            {"name": "Ada", "age": 36}
        ]
        assert len(m) == 0
        assert len(kb) == 1
        assert S.person(S.Ada, 36) in kb
    finally:
        kb.drop()
```

Storage inspection belongs to the space: use `m.self.atoms()`, `m.self.type(atom)`, and `m.self.builtins()`.

| Receiver | Meaning |
|---|---|
| `m.self` | The context's home space |
| `m.space()` | A fresh anonymous space |
| `m.space("&people")` | A handle for a named space |
| `m.space(name, backing=provider)` | A space backed by a provider |
| `metta.space()` | An anonymous space in the ambient context |
| `with kb:` | Bind ambient operations to that space for the block |
| `kb.drop()` | End the space's life and retire its declarations |
| `m.close()` | Close the context; `with MeTTa()` does this on exit |

Naming a space selects its address; adding facts or definitions gives it content.

## Atoms and terms

`S` makes symbols, `V` makes variables, and applying a symbol builds an expression.

```python
from metta import S, V, G, Expression, TRUE, FALSE, UNIT

assert str(S.Parent(S.Tom, V.child)) == "(Parent Tom $child)"
assert str(G("Tom")) == '"Tom"'
assert str(S.Tom) == "Tom"
assert str(Expression(S.pair, 1, 2)) == "(pair 1 2)"
assert str(TRUE) == "True"
assert str(FALSE) == "False"
assert str(UNIT) == "()"
```

Python strings are grounded text when building terms, so use `S.Ada` for the symbol and `"Ada"` for text.

| Construction | Meaning |
|---|---|
| `S.parent` | Symbol `parent` |
| `S["prime?"]` | A symbol outside Python's identifier grammar |
| `S.car_atom` | Symbol `car-atom` through the Python naming convention |
| `V.x` | Named variable `$x` |
| `Variable("_")` | An anonymous variable |
| `G(7)` | Grounded integer |
| `ground(value)` | Carry a Python value as an atom |
| `Expression(S.edge, 1, 2)` | Expression `(edge 1 2)` |
| `parse("(edge $a $b)")` | Read exactly one form |
| `forms("(a) (b)")` | Read every top-level form without evaluating it |

Arithmetic on atoms builds terms; `.value` retrieves a grounded payload for Python arithmetic.

```python
from metta import G, V

assert str(V.x + 1) == "(+ $x 1)"
assert str(G(2) + G(3)) == "(+ 2 3)"
assert G(2).value + G(3).value == 5
assert str(V.x.ge(18)) == "(>= $x 18)"
```

Rich comparisons answer Python booleans in term order, so use `.lt()`, `.le()`, `.eq()`, `.ne()`, `.ge()`, and `.gt()` to build query guards.

| Inspection | Result |
|---|---|
| `atom.metatype` | Symbol, variable, grounded value, or expression kind |
| `expression.head` | First child |
| `expression.args` | Children after the head |
| `expression.children` | All children |
| `atom.vars` | Its variables |
| `atom.alpha_eq(other)` | Equality modulo variable renaming |
| `atom.alpha(other)` | A built alpha-equality term |
| `atom.to_wire()` | The seat's tagged wire representation |

Unification returns bindings that substitution consumes directly, as in [first_steps.py](examples/basics/first_steps.py).

```python
from metta import S, V

pattern = S.Parent(V.parent, V.child)
bindings = pattern.unify(S.Parent(S.Tom, S.Bob))
assert bindings is not None
assert S.Cares(V.parent, V.child).subs(bindings) == S.Cares(S.Tom, S.Bob)
assert pattern.unify(S.Unrelated) is None
```

## Reading and running

`parse` reads one term, `eval` evaluates a term, and `run` processes source with one answer group per `!`.

```python
from metta import MeTTa, S, Expression

with MeTTa() as m:
    term = m.self.parse("(+ 20 22)")
    assert m.eval(term) == [42]
    assert m.eval(S["+"](1, 2), S["*"](3, 4)) == [[3], [12]]
    assert m.run("!(+ 1 2) !(* 3 4)") == [[3], [12]]
    assert m.eval(S.superpose(Expression(1, 2, 3))) == [1, 2, 3]
```

An unevaluated call remains a term; an empty answer sequence and the unit atom `()` are different results.

| Door | Return shape |
|---|---|
| `kb.eval(term)` | Eager flat list of answers |
| `kb.eval(a, b)` | One answer list per supplied term |
| `kb.run(source)` | One answer list per directive |
| `kb.answers(term)` | Lazy, replayable `Answers` |
| `kb.match(pattern)` | Lazy, replayable `Answers` carrying bindings |
| `kb.stream(pattern)` | Pulled query stream |
| `kb.eval_status(term)` | Answers paired with reduction status |
| `kb.run_status(source)` | Grouped answers paired with reduction status |

Use a result's `one()` when exactly one answer is required, and `first()` when only its first answer matters.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    m.add(S.owner(S.manual, S.Ada))
    answers = m.match(S.owner(S.manual, V.person))
    assert answers.one().person == S.Ada
    assert answers.first().person == S.Ada
    assert answers.to_dicts() == [{"person": "Ada"}]
```

Answers preserve multiplicity and do not promise order; sort for presentation without converting to a set.

## Adding, removing, and moving

A space is a multiset, so two equal facts remain two occurrences.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    kb = m.self
    fact = S.edge(S.a, S.b)
    kb.add(fact, fact, S.edge(S.b, S.c))
    assert len(kb.match(fact)) == 2
    assert kb.remove(fact) is True
    assert len(kb.match(fact)) == 1
    del kb[S.edge(V.a, V.b)]
    assert len(kb) == 0
```

The removal doors differ in grain and in what they report about absence.

| Door | Mutation and result |
|---|---|
| `kb.add(a, b)` | Bulk addition through one engine crossing |
| `kb += atom` | Add one atom |
| `kb += [(S.Edge, 1, 2), (S.Edge, 2, 3)]` | Add a fact stream |
| `kb += (S.Edge, 1, 2)` | Add one tuple-shaped fact |
| `kb.remove(atom)` | Remove one unifying occurrence; return a boolean |
| `kb.remove(a, b)` | Remove one occurrence per input; return the number found |
| `kb -= atom` | Remove one occurrence |
| `del kb[pattern]` | Remove every matching occurrence; raise `KeyError` if none match |
| `kb.transfer(a, b, to=other)` | Move one occurrence of each in one transaction |
| `kb.clear()` | Empty content, including compiled equations |
| `kb.copy()` | Copy content into a new anonymous space |
| `kb.digest()` | Content digest |
| `kb.source()` | Directly stored program as loadable source |
| `kb.save(path)` | Write the space's authored source |
| `kb.load(path)` | Load source or a trusted fast cache |

A copy has its own lifetime, so release it when the comparison or branch is finished.

```python
from metta import MeTTa, S

with MeTTa() as m:
    m.add(S.note(1))
    duplicate = m.self.copy()
    try:
        assert duplicate.digest() == m.self.digest()
        duplicate.add(S.note(2))
        assert duplicate.digest() != m.self.digest()
        assert len(m) == 1
    finally:
        duplicate.drop()
```

## Mutable cells

`State` stores a mutable engine cell with a Python property for reading and writing its value.

```python
from metta import MeTTa, State

with MeTTa() as m:
    counter = State(0, space=m.self)
    assert counter.value == 0
    counter.value = 7
    assert counter.value == 7
```

The cell's atom crosses through `__metta__`, so engine state operations and Python property access refer to the same cell.

## Queries, joins, and guards

Shared variables join patterns, as in [first_steps.py](examples/basics/first_steps.py).

```python
from metta import MeTTa, S, V

with MeTTa() as context:
    m = context.self
    m.add(
        S.Parent(S.Tom, S.Bob),
        S.Parent(S.Bob, S.Ann),
        S.Age(S.Tom, 65),
        S.Age(S.Bob, 38),
    )
    assert m.match(S.Parent(V.gp, V.p), S.Parent(V.p, V.gc)).to_dicts() == [
        {"gp": "Tom", "p": "Bob", "gc": "Ann"}
    ]
    assert m.match(S.Age(V.person, V.age), where=V.age.ge(60)).to_dicts() == [
        {"person": "Tom", "age": 65}
    ]
```

`where=` is a guard over the same bindings, and a Python callable is lowered through the query's guard path.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    m.add(S.Age(S.Ada, 36), S.Age(S.Bob, 17))
    adults = m.match(S.Age(V.person, V.age), where=V.age.ge(18))
    assert adults[0].person == S.Ada
    assert adults[0].age.value == 36
    assert adults.to_dicts() == [{"person": "Ada", "age": 36}]
```

A bound limits answers, while the engine retains candidates needed to decide a guarded or joined query.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    m.add(*(S.item(n) for n in range(5)))
    assert len(m.match(S.item(V.n), limit=2)) == 2
    assert len(m.match(S.item(V.n))[:2]) == 2
    assert len(m.match(S.item(V.n), where=V.n.ge(3), limit=1)) == 1
```

Relational solving can bind a variable on the other side of arithmetic.

```python
from metta import MeTTa, V

with MeTTa() as m:
    assert m.solve(4, V.x - 1).x == 5
```

## Prepared queries and temporary facts

`prepare` retains a query's shape and columns while each `solve()` reads current facts.

```python
from metta import MeTTa, S, V

with MeTTa() as context:
    m = context.self
    m.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann))
    grand = m.prepare(S.Parent(V.x, V.y), S.Parent(V.y, V.z))
    assert grand.columns == ("x", "y", "z")
    assert grand.solve().to_dicts() == [{"x": "Tom", "y": "Bob", "z": "Ann"}]

    answers = grand.solve(given=[S.Parent(S.Ann, S.Zoe)])
    assert len(answers) == 2
    assert len(grand.solve()) == 1
```

`assuming` keeps temporary facts for a block, then removes them even when the block raises.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    with m.self.assuming(S.available(S.Ada)):
        assert m.match(S.available(V.who)).one().who == S.Ada
    assert not m.match(S.available(V.who))
```

[multishot_solving.py](examples/integration/multishot_solving.py) builds reusable program parts and retractable external facts on these doors.

## Rows, dictionaries, and dataframes

Bindings remain atoms until an explicit conversion unwraps grounded values and renders symbols or structure.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    m.add(S.person(S.Ada, 36), S.person(S.Bob, 17))
    answers = m.match(S.person(V.name, V.age))
    assert answers.to_dicts() == [
        {"name": "Ada", "age": 36},
        {"name": "Bob", "age": 17},
    ]
    assert answers.table() == {"name": ["Ada", "Bob"], "age": [36, 17]}
    assert answers.rows.columns == ("name", "age")
```

| Result door | Meaning |
|---|---|
| `answers.columns` | Query columns in first-appearance order |
| `answer.name` | One named binding |
| `answers.rows` | Materialized row view |
| `rows.to_dicts()` | One plain mapping per row |
| `rows.table()` | A column-to-list mapping |
| `rows.column(name)` | One column |
| `rows.group_by(...)` | Group rows |
| `rows.into(Type)` | Construct values through the declared conversion path |
| `rows.build(Type)` | Build host values from rows |
| `rows.raise_for_errors()` | Raise for stored `Error` values on request |
| `rows.explain()` | Explain the originating query |
| `rows.why()` | Explain an empty query |
| `rows.to_df()` | pandas conversion supplied by its integration |
| `rows.to_pl()` | Polars conversion supplied by its integration |
| `rows.__arrow_c_stream__()` | Arrow stream export through the Arrow integration |

With the dataframe extra installed, the checked idiom from [engine_controls.py](examples/operations/engine_controls.py) is a result method.

```python
import metta_polars
from metta import MeTTa, S, V

with MeTTa() as m:
    m.add(S.edge(1, 2), S.edge(2, 3))
    rows = m.match(S.edge(V.a, V.b))
    frame = rows.to_pl()
    assert frame.columns == ["a", "b"]
    assert frame.height == 2
```

A consumer can also construct a dataframe from `rows.table()`, whose plain mapping needs no dataframe package to produce.

## Defining Python as MeTTa

`@m.define` lowers a Python body to equations and keeps its Python twin, as in [python_definitions.py](examples/operations/python_definitions.py).

```python
from metta import MeTTa, S

with MeTTa() as context:
    m = context.self

    @m.define
    def fact(n):
        if n == 0:
            return 1
        return n * fact(n - 1)

    assert m.run("!(fact 6)") == [[720]]
    assert fact(6) == [720]
    assert fact.py(6) == 720
    assert str(S.fact(6)) == "(fact 6)"
```

A generator lowers to nondeterminism, with one answer per yield.

```python
from metta import MeTTa

with MeTTa() as m:
    @m.define
    def moves(pos):
        yield pos - 1
        yield pos + 1

    assert sorted(moves(10)) == [9, 11]
    assert m.run("!(collapse (moves 10))") == [[m.self.parse("(9 11)")]]
```

Typed arithmetic can lower to engine operators; `fn` also names engine relations explicitly when reversibility matters.

```python
from metta import MeTTa, fn

with MeTTa() as m:
    @m.define
    def twice(value: int) -> int:
        return fn.mul(value, 2)

    assert twice(7) == [14]
```

The compiler reports unsupported constructs with their source location and a remedy; use recursion where a `while` loop is refused.

| Definition form | What enters MeTTa |
|---|---|
| `@m.define` | Equations compiled from the function |
| `m.define(function)` | The same operation without decorator syntax |
| `m.define(Class)` | A class declaration with field accessors and methods |
| `m.define(Class, accessors=False, methods=False)` | A class without those exposed members |
| `equation(head).to(body)` | One built equation |
| `@rules` | A generator of equation atoms |
| `m.rules(function)` | Collect and install an equation bundle |
| `m.define(prolog=source, name="p-sum")` | A Prolog-backed definition |
| `py(expression)` | An explicit host island in a lowered body |

Built equations remain ordinary atoms that can be stored and queried.

```python
from metta import MeTTa, S, V, equation, rules

with MeTTa() as m:
    @rules
    def arithmetic(value):
        yield equation(S.successor(value)).to(value + 1)

    m.add(arithmetic)
    assert m.eval(S.successor(6)) == [7]
    assert m.match(S["="](S.successor(V.x), V.body))
```

## Calling Python with effect decorators

The four decorators in [effect_ranks.py](examples/operations/effect_ranks.py) describe what a callback touches; generator inspection supplies the fifth effect class.

| Decorator | Declared class | Use |
|---|---|---|
| `@m.pure` | `pureStructural` | Answer depends only on arguments |
| `@m.reads` | `readOnlyLookup` | Read stable state |
| `@m.writes` | `writesState` | Change engine or host state |
| `@m.io` | `oracleIO` | Observe a clock, network, file, randomness, or external runtime |
| A generator with `@m.pure` or `@m.reads` | Lifted to `nondeterministicReadOnly` | More than one possible answer |

A callback stays Python while the engine calls it by its registered name.

```python
from metta import MeTTa, S

with MeTTa() as m:
    @m.pure
    def shout(word: str) -> str:
        return word.upper()

    @m.pure
    def either(x: int):
        yield x
        yield x + 1

    assert m.run('!(shout "hi")') == [["HI"]]
    assert sorted(m.eval(S.either(4))) == [4, 5]
    assert str(m.self.effect_plan(S.either(4)).effect) == "nondeterministicReadOnly"
```

Reads, writes, and external observations use the same registration form.

```python
import time
from metta import MeTTa, S

with MeTTa() as m:
    notes = []

    @m.reads
    def note_count() -> int:
        return len(notes)

    @m.writes
    def note(value: int) -> int:
        notes.append(value)
        return value

    @m.io
    def clock() -> float:
        return time.time()

    assert m.eval(S.note(7)) == [7]
    assert m.eval(S.note_count()) == [1]
    assert m.eval(S.clock())[0].value > 0
```

A generator's answer-count floor never weakens a stronger write or I/O declaration.

| Registration option | Meaning |
|---|---|
| `name=` | Exact MeTTa name instead of the Python-derived spelling |
| `arities=` | Declared supported arities |
| `declarations=` | Additional declaration atoms |
| `inverse=` | An inverse operation |
| `transport=` | Callback argument transport |
| `m.unregister_op(name)` | Remove the registered operation |

`m.op` is the underlying registration door; the named decorators supply its effect classification.

## Types, casts, and annotations

`typed` builds a declaration and `arrow` builds a function type.

```python
from metta import MeTTa, S, arrow, typed

with MeTTa() as m:
    m.add(typed(S.double, arrow(S.Number, S.Number)))
    assert str(m.self.type(S.double)) == "(-> Number Number)"
    assert m.self.cast(7, S.Number) == 7
```

An `Atom` parameter receives the written term, while an ordinary callback parameter receives its evaluated value.

```python
from metta import Atom, MeTTa

with MeTTa() as m:
    @m.pure
    def anyatom(term: Atom) -> Atom:
        return term

    @m.pure
    def anyval(term):
        return term

    m.run("(= (side) 42)")
    assert m.run("!(anyatom (side))") == [[m.self.parse("(side)")]]
    assert m.run("!(anyval (side))") == [[42]]
```

Local annotations become executable claims, and compiled definitions expose source spans and lexical dependencies.

```python
from metta import MeTTa

with MeTTa() as m:
    @m.define
    def checked(value):
        result: int = value
        return result

    assert checked(7) == [7]
    assert checked("nope") == []
    assert checked.pure is True
```

[annotation_contracts.py](examples/operations/annotation_contracts.py) checks the reflection facts emitted from those definitions.

## Host objects and conversion

Projection makes structure visible to MeTTa, while grounding keeps a live Python reference.

```python
from dataclasses import dataclass
from enum import Enum
from metta.convert import project, build

class Mood(Enum):
    calm = 1
    stormy = 2

@dataclass
class Robot:
    name: str
    mood: Mood

projected = project(Robot("R2", Mood.calm))
assert str(projected.atom) == '(Robot "R2" calm)'
rebuilt = build(projected.atom)
assert isinstance(rebuilt, Robot)
assert rebuilt.mood is Mood.calm
```

Store `projected.declarations` with `projected.atom` when the receiving space should know the projected type.

| Representation | Contract |
|---|---|
| `ground(obj)` | Carry the live object |
| `convert.project(obj)` | Return an atom and its declarations |
| `convert.build(atom)` | Reconstruct a registered host value |
| `convert.encode(value)` | Convert a host value to an atom |
| `convert.decode(atom)` | Read its host representation |
| `obj.__metta__()` | An owned type's structural image |
| `Type.__from_metta__(...)` | An owned type's reconstruction hook |
| `kb.image(type_name, setting)` | Declare how a type crosses a context boundary |

[python_objects.py](examples/integration/python_objects.py) also presents object fields as a live relation and shows reversible conversion hooks.

## Arrays and shape types

The array integration uses Array API and DLPack protocols, with the actual operations supplied by `metta-arrays`.

```python
import numpy
import metta_arrays as arrays
import metta_numpy
from metta import MeTTa, Expression

with MeTTa() as context:
    m = context.self
    arrays.install(m, default=numpy)
    assert m.run(
        "!(t-tolist (matmul (tensor ((1.0 2.0))) (tensor ((3.0) (4.0)))))"
    ) == [[Expression(Expression(11.0))]]
```

[array_interop.py](examples/data/array_interop.py) checks object identity and mixed NumPy/PyTorch operations, while [symbolic_tensors.py](examples/gallery/symbolic_tensors.py) works with shape declarations.

`metta.typing` stores shape rules as equations; declared dimensions can relate multiple parameters and the result.

## Algebras and semirings

A query's `under=` selects how annotations combine across alternatives and extend along a derivation.

| Carrier | Interpretation |
|---|---|
| `set` | Set-oriented annotation carrier |
| `bag` | Multiplicity while retaining individual rows |
| `bool` | Boolean support |
| `counting` | One aggregate count of derivations |
| `tropical` | Min-plus costs |
| `prob` | Sum-product weights |
| `ranked` | Ranked alternatives |
| `prov` | Provenance expressions naming supporting sources |
| `budget` | Resource annotations |
| `amplitude` | Exact complex amplitudes |

Tagged facts and rules keep the annotation model separate from the relation being defined.

```python
from metta import MeTTa, S, V, counting, prov

with MeTTa() as m:
    kb = m.self
    kb.add_tagged_fact(S.p1, S.edge(S.a, S.b))
    kb.add_tagged_fact(S.p2, S.edge(S.b, S.c))
    kb.add_tagged_rule(
        S.two_steps,
        S.path(V.a, V.c),
        S.edge(V.a, V.b),
        S.edge(V.b, V.c),
    )
    answer = kb.match(S.path(S.a, S.c), under=prov).one()
    assert str(answer.value) == "(path a c)"
    assert all(name in str(answer.annotation) for name in ("p1", "p2", "two-steps"))
    assert kb.match(S.path(S.a, S.c), under=counting).one().annotation == 1
```

`counting` returns one row with unit as its value and the count as its annotation; `bag` keeps the individual conclusions.

A retained derivation can be reinterpreted under another carrier without repeating the query.

```python
from metta import MeTTa, S, prov, counting

with MeTTa() as m:
    m.self.add_tagged_fact(S.source, S.available(S.Ada))
    answer = m.match(S.available(S.Ada), under=prov).one()
    counted = answer.under(counting)
    assert counted.annotation == 1
```

Custom carriers declare operations, identities, and optional membership constraints.

```python
import metta

with metta.MeTTa() as context:
    with context.self:
        carrier = metta.algebra(
            "capacity",
            plus=max,
            times=min,
            zero=0,
            one=10,
            type=int,
        )
        assert carrier is not None
```

Law certification requires the complete finite `carrier=` domain, and an invalid law or out-of-carrier result is refused.

| Declaration input | Role |
|---|---|
| `plus=`, `times=` on the callable algebra module | Python annotation operations |
| `combine=`, `extend=` on `space.algebra` | Named engine annotation operations |
| `zero=`, `one=` | Alternative and conjunction identities |
| `type=` | Membership checked through a Python type, MeTTa type, or predicate |
| `carrier=` | Complete finite domain for exhaustive law checks |
| `laws=` | Requested algebra laws |
| `requires=` | Required context capabilities |
| `order=` | Declared ordering |

[family_algebras.py](examples/gallery/family_algebras.py) asks the same relation in every ground/free direction under several carriers.

## Concurrency and ownership

A scope joins its children and releases the resources created inside it.

```python
from metta import MeTTa, S, spawn

with MeTTa() as context:
    with context.self:
        with context.scope():
            future = spawn(S["+"](20, 22))
            future.wait()
            assert future.settled()
            assert list(future) == [42]
```

| Door | Result or lifetime |
|---|---|
| `spawn(term)` | A `FutureSpace` whose answers fill as it runs |
| `future.wait()` | Wait for settlement |
| `future.settled()` | Inspect completion |
| `future.cancel()` | Request cancellation |
| `par_map(function, items)` | Concurrent unary evaluation in input order |
| `race(a, b)` | First successful answer; cancel remaining branches |
| `every(interval, term)` | Repeated work until cancelled |
| `scope()` | Structured resource and child ownership |
| `move_on_after(seconds)` | Deadline scope that suppresses its own cancellation |
| `kb.parallel(*terms)` | Evaluate branches concurrently |
| `kb.pool(workers=...)` | Thread pool with attached Prolog engines |
| `parallel.process_pool(...)` | Separate worker processes |

The pool example uses ordinary Python callables that evaluate against the selected space.

```python
from metta import MeTTa, S

with MeTTa() as context:
    space = context.self
    with space.pool(workers=2) as pool:
        values = list(pool.starmap(
            lambda left, right: space.eval(S["+"](left, right))[0],
            [(1, 2), (3, 4)],
        ))
        assert values == [3, 7]
```

Process pools require picklable work and worker-local engine access; live engine handles do not cross processes.

A channel is a FIFO space, and `try_recv()` distinguishes an empty mailbox without blocking.

```python
from metta import MeTTa, S, channel

with MeTTa() as context:
    with context.self, channel(max=1) as mailbox:
        assert mailbox.try_recv() is None
        mailbox.send(S.job(7))
        assert mailbox.try_recv() == S.job(7)
        assert mailbox.try_recv() is None
```

[concurrency_handles.py](examples/operations/concurrency_handles.py) checks both examples, and [linda_coordination.py](examples/gallery/linda_coordination.py) uses `peek` and `take` for tuple-space coordination.

## Async

`AsyncMeTTa` runs requests on an owned engine thread so awaiting a query does not block the event loop.

```python
import asyncio
from metta import S, V
from metta.aio import AsyncMeTTa

async def main():
    async with AsyncMeTTa() as m:
        await m.add(S.item(7))
        rows = await m.match(S.item(V.value))
        assert rows.to_dicts() == [{"value": 7}]
        assert await m.eval(S["+"](20, 22)) == [42]

asyncio.run(main())
```

The asynchronous mirror carries declared doors with their awaitable return paths, including prepared queries.

```python
import asyncio
from metta import S, V
from metta.aio import AsyncMeTTa

async def main():
    async with AsyncMeTTa() as m:
        await m.add(S.edge(1, 2))
        query = await m.prepare(S.edge(V.a, V.b))
        rows = await query.solve()
        assert rows.to_dicts() == [{"a": 1, "b": 2}]

asyncio.run(main())
```

Cancellation reaches the active engine call, and leaving the async context closes its worker.

## Transactions and speculation

`transaction(callable)` gives several calls one all-or-nothing engine boundary.

```python
from metta import MeTTa, S

with MeTTa() as m:
    def write_pair():
        m.add(S.item(1))
        m.add(S.item(2))
        return "committed"

    assert m.transaction(write_pair) == "committed"
    assert len(m) == 2

    def fail_after_write():
        m.add(S.item(3))
        raise ValueError("cancel this pair")

    try:
        m.transaction(fail_after_write)
    except ValueError:
        pass
    assert S.item(3) not in m
```

`atomic()` and `speculative()` apply their policy separately to every call in a block.

```python
from metta import MeTTa, S

with MeTTa() as m:
    with m.self.speculative():
        m.add(S.temporary(1))
        assert S.temporary(1) not in m

    with m.atomic():
        m.add(S.committed(1))
    assert S.committed(1) in m
```

| Boundary | Commit behavior |
|---|---|
| `m.transaction(term)` | One closed engine goal |
| `m.transaction(callable)` | One transaction across the callable's calls |
| `@kb.transactional` | Decorator form of the callable boundary |
| `with m.atomic():` | Each call commits independently |
| `with kb.speculative():` | Each call discards its own writes |
| `with metta.speculate():` | Ambient per-call speculation |
| `with kb.batch():` | Collect additions and send one batch |

There is no transaction context-manager form because an engine transaction cannot suspend across separate host calls.

## Reified worlds and compensation

A reified world returns answers and a successor world, leaving its origin unchanged until an explicit commit.

```python
from metta import MeTTa, S

with MeTTa() as m:
    kb = m.self
    kb.add(S.Base(1))
    kb.covers("writesState")
    base = kb.reify()
    answers, successor = base.eval(S.add_atom(S["&self"], S.Decision(S.launch)))
    assert answers == [True]
    assert S.Decision(S.launch) not in kb
    kb.commit(successor)
    assert S.Decision(S.launch) in kb
```

[git_like_worlds.py](examples/gallery/git_like_worlds.py) compares two successors and checks that observers see the complete selected commit.

A saga records committed effects and runs declared compensations in reverse order on exceptional exit.

```python
from metta import MeTTa, S

with MeTTa() as context:
    orders = context.space()
    receipts = context.space()
    try:
        orders.run(
            "(= (undo-add (did add-atom ($space $atom) $result)) "
            "(remove-atom $space $atom))"
        )
        orders.compensates("add-atom", "undo-add")
        try:
            with orders.saga(receipts) as saga:
                saga.run(S.add_atom(orders, S.booked(S.Ada)))
                raise ValueError("cancel booking")
        except ValueError:
            pass
        assert S.booked(S.Ada) not in orders
        assert len(receipts) == 0
    finally:
        receipts.drop()
        orders.drop()
```

[saga_compensation.py](examples/operations/saga_compensation.py) checks both the recovery and receipt retirement.

## Events and standing queries

A subscription follows matching writes, including writes made from MeTTa source.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    seen = []
    subscription = m.self.subscribe(
        S.audit(V.what),
        lambda event: seen.append(str(event.bindings["what"])),
    )
    try:
        m.add(S.audit(S.from_python))
        m.run("!(add-atom &self (audit from-metta))")
        assert seen == ["from-python", "from-metta"]
    finally:
        subscription.cancel()
```

Omitting the callback selects queued delivery, and `on="both"` includes additions and removals.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    inbox = m.self.subscribe(S.letter(V.body), on="add")
    try:
        m.add(S.letter(S.first), S.letter(S.second))
        assert [str(e.bindings["body"]) for e in inbox.drain()] == ["first", "second"]
        assert inbox.drain() == []
    finally:
        inbox.cancel()
```

| Door | Delivery |
|---|---|
| `kb.subscribe(pattern, callback)` | Callback on each matching change |
| `kb.subscribe(pattern)` | Queue drained by the caller |
| `kb.watch(pattern)` | Iterator over matching changes |
| `subscription.cancel()` | Stop delivery and remove the standing query |
| `kb.events()` | Inspect the event stream and live folds |
| `kb.reacts(pattern, operation)` | Declare an engine reaction |
| `kb.agenda(policy)` | Declare reaction ordering |

Rollback delivers no committed changes, and callbacks after a successful transaction see its completed state.

## Materialized answers

With `metta-live` installed, `m.live(...)` keeps a multiset of current answers.

```python
import metta_live
from metta import MeTTa, S, V

with MeTTa() as m:
    with m.live(S.alert(V.level)) as alerts:
        m.add(S.alert(S.red), S.alert(S.red), S.alert(S.amber))
        assert len(alerts) == 3
        assert alerts.count(S.alert(S.red)) == 2
        m.remove(S.alert(S.red))
        assert alerts.count(S.alert(S.red)) == 1
```

A live join uses the same pattern conjunction as `match`, while its change stream includes a progress marker at each commit boundary.

```python
import metta_live
from metta import MeTTa, S, V
from metta.live import Delta

with MeTTa() as m:
    with m.live(S.tick(V.n)) as ticks, ticks.changes(timeout=5) as changes:
        m.transaction(lambda: m.add(S.tick(1), S.tick(2)))
        added = []
        for change in changes:
            match change:
                case Delta("add", 1, row, _atom, _generation):
                    added.append(row["n"])
                case Delta("progress", _, None, None, _generation):
                    break
        assert added == [1, 2]
```

[standing_queries.py](examples/live/standing_queries.py) also builds two actors whose messages are ordinary additions.

## Foreign spaces

Implement capabilities on a provider and bind it through `backing=`, as in [provider_policy.py](examples/integration/provider_policy.py).

```python
from metta import MeTTa, S, V
from metta.foreign import SpaceProvider

class Facts(SpaceProvider):
    def __init__(self):
        self.stored = []

    def atoms(self):
        return iter(self.stored)

    def add(self, atom):
        self.stored.append(atom)

with MeTTa() as context:
    provider = Facts()
    kb = context.space("&example-facts", backing=provider)
    kb.add(S.person(S.Ada))
    assert kb.match(S.person(V.who)).one().who == S.Ada
```

Capabilities are structural protocols, so a backend implements only operations it can actually provide.

| Protocol | Capability |
|---|---|
| `Matcher` | Pattern matching |
| `BoundedMatcher` | Matching with an offered answer bound |
| `Enumerable` | Enumerate atoms |
| `Adder` | Add an atom |
| `BulkAdder` | Add a batch |
| `Remover` | Remove one occurrence |
| `Clearer` | Clear stored atoms |
| `Planner` | Plan a query |
| `Transactional` | Participate in transaction boundaries |
| `Snapshotter` | Supply a storage snapshot |
| `TokenProvider` | Expose occurrence identities |
| `TokenAdder` | Add with occurrence identity |
| `TokenRemover` | Remove a specific occurrence |
| `WorldCommitter` | Commit a reified world's diff |
| `MatchClassifier` | Classify matching fidelity |
| `CustomMatch` | Let a grounded object's `match_` define unification |

`can_run` describes implementation capability, `should_run` admits a concrete request, and `refusal` supplies the reason for a denied request.

| Provider declaration | Meaning |
|---|---|
| `kb.handles(pattern, "Exact")` | Trust the provider's answer set for that shape |
| `kb.context("closed-world")` | Give absence a closed-world interpretation |
| `kb.annotations("bag")` | Declare annotation semantics |
| `kb.atomicity("transactional")` | Declare transaction participation |
| `kb.consumption("repeated")` | Declare repeatable consumption |
| `kb.emits(policy)` | Declare emission ordering |
| `kb.on_error(...)` | Declare query-failure handling |
| `kb.merge(pattern, policy)` | Declare answer combination |

An `Exact` declaration is a promise the provider must satisfy, not a verification the engine performs for it.

[provider_worlds.py](examples/integration/provider_worlds.py) checks bound delivery and atomic world commits through the provider seam.

## Composed spaces and live objects

Compositions read their sources through providers instead of copying them.

| Composition | Contract |
|---|---|
| `metta.spaces.union(*spaces)` | Read several spaces as one; refuse writes |
| `metta.spaces.overlay(front, back)` | Read both and write to the front |
| `metta.spaces.readonly(space)` | Read through a handle that refuses writes |
| `metta.spaces.mapped(space, shape)` | Derive a shape view from a declaration |
| `metta.spaces.view(obj)` | Attach a live dict, set, or sequence |
| `metta.spaces.object_view(obj)` | Expose object fields through a provider |
| `metta.spaces.diff(a, b)` | Describe content differences |

A field relation can have its own name without changing the underlying object.

```python
from dataclasses import dataclass
from metta import MeTTa, S, V, spaces

@dataclass
class Robot:
    name: str
    charge: int

with MeTTa() as m:
    kb = m.space(backing=spaces.object_view(
        Robot("C3", 80), relation="robot-field",
    ))
    try:
        rows = kb.match(S["robot-field"](V.object, V.field, V.value))
        assert {str(row.field) for row in rows} == {"name", "charge"}
    finally:
        kb.drop()
```

`metta.paths.path` can select a field or indexed element inside an opaque value without projecting its entire structure.

## Tables and SQL

A bridge declaration relates an atom pattern to database columns and supplies both conversion directions.

```python
import sqlite3
from metta import MeTTa, S, V, tables
from metta.tables import TableBridge

with MeTTa() as context, sqlite3.connect(":memory:") as connection:
    connection.execute("CREATE TABLE edges (a INTEGER, b INTEGER)")
    connection.executemany("INSERT INTO edges VALUES (?, ?)", [(1, 2), (2, 3)])
    tables.declare(
        context.self,
        "&sql-example",
        "(bridge (edge $a $b) (row edges (a $a) (b $b)))",
    )
    provider = TableBridge.from_context(context.self, "&sql-example", connection)
    kb = context.space("&sql-example", backing=provider)
    assert kb.match(S.edge(V.a, V.b)).to_dicts() == [
        {"a": 1, "b": 2}, {"a": 2, "b": 3},
    ]
```

Bound positions become SQL predicates, repeated variables become column equalities, and eligible bounded queries push down a limit.

Plain tabular ingestion uses the same fact shape without requiring a database.

```python
from metta import MeTTa, S, V, tables

with MeTTa() as m:
    tables.add(m.self, "edge", [(1, 2), (2, 3), (3, 4)])
    rows = m.match(S.edge(V.a, V.b), S.edge(V.b, V.c))
    assert rows.to_dicts() == [
        {"a": 1, "b": 2, "c": 3},
        {"a": 2, "b": 3, "c": 4},
    ]
```

[sqlite_space.py](examples/integration/sqlite_space.py) covers blob images and lazy paths, while [duckdb_space.py](examples/integration/duckdb_space.py) covers NULL and non-primitive SQL values.

## Remote serving and authorization

`metta.remote.serve` exposes selected spaces over HTTP and returns a server with an explicit lifetime.

```python
import secrets
from metta import MeTTa, S
from metta.remote import serve

with MeTTa() as context:
    kb = context.space("&served")
    kb.add(S.item(1))
    name = str(kb.name)
    token = secrets.token_urlsafe(32)

    def authorize(request):
        return request.operation == "health" or (
            request.space == name
            and request.operation in {"match", "atoms", "ask", "next", "stop"}
        )

    with serve(
        kb,
        spaces=[name],
        token=token,
        authorize=authorize,
        cursor_idle=30,
        cursor_limit=8,
    ) as server:
        assert server.port > 0
        # Hand server.url and the token to the application's deployment layer.
```

`token=` requires Bearer authentication, and `authorize` receives the operation, resolved space, and headers for each request.

| Server option | Purpose |
|---|---|
| `host=`, `port=` | Bind address; port zero selects a free port |
| `spaces=` | Space allowlist |
| `token=` | Required Bearer token |
| `authorize=` | Request-specific policy |
| `ssl_context=` | Python TLS context with the server certificate |
| `cursor_idle=` | Idle cursor lifetime |
| `cursor_limit=` | Maximum live cursors |
| `mutation_ttl=` | Retention of keyed mutation receipts |
| `mutation_limit=` | Bound on the mutation replay ledger |

The client refuses credentials over plain HTTP, so authenticated remote clients use an HTTPS endpoint.

```python
import os
from metta.remote import connect, RemoteSpace

# Deployment recipe: the URL and credential belong to the operator.
transport = connect(
    "https://engine.example/api",
    token=os.environ["METTA_TOKEN"],
    headers={"X-Tenant": "research"},
    timeout=30,
)
remote = RemoteSpace(transport, "&served")
# remote.server_capabilities() inspects the server before a write.
```

Separate processes are required when attaching a served space back through the engine; direct in-process composition already has native space handles.

| Client door | Meaning |
|---|---|
| `remote.server_capabilities()` | Inspect advertised behavior |
| `remote.match(pattern)` | Fetch matching instantiated atoms |
| `remote.atoms()` | Enumerate remote atoms |
| `remote.add(atom)` | Add remotely |
| `remote.add_many(atoms)` | Batch addition |
| `remote.remove(atom)` | Remove remotely |
| `remote.stream(pattern, batch=...)` | Own a remote cursor |
| `cursor.close()` | Release that cursor |

A lost mutation response can raise `OutcomeUnknown`; the client does not blindly resend an unkeyed mutation.

## HTTP and GraphQL doors

The installed `metta-remote` package publishes the `m.remote` namespace with the same transport and server contracts.

```python
import metta_remote
from metta import MeTTa, S

with MeTTa() as m:
    m.add(S.item(1))
    with m.remote.serve(spaces=[str(m.self.name)]) as server:
        assert server.port > 0
```

The current public HTTP accessor is `remote`; GraphQL schema and execution are methods on `Gateway`.

| Door | Purpose |
|---|---|
| `m.remote.connect(url, ...)` | Construct an HTTP transport |
| `m.remote.serve(...)` | Serve the receiver's engine |
| `metta.remote.Gateway(space)` | Protocol operations without a socket |
| `gateway.openapi()` | OpenAPI document |
| `gateway.graphql_schema()` | GraphQL SDL derived from declarations |
| `gateway.graphql(request)` | Execute a GraphQL request |
| `GET /health` | Capabilities and mutation negotiation |
| `GET /openapi.json` | HTTP schema |
| `GET /graphql` | GraphQL schema |
| `POST /graphql` | GraphQL execution through its registered provider |

Schema publication needs no GraphQL executor, while request execution needs the `pymetta[graphql]` extra.

```python
import metta_graphql
from metta import MeTTa, S
from metta.remote import Gateway

with MeTTa() as m:
    m.add(S.users(1, "Ada"), S.users(2, "Bob"))
    m.run("(: users (-> Number String Bool))")
    with Gateway(m.self) as gateway:
        assert "type Query" in gateway.graphql_schema()
        answer = gateway.graphql({"query": "{ users { x1 x2 } }"})
        assert answer == {
            "data": {"users": [{"x1": 1, "x2": "Ada"}, {"x1": 2, "x2": "Bob"}]}
        }
```

GraphQL's generic `match` field reaches terms whose heads cannot become GraphQL field names.

## Integrations and entry points

Extension packages advertise seam registrars through the `metta.extensions` entry-point group and register against declared seam points.

```python
from metta import integrate, seam

advertised = integrate.entry_points(seam.GROUP)
assert isinstance(advertised, dict)
# Discovery here lists names without importing their implementations.
```

[registration_lifecycle.py](examples/integration/registration_lifecycle.py) pairs each installed global hook with its exact unregister operation.

Per-space installers use the separate group named by `integrate.ENTRY_POINT_GROUP`, which is the default for `integrate.entry_points()` and the input to `integrate.discover()`.

| Registration | Inverse or use |
|---|---|
| `integrate.register_type` | `integrate.unregister_type` |
| `integrate.register_object_type` | `integrate.unregister_object_type` |
| `integrate.register_repr` | `integrate.unregister_repr` |
| `integrate.register_reflector` | `integrate.unregister_reflector` |
| `integrate.reflect` | Lower an object to facts through its claiming reflector |
| `integrate.facts` | Bulk fact insertion |
| `integrate.wrap_callable` | Register a host callable |
| `integrate.wrap_object` | Register an object's selected methods |
| `integrate.module_ops` | Register selected module functions |
| `integrate.face` | Produce a source face for selected module functions |
| `integrate.discover` | Load and install advertised integrations |
| `integrate.installed` | Read installed integration ownership |
| `kb.integrate(target)` | Install a target for that space |

A package can contribute a namespace through `metta.seam.door`; the door records carry signatures, effects, receiver tiers, and evidence.

```python
from metta import doors

contracts = doors.table()
assert "space:match" in contracts
assert contracts["space:match"].python == "match"
assert contracts["space:match"].docs
```

[PyMeTTa-Extensions](../../ext/README.md) contains the separate distributions and their registration code.

## Libraries and deployment

A library is knowledge imported through a space's write door.

```python
from metta import MeTTa, lib

with MeTTa() as m:
    m += lib.math
    assert m.run("!(math-sqrt 9)") == [[3.0]]
```

The `metta.library` module reads the library roster, declarations, cards, and content digests from their source.

| Door | Purpose |
|---|---|
| `lib.name` | Select a library by its shorthand |
| `Library` | Library value type |
| `kb.from_(source, map=...)` | Store an import or mapped source relationship |
| `metta.library.roster()` | Discover library files |
| `metta.library.rows(name)` | Read declaration rows |
| `metta.library.card(name)` | Read a library's public card |
| `metta.library.digest(name)` | Compute its content digest |
| `Lock`, `Drift` | Recorded dependencies and detected changes |
| `metta.boot(path)` | Assemble an application from a manifest |

The Python import hook loads `.metta` modules into a chosen space and removes its registrations when its context exits; this example selects a library directory from the workspace root.

```python
from metta import MeTTa
from metta.importing import install

with MeTTa() as m:
    with install(m.self, path="lib/lib_math"):
        import lib_math
        assert lib_math is not None
```

[ecosystem_graph.py](examples/gallery/ecosystem_graph.py) turns library metadata into a queryable dependency graph.

## Bounds, counters, and configuration

`limits` scopes engine bounds, while `stats` measures the work performed inside a block.

```python
from metta import MeTTa, S

with MeTTa() as m:
    with m.limits(inferences=100_000, timeout=5):
        with m.stats() as spent:
            assert m.eval(S["+"](20, 22)) == [42]
    assert spent.inferences > 0
    assert spent.walltime >= 0
```

| Counter | Meaning |
|---|---|
| `inferences` | Engine inference delta |
| `cputime` | CPU-time delta |
| `walltime` | Elapsed-time delta |
| `gc_count` | Garbage-collection count delta |
| `gc_freed` | Bytes reclaimed by garbage collection |
| `gc_time` | Garbage-collection time delta |
| `table_bytes` | Table-memory delta |
| `heartbeats` | Interrupt polls during the block |

Capture keeps printed engine output separate from structured answers.

```python
from metta import MeTTa

with MeTTa() as m:
    with m.capture() as output:
        groups = m.run("!(println! (hello world)) !(+ 1 2)")
    assert "(hello world)" in output.text
    assert groups[1] == [3]
```

Process-wide settings are inspectable through `config`, with startup settings frozen after the runtime starts.

```python
from metta import config

settings = config.as_dict()
assert "stack_limit" in settings
assert "heartbeat_interval" in settings
assert "display_rows" in settings
```

[runtime_configuration.py](examples/operations/runtime_configuration.py) configures startup before boot and reads live presentation settings through the engine catalog.

## Explanations, traces, and recordings

An explanation reports the selected query plan without consuming the query's answers.

```python
from metta import MeTTa, S, V

with MeTTa() as m:
    m.add(S.edge(1, 2), S.edge(2, 3))
    rows = m.match(S.edge(V.a, V.b), S.edge(V.b, V.c))
    explanation = rows.explain()
    assert explanation.plan is not None
    assert rows.to_dicts() == [{"a": 1, "b": 2, "c": 3}]
```

`analyze=True` runs the query to measure it, and a query that writes requires `allow_writes=True`.

| Door | Evidence it returns |
|---|---|
| `kb.explain(query)` | Plan, route, and declared write behavior |
| `kb.explain(query, analyze=True)` | Plan plus measured query work |
| `kb.effect_plan(term)` | Operations and their joined effect without execution |
| `kb.why(pattern)` | Why a match is empty |
| `kb.derivation(term)` | Proof trees |
| `kb.trace(term)` | Reduction events |
| `kb.trace(term, filter=[S.f])` | Events for selected heads |
| `kb.record(term, seed=...)` | A recording with the state needed for replay |
| `kb.debug(term, on=[S.f])` | Suspended execution at breakpoints |
| `kb.profile(source)` | Statistical engine profile |
| `kb.profile_extension(source, names=[...])` | Profile restricted to selected extension functions |

Tracing evaluates the program for real, including its writes.

```python
from metta import MeTTa, S

with MeTTa() as m:
    m.run("(= (double $x) (* 2 $x))")
    trace = m.trace(S.double(3), filter=[S.double], max_events=100)
    assert trace.stopped is None
```

A trace's `max_events` bounds recorded events, while `timeout` and `inferences` bound execution.

[explaining_a_query.py](examples/operations/explaining_a_query.py) checks plan selection, measured analysis, stored explanations, and refusal of unapproved writes.

## Refusals and errors

A deliberate refusal carries structured context and a remedy beside its message.

```python
from metta import MeTTa
from metta._errors.errors import AssertionFailure

with MeTTa() as m:
    try:
        m.run("!(test (+ 1 1) 3)")
    except AssertionFailure as failure:
        assert failure.operation == "test"
        assert failure.actual == 2
        assert failure.expected == 3
    else:
        raise AssertionError("the false claim was accepted")
```

| Failure | Meaning |
|---|---|
| `MettaError` | Base for the seat's structured errors |
| `EngineError` | Engine-level failure |
| `MettaSyntaxError` | Source-reading failure |
| `CompileError` | Python lowering refusal with a source location |
| `CastError` | A value failed its requested type |
| `SourceNotFound` | Missing program source |
| `MettaResultError` | An error-valued answer raised into Python |
| `AssertionFailure` | A false program assertion with actual and expected values |
| `SpaceCapabilityError` | A space lacks a required operation |
| `TransportFailure` | Failure crossing a transport boundary |
| `ResourceLimitError` | An engine resource bound was reached |
| `Interrupted` | Interrupted evaluation |
| `Timeout` | Timeout reported by the relevant waiting interface |

Specific exception classes live in `metta._errors.errors`; the root exports `MettaError`, `NotReducible`, `Timeout`, and `is_transport_failure`.

Stored `Error` atoms remain data until a caller asks the result view to raise them.

```python
from metta import MeTTa, S, V
from metta._errors.errors import MettaResultError

with MeTTa() as m:
    m.add('(log failed (Error (job 1) "boom"))')
    rows = m.match(S.log(S.failed, V.value))
    try:
        rows.raise_for_errors()
    except MettaResultError as failure:
        assert str(failure.culprit) == "(job 1)"
    else:
        raise AssertionError("the error value was not raised")
```

[error_handling.py](examples/operations/error_handling.py) checks the distinction between a false claim, error data, and an engine fault.

## Testing

The shipped pytest plugin supplies an engine fixture and a fresh `scratch_space` for each test.

```python
from metta import S, V
from metta.testing import assert_answers

def test_parent_query(scratch_space):
    scratch_space.add(S.Parent(S.Tom, S.Bob))
    rows = scratch_space.match(S.Parent(S.Tom, V.child))
    assert_answers([row.child for row in rows], [S.Bob])
```

Answer assertions compare multiplicity and alpha-equivalence rather than imposing an answer order.

| Testing door | Purpose |
|---|---|
| `assert_answers(actual, expected)` | Exact answer multiset |
| `assert_includes(actual, expected)` | Required answer inclusion |
| `atoms`, `ground_atoms`, `expressions` | Atom strategies |
| `symbols`, `variables`, `grounded` | Kind-specific strategies |
| `names`, `numbers`, `texts`, `library_scalars` | Value strategies |
| `patterns`, `programs` | Pattern and program strategies |
| `from_pattern(pattern)` | Ground instances respecting shared variables |
| `SpaceMachine` | Stateful space tests |
| `SpaceComplianceSuite` | Provider contract tests |
| `GatewayComplianceSuite` | Gateway contract tests |
| `check_space_provider(provider)` | Direct provider checks |
| `check_codec`, `check_minted_handles` | Codec and handle checks |
| `check_replay`, `record_replay` | Recording and replay checks |
| `check_twin` | Cross-surface comparison |
| `cases`, `laws` | Declared test cases and laws |

A pattern strategy keeps repeated named variables equal while anonymous occurrences are independent.

```python
from hypothesis import find
from metta import S, V, testing

instance = find(
    testing.from_pattern(S.edge(V.node, V.node), max_leaves=2),
    lambda atom: True,
)
assert instance.vars == ()
assert instance[1] == instance[2]
```

Subclass `SpaceComplianceSuite` and supply a pytest `provider` fixture to run its tests against your backend.

The suite reports unsupported capabilities as skips and refuses a vacuous provider; destructive clearing requires its explicit opt-in.

## Linting

The linter reads declarations, equations, and calls in a space.

```python
from metta import MeTTa

with MeTTa() as m:
    m.run("(: double (-> Number Number)) (= (double $x) (* 2 $x))")
    findings = m.self.lint()
    assert isinstance(findings, list)
```

| Door | Purpose |
|---|---|
| `metta.lint.lint(space)` | Findings over a space |
| `metta.lint.lint_file(path, ...)` | Findings with source locations |
| `metta.lint.diagnostics(findings)` | LSP diagnostic objects |
| `metta.lint.apply(space, findings)` | Apply machine remedies to a space |
| `metta.lint.fix_file(path, ...)` | Apply machine remedies to source |
| `Finding` | One diagnostic |
| `Repair` | Applied changes and skipped remedies |
| `Skipped` | A remedy that was not applied and its reason |

The CLI reports findings through its exit status and can emit JSON diagnostics or apply available fixes.

```sh
python -m metta lint program.metta
python -m metta lint --json program.metta
python -m metta lint --fix program.metta
```

## CLI

`python -m metta` exposes the same program, deployment, and inspection operations to the shell.

| Command | Use |
|---|---|
| `python -m metta run program.metta` | Run files and print directive answer groups |
| `python -m metta repl` | Interactive evaluation |
| `python -m metta serve program.metta --port 8080` | Serve loaded spaces |
| `python -m metta boot app.metta` | Assemble a manifest |
| `python -m metta lint program.metta` | Diagnose source |
| `python -m metta doc name program.metta` | Read a name's documentation |
| `python -m metta card lib_math` | Read a library card |
| `python -m metta lock program.metta` | Record loaded dependencies |
| `python -m metta llms` | Print the usage reference |
| `python -m metta stubs program.metta -o program.pyi` | Generate type stubs |
| `python -m metta convert program.py -o program.metta` | Export Python-authored declarations |
| `python -m metta extension new my-extension` | Scaffold an extension distribution |
| `python -m metta --version` | Report the installed version |

Conversion imports the Python program in a fresh declaration space, so its top-level Python code executes.

```sh
python -m metta convert rules.py -o rules.metta
python -m metta run rules.metta
python -m metta stubs rules.metta -o rules.pyi
```

## IPython

Load the extension in an ordinary Python notebook to add a line magic and a cell magic.

```ipython
%load_ext metta.ipython
%metta !(+ 1 2)
# Printed answer: 3
```

A cell magic accepts a space name on its first line.

```ipython
%%metta &notebook
(= (double $x) (* 2 $x))
!(double 21)
```

Select an existing Python space for both magics through `use`.

```python
from metta import MeTTa
from metta.ipython import use

m = MeTTa()
use(m.self)
# Subsequent %metta and %%metta calls use this space.
# Close m when the notebook session is finished.
```

## Stores for Python-side algorithms

The structural stores use atom matching and alpha-equivalence where an ordinary Python dictionary or set would use exact equality.

| Store | Purpose |
|---|---|
| `metta.structures.AlphaSet` | Set modulo variable renaming |
| `metta.structures.PatternMap` | Mapping keyed by atom patterns |
| `metta.structures.MatchIndex` | Find registered patterns matching an incoming atom |
| `metta.structures.TabledMap` | Read a computed tabled cache |
| `metta.structures.LiveView` | Maintain one pattern's answers |
| `metta.structures.ClosureView` | Maintain relation reachability |

[networkx_space.py](examples/integration/networkx_space.py) reads space relations as graphs and writes algorithm results back as facts.

## Space door inventory

The live core registry contains 137 space records, including inherited atom operations, Python protocols, and evaluation option forms.

The table below distinguishes option forms from receiver attributes; exact signatures and declared evidence are available from `metta.doors.table()`.

| Door | Kind | Contract |
|---|---|---|
| `eval` | evaluation | Evaluate a term, returning every answer. |
| `answers` | evaluation | Evaluate as an immutable, cached and replayable view. |
| `parallel` | evaluation | Evaluate every target concurrently, answering every branch's answers. |
| `pool` | provider | A pool of worker threads that each hold their own Prolog engine. |
| `reducible` | introspection | Whether a head reduces here, asked without evaluating anything. |
| `eval_status` | evaluation | Evaluate a term, pairing each answer with how it was produced. |
| `run_status` | evaluation | run(), with each directive's answers paired with how they arose. |
| `eval(..., answer="one")` | evaluation | Evaluation option selecting exactly one answer. |
| `eval(..., answer="first")` | evaluation | Evaluation option selecting the first answer. |
| `name` | introspection | The live engine name represented by this handle. |
| `self` | introspection | The space this receiver's doors work in, which for a space is itself. |
| `space_names` | introspection | Every space name this engine registers, sorted: '&self' and '&metta' from boot, every native space something created or wrote to, and every foreign space currently bound. |
| `drop` | lifecycle | Clear this space and release its owned resources. |
| `dropped` | lifecycle | Whether this handle's space has been released, by any party. |
| `to_wire` | introspection | Encode the live engine reference as a portable space operand. |
| `metatype` | introspection | Read the handle's atom kind. |
| `bind` | scope | Scope named host values for source interpolation. |
| `runtime` | introspection | The engine bridge itself, for callers going under the surface. |
| `metta` | introspection | Reach the owning context, including its sibling-space factory. |
| `alpha` | introspection | The alpha-equality TERM, (=alpha self other); alpha_eq answers now. |
| `alpha_eq` | introspection | Whether two atoms differ only by consistent variable renaming. |
| `args` | introspection | Inherited atom access to arguments. |
| `children` | introspection | Inherited atom access to children. |
| `eq` | introspection | The equality TERM, (== self other); == itself compares atoms. |
| `ge` | introspection | The greater-or-equal TERM, (>= self other). |
| `gt` | introspection | The strictly-greater TERM, (> self other). |
| `head` | introspection | Inherited atom access to the head. |
| `le` | introspection | The less-or-equal TERM, (<= self other). |
| `lt` | introspection | The strictly-less TERM, (< self other). |
| `map` | introspection | Transform every node, children before parents, without recursion. |
| `ne` | introspection | Build an inequality term. |
| `subs` | introspection | Replace each atom the bindings name, everywhere it occurs. |
| `unify` | introspection | Unify with the others, returning bindings or ``None``. |
| `vars` | introspection | The variables in first-appearance order; none means ground. |
| `value` | introspection | The inherited payload slot remains unset: a Space is a Handle, and reading value raises AttributeError. |
| `profile` | introspection | Run source under the engine's statistical profiler, answering (groups, profile): the groups exactly as run() answers them, and the profile carrying sample counters plus one row per predicate, self-ticks first. |
| `profile_extension` | introspection | Run source under the profiler, reporting only YOUR functions. |
| `stats` | introspection | The engine's own counters over a with-block, as deltas. |
| `get_property` | introspection | Return visibility, origins and declared properties of a head. |
| `match` | query | Lazily match patterns against this space as one conjunction. |
| `stream` | query | match(), pulled: the same conjunction and guard, answered one row at a time through a cursor the engine holds open. |
| `solve` | evaluation | Run relational ``let`` and return bindings keyed by its variables. |
| `prepare` | query | A query whose shape is fixed and whose facts are not: the wire form and columns build once, and each solve() may bring per-call facts (given=) that leave nothing behind. |
| `assuming` | scope | Facts held only inside a with-block: the assumptions reading of a what-if query, added on entry, removed on exit, exceptions included. |
| `transaction` | scope | Run one callable or term inside a closed engine transaction. |
| `limits` | scope | Set per-call inference, time, and stack bounds for a block. |
| `capture` | scope | Collect printed engine text without changing answer shapes. |
| `scope` | scope | Join children and release resources created in this block. |
| `atomic` | scope | Make each CALL in the block one committing engine transaction. |
| `speculative` | scope | Run each CALL against a snapshot and discard its writes. |
| `batch` | scope | Collect additions and send one batch on exit. |
| `transactional` | scope | transaction()'s decorator twin, the atomic shape Django made familiar: each CALL of the wrapped function runs inside its own engine transaction. |
| `run` | evaluation | Run source with one answer list per directive. |
| `save` | introspection | Write the authored atoms of this space, equations included, as MeTTa source by default. |
| `source` | introspection | Return this space's authored atoms as loadable MeTTa text. |
| `load` | introspection | Add a text program or trusted fast cache to this space. |
| `parse` | introspection | Read one form into an atom without evaluating it. |
| `register_token` | provider | Register a full-token regex and its Atom constructor. |
| `unregister_token` | provider | Remove a reader-token class; an absent pattern is already removed. |
| `_repr_html_` | introspection | Show this space's loadable MeTTa source in rich notebooks. |
| `add` | write | Add atoms to this space, one engine round-trip for the lot. |
| `from_` | write | Reference a library or space through a stored ``(from source map)`` row. |
| `remove` | write | Remove ONE unifying occurrence and say whether one was there, which is Python's own `list.remove` grain. |
| `transfer` | write | Move ONE unifying occurrence of each atom into another space. |
| `atoms` | introspection | Every stored atom in this space. |
| `peek` | query | Wait for one matching atom and leave it in this space. |
| `take` | write | Wait for and remove exactly one matching atom from this space. |
| `cast` | introspection | Cast this space atom ambiently with one argument, or answer value narrowed by this space's type discipline with two arguments. |
| `copy` | lifecycle | This space's contents in a new anonymous space, cloned through one bulk write, so equations copy as equations and keep running: "a scratch space set up like production" is one line. |
| `digest` | introspection | A sha256 hex digest of this space's content: every stored atom, equations included, canonicalized (variables numbered, multiset sorted) so the same atoms answer the same digest in any insertion order and in any process. |
| `__len__` | introspection | Count stored atoms. |
| `__bool__` | introspection | Always true: a space is a handle to a store, not a value that dwindles. |
| `__contains__` | introspection | Test atom membership. |
| `clear` | write | Remove everything stored here, compiled equations included. |
| `__iadd__` | write | add()'s operator spelling for one atom or one fact stream. |
| `__isub__` | write | Remove one occurrence per supplied atom. |
| `__ior__` | write | Merge into this space in one bulk crossing: every atom of another space, of a registered space name, or of an iterable. |
| `__iter__` | introspection | Iterate one assembly-order snapshot of the stored atoms. |
| `__getitem__` | introspection | Subscription is query. |
| `__delitem__` | write | Del m[pattern] removes every unifying occurrence, the bulk spelling of remove()'s multiset subtraction: m[pattern] is a query answering many rows, so deleting it deletes them all, the way DELETE WHERE does. |
| `watch` | scope | Yield matching changes, raising Timeout after each quiet deadline. |
| `subscribe` | scope | A standing query on this space: every added (or removed, or both) atom unifying with the pattern becomes an Event. |
| `integrate` | provider | Install a library integration; see metta.integrate. |
| `handles` | provider | Declare how faithfully a space answers queries of one shape. |
| `annotations` | provider | Declare the algebra a context's answer annotations live in. |
| `algebra` | provider | Declare operations with carrier membership and optional checked laws. |
| `covers` | write | Declare the strongest effect this reified world can handle. |
| `compensates` | write | Declare one recovery operation for an effectful operation. |
| `add_tagged_fact` | write | Store ``(fact tag proposition)``, the normative annotation form. |
| `add_tagged_rule` | write | Store one rule generated by the algebra-agnostic tag threader. |
| `image` | write | Choose how one Python type crosses one context boundary. |
| `sample` | evaluation | Choose ``k`` tagged alternatives with replacement by ``(rate n)``. |
| `consumption` | write | Declare a space's consumption discipline. |
| `on_error` | write | Declare what a context's failure becomes, per query shape. |
| `merge` | write | Declare how the engine merges one query shape's answers ACROSS contexts, for the multi-context idiom (match (superpose (&a &b)) ...). |
| `context` | write | Record what a space's absence means. |
| `agenda` | write | Declare which reaction fires first when several match one write. |
| `reacts` | write | Declare a reaction, stored as an (on ...) atom: when an atom matching PATTERN lands in the space, OPERATION runs under the match's bindings. |
| `admits` | write | Type a pool's membership: only TYPE-carrying atoms enter. |
| `capacity` | write | Bound a pool: an add beyond LIMIT atoms is refused loudly. |
| `atomicity` | write | Declare what a space's writes promise inside a transaction. |
| `emits` | write | Declare the order a context emits its own answers in. |
| `events` | write | Return the event stream, or declare what this context promises. |
| `define` | provider | Compile a Python function into MeTTa equations, decorator-style. |
| `rules` | provider | Collect and land a non-exclusive equation bundle in this space. |
| `pre_add` | write | Compile or accept one unary judge and claim this space's write hook. |
| `type` | introspection | Return this space's first ``get-type`` answer, including undefined. |
| `infer_types` | write | Propose a `(: head (-> ...))` for every head here that has none. |
| `doc` | introspection | Return this space's structured ``get-doc`` answer for one subject. |
| `builtins` | introspection | Every function callable from this space, plus every special form. |
| `is_function` | introspection | Report whether the name is registered as a function anywhere. |
| `is_function_here` | introspection | Whether a function would answer from THIS space: it has clauses this space's module sees, its own or the shared ones in user. |
| `arities` | introspection | Compiled predicate arities for a name: MeTTa arity plus one each. |
| `fn` | introspection | Functions visible here, as bound attribute or exact-name handles. |
| `op` | provider | Register a Python callable as a MeTTa function, decorator-style. |
| `pure` | provider | An operation whose answer depends only on its arguments. |
| `reads` | provider | An operation that reads stable state without changing it. |
| `writes` | provider | An operation that changes engine or host state. |
| `io` | provider | An operation that observes an external oracle. |
| `unregister_op` | provider | Remove a registered operation, every arity of it. |
| `register_prolog` | provider | Register Prolog predicates as MeTTa functions, at native speed. |
| `register_foreign_library` | provider | Load a compiled `.so` and register its predicates as MeTTa functions. |
| `register_library_path` | provider | Point MeTTa at a directory of files your package ships. |
| `unregister_prolog` | provider | Release everything one extension registered, and its clauses. |
| `prolog` | introspection | Drop into the engine's own interactive Prolog toplevel, the deepest debugging lever there is: listing/1 shows compiled equations, trace/0 steps through them, and quitting the toplevel returns here with the session intact. |
| `debug` | scope | Run a TERM, or source, under breakpoints, stepped from Python. |
| `explain` | introspection | What the engine will do with this query, reflected rather than run. |
| `effect_plan` | introspection | Return operations the target may execute and their joined effect. |
| `derivation` | introspection | Every proof of an answer, as trees in MeTTa terms. |
| `why` | introspection | Why a pattern matches nothing here, in words. |
| `record` | scope | Run a TERM, or source, and keep the whole run as data. |
| `trace` | scope | Run a TERM, or source, under the engine's reduction trace and answer TraceEvent records: what entered reduction at which depth, what it answered, and which reductions failed (a call with no exit). |
| `lint` | introspection | Diagnose this space for the silently-wrong class: declared types nothing defines, arity mismatches, unbound body variables, duplicate equations, and references no function or fact carries. |
| `saga` | scope | Open a committed-receipt saga over this execution space. |
| `reify` | lifecycle | Capture this space as an immutable, independently evaluable world. |
| `commit` | write | Apply one reified world's diff through this originating space. |
| `blame` | introspection | Return each matching occurrence's ``(t actor generation)`` identity. |

Package namespaces add their own records at discovery time, so an installed integration can extend this inventory without changing the core.

## Example programs

Each program below lives beside this page and checks the claims it demonstrates.

| Program | What it demonstrates |
|---|---|
| [first_steps.py](examples/basics/first_steps.py) | Atoms, joins, substitution, evaluation, and proofs |
| [array_interop.py](examples/data/array_interop.py) | DLPack arrays, identity, and mixed libraries |
| [ecosystem_graph.py](examples/gallery/ecosystem_graph.py) | Queryable library and dependency metadata |
| [family_algebras.py](examples/gallery/family_algebras.py) | Relational directions and annotation carriers |
| [git_like_worlds.py](examples/gallery/git_like_worlds.py) | Immutable branches, diff, commit, and observation |
| [journaled_observed_store.py](examples/gallery/journaled_observed_store.py) | Validation, journal replay, and transaction events |
| [linda_coordination.py](examples/gallery/linda_coordination.py) | Blocking tuple-space coordination |
| [symbolic_tensors.py](examples/gallery/symbolic_tensors.py) | Symbolic tensor shapes |
| [cmetta_space.py](examples/integration/cmetta_space.py) | A C runtime used as a provider |
| [duckdb_space.py](examples/integration/duckdb_space.py) | SQL pushdown, NULL, and non-primitive values |
| [multishot_solving.py](examples/integration/multishot_solving.py) | Program parts and retractable external facts |
| [networkx_space.py](examples/integration/networkx_space.py) | Graph views over native and SQL facts |
| [persistent_migration.py](examples/integration/persistent_migration.py) | Persistent schema migration |
| [provider_policy.py](examples/integration/provider_policy.py) | Capability and request-specific admission |
| [provider_worlds.py](examples/integration/provider_worlds.py) | Bounded matching and provider world commits |
| [python_objects.py](examples/integration/python_objects.py) | Object projection, reconstruction, and reflection |
| [registration_lifecycle.py](examples/integration/registration_lifecycle.py) | Discovery and reversible integration hooks |
| [remote_controls.py](examples/integration/remote_controls.py) | Authorization and cursor ownership |
| [routing_equations.py](examples/integration/routing_equations.py) | Route and middleware equations |
| [sqlite_space.py](examples/integration/sqlite_space.py) | Declarative SQL bridges and opaque blobs |
| [web_routes.py](examples/integration/web_routes.py) | Typed path parameters and route dispatch |
| [standing_queries.py](examples/live/standing_queries.py) | Actors, subscriptions, live joins, and deltas |
| [annotation_contracts.py](examples/operations/annotation_contracts.py) | Written arguments, local claims, and reflection |
| [concurrency_handles.py](examples/operations/concurrency_handles.py) | Pools and nonblocking mailboxes |
| [effect_ranks.py](examples/operations/effect_ranks.py) | Four decorators and five derived effect classes |
| [engine_controls.py](examples/operations/engine_controls.py) | Bounds, counters, output capture, and frames |
| [error_handling.py](examples/operations/error_handling.py) | Assertion failures and error-valued answers |
| [explaining_a_query.py](examples/operations/explaining_a_query.py) | Planning, analysis, and write admission |
| [property_instances.py](examples/operations/property_instances.py) | Ground instances preserving variable identity |
| [python_definitions.py](examples/operations/python_definitions.py) | Lowering, generators, rules, and class exposure |
| [runtime_configuration.py](examples/operations/runtime_configuration.py) | Startup and live configuration |
| [saga_compensation.py](examples/operations/saga_compensation.py) | Receipts and reverse recovery |
| [custom_matchers.py](examples/reasoning/custom_matchers.py) | Regex, fuzzy, and semantic matching |
| [evolutionary_search.py](examples/reasoning/evolutionary_search.py) | Population rewriting and effectful variation |
| [literature_discovery.py](examples/reasoning/literature_discovery.py) | Tagged evidence across a vocabulary gap |
| [neurosymbolic_addition.py](examples/reasoning/neurosymbolic_addition.py) | Uncertain perception and relational constraints |
| [pln_uncertain_reasoning.py](examples/reasoning/pln_uncertain_reasoning.py) | Engine PLN truth values from Python |

## Worked example: recommendations with their sources

A recommendation follows from a person's interest and a paper's topic, and its annotation records both sources and the rule.

```python
from metta import MeTTa, S, V, counting, prov

with MeTTa() as context:
    kb = context.self

    kb.add_tagged_fact(S.profile, S.interested(S.Ada, S.logic))
    kb.add_tagged_fact(S.catalog_entry, S.about(S.paper1, S.logic))
    kb.add_tagged_rule(
        S.recommendation_rule,
        S.recommend(V.person, V.paper),
        S.interested(V.person, V.topic),
        S.about(V.paper, V.topic),
    )

    answer = kb.match(S.recommend(S.Ada, V.paper), under=prov).one()
    assert str(answer.value) == "(recommend Ada paper1)"
    assert all(
        source in str(answer.annotation)
        for source in ("profile", "catalog-entry", "recommendation-rule")
    )

    support = kb.match(S.recommend(S.Ada, S.paper1), under=counting).one()
    assert support.annotation == 1

    @kb.define
    def double(value: int) -> int:
        return value * 2

    assert double(21) == [42]
    assert double.py(21) == 42

    delivered = []
    subscription = kb.subscribe(
        S.delivered(V.person, V.paper),
        lambda event: delivered.append(event.bindings),
    )
    try:
        kb.transaction(lambda: kb.add(S.delivered(S.Ada, S.paper1)))
        assert len(delivered) == 1
        assert delivered[0]["person"] == S.Ada

        rows = kb.match(S.delivered(V.person, V.paper))
        assert rows.to_dicts() == [{"person": "Ada", "paper": "paper1"}]

        with kb.stats() as spent:
            assert kb.eval(S.double(21)) == [42]
        assert spent.inferences > 0
    finally:
        subscription.cancel()
```

The query yields `(recommend Ada paper1)`, its count is `1`, and the committed delivery becomes `{"person": "Ada", "paper": "paper1"}`.
