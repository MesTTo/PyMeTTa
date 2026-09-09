"""Purpose: resolve Python call targets while retaining open source boundaries.

Assumes: source describes ordinary lexical imports and object construction.
Dynamic dispatch which the assignment graph cannot resolve remains an open
call site [tested: test_door_order_retains_unresolved_callbacks; commit=WORKTREE].
Guarantees: aliases and helper arguments propagate to a fixed point before
call facts are returned [tested: test_door_order_follows_aliases_and_helpers;
commit=WORKTREE]. No analyzed source is imported or executed.
Decides: Runtime and JanusBridge are local engine boundaries; third-party
calls and supplied callbacks are open, while stdlib operations are host work
[source: extensions/python/metta/_binding/runtime.py:363; commit=WORKTREE].

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
        for parameter in scope.parameters:
            scope.locals.add(parameter.arg)

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
            if reference.name in {"typing.Any", "typing.Self", "typing.Callable", "collections.abc.Callable"}:
                continue
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
        assert isinstance(scope.node, ast.ClassDef)
        assert scope.parent is not None
        bases = [reference.name for node in scope.node.bases
                 for reference in self._annotation(node, self.scopes[scope.parent])]
        if not scope.node.bases:
            bases = ["builtins.object"]
        sequences = [list(self._bases(base, seen | {name})) for base in bases] + [bases[:]]
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
            elif reference.kind in {"class", "instance"}:
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
                                and not base.startswith("builtins.")
                                and not base.startswith(("collections.abc.", "typing.", "contextlib.Abstract"))
                            ):
                                result.add(Reference("external", base + "." + member))
                                break
                            if self._final:
                                result.add(Reference("unknown", base + "." + member))
                                break
                        continue
                    for value in members:
                        if value.kind == "function" and reference.kind == "instance":
                            scope = self.scopes[value.name]
                            decorators = getattr(scope.node, "decorator_list", ())
                            if any(ast.unparse(item).rsplit(".", 1)[-1] == "property" for item in decorators):
                                if node is not None:
                                    result.update(self._call(frozenset({Reference("bound", value.name, reference.name)}), [], {}, node))
                            elif any(ast.unparse(item).rsplit(".", 1)[-1] == "staticmethod" for item in decorators):
                                result.add(value)
                            else:
                                result.add(Reference("bound", value.name, reference.name))
                        else:
                            result.add(value)
                    break
                else:
                    if self._final and not any(value.name.startswith(reference.name) for value in result):
                        result.add(Reference("unknown", f"attribute on {reference.name}"))
            elif reference.kind == "generator":
                result.add(Reference("function", reference.name))
            elif reference.kind == "unknown":
                result.add(reference)
            else:
                result.add(Reference("instance", "builtins.object"))
        return frozenset(result)

    def _where(self, node: ast.AST, reason: str) -> str:
        return f"{self.current}:{getattr(node, 'lineno', 0)}: {reason} ({ast.unparse(node)})"

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
        result = set()
        references = self._references(values)
        if not references and self._final:
            self.open.add(self._where(node, "unresolved call target"))
        for reference in references:
            if reference.kind == "class":
                instance = Reference("instance", reference.name)
                result.add(instance)
                constructors = self._attribute(frozenset({instance}), "__init__", node)
                self._call(constructors, positional, keywords, node)
                continue
            if reference.kind == "instance":
                result.update(self._protocol(frozenset({reference}), "__call__", node))
                continue
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
                    result.update(self._annotation(returns, scope) or self._get((name, "<return>")))
                continue
            if reference.kind == "external":
                name = reference.name
                root = name.split(".")[0]
                if root == "janus_swi":
                    self.native.add(self._where(node, name))
                elif root not in sys.stdlib_module_names and root != "builtins":
                    self.open.add(self._where(node, f"external call {name}"))
                if name in {"typing.cast", "typing.assert_type"} and len(positional) > 1:
                    result.update(positional[1])
                elif name in {"importlib.import_module", "metta._lazy.lazy"}:
                    if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        result.update(self._symbol(node.args[0].value))
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
            for element in ((node.key, node.value) if isinstance(node, ast.DictComp) else (node.elt,)):
                self._value(element, scope)
            return frozenset({Reference("instance", "builtins.dict" if isinstance(node, ast.DictComp) else "builtins.list")})
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
                if reference.kind in {"class", "instance"} and reference.name in self.classes:
                    self._put((reference.name, node.attr), values)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                self._assign(element, values, scope)
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
                classes = {reference.name for reference in self._value(test.args[1], scope)
                           if reference.kind in {"class", "external"}}
                def matches(reference: Reference) -> bool:
                    return bool(classes.intersection(self._bases(reference.name)))
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
            if isinstance(node, ast.AnnAssign):
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
