"""Purpose: resolve Python call targets while retaining open source boundaries.

Assumes: source describes ordinary lexical imports and object construction.
Dynamic dispatch which the assignment graph cannot resolve remains an open
call site [tested: test_door_order_retains_unresolved_callbacks; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Guarantees: aliases and helper arguments propagate to a fixed point before
call facts are returned [tested: test_door_order_follows_aliases_and_helpers;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]. No analyzed source is imported or executed.
Declared container contents and alias writes retain callable targets; type
qualifiers do not replace their initializers [tested:
test_declared_callable_mapping_retains_every_door_target,
test_mapping_mutation_cannot_hide_a_supplied_callback; commit=WORKTREE].
Decides: Runtime and JanusBridge are local engine boundaries; third-party
calls and supplied callbacks are open, while stdlib operations are host work
[source: extensions/python/metta/_binding/runtime.py:363; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

The finite assignment-set representation follows PyCG's published method:
https://arxiv.org/abs/2103.00587. Lexical bindings, annotated receivers and
instance fields follow the analysis described by Pyan at
https://github.com/Technologicat/pyan/tree/8522ca4f59b9a731e6a1685c77e8cf983813ceee.
"""

from __future__ import annotations

import ast
import builtins
import sys
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Reference:
    """One finite possible value, with a receiver for a bound method."""

    kind: str
    name: str
    receiver: str = ""


type Values = frozenset[Reference]
type Slot = tuple[str, str]


@dataclass(frozen=True, slots=True)
class Calls:
    """Explicit calls and implicit source protocols reached by one body."""

    targets: frozenset[str] = frozenset()
    native: frozenset[str] = frozenset()
    open: frozenset[str] = frozenset()


@dataclass(slots=True)
class _Scope:
    name: str
    module: str
    node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    parent: str | None
    owner: str | None = None
    locals: set[str] = field(default_factory=set)
    redirects: dict[str, str] = field(default_factory=dict)

    @property
    def statements(self) -> list[ast.stmt]:
        if isinstance(self.node, ast.Lambda):
            return [ast.copy_location(ast.Return(value=self.node.body), self.node)]
        return self.node.body

    @property
    def parameters(self) -> list[ast.arg]:
        if isinstance(self.node, (ast.Module, ast.ClassDef)):
            return []
        args = self.node.args
        return [*args.posonlyargs, *args.args, *args.kwonlyargs,
                *([args.vararg] if args.vararg else []),
                *([args.kwarg] if args.kwarg else [])]


class CallGraph:
    """A worklist of source scopes whose finite possible values only grow."""

    def __init__(self, sources: Mapping[str, str], entries: Iterable[str], lifetimes: Iterable[str] = ()) -> None:
        """Index declarations before resolving calls from the selected entries."""
        self.scopes: dict[str, _Scope] = {}
        self.classes: set[str] = set()
        self.functions: set[str] = set()
        self.modules = set(sources)
        self.module_prefixes = set(sources)
        self.entries = frozenset(entries)
        self.lifetimes = frozenset(lifetimes)
        self.values: dict[Slot, Values] = {}
        self.readers: dict[Slot, set[str]] = defaultdict(set)
        self.queue: deque[str] = deque()
        self.queued: set[str] = set()
        self.current = ""
        self.facts: dict[str, Calls] = {}
        self.targets: set[str] = set()
        self.native: set[str] = set()
        self.open: set[str] = set()
        self.lambdas: dict[int, str] = {}
        self.generators: set[str] = set()
        self.containers: dict[str, Reference] = {}
        self.container_keys: dict[object, int] = {}
        self.narrowed: dict[Slot, Values] = {}
        self._final = False
        for module, text in sources.items():
            self._index(_Scope(module, module, ast.parse(text), None))
        for name in self.modules | self.classes | self.entries.intersection(self.scopes):
            self._schedule(name)

    def _schedule(self, name: str) -> None:
        if name not in self.queued:
            self.queue.append(name)
            self.queued.add(name)

    def _get(self, slot: Slot) -> Values:
        if self.current:
            self.readers[slot].add(self.current)
        return self.narrowed.get(slot, self.values.get(slot, frozenset()))

    def _put(self, slot: Slot, values: Values) -> None:
        previous = self.values.get(slot, frozenset())
        added = values - previous
        if added:
            self.values[slot] = previous | added
            for reader in self.readers[slot]:
                self._schedule(reader)

    def _index(self, scope: _Scope) -> None:
        self.scopes[scope.name] = scope
        scope.locals.update(parameter.arg for parameter in scope.parameters)

        def visit(node: ast.AST) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = scope.name + "." + node.name
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                scope.locals.add(node.name)
                self._put((scope.name, node.name), frozenset({Reference(kind, name)}))
                (self.classes if kind == "class" else self.functions).add(name)
                owner = scope.name if isinstance(scope.node, ast.ClassDef) else None
                self._index(_Scope(name, scope.module, node, scope.name, owner))
                return
            if isinstance(node, ast.Lambda):
                name = f"{scope.name}.<lambda@{node.lineno}:{node.col_offset}>"
                self.lambdas[id(node)] = name
                self.functions.add(name)
                self._index(_Scope(name, scope.module, node, scope.name))
                return
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                self.generators.add(scope.name)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for module in imported:
                    parts = module.split(".")
                    self.module_prefixes.update(".".join(parts[:index]) for index in range(1, len(parts) + 1))
                for alias in node.names:
                    name = alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name)
                    scope.locals.add(name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                scope.locals.add(node.id)
            elif isinstance(node, ast.Global):
                scope.redirects.update((name, scope.module) for name in node.names)
            elif isinstance(node, ast.Nonlocal):
                for name in node.names:
                    parent = scope.parent
                    while parent is not None:
                        outer = self.scopes[parent]
                        if name in outer.locals:
                            scope.redirects[name] = parent
                            break
                        parent = outer.parent
            for child in ast.iter_child_nodes(node):
                visit(child)

        for node in scope.statements:
            visit(node)

    def _slot(self, scope: _Scope, name: str) -> Slot:
        if name in scope.redirects:
            return scope.redirects[name], name
        if name in scope.locals or scope.parent is None:
            return scope.name, name
        parent = self.scopes[scope.parent]
        # Method lexical lookup skips the enclosing class namespace.
        if isinstance(parent.node, ast.ClassDef) and parent.parent:
            parent = self.scopes[parent.parent]
        return self._slot(parent, name)

    def _symbol(self, name: str, seen: frozenset[str] = frozenset()) -> Values:
        if name in seen:
            return frozenset({Reference("unknown", f"cyclic alias {name}")})
        if name in self.functions:
            return frozenset({Reference("function", name)})
        if name in self.classes:
            return frozenset({Reference("class", name)})
        if name in self.modules:
            return frozenset({Reference("module", name)})
        parent, _, member = name.rpartition(".")
        if parent in self.modules or parent in self.classes:
            values = self._get((parent, member))
            return frozenset(value for reference in values for value in (
                self._symbol(reference.name, seen | {name}) if reference.kind == "symbol" else (reference,)
            ))
        if name.split(".", 1)[0] not in {module.split(".", 1)[0] for module in self.modules}:
            return frozenset({Reference("external", name)})
        # A qualified import may name an attribute of a reexported class.
        if parent:
            return self._attribute(self._symbol(parent, seen | {name}), member, None)
        return frozenset()

    def _references(self, values: Values) -> Values:
        return frozenset(value for reference in values for value in (
            self._symbol(reference.name) if reference.kind == "symbol" else (reference,)
        ))

    def _annotation(self, node: ast.expr | None, scope: _Scope) -> Values:
        if node is None:
            return frozenset()
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                try:
                    return self._annotation(ast.parse(node.value, mode="eval").body, scope)
                except SyntaxError:
                    return frozenset()
            return frozenset({Reference("instance", "builtins.NoneType")})
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self._annotation(node.left, scope) | self._annotation(node.right, scope)
        if isinstance(node, ast.Subscript):
            names = {reference.name for reference in self._annotation_symbols(node.value, scope)}
            # These qualifiers describe a binding, not a runtime receiver.
            # https://docs.python.org/3.14/library/typing.html#typing.Final
            # policy-inventory-exempt: mechanism-internal; reason=Python type qualifiers carry their underlying type in the first argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._annotation
            if names.intersection({"typing.Final", "typing.ClassVar", "typing.Annotated"}):
                value = node.slice.elts[0] if isinstance(node.slice, ast.Tuple) else node.slice
                return self._annotation(value, scope)
            return self._annotation(node.value, scope)
        if isinstance(node, ast.Name):
            references = self._references(self._get(self._slot(scope, node.id)))
            if not references and hasattr(builtins, node.id):
                references = frozenset({Reference("external", "builtins." + node.id)})
        elif isinstance(node, ast.Attribute):
            references = self._attribute(self._annotation_symbols(node.value, scope), node.attr, None)
        else:
            return frozenset()
        result = set()
        for reference in references:
            # policy-inventory-exempt: mechanism-internal; reason=abstract typing forms do not identify a concrete receiver class; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._annotation
            if reference.name in {"typing.Any", "typing.Self", "typing.Callable", "collections.abc.Callable",
                                  "typing.Final", "typing.ClassVar", "typing.Annotated"}:
                continue
            # policy-inventory-exempt: mechanism-internal; reason=these reference variants carry a class identity usable as an annotation; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._annotation
            if reference.kind in {"class", "external", "instance"}:
                result.add(Reference("instance", reference.name))
        return frozenset(result)

    def _annotation_symbols(self, node: ast.expr, scope: _Scope) -> Values:
        if isinstance(node, ast.Name):
            return self._references(self._get(self._slot(scope, node.id)))
        if isinstance(node, ast.Attribute):
            return self._attribute(self._annotation_symbols(node.value, scope), node.attr, None)
        return frozenset()

    def _bases(self, name: str, seen: frozenset[str] = frozenset()) -> tuple[str, ...]:
        if name in seen or name not in self.classes:
            return (name,)
        scope = self.scopes[name]
        assert isinstance(scope.node, ast.ClassDef)  # nosec B101 # _bases only receives indexed class scopes
        assert scope.parent is not None  # nosec B101 # every indexed class has an enclosing scope
        bases = [reference.name for node in scope.node.bases
                 for reference in self._annotation(node, self.scopes[scope.parent])]
        if not scope.node.bases:
            bases = ["builtins.object"]
        sequences = [list(self._bases(base, seen | {name})) for base in bases] + [bases.copy()]
        result = [name]
        while any(sequences):
            sequences = [sequence for sequence in sequences if sequence]
            candidate = next((sequence[0] for sequence in sequences
                              if all(sequence[0] not in other[1:] for other in sequences)), None)
            if candidate is None:
                # A source hierarchy that cannot be resolved has no safe MRO.
                return (*result, "<unresolved-mro>")
            result.append(candidate)
            for sequence in sequences:
                if sequence[0] == candidate:
                    sequence.pop(0)
        return tuple(dict.fromkeys(result))

    def _attribute(self, values: Values, member: str, node: ast.AST | None) -> Values:
        result: set[Reference] = set()
        for reference in self._references(values):
            if reference.kind == "module":
                result.update(self._symbol(reference.name + "." + member))
            elif reference.kind == "external":
                builtin = getattr(builtins, reference.name.removeprefix("builtins."), None)
                if node is None or reference.name in self.module_prefixes or (
                    reference.name.startswith("builtins.") and isinstance(builtin, type) and hasattr(builtin, member)
                ):
                    result.add(Reference("external", reference.name + "." + member))
                else:
                    result.add(Reference("unknown", self._where(node, "attribute of an external value")))
            # policy-inventory-exempt: mechanism-internal; reason=class and instance references resolve members through the MRO; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._class_attribute
            elif reference.kind in {"class", "instance"}:
                self._class_attribute(reference, member, node, result)
            elif reference.kind == "generator":
                result.add(Reference("function", reference.name))
            elif reference.kind == "container":
                kind = getattr(builtins, reference.receiver.removeprefix("builtins."))
                if hasattr(kind, member):
                    result.add(Reference("container_method", member, reference.name))
                elif self._final:
                    result.add(Reference("unknown", reference.receiver + "." + member))
            elif reference.kind == "unknown":
                result.add(reference)
            else:
                result.add(Reference("instance", "builtins.object"))
        return frozenset(result)

    def _class_attribute(self, reference: Reference, member: str, node: ast.AST | None, result: set[Reference]) -> None:
        """Resolve the first MRO member and apply Python's descriptor binding."""
        for base in self._bases(reference.name):
            initializer = base + ".__init__"
            if initializer in self.functions and initializer not in self.facts:
                self._schedule(initializer)
            members = self._references(self._get((base, member)))
            if not members:
                if base not in self.classes:
                    builtin = getattr(builtins, base.removeprefix("builtins."), None)
                    if (base.startswith("builtins.") and hasattr(builtin, member)) or (
                        base.split(".", 1)[0] in sys.stdlib_module_names
                        and not base.startswith(("builtins.", "collections.abc.", "typing.", "contextlib.Abstract"))
                    ):
                        result.add(Reference("external", base + "." + member))
                        return
                    if self._final:
                        result.add(Reference("unknown", base + "." + member))
                        return
                continue
            for value in members:
                if value.kind != "function" or reference.kind != "instance":
                    result.add(value)
                    continue
                scope = self.scopes[value.name]
                decorators = getattr(scope.node, "decorator_list", ())
                if any(ast.unparse(item).rsplit(".", 1)[-1] == "property" for item in decorators):
                    if node is not None:
                        result.update(self._call(frozenset({Reference("bound", value.name, reference.name)}), [], {}, node))
                elif any(ast.unparse(item).rsplit(".", 1)[-1] == "staticmethod" for item in decorators):
                    result.add(value)
                else:
                    result.add(Reference("bound", value.name, reference.name))
            return
        if self._final and not any(value.name.startswith(reference.name) for value in result):
            result.add(Reference("unknown", f"attribute on {reference.name}"))

    def _where(self, node: ast.AST, reason: str) -> str:
        return f"{self.current}:{getattr(node, 'lineno', 0)}: {reason} ({ast.unparse(node)})"

    def _key(self, node: ast.AST | None) -> str:
        """Join equal literal keys using Python's own mapping equality."""
        try:
            value = ast.literal_eval(node) if node is not None else None
            if node is None:
                return "<unknown-items>"
            index = self.container_keys.setdefault(value, len(self.container_keys))
        except (ValueError, TypeError):
            return "<unknown-items>"
        return f"<key:{index}>"

    def _container(self, node: ast.AST, kind: str, elements: Iterable[Values] = (),
                   *, keys: Values = frozenset(), positions: bool = False) -> Values:
        """Keep one finite allocation site and the values that can flow into it."""
        # PyCG keeps container allocations and content pointers in its assignment graph:
        # https://github.com/vitsalis/PyCG/blob/8d5dc40837803beef1d8d379fbf2cdad6cd94641/pycg/processing/postprocessor.py
        name = f"{self.current}.<container@{getattr(node, 'lineno', 0)}:{getattr(node, 'col_offset', 0)}:{kind}>"
        reference = Reference("container", name, "builtins." + kind)
        self.containers[name] = reference
        elements = tuple(elements)
        for index, values in enumerate(elements):
            self._put((name, "<items>"), values)
            if positions:
                self._put((name, str(index)), values)
                self._put((name, self._key(ast.Constant(value=index))), values)
                self._put((name, self._key(ast.Constant(value=index - len(elements)))), values)
            else:
                self._put((name, "<unknown-items>"), values)
        self._put((name, "<keys>"), keys)
        return frozenset({reference})

    def _container_call(self, reference: Reference, positional: list[Values],
                        keywords: dict[str, Values], node: ast.AST) -> Values:
        """Transfer builtin container contents; unmodeled operations stay open."""
        container = self.containers[reference.receiver]
        name, method = container.name, reference.name
        items = self._get((name, "<items>"))
        keys = self._get((name, "<keys>"))
        none = frozenset({Reference("instance", "builtins.NoneType")})
        if method == "__iter__":
            return keys if container.receiver == "builtins.dict" else items
        key = self._key(node.slice if isinstance(node, ast.Subscript) else
                        node.args[0] if isinstance(node, ast.Call) and node.args else None)
        selected = items if key == "<unknown-items>" else self._get((name, key)) | self._get((name, "<unknown-items>"))
        # policy-inventory-exempt: mechanism-internal; reason=these builtin methods read a stored element; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"__getitem__", "pop"}:
            if method == "pop" and container.receiver != "builtins.dict":
                self._put((name, "<unknown-items>"), items)
                selected = items
            return selected | (positional[1] if len(positional) > 1 else frozenset())
        # policy-inventory-exempt: mechanism-internal; reason=mapping defaults remain possible values and setdefault may publish one; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"get", "setdefault"}:
            default = positional[1] if len(positional) > 1 else none
            if method == "setdefault":
                self._put((name, "<items>"), default)
                self._put((name, key), default)
                if positional:
                    self._put((name, "<keys>"), positional[0])
            return selected | default
        # policy-inventory-exempt: mechanism-internal; reason=builtin views expose dictionary contents without replacing callable identities; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"keys", "values", "items"}:
            values = keys if method == "keys" else items
            if method == "items":
                values = self._container(node, "tuple", (keys, items), positions=True)
            return self._container(node, "list", (values,))
        # policy-inventory-exempt: mechanism-internal; reason=these builtin mutations insert one element at the declared argument position; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"append", "add", "insert", "__setitem__"}:
            index = int(method in {"insert", "__setitem__"})
            if len(positional) > index:
                self._put((name, "<items>"), positional[index])
                self._put((name, key if method == "__setitem__" and container.receiver == "builtins.dict"
                           else "<unknown-items>"), positional[index])
            if method == "insert":
                self._put((name, "<unknown-items>"), items)
            if method == "__setitem__" and positional:
                self._put((name, "<keys>"), positional[0])
            return none
        # policy-inventory-exempt: mechanism-internal; reason=bulk builtin mutations propagate every supplied element; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"extend", "update", "__ior__", "__iadd__"}:
            for argument in positional:
                for value in argument:
                    if container.receiver == "builtins.dict" and value.kind == "container" and value.receiver == "builtins.dict":
                        self._put((name, "<items>"), self._get((value.name, "<items>")))
                        self._put((name, "<unknown-items>"), self._get((value.name, "<items>")))
                        self._put((name, "<keys>"), self._get((value.name, "<keys>")))
                    else:
                        values = self._protocol(frozenset({value}), "__iter__", node)
                        if container.receiver == "builtins.dict":
                            values = self._protocol(values, "__iter__", node)
                        self._put((name, "<items>"), values)
                        self._put((name, "<unknown-items>"), values)
            for values in keywords.values():
                self._put((name, "<items>"), values)
                self._put((name, "<unknown-items>"), values)
            if keywords:
                self._put((name, "<keys>"), frozenset({Reference("instance", "builtins.str")}))
            return frozenset({container}) if method.startswith("__i") else none
        if method == "copy":
            return self._container(node, container.receiver.removeprefix("builtins."), (items,), keys=keys)
        # Removing or reordering values cannot remove a possible call from a
        # flow-insensitive graph. sort still invokes its declared key function.
        # policy-inventory-exempt: mechanism-internal; reason=these builtin mutations add no elements but sort invokes its key callback; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"clear", "remove", "discard", "reverse", "sort", "__delitem__"}:
            self._put((name, "<unknown-items>"), items)
            if "key" in keywords:
                self._call(keywords["key"], [items], {}, node)
            return none
        # policy-inventory-exempt: mechanism-internal; reason=these builtin queries return scalar values rather than stored callables; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"__len__", "count", "index", "__contains__"}:
            return frozenset({Reference("instance", "builtins.int")})
        unknown = Reference("unknown", self._where(node, f"unresolved container operation {container.receiver}.{method}"))
        if self._final:
            self.open.add(unknown.name)
        return frozenset({unknown})

    def _protocol(self, values: Values, name: str, node: ast.AST) -> Values:
        yielded: set[Reference] = set()
        for reference in values:
            if reference.kind == "generator":
                self.targets.add(reference.name)
                yielded.update(self._get((reference.name, "<yield>")))
        concrete = frozenset(reference for reference in values
                             if reference.kind != "generator" and (reference.kind != "instance" or not reference.name.startswith("builtins.")))
        if not concrete:
            return frozenset(yielded) or frozenset({Reference("instance", "builtins.object")})
        return frozenset(yielded) | self._call(self._attribute(concrete, name, node), [], {}, node)

    def _call(self, values: Values, positional: list[Values], keywords: dict[str, Values], node: ast.AST) -> Values:
        result: set[Reference] = set()
        references = self._references(values)
        if not references and self._final:
            self.open.add(self._where(node, "unresolved call target"))
        for reference in references:
            if reference.kind == "container_method":
                result.update(self._container_call(reference, positional, keywords, node))
                continue
            if reference.kind == "class":
                instance = Reference("instance", reference.name)
                result.add(instance)
                constructors = self._attribute(frozenset({instance}), "__init__", node)
                self._call(constructors, positional, keywords, node)
                continue
            if reference.kind == "instance":
                result.update(self._protocol(frozenset({reference}), "__call__", node))
                continue
            # policy-inventory-exempt: mechanism-internal; reason=plain and bound function references carry indexed callable scopes; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
            if reference.kind in {"function", "bound"}:
                name = reference.name
                scope = self.scopes[name]
                arguments = ([frozenset({Reference("instance", reference.receiver)})]
                             if reference.kind == "bound" else []) + positional
                for parameter, supplied in zip(scope.parameters, arguments, strict=False):
                    self._put((name, parameter.arg), supplied)
                for parameter_name, supplied in keywords.items():
                    self._put((name, parameter_name), supplied)
                if name.startswith(("metta._binding.runtime.Runtime.", "metta._binding.runtime.JanusBridge.")):
                    self.native.add(self._where(node, name))
                elif any(isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                         and statement.value.value is Ellipsis for statement in scope.statements):
                    self.open.add(self._where(node, f"abstract or external body {name}"))
                else:
                    self.targets.add(name)
                    if name not in self.facts:
                        self._schedule(name)
                if name in self.generators:
                    result.add(Reference("generator", name))
                else:
                    returns = getattr(scope.node, "returns", None)
                    returned = self._get((name, "<return>"))
                    result.update(returned if any(value.kind == "container" for value in returned)
                                  else self._annotation(returns, scope) or returned)
                continue
            if reference.kind == "external":
                name = reference.name
                root = name.split(".")[0]
                if root == "janus_swi":
                    self.native.add(self._where(node, name))
                elif root not in sys.stdlib_module_names and root != "builtins":
                    self.open.add(self._where(node, f"external call {name}"))
                # policy-inventory-exempt: mechanism-internal; reason=builtin container constructors retain the elements supplied by their input iterable; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
                if name in {"builtins.list", "builtins.tuple", "builtins.set", "builtins.frozenset", "builtins.dict"}:
                    kind = name.removeprefix("builtins.")
                    container = self._container(node, kind)
                    if kind == "dict":
                        self._call(self._attribute(container, "update", node), positional, keywords, node)
                    elif positional:
                        items = self._protocol(positional[0], "__iter__", node)
                        container = self._container(node, kind, (items,))
                    result.update(container)
                    continue
                # policy-inventory-exempt: mechanism-internal; reason=typing identity helpers return their second argument unchanged; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
                if name in {"typing.cast", "typing.assert_type"} and len(positional) > 1:
                    result.update(positional[1])
                # policy-inventory-exempt: mechanism-internal; reason=ordinary and deferred module loaders resolve the literal module argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
                elif name in {"importlib.import_module", "metta._lazy.lazy"}:
                    if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        result.update(self._symbol(node.args[0].value))
                # policy-inventory-exempt: mechanism-internal; reason=both attribute helpers access the member named by their second argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
                elif name in {"builtins.getattr", "builtins.hasattr"} and len(positional) > 1:
                    if isinstance(node, ast.Call) and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                        result.update(self._attribute(positional[0], node.args[1].value, node))
                    else:
                        result.add(Reference("unknown", self._where(node, "dynamic attribute")))
                else:
                    protocols = {"builtins.len": "__len__", "builtins.bool": "__bool__",
                                 "builtins.iter": "__iter__", "builtins.next": "__next__",
                                 "builtins.list": "__iter__", "builtins.tuple": "__iter__",
                                 "builtins.set": "__iter__", "builtins.sorted": "__iter__"}
                    if name in protocols and positional:
                        self._protocol(positional[0], protocols[name], node)
                    if "key" in keywords:
                        self._call(keywords["key"], [], {}, node)
                    # policy-inventory-exempt: mechanism-internal; reason=these higher-order standard operations invoke their first argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
                    if name in {"builtins.map", "builtins.filter", "functools.reduce"} and positional:
                        self._call(positional[0], positional[1:], {}, node)
                    target = getattr(builtins, name.removeprefix("builtins."), None) if root == "builtins" else None
                    if isinstance(target, type):
                        result.add(Reference("instance", name))
                    else:
                        result.add(Reference("instance", "builtins.object"))
                continue
            if reference.kind == "unknown":
                self.open.add(self._where(node, reference.name))
                result.add(reference)
            # policy-inventory-exempt: mechanism-internal; reason=callable reference cases already handled above must not become unresolved calls; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._call
            elif reference.kind not in {"class", "instance", "function", "bound", "external"} and self._final:
                self.open.add(self._where(node, f"unresolved callable {reference.name}"))
        return frozenset(result)

    def _value(self, node: ast.expr | None, scope: _Scope) -> Values:
        if node is None:
            return frozenset({Reference("instance", "builtins.NoneType")})
        if isinstance(node, ast.Name):
            values = self._references(self._get(self._slot(scope, node.id)))
            if not values and hasattr(builtins, node.id):
                return frozenset({Reference("external", "builtins." + node.id)})
            return values
        if isinstance(node, ast.Constant):
            return frozenset({Reference("instance", "builtins." + type(node.value).__name__)})
        if isinstance(node, ast.Attribute):
            return self._attribute(self._value(node.value, scope), node.attr, node)
        if isinstance(node, ast.Lambda):
            return frozenset({Reference("function", self.lambdas[id(node)] )})
        if isinstance(node, ast.Call):
            references = self._value(node.func, scope)
            positional = [self._value(argument, scope) for argument in node.args]
            keywords = {item.arg: self._value(item.value, scope) for item in node.keywords if item.arg is not None}
            names = {reference.name for reference in self._references(references)}
            if names.intersection({"metta._lazy.lazy", "importlib.import_module"}) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return self._symbol(node.args[0].value)
            if names.intersection({"typing.TypeVar", "typing.NewType"}):
                bounds = [item.value for item in node.keywords if item.arg == "bound"]
                if not bounds and len(node.args) > 1:
                    bounds = node.args[1:]
                return frozenset(reference for bound in bounds for reference in self._annotation(bound, scope))
            if names == {"builtins.super"} and scope.owner:
                return frozenset({Reference("instance", name) for name in self._bases(scope.owner)[1:2]})
            return self._call(references, positional, keywords, node)
        if isinstance(node, ast.NamedExpr):
            values = self._value(node.value, scope)
            self._assign(node.target, values, scope)
            return values
        if isinstance(node, ast.IfExp):
            self._value(node.test, scope)
            previous = self.narrowed.copy()
            self._narrow(node.test, scope, truth=True)
            body = self._value(node.body, scope)
            self.narrowed = previous.copy()
            self._narrow(node.test, scope, truth=False)
            other = self._value(node.orelse, scope)
            self.narrowed = previous
            return body | other
        if isinstance(node, ast.BoolOp):
            return frozenset(reference for index, value in enumerate(node.values)
                             for reference in self._value(value, scope)
                             if not (isinstance(node.op, ast.Or) and index < len(node.values) - 1
                                     and reference.name == "builtins.NoneType"))
        if isinstance(node, ast.Subscript):
            values = self._value(node.value, scope)
            self._value(node.slice, scope)
            return self._protocol(values, "__getitem__", node)
        if isinstance(node, (ast.Await, ast.Yield, ast.YieldFrom)):
            values = self._value(node.value, scope)
            if isinstance(node, ast.YieldFrom):
                self._protocol(values, "__iter__", node)
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                self._put((scope.name, "<yield>"), values)
            return values
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in node.generators:
                values = self._protocol(self._value(generator.iter, scope), "__iter__", generator.iter)
                self._assign(generator.target, values, scope)
                for condition in generator.ifs:
                    self._value(condition, scope)
            if isinstance(node, ast.DictComp):
                return self._container(node, "dict", (self._value(node.value, scope),), keys=self._value(node.key, scope))
            return self._container(node, "set" if isinstance(node, ast.SetComp) else "list", (self._value(node.elt, scope),))
        if isinstance(node, ast.Dict):
            reference = self._container(node, "dict")
            container = next(iter(reference))
            for key, value in zip(node.keys, node.values, strict=True):
                if key is None:
                    self._call(self._attribute(reference, "update", node), [self._value(value, scope)], {}, node)
                else:
                    self._put((container.name, "<keys>"), self._value(key, scope))
                    values = self._value(value, scope)
                    self._put((container.name, "<items>"), values)
                    self._put((container.name, self._key(key)), values)
            return reference
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            elements = [self._protocol(self._value(item.value, scope), "__iter__", item)
                        if isinstance(item, ast.Starred) else self._value(item, scope) for item in node.elts]
            kind = "tuple" if isinstance(node, ast.Tuple) else "list" if isinstance(node, ast.List) else "set"
            return self._container(node, kind, elements,
                                   positions=isinstance(node, (ast.Tuple, ast.List)) and not any(isinstance(item, ast.Starred) for item in node.elts))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self._value(child, scope)
        kind = "list" if isinstance(node, ast.List) else "tuple" if isinstance(node, ast.Tuple) else "dict" if isinstance(node, ast.Dict) else "set" if isinstance(node, ast.Set) else "object"
        return frozenset({Reference("instance", "builtins." + kind)})

    def _assign(self, node: ast.expr, values: Values, scope: _Scope) -> None:
        if isinstance(node, ast.Name):
            self._put(self._slot(scope, node.id), values)
        elif isinstance(node, ast.Attribute):
            for reference in self._value(node.value, scope):
                # policy-inventory-exempt: mechanism-internal; reason=only class and instance references own indexed attribute assignments; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._assign
                if reference.kind in {"class", "instance"} and reference.name in self.classes:
                    self._put((reference.name, node.attr), values)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for index, element in enumerate(node.elts):
                members = frozenset(value for reference in values for value in (
                    ((self._get((reference.name, str(index))) or self._get((reference.name, "<items>")))
                     | self._get((reference.name, "<unknown-items>")))
                    if reference.kind == "container" else self._protocol(frozenset({reference}), "__iter__", node)
                ))
                self._assign(element, members, scope)
        elif isinstance(node, ast.Subscript):
            self._call(self._attribute(self._value(node.value, scope), "__setitem__", node),
                       [self._value(node.slice, scope), values], {}, node)
        elif isinstance(node, ast.Starred):
            self._assign(node.value, values, scope)

    def _narrow(self, test: ast.expr, scope: _Scope, *, truth: bool) -> None:
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            self._narrow(test.operand, scope, truth=not truth)
        elif isinstance(test, ast.BoolOp) and (
            (truth and isinstance(test.op, ast.And)) or (not truth and isinstance(test.op, ast.Or))
        ):
            for value in test.values:
                self._narrow(value, scope, truth=truth)
        elif isinstance(test, ast.Call) and len(test.args) == 2 and isinstance(test.args[0], ast.Name):
            functions = self._value(test.func, scope)
            if {reference.name for reference in functions} == {"builtins.isinstance"}:
                slot = self._slot(scope, test.args[0].id)
                declared = self._value(test.args[1], scope)
                declared = frozenset(value for reference in declared for value in (
                    self._get((reference.name, "<items>")) if reference.kind == "container" else (reference,)
                ))
                classes = {reference.name for reference in declared
                           # policy-inventory-exempt: mechanism-internal; reason=isinstance narrowing reads locally indexed or external class objects; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._narrow
                           if reference.kind in {"class", "external"}}
                def matches(reference: Reference) -> bool:
                    return bool(classes.intersection(self._bases(reference.receiver if reference.kind == "container" else reference.name)))
                values = self._get(slot)
                self.narrowed[slot] = frozenset(reference for reference in values
                                               if reference.kind == "unknown" or matches(reference) == truth)
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.left, ast.Name):
            right = test.comparators[0]
            if isinstance(right, ast.Constant) and right.value is None and isinstance(test.ops[0], (ast.Is, ast.IsNot)):
                slot = self._slot(scope, test.left.id)
                keep_none = truth == isinstance(test.ops[0], ast.Is)
                self.narrowed[slot] = frozenset(reference for reference in self._get(slot)
                                               if (reference.name == "builtins.NoneType") == keep_none)

    def _statement(self, node: ast.stmt, scope: _Scope) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if isinstance(node, ast.Import):
                    imported = alias.name if alias.asname else alias.name.split(".")[0]
                    local = alias.asname or imported
                    value = Reference("module" if imported in self.modules else "external", imported)
                else:
                    parent = scope.module
                    if node.level:
                        # A package is a module with indexed children.
                        package = parent if any(name.startswith(parent + ".") for name in self.modules) else parent.rpartition(".")[0]
                        parts = package.split(".")
                        parent = ".".join(parts[:len(parts) - node.level + 1])
                        imported = ".".join(filter(None, (parent, node.module)))
                    else:
                        imported = node.module or ""
                    local = alias.asname or alias.name
                    value = Reference("symbol", imported + "." + alias.name)
                self._put(self._slot(scope, local), frozenset({value}))
            return
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            values = self._value(node.value, scope)
            if isinstance(node, ast.AnnAssign) and not any(value.kind == "container" for value in values):
                values = self._annotation(node.annotation, scope) or values
            for target in node.targets if isinstance(node, ast.Assign) else (node.target,):
                self._assign(target, values, scope)
            return
        if isinstance(node, ast.Return):
            self._put((scope.name, "<return>"), self._value(node.value, scope))
            return
        if isinstance(node, ast.If):
            self._value(node.test, scope)
            previous = self.narrowed.copy()
            for truth, branch in ((True, node.body), (False, node.orelse)):
                self.narrowed = previous.copy()
                self._narrow(node.test, scope, truth=truth)
                for statement in branch:
                    self._statement(statement, scope)
            self.narrowed = previous
            return
        if isinstance(node, (ast.For, ast.AsyncFor)):
            values = self._protocol(self._value(node.iter, scope), "__aiter__" if isinstance(node, ast.AsyncFor) else "__iter__", node.iter)
            self._assign(node.target, values, scope)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                values = self._value(item.context_expr, scope)
                asynchronous = isinstance(node, ast.AsyncWith)
                entered = self._protocol(values, "__aenter__" if asynchronous else "__enter__", item.context_expr)
                self._protocol(values, "__aexit__" if asynchronous else "__exit__", item.context_expr)
                if item.optional_vars:
                    self._assign(item.optional_vars, entered, scope)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._value(child, scope)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                self._statement(child, scope)
            elif isinstance(child, (ast.ExceptHandler, ast.match_case)):
                for statement in child.body:
                    self._statement(statement, scope)

    def _evaluate(self, scope: _Scope) -> None:
        self.current = scope.name
        self.narrowed = {}
        self.targets, self.native, self.open = set(), set(), set()
        for index, parameter in enumerate(scope.parameters):
            values = self._annotation(parameter.annotation, scope)
            # policy-inventory-exempt: mechanism-internal; reason=Python method receiver conventions seed the enclosing class identity; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._evaluate
            if index == 0 and scope.owner and parameter.arg in {"self", "cls"}:
                values |= frozenset({Reference("instance" if parameter.arg == "self" else "class", scope.owner)})
            self._put((scope.name, parameter.arg), values)
            if self._final and scope.name in self.entries and not self._get((scope.name, parameter.arg)):
                self._put((scope.name, parameter.arg), frozenset({Reference("unknown", f"supplied parameter {scope.name}.{parameter.arg}")}))
        for statement in scope.statements:
            self._statement(statement, scope)
        if scope.name in self.lifetimes:
            values = self._get((scope.name, "<return>"))
            for reference in values:
                if reference.kind == "instance" and reference.name in self.classes and reference.name != scope.owner:
                    for protocol in ("__enter__", "__exit__", "__iter__", "__next__", "close"):
                        if any(self._get((base, protocol)) for base in self._bases(reference.name)):
                            self._protocol(frozenset({reference}), protocol, scope.node)
        self.facts[scope.name] = Calls(frozenset(self.targets), frozenset(self.native), frozenset(self.open))
        self.current = ""

    def solve(self) -> Mapping[str, Calls]:
        """Resolve available targets, then propagate explicit entry-point unknowns."""
        for final in (False, True):
            self._final = final
            for name in set(self.facts) | self.modules | self.classes | self.entries.intersection(self.scopes):
                self._schedule(name)
            while self.queue:
                name = self.queue.popleft()
                self.queued.remove(name)
                self._evaluate(self.scopes[name])
        return {name: self.facts[name] for name in sorted(self.functions.intersection(self.facts))}
