## 2026-09-11, later: the data model walked section by section
Source: the Python 3.14 Language Reference, section 3.3 "Special method names" (https://docs.python.org/3.14/reference/datamodel.html#special-method-names), section 8.7 "Class definitions" (https://docs.python.org/3.14/reference/compound_stmts.html#class-definitions), the dataclasses module (https://docs.python.org/3.14/library/dataclasses.html) and functools (https://docs.python.org/3.14/library/functools.html). Every name those pages define gets one row; a row is "exists", "derived" (written by the declaration from the class alone), "compiled" (lowered from a method body), "declaration-time" (Python runs it once while the class is created and nothing lowers it), or "island" (a visible per-application host call).

### The mapping law, stated once
An instance is a constructor term in every grain. A special method is a MeTTa function whose name is the dunder's word (`eq`, `lt`, `add`, `size`, `elements`, `get`, `contains`, `enter`, `exit`, `call`, `repr`) typed by the class arrow, with one equation per defining class; Python's reflected and in-place forms are not separate heads, because MeTTa dispatches on every argument (a `__radd__` is the same `add` with the pattern on the other side, an `__iadd__` is `add` followed by a rebind for a value or a write for an entity). The compiler lowers the Python syntax that Python itself routes to a dunder (`a + b`, `a == b`, `len(a)`, `a[i]`, `x in a`, `for x in a`, `if a`, `a(x)`, `with a as v`, `str(a)`) to that head when the operand's static type is a declared class, and to the builtin otherwise. Static types come from three places and nowhere else: parameter annotations, constructor calls in the body, and field annotations of a declared class; a local of unknown type keeps the builtin, and the builtin's refusal on a term names the annotation as the remedy.

### 3.3.1 basic customization
| name | grain | mapping |
|---|---|---|
| `__new__` | all | declaration-time; a class that customises allocation is constructed by Python and crosses as a grounded value |
| `__init__` | value | compiled into the constructor: the body's `self.f = expr` assignments become `let` bindings and the term is built last, `(= (make-Point $x $y) (let $n (norm-of $x $y) (Point $x $y $n)))`; the constructor arrow stays `(: Point (-> ...))` |
| `__init__` | entity, prototype | compiled: each `self.f = expr` is a fact written into the class space (or the instance space) under the fresh handle, in one transaction |
| `__del__` | entity, prototype | `del obj` and scope exit retire the handle's facts (`owned-by` rows) or drop the space; there is no finaliser to run because the engine has no reference counting; a `__del__` body is refused with the remedy `with`/`scope` |
| `__repr__`, `__str__`, `__format__`, `__bytes__` | all | the term's own rendering is the default; a class-defined `__repr__` compiles to `repr`; `__format__` and `__bytes__` are islands |
| `__lt__` `__le__` `__gt__` `__ge__` | all | `lt` `le` `gt` `ge` equations; `@dataclass(order=True)` derives them as tuple comparison over the fields in definition order (the reference's rule) and `@functools.total_ordering` derives the other three from `eq` and the one given |
| `__eq__`, `__ne__` | value | structural `==` (the engine's equality policy) unless the class defines `__eq__`, then `eq`; `__ne__` is `not eq` |
| `__eq__` | entity | the reference: a mutable `@dataclass` compares fields, an ordinary class compares identity; derived accordingly, `eq` over the facts for a dataclass, handle equality otherwise |
| `__hash__` | all | the dataclasses rule is carried as a declaration: `eq=True, frozen=True` hashes by fields (the term); `eq=True, frozen=False` is unhashable, so `dict[obj]` on it is a compile-time refusal naming the rule; `unsafe_hash=True` hashes by fields anyway |
| `__bool__` | all | `truthy`; `if a:` lowers to it for a declared class |

### 3.3.2 attribute access, descriptors, slots, subclass hooks
| name | mapping |
|---|---|
| `__getattr__` | entity and prototype: dynamic field lookup `(match &C (field (C $id) $name $v) $v)` when the static field set has no such name; value: refused (a term has fixed positions) |
| `__getattribute__`, `__setattr__`, `__delattr__` | declaration-time when they only validate (their effect is visible in `__init__`'s lowering); otherwise the class's attribute access is an island and the catalog says so |
| `__dir__` | the catalog answers (`get-type`, the accessor rows); nothing to compile |
| `__get__`, `__set__`, `__delete__`, `__set_name__` (descriptors) | `property`, `cached_property`, `classmethod`, `staticmethod` and `functools.partialmethod` are known descriptors with rows of their own; an unknown descriptor makes that attribute's accessor an island, visible in the equation |
| `__slots__` | value: exact arity of the constructor arrow; entity: the closed field set, so `obj.other = 1` is refused at compile time and `__getattr__`'s open lookup is not derived |
| `__init_subclass__`, `__mro_entries__` | declaration-time |

### 3.3.3 to 3.3.5 class creation, instance checks, generics
| name | mapping |
|---|---|
| metaclasses, `__prepare__`, class keyword arguments | declaration-time; the class the metaclass produced is what declares |
| `__instancecheck__`, `__subclasscheck__` | declaration-time; `isinstance(x, C)` lowers to `get-type` with the `:<` edges, which is what the reference's default check means; a class that overrides them keeps Python's answer through an island |
| `__class_getitem__`, PEP 695 `class Box[T]:` | parametric arrows with type variables (exists); `Box[int]` at a call site is an annotation the compiler reads, never a runtime call |

### 3.3.6 to 3.3.10 callables, containers, numbers, context managers, patterns
| name | mapping |
|---|---|
| `__call__` | `(= ((Adder $n) $x) (+ $n $x))`: the instance term is the head; `a(x)` lowers to `($a $x)` for a declared class |
| `__len__`, `__length_hint__` | `size`; the hint has no meaning and is ignored |
| `__getitem__`, `__setitem__`, `__delitem__`, `__missing__` | `get`, `put`, `remove`, and `__missing__` as `get`'s fallback equation; slices lower to the existing slice image |
| `__iter__` written with `yield` | `elements`, a nondeterministic equation, exactly the generator lowering the function compiler already does: each `yield` is one answer, `for x in obj` is `for` over the answers, `list(obj)` is `collapse`; an iterator class with `__next__` and state is an entity whose `__next__` compiles like any method, and `iter(obj)`/`next(it)` lower to the seat's cursor over `elements`, which is how the seat already reads a nondeterministic answer stream one item at a time |
| `__reversed__` | `reversed-elements`, nondeterministic like `elements` |
| `__contains__` | `contains`; `x in a` lowers to it |
| numeric dunders (`__add__` ... `__or__`) | one head per operator word (`add`, `sub`, `mul`, `matmul`, `truediv`, `floordiv`, `mod`, `divmod`, `pow`, `lshift`, `rshift`, `and`, `xor`, `or`); reflected forms are the same head with the pattern on the other side; in-place forms are the head plus a rebind (value) or a write (entity) |
| unary `__neg__` `__pos__` `__abs__` `__invert__` | `neg` `pos` `abs` `invert` |
| `__complex__` `__int__` `__float__` `__index__` `__round__` `__trunc__` `__floor__` `__ceil__` | conversions: `int(a)`, `float(a)`, `round(a)` on a declared class lower to `to-int`, `to-float`, `round`; `__index__` is `to-int` used where an index is needed |
| `__enter__`, `__exit__`, `@contextlib.contextmanager` | `enter` and `exit`; `with a as v: body` lowers to `(let $v (enter $a) (try body finally (exit $a)))` on the existing try/finally lowering; a generator-based `@contextmanager` is the same with its `yield` as the split point; the engine's own scoped resources (lib_thread's `scope`, the space's limits block, which `with` lowers to today) keep their forms |
| `__match_args__` | `case C(x=0, y=y)` maps keyword patterns to positions through it and lowers to `(C 0 $y)`; a dataclass sets it from its fields, `install_type` already sets it for annotated plain classes |
| `__buffer__`, `__release_buffer__` | islands; a buffer is host memory |
| `__await__`, `__aiter__`, `__anext__`, `__aenter__`, `__aexit__` | the async faces the aio mirror generates; an `async def` method is the same equation reached through the aio door, as the function compiler already treats `async def` |
| `__annotations__`, `__annotate__` | the arrows (exists) |

### 8.7 class definitions
Decorators apply in nested order at declaration; the class the outermost decorator returns is what declares (so `@m.define` outermost sees the finished class, `@dataclass(slots=True)` returning a new class included). The inheritance list gives the `:<` edges in MRO order and the class keyword arguments (including `metaclass=`) are declaration-time. A class body's namespace is read for annotated fields, methods, `ClassVar`s (class-space atoms) and nested classes (declared as `Outer.Inner`); everything else the body executes is declaration-time. `__qualname__` and `__module__` name the class's home in the catalog.

### dataclasses, every option
`init` (the constructor equation is derived or the class's own `__init__` compiles), `repr` (rendering), `eq`/`order`/`unsafe_hash` (the rows above), `frozen` (the value grain), `match_args` (the pattern row), `kw_only` and `KW_ONLY` (Python-side only: MeTTa calls are positional, the twin's constructor accepts keywords), `slots` (exact arity), `weakref_slot` (nothing). `field(default=, default_factory=)` are constructor defaults, a factory being a call at construction; `field(init=False)` is a field the constructor computes (from `__post_init__`); `field(repr=False, compare=False, hash=False)` exclude the field from `repr`, `eq`/`order`, `hash` derivations; `field(metadata=)` lands as a documentation row; `field(doc=)` is the field's docstring row (exists through `attribute_docstrings`). `InitVar` is a constructor-only parameter handed to the `__post_init__` lowering; `fields()`, `asdict()`, `astuple()` are the catalog's own answers (the accessor rows, a dict-space projection, the term's children); `replace()` is `__replace__`, a rebuilt term; `make_dataclass` produces a class that declares like any other; `FrozenInstanceError` is the refusal a write to a value raises.

### functools, every decorator
`cache` and `lru_cache(maxsize, typed)` are `memoize` and the bounded memo (the 2026-09-06 rows; `typed` is meaningless under structural equality and is ignored with a note); `cached_property` is a memoised accessor (its "not thread-safe, may run twice" caveat becomes the memo's own transactional rule); `total_ordering` derives from `eq` and the one comparison given; `singledispatch` and `singledispatchmethod` are the ordinary equation set, one per registered type (the "dispatch on the first non-self argument" rule is what a head pattern does); `partial` and `partialmethod` are curried equations, `(= (add5 $x) (add 5 $x))`; `wraps` and `update_wrapper` are declaration-time; `reduce` lowers to `foldall`; `cmp_to_key` and `Placeholder` are islands.

### Identity, decided
An entity's identity is one of the engine's own tokens: `engine/identity.pl` mints actor-and-generation tokens under `flag/3` serialisation, unique across processes (the actor is a UUID) and already carried by every native occurrence. A state cell was rejected because `new-state` writes are not rolled back by `snapshot/1` and a read-modify-write on it does not serialise (`2026-09-06-audit-library-defects.md`); a `new-space` per identity was rejected by the cost table. The handle is `(Account <token>)`; the seat's projection renders and rebuilds it like any constructor term.

### Where a class's rows live, decided
A class declares into a space of its own, `&Account`, holding its arrow, its accessor and writer equations, its method equations, its `ClassVar` atoms and its instances' facts. The declaring space references it with `(from &Account)`, the reference-row mechanism of FROM, so the class is a module a program imports like a library and its population is one space to query. A `from` row exposes the class's public face and refuses an `internal` head (`2026-09-09-import-and-module-semantics.md`): the derived rows mark the field facts and the identity minting `internal`, and the methods, accessors and constructor public, which is Python's own convention read literally (a leading underscore marks a method `internal` too). A subclass's space references its bases in MRO order.

### The Python side of a compiled instance
A value instance in Python is the ordinary dataclass value it always was, crossing by projection. An entity or prototype instance in Python is a proxy whose attribute reads and writes go to the engine's facts and whose method calls go to the equations, the way an ORM instrument (SQLAlchemy's instrumented attributes, Django's descriptors, the direction section 7 of the faces thread named): `a = Account("alice", 100)` mints the handle and returns the proxy, `a.balance` is `(Account-balance (Account <token>))`, `a.deposit(25)` is `(deposit (Account <token>) 25)`, and a MeTTa program that finds the same handle by a `match` sees the same object. That is what "people write Python" means for objects: one object, two notations.

### Generators, reused
The user's point holds and is already the design: a `yield` is one nondeterministic answer, so a `__iter__` with `yield` is the `elements` equation and needs nothing new; a `for` over an object, a comprehension over it, `list()`, `any()`/`all()` and `sum()` over it are the same lowerings the function compiler applies to a generator today, and `next()` is the seat's cursor. The only class-specific piece is `__next__` with state, which is a method on an entity like any other.

### Decided: the order of work for the package
1. Grains and rows in `install_type` (identity tokens, class space, entity facts, writers, `internal` marks, retirement), measured against the cost table.
2. Methods compile with `self` as a parameter; accessor and writer lowering; `super()`; the proxy for entity and prototype instances.
3. The dunder heads and the type-directed operator lowering; keyword class patterns; `with` on context managers; iterator classes.
4. The decorator rows the 2026-09-06 thread ordered (cache, cached_property, total_ordering, singledispatch, abstractmethod/Protocol, override/final).
5. The five examples with twins, the corpus records, the reference pages, README, `llms.txt`, CHANGELOG, this thread's closing section with the measured numbers.
