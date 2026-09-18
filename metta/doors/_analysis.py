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
test_mapping_mutation_cannot_hide_a_supplied_callback; commit=15e4ceec343bc2523a1d34a391054948c0b1b3bf].
Calls through declared supplied parameters carry their source contract;
undeclared members and registry callbacks remain defects [tested:
test_parameter_contracts_follow_declared_protocols,
test_undeclared_parameter_members_remain_defects,
test_registry_callable_is_a_defect_open_boundary; commit=07976cf8b415390449863d803277b73102673b51].
Literal field names retain their declarations through object access and
delegating setters; class descriptors and instance-held callbacks keep
their different binding laws [tested:
test_literal_field_names_flow_through_a_declared_setter,
test_object_attribute_access_keeps_descriptor_crossings,
test_instance_callback_fields_are_not_bound_like_class_methods; commit=d2a1b574173fbe576d1912e4d96ce58b99c0d59c].
Caller propagation settles before missing helper annotations are completed;
broad annotations retain actual returned callables [tested:
test_late_values_do_not_seed_helper_annotation_alternatives,
test_annotations_do_not_replace_returned_or_assigned_callbacks; commit=d2a1b574173fbe576d1912e4d96ce58b99c0d59c].
A body that only forwards its own parameters to an attribute intrinsic is
that intrinsic at every caller, so field names stay paired with their values;
a wrapper with another statement, a class data descriptor and a dynamic name
keep their effects [tested: test_transparent_setter_keeps_each_field_paired_with_its_value,
test_transparent_setter_is_recognised_through_its_resolved_declaration,
test_setter_with_a_native_statement_keeps_its_crossing,
test_transparent_setter_still_invokes_a_class_data_descriptor,
test_transparent_setter_keeps_a_dynamic_member_name_open; commit=d2a1b574173fbe576d1912e4d96ce58b99c0d59c].
Memoized declaration lookups replay their slot reads, so the report of the
shipped tree is identical with and without them and under two hash seeds
[measured 2026-09-15: doororder.py 41s before, 17.8s after, PYTHONHASHSEED 123
and 456 equal; commit=d2a1b574173fbe576d1912e4d96ce58b99c0d59c].
A generic annotation keeps the elements, keys, positions or class it
declares, and admits only its own type's operations; a declaration refines
an actual of unknown structure; a public contract is read from a door's
overloads; the standard-library calls that invoke a supplied callback are
the ones typeshed declares Callable; *args and **kwargs are the tuple and
mapping Python binds; a __slots__ descriptor and an inherited UserList
reach their fields; callable() and an early exit narrow like a type checker
[tested: test_generic_annotations_declare_their_element_structure,
test_declared_container_types_admit_only_their_own_operations,
test_declared_parameter_types_refine_actuals_of_unknown_structure,
test_callable_and_early_exit_narrowing_separate_a_union,
test_a_callable_passed_to_the_standard_library_is_invoked_where_typeshed_declares_it,
test_variadic_parameters_hold_a_tuple_and_a_mapping,
test_slot_descriptors_write_and_read_the_declared_field,
test_a_generic_base_class_names_its_class_and_holds_its_elements; commit=2ef13993eeb63385a1aece70f37e72bef1cfd5ac].
A value the standard library made is host work, an attribute no
standard-library type declares is open, and what a supplied callable
answers carries its contract; every such value is one finite reference
[tested: test_a_standard_library_value_is_host_work_and_an_unknown_member_is_not,
test_a_value_a_supplied_callback_returned_carries_its_contract,
test_wrapper_unwrapping_has_a_finite_abstract_domain; commit=2ef13993eeb63385a1aece70f37e72bef1cfd5ac].
A declaration the type checker verified is authoritative: a source value it
cannot admit does not escape, and a caller's supplied, unknown, opaque or
external value reaches a concrete parameter as the declared class; an Any
narrowed by isinstance is that class; a public return is the overloads';
getattr answers its default; type(x) is x's class; iteration through a
source __iter__ or an inherited container yields the elements; a field
tested against None is narrowed wherever a subclass holds it; a branch no
value enters is unreachable rather than unresolved [tested:
test_a_verified_return_declaration_excludes_the_values_it_refuses,
test_a_supplied_value_reaches_a_concrete_parameter_as_its_declared_class,
test_an_any_value_narrowed_by_isinstance_is_that_type,
test_getattr_with_a_default_answers_the_default,
test_type_of_a_value_is_its_class_and_a_made_class_resolves_through_its_bases,
test_a_source_iter_yields_its_elements_to_a_loop,
test_an_inherited_container_iterates_what_it_stores,
test_a_field_test_against_none_narrows_the_field; commit=a6874e867225cd6efb26177d803b942d0dc02dcf].
Fails when: a setter carries statements beside its intrinsic call; its
callers' names and values are then joined across all call sites, which
reports every assigned value as a possible receiver [tested:
test_setter_with_a_native_statement_keeps_its_crossing; commit=d2a1b574173fbe576d1912e4d96ce58b99c0d59c].
A standard-library call that returns one of its arguments' elements, other
than the container constructors, iter, next and the mapping reads modelled
here, loses those elements: sorted(rows)[0] is host work with no door in
it [assumed 2026-09-16; commit=2ef13993eeb63385a1aece70f37e72bef1cfd5ac].
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
import collections.abc
import importlib
import sys
import types
import typing
from collections import defaultdict, deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from functools import cache
from typing import cast

from metta.doors._invocations import INVOCATIONS


@dataclass(frozen=True, slots=True)
class Reference:
    """One finite possible value, with a receiver for a bound method."""

    kind: str
    name: str
    receiver: str = ""
    member: str = ""
    operations: frozenset[str] = frozenset()
    literal: str | None = None
    _hash: int = field(init=False, repr=False, compare=False, default=0)

    def __post_init__(self) -> None:
        # Set algebra hashes every member on each union and difference; the
        # six-field tuple hash is computed once per reference instead.
        object.__setattr__(self, "_hash", hash((self.kind, self.name, self.receiver, self.member,
                                                self.operations, self.literal)))

    def __hash__(self) -> int:
        return self._hash


type Values = frozenset[Reference]
type Slot = tuple[str, str]

# These builtins read or write the member named by their second argument.
# A body that only forwards its own parameters to one of them is that
# intrinsic under an argument permutation, so its callers apply the intrinsic
# to their own paired actuals. Joining every caller's arguments in the
# forwarder's parameter slots instead pairs every field name with every
# value, the context-insensitive loss that Hybrid Inlining removes by
# propagating context-critical statements to their callers:
# https://arxiv.org/abs/2210.14436
_ATTRIBUTE_INTRINSICS = frozenset({
    "builtins.getattr", "builtins.hasattr", "builtins.object.__getattribute__",
    "builtins.setattr", "builtins.object.__setattr__",
})


@cache
def _stdlib_object(name: str) -> object | None:
    """The standard-library object a qualified name denotes, or None.

    A builtin type whose module does not export it, NoneType above all, is
    found by the qualified name it reports for itself, which is the name
    this analysis writes for the type of a constant.
    """
    module, _, member = name.rpartition(".")
    if module.split(".", 1)[0] not in sys.stdlib_module_names:
        return None
    try:
        return getattr(importlib.import_module(module), member)
    except AttributeError:
        return next((value for value in vars(types).values() if isinstance(value, type)
                     and value.__module__ == module and value.__qualname__ == member), None)
    except ImportError:
        return None


# These standard-library bases hold their elements in a documented public
# attribute, so a source class that inherits one stores there.
# https://docs.python.org/3.14/library/collections.html#userlist-objects
# closed-set: decides; policy=the standard-library container bases whose instances store their elements in a documented attribute; reads=none
_INHERITED_STORAGE = {"collections.UserList": "data", "collections.UserDict": "data",
                      "collections.UserString": "data"}


@cache
def _members(name: str) -> frozenset[str]:
    """The member names instances of a standard-library type provide.

    Read from the MRO's own namespaces rather than through hasattr, which
    answers about the class object: every class is callable, so
    hasattr(str, "__call__") is True while a str is not callable.
    https://docs.python.org/3.14/reference/datamodel.html#invoking-descriptors
    """
    kind = _stdlib_object(name)
    if not isinstance(kind, type):
        return frozenset()
    return frozenset(member for base in kind.__mro__ for member in vars(base))


@cache
def _mapping(name: str) -> bool:
    """Whether a container's own type holds keys as well as values."""
    kind = _stdlib_object(name)
    return isinstance(kind, type) and issubclass(kind, collections.abc.Mapping)


@cache
def _shape(name: str) -> tuple[str, str] | None:
    """How a subscripted annotation head holds its arguments, and its own type.

    Classified by Python's own hierarchy through typing.get_origin, as
    metta._catalog.annotations classifies runtime annotations: a Mapping
    holds keys and values, a tuple its positions, an Iterator and any other
    Iterable their elements, an Awaitable the value it yields, and type the
    class it names. The second name is the declared type itself, so the
    operations the value admits stay exactly that type's own.
    """
    head = _stdlib_object(name)
    origin = typing.get_origin(head) or head
    if not isinstance(origin, type):
        return None
    receiver = f"{origin.__module__}.{origin.__qualname__}"
    if origin is type:
        return "class", receiver
    if issubclass(origin, collections.abc.Mapping):
        return "dict", receiver
    if issubclass(origin, tuple):
        return "tuple", receiver
    if issubclass(origin, (collections.abc.Iterable, collections.abc.AsyncIterable)):
        return "list", receiver
    if issubclass(origin, collections.abc.Awaitable):
        return "awaited", receiver
    return None


@dataclass(frozen=True, slots=True)
class ContractCall:
    """An open call tied to a declared parameter of a public door."""

    site: str
    parameter: str
    annotation: str


@dataclass(frozen=True, slots=True)
class Calls:
    """Explicit calls and implicit source protocols reached by one body."""

    targets: frozenset[str] = frozenset()
    native: frozenset[str] = frozenset()
    open: frozenset[str] = frozenset()
    contracts: frozenset[ContractCall] = frozenset()


@dataclass(slots=True)
class _Scope:
    name: str
    module: str
    node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    parent: str | None
    owner: str | None = None
    locals: set[str] = field(default_factory=set)
    redirects: dict[str, str] = field(default_factory=dict)
    decorators: frozenset[str] = frozenset()

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

    @property
    def arguments(self) -> ast.arguments | None:
        """The signature, when this scope is a callable one."""
        return self.node.args if isinstance(self.node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) else None


def _terminates(statements: list[ast.stmt]) -> bool:
    """Whether a block always leaves its enclosing block on every path."""
    if not statements:
        return False
    last = statements[-1]
    if isinstance(last, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
        return True
    if isinstance(last, ast.If):
        return _terminates(last.body) and _terminates(last.orelse)
    return False


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
        self.contracts: set[ContractCall] = set()
        self.lambdas: dict[int, str] = {}
        self.generators: set[str] = set()
        self.containers: dict[str, Reference] = {}
        self.positioned: set[str] = set()
        self.container_keys: dict[object, int] = {}
        self.narrowed: dict[Slot, Values] = {}
        self.forwarders: dict[str, tuple[ast.expr, tuple[int, ...]] | None] = {}
        self.forwarding: set[str] = set()
        self.memos: dict[str, tuple[object, frozenset[Slot]]] = {}
        self.subclasses: dict[str, set[str]] = defaultdict(set)
        self.overloads: dict[str, list[ast.arguments]] = defaultdict(list)
        self.overload_returns: dict[str, list[ast.expr | None]] = defaultdict(list)
        self.memo_readers: dict[Slot, set[str]] = defaultdict(set)
        self.collecting: list[set[Slot]] = []
        # Keyed by node identity and holding the node, so a synthetic node
        # freed and reallocated at the same address cannot hit a stale entry.
        self.unparsed: dict[int, tuple[ast.AST, str]] = {}
        self.literal_keys: dict[int, tuple[ast.AST, str]] = {}
        self._final = False
        self._reporting = False
        for module, text in sources.items():
            self._index(_Scope(module, module, ast.parse(text), None))
        self._schedule_declarations()

    def _schedule_declarations(self) -> None:
        """Bind module declarations before any class body or entry reads them."""
        for name in (*sorted(self.modules), *sorted(self.classes), *sorted(self.entries.intersection(self.scopes))):
            self._schedule(name)
        # Every class's MRO is indexed once, so the reverse index is complete
        # before a base method reads a field a subclass assigned.
        for name in sorted(self.classes):
            self._bases(name)

    def _schedule(self, name: str) -> None:
        if not self._reporting and name not in self.queued:
            self.queue.append(name)
            self.queued.add(name)

    def _get(self, slot: Slot) -> Values:
        if self.current:
            self.readers[slot].add(self.current)
        for reads in self.collecting:
            reads.add(slot)
        return self.narrowed.get(slot, self.values.get(slot, frozenset()))

    def _put(self, slot: Slot, values: Values) -> None:
        if self._reporting:
            return
        previous = self.values.get(slot, frozenset())
        added = values - previous
        if added:
            self.values[slot] = previous | added
            for reader in self.readers[slot]:
                self._schedule(reader)
            for key in self.memo_readers.pop(slot, ()):
                self.memos.pop(key, None)

    def _memo[T](self, key: str, compute: Callable[[], T]) -> T:
        """Reuse a pure store lookup until one of the slots it read grows.

        A hit replays the reader registration the computation would have
        made, so the current scope is still rescheduled by later growth. A
        result that read a narrowed slot is not kept: narrowing is local to
        one evaluation.
        """
        hit = self.memos.get(key)
        if hit is not None:
            cached, read = hit
            if self.current:
                for slot in read:
                    self.readers[slot].add(self.current)
            for outer in self.collecting:
                outer.update(read)
            return cast("T", cached)
        reads: set[Slot] = set()
        self.collecting.append(reads)
        try:
            value = compute()
        finally:
            self.collecting.pop()
        if not any(slot in self.narrowed for slot in reads):
            self.memos[key] = value, frozenset(reads)
            for slot in reads:
                self.memo_readers[slot].add(key)
        return value

    def _index(self, scope: _Scope) -> None:
        self.scopes[scope.name] = scope
        scope.locals.update(parameter.arg for parameter in scope.parameters)

        def visit(node: ast.AST) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = scope.name + "." + node.name
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                    ast.unparse(item).rsplit(".", 1)[-1] == "overload" for item in node.decorator_list
                ):
                    # An overload declares the public contract the
                    # implementation's own annotation widens to Any.
                    # https://docs.python.org/3.14/library/typing.html#typing.overload
                    self.overloads[name].append(node.args)
                    self.overload_returns[name].append(node.returns)
                    return
                scope.locals.add(node.name)
                self._put((scope.name, node.name), frozenset({Reference(kind, name)}))
                (self.classes if kind == "class" else self.functions).add(name)
                owner = scope.name if isinstance(scope.node, ast.ClassDef) else None
                decorators = frozenset(ast.unparse(item).rsplit(".", 1)[-1] for item in node.decorator_list)
                self._index(_Scope(name, scope.module, node, scope.name, owner, decorators=decorators))
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
        if not seen:
            return self._memo("symbol:" + name, lambda: self._symbol(name, frozenset({""})))
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
        for reference in values:
            if reference.kind == "symbol":
                break
        else:
            return values
        return frozenset(value for reference in values for value in (
            self._symbol(reference.name) if reference.kind == "symbol" else (reference,)
        ))

    def _annotation(self, node: ast.expr | None, scope: _Scope) -> Values:
        if node is None:
            return frozenset()
        return self._memo(f"annotation:{id(node)}", lambda: self._annotation_of(node, scope))

    def _annotation_of(self, node: ast.expr, scope: _Scope) -> Values:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                try:
                    forward = ast.parse(node.value, mode="eval").body
                except SyntaxError:
                    return frozenset()
                # A forward reference keeps its constant's position, so two
                # quoted annotations in one scope allocate distinct containers.
                for child in ast.walk(forward):
                    if isinstance(child, (ast.expr, ast.stmt)):
                        child.lineno = node.lineno
                        child.col_offset += node.col_offset + 1
                return self._annotation(forward, scope)
            return frozenset({Reference("instance", "builtins.NoneType")})
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self._annotation(node.left, scope) | self._annotation(node.right, scope)
        if isinstance(node, ast.Subscript):
            return self._subscripted_annotation(node, scope)
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
            if reference.name == "typing.Self" and scope.owner:
                result.add(Reference("instance", scope.owner))
                continue
            # policy-inventory-exempt: mechanism-internal; reason=abstract typing forms do not identify a concrete receiver class; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._annotation
            if reference.name in {"typing.Any", "typing.Self", "typing.Callable", "collections.abc.Callable",
                                  "typing.Final", "typing.ClassVar", "typing.Annotated"}:
                continue
            # policy-inventory-exempt: mechanism-internal; reason=these reference variants carry a class identity usable as an annotation; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._annotation
            if reference.kind in {"class", "external", "instance"}:
                result.add(Reference("instance", reference.name))
        return frozenset(result)

    def _subscripted_annotation(self, node: ast.Subscript, scope: _Scope) -> Values:
        """Keep the declared element, key, position or class structure of a generic."""
        names = {reference.name for reference in self._annotation_symbols(node.value, scope)}
        arguments = list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
        # These qualifiers describe a binding, not a runtime receiver.
        # https://docs.python.org/3.14/library/typing.html#typing.Final
        if names.intersection(
            {"typing.Final", "typing.ClassVar", "typing.Annotated"}
        ):
            return self._annotation(arguments[0], scope)
        if names.intersection(
            {"typing.Optional", "typing.Union"}
        ):
            values = frozenset().union(*(self._annotation(argument, scope) for argument in arguments))
            return values | frozenset({Reference("instance", "builtins.NoneType")}) if "typing.Optional" in names else values
        if "typing.Literal" in names:
            literals: set[Reference] = set()
            for argument in arguments:
                if isinstance(argument, ast.Constant):
                    literals.add(Reference("instance", "builtins." + type(argument.value).__name__,
                                           literal=argument.value if isinstance(argument.value, str) else None))
                else:
                    literals.update(self._annotation(argument, scope))
            return frozenset(literals)
        shapes = {found for name in names if (found := _shape(name)) is not None}
        if len(shapes) != 1:
            return self._annotation(node.value, scope)
        shape, receiver = next(iter(shapes))
        if shape == "class":
            return frozenset(Reference("class" if value.name in self.classes else "external", value.name)
                             for value in self._annotation(arguments[0], scope))
        if shape == "awaited":
            return self._annotation(arguments[-1], scope)
        elements = [self._annotation(argument, scope) for argument in arguments]
        if shape == "dict":
            return self._container(node, receiver, elements[1:2], keys=elements[0], owner=scope.name)
        if shape == "tuple" and not (len(arguments) == 2 and isinstance(arguments[1], ast.Constant)
                                     and arguments[1].value is Ellipsis):
            return self._container(node, receiver, elements, positions=True, owner=scope.name)
        return self._container(node, receiver, elements[:1], owner=scope.name)

    def _annotation_symbols(self, node: ast.expr, scope: _Scope) -> Values:
        if isinstance(node, ast.Name):
            references = self._references(self._get(self._slot(scope, node.id)))
            if not references and hasattr(builtins, node.id):
                references = frozenset({Reference("external", "builtins." + node.id)})
            return references
        if isinstance(node, ast.Attribute):
            return self._attribute(self._annotation_symbols(node.value, scope), node.attr, None)
        return frozenset()

    def _declared_values(self, values: Values, annotation: ast.expr | None, scope: _Scope) -> Values:
        """Apply a declaration the type checker verified to source values.

        A value of unknown structure (an opaque result, an external value,
        the object placeholder) becomes the declared one. A source value the
        declaration cannot admit does not escape: `runtime() -> Runtime`
        returns the module's `Runtime | None` state, and mypy, a gate lane
        here, has checked that the None arm cannot. What the analysis cannot
        classify is kept, and a declaration naming nothing concrete leaves
        every value alone.
        """
        declared = self._annotation(annotation, scope)
        if not declared:
            return values
        admitted = {reference.receiver if reference.kind == "container" else reference.name for reference in declared}

        concrete = self._contract_free(declared)

        def refined(reference: Reference) -> Values:
            # policy-inventory-exempt: mechanism-internal; reason=a declaration refines a value whose structure the source does not give; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._declared_values
            if reference.kind in {"opaque", "external"} or (
                reference.kind == "instance" and reference.name == "builtins.object"
            ):
                return declared
            # policy-inventory-exempt: mechanism-internal; reason=a caller's supplied or unknown value reaches a concrete declaration as that class; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._declared_values
            if reference.kind in {"parameter", "unknown"} and concrete:
                # A caller's own value reaches a parameter declared as a
                # concrete class as that class: the callee may rely on what
                # it declared, and the caller's re-entrancy or undeclared
                # read is recorded at the caller's own site.
                return concrete
            name = reference.receiver if reference.kind == "container" else reference.name
            # policy-inventory-exempt: mechanism-internal; reason=these two reference variants carry a class identity a declaration can refuse; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._declared_values
            if reference.kind in {"instance", "container"} and (name in self.classes or _stdlib_object(name) is not None):
                return frozenset({reference}) if any(self._admits(base, name) for base in admitted) else frozenset()
            return frozenset({reference})

        refinement = frozenset().union(*(refined(reference) for reference in values)) if values else frozenset()
        return refinement or values

    def _admits(self, declared: str, name: str) -> bool:
        """Whether a declared class admits instances of a source or stdlib class."""
        if name in self.classes or declared in self.classes:
            return declared in self._bases(name)
        kind, wanted = _stdlib_object(name), _stdlib_object(declared)
        return isinstance(kind, type) and isinstance(wanted, type) and issubclass(kind, wanted)

    def _declarations(self, scope: _Scope, parameter: ast.arg) -> list[ast.expr | None]:
        """The annotations callers see for a parameter.

        With overloads those are the overloads' alone: the implementation's
        signature is not visible to a caller, and it is where a union widens
        to Any. https://typing.python.org/en/latest/spec/overload.html
        """
        signatures = self.overloads.get(scope.name)
        if not signatures:
            return [parameter.annotation]
        return [other.annotation for signature in signatures for other in
                (*signature.posonlyargs, *signature.args, *signature.kwonlyargs,
                 *([signature.vararg] if signature.vararg else []),
                 *([signature.kwarg] if signature.kwarg else []))
                if other.arg == parameter.arg]

    def _returns(self, scope: _Scope) -> list[ast.expr | None]:
        """The return annotations callers see: the overloads', or the body's own."""
        signatures = self.overload_returns.get(scope.name)
        return list(signatures) if signatures else [getattr(scope.node, "returns", None)]

    def _unstructured(self, node: ast.expr | None, scope: _Scope) -> bool:
        """Whether a declaration admits a value of unknown structure."""
        if node is None:
            return False
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                return self._unstructured(ast.parse(node.value, mode="eval").body, scope)
            except SyntaxError:
                return False
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self._unstructured(node.left, scope) or self._unstructured(node.right, scope)
        if isinstance(node, ast.Subscript):
            names = {reference.name for reference in self._annotation_symbols(node.value, scope)}
            if names.intersection(
                {"typing.Optional", "typing.Union", "typing.Final", "typing.Annotated", "typing.ClassVar"}
            ):
                arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
                return any(self._unstructured(argument, scope) for argument in arguments[:1 if "typing.Annotated" in names else None])
            return False
        return bool({"typing.Any", "builtins.object"}.intersection(
            reference.name for reference in self._annotation_symbols(node, scope)))

    def _parameter_contract(self, node: ast.expr | None, scope: _Scope) -> frozenset[str]:
        """Read a caller-implemented contract from an entry's own annotation."""
        if node is None:
            return frozenset()
        return self._memo(f"contract:{id(node)}", lambda: self._parameter_contract_of(node, scope))

    def _parameter_contract_of(self, node: ast.expr, scope: _Scope) -> frozenset[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                return self._parameter_contract(ast.parse(node.value, mode="eval").body, scope)
            except SyntaxError:
                return frozenset()
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self._parameter_contract(node.left, scope) | self._parameter_contract(node.right, scope)
        if isinstance(node, ast.Subscript):
            names = {reference.name for reference in self._annotation_symbols(node.value, scope)}
            if names.intersection(
                {"typing.Optional", "typing.Union", "typing.Final", "typing.Annotated"}
            ):
                arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
                if "typing.Annotated" in names:
                    arguments = arguments[:1]
                return frozenset().union(*(self._parameter_contract(argument, scope) for argument in arguments))
            return self._parameter_contract(node.value, scope)
        operations: set[str] = set()
        for reference in self._annotation_symbols(node, scope):
            module, _, name = reference.name.rpartition(".")
            # policy-inventory-exempt: mechanism-internal; reason=these standard protocols declare behavior implemented by the caller; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._parameter_contract
            if module in {"typing", "collections.abc"} and name in {
                "Callable", "Iterable", "Iterator", "AsyncIterable", "AsyncIterator",
            }:
                protocol = getattr(collections.abc, name)
                operations.update(member for base in protocol.__mro__ if base is not object
                                  for member, value in vars(base).items() if callable(value))
            bases = self._bases(reference.name)
            if {"typing.Protocol", "typing_extensions.Protocol"}.intersection(bases):
                operations.update(member for base in bases if base in self.classes
                                  for member in self.scopes[base].locals
                                  if base + "." + member in self.functions)
        return frozenset(operations)

    def _bases(self, name: str, seen: frozenset[str] = frozenset()) -> tuple[str, ...]:
        if name in seen or name not in self.classes:
            return (name,)
        if not seen:
            return self._memo("bases:" + name, lambda: self._indexed_bases(name))
        scope = self.scopes[name]
        assert isinstance(scope.node, ast.ClassDef)  # nosec B101 # _bases only receives indexed class scopes
        assert scope.parent is not None  # nosec B101 # every indexed class has an enclosing scope
        # A generic base names its class: list[Any] is list.
        bases = [reference.name
                 for node in (base.value if isinstance(base, ast.Subscript) else base for base in scope.node.bases)
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

    def _indexed_bases(self, name: str) -> tuple[str, ...]:
        """Compute a class's MRO and record it under each base it contains."""
        result = self._bases(name, frozenset({""}))
        for base in result:
            self.subclasses[base].add(name)
        return result

    def _attribute(self, values: Values, member: str, node: ast.AST | None) -> Values:
        result: set[Reference] = set()
        for reference in self._references(values):
            if reference.kind == "module":
                result.update(self._symbol(reference.name + "." + member))
            elif reference.kind == "function":
                declared = self._get((reference.name, member))
                if declared:
                    result.update(declared)
                elif member == "__call__":
                    result.add(reference)
                elif self._reporting:
                    result.add(Reference("instance", "builtins.object"))
            elif reference.kind == "external":
                # A name outside the analysed tree extends through modules,
                # classes and builtin type members. One member that exists on
                # any other real stdlib object is a known operation on that
                # value. Every further attribute, and any attribute that does
                # not exist, is a value of unknown structure, member "*",
                # which stays itself under access and is open when called.
                # The universe is finite: names, one member, or "*".
                builtin = getattr(builtins, reference.name.removeprefix("builtins."), None)
                stdlib = _stdlib_object(reference.name)
                if reference.member == "*":
                    result.add(reference)
                elif reference.member:
                    result.add(Reference("external", reference.name, member="*"))
                elif node is None or reference.name in self.module_prefixes or isinstance(
                    stdlib, (type, types.ModuleType)
                ) or (isinstance(builtin, type) and hasattr(builtin, member)):
                    result.add(Reference("external", reference.name + "." + member))
                elif stdlib is not None and hasattr(stdlib, member):
                    result.add(Reference("external", reference.name, member=member))
                else:
                    result.add(Reference("external", reference.name, member="*"))
            elif reference.kind == "class" and member == "__dict__" and reference.name in self.classes:
                result.add(Reference("namespace", reference.name))
            # policy-inventory-exempt: mechanism-internal; reason=class and instance references resolve members through the MRO; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._class_attribute
            elif reference.kind in {"class", "instance"}:
                self._class_attribute(reference, member, node, result)
            elif reference.kind == "namespace":
                # policy-inventory-exempt: mechanism-internal; reason=a class namespace reads a member through these two mapping operations; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._attribute
                if member in {"__getitem__", "get"}:
                    result.add(Reference("namespace_item", reference.name))
                elif self._reporting:
                    result.add(Reference("unknown", f"class namespace {reference.name}.{member}"))
            elif reference.kind == "slot":
                # A __slots__ member descriptor: its __set__ and __get__ reach
                # the instance field the declaration names.
                # https://docs.python.org/3.14/reference/datamodel.html#slots
                # policy-inventory-exempt: mechanism-internal; reason=the descriptor protocol's own write and read for a slot member; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._attribute
                if member in {"__set__", "__get__"}:
                    result.add(Reference("slot_" + member.strip("_"), reference.name, member=reference.member))
                elif self._reporting:
                    result.add(Reference("unknown", f"slot descriptor {reference.name}.{reference.member}.{member}"))
            elif reference.kind == "generator":
                result.add(Reference("function", reference.name))
            elif reference.kind == "container":
                if hasattr(_stdlib_object(reference.receiver), member):
                    result.add(Reference("container_method", member, reference.name))
                elif self._reporting:
                    result.add(Reference("unknown", reference.receiver + "." + member))
            elif reference.kind == "parameter":
                if member in reference.operations:
                    result.add(Reference("parameter", reference.name, reference.receiver, member,
                                         reference.operations))
                elif reference.operations:
                    # The defect is the read itself, recorded where it happens,
                    # so a callee that declares its parameter is not charged
                    # with what its caller read off a contract.
                    reason = f"undeclared member {reference.name}.{member}"
                    if node is not None and self._reporting:
                        self.open.add(self._where(node, reason))
                    result.add(Reference("unknown", reason))
                else:
                    # A value the contract produced declares nothing, so every
                    # member of it is the caller's too. One derived value per
                    # parameter, so the domain stays finite however deep the
                    # chain of members and calls goes.
                    result.add(reference)
            # policy-inventory-exempt: mechanism-internal; reason=these two reference variants carry no callable identity of their own; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._attribute
            elif reference.kind in {"unknown", "opaque", "unreachable"}:
                result.add(reference)
            else:
                result.add(Reference("instance", "builtins.object"))
        return frozenset(result)

    def _class_attribute(self, reference: Reference, member: str, node: ast.AST | None, result: set[Reference]) -> None:
        """Resolve the first MRO member and apply Python's descriptor binding."""
        bases = self._bases(reference.name)
        # A method of a base runs on instances of its subclasses too, so a
        # field one of them assigned is a value this receiver can hold.
        holders = (*bases, *self._descendants(reference.name)) if reference.kind == "instance" else ()
        fields = frozenset().union(*(self._get((base, f"<field:{member}>")) for base in holders)) \
            if holders else frozenset()
        for base in bases:
            initializer = base + ".__init__"
            if initializer in self.functions and initializer not in self.facts:
                self._schedule(initializer)
            members = self._references(self._get((base, member)))
            if not members:
                if base not in self.classes:
                    if fields:
                        result.update(fields)
                        return
                    if (base in _INHERITED_STORAGE and node is not None and reference.kind == "instance"
                            and member != "__init__"):
                        # The inherited container operates on what it stores;
                        # construction is what stores it.
                        stored = frozenset().union(*(self._get((holder, f"<field:{_INHERITED_STORAGE[base]}>"))
                                                     for holder in holders))
                        if stored:
                            result.update(self._attribute(stored, member, node))
                            return
                    builtin = getattr(builtins, base.removeprefix("builtins."), None)
                    if (base.startswith("builtins.") and hasattr(builtin, member)) or (
                        base.split(".", 1)[0] in sys.stdlib_module_names
                        and not base.startswith(("builtins.", "collections.abc.", "typing.", "contextlib.Abstract"))
                    ):
                        result.add(Reference("external", base + "." + member))
                        return
                    if self._reporting:
                        result.add(Reference("unknown", base + "." + member))
                        return
                continue
            for value in members:
                descriptor = value.kind == "instance" and self._has_method(value, "__get__")
                data = descriptor and (self._has_method(value, "__set__") or self._has_method(value, "__delete__"))
                decorators = self.scopes[value.name].decorators if value.kind == "function" else frozenset()
                property_ = "property" in decorators
                # A function or descriptor held on the instance is data. Only
                # class descriptors bind, with data descriptors taking priority.
                # https://docs.python.org/3.14/howto/descriptor.html#invocation-from-an-instance
                if fields and not data and not property_:
                    result.update(fields)
                    continue
                if descriptor:
                    if node is not None:
                        receiver = reference if reference.kind == "instance" else Reference("instance", "builtins.NoneType")
                        result.update(self._call(
                            self._attribute(frozenset({value}), "__get__", node),
                            [frozenset({receiver}), frozenset({Reference("class", reference.name)})], {}, node,
                        ))
                    continue
                if value.kind != "function" or reference.kind != "instance":
                    result.add(value)
                    continue
                if property_:
                    if node is not None:
                        result.update(self._call(frozenset({Reference("bound", value.name, reference.name)}), [], {}, node))
                elif "staticmethod" in decorators:
                    result.add(value)
                else:
                    result.add(Reference("bound", value.name, reference.name))
            return
        if fields:
            result.update(fields)
            return
        if self._reporting and not any(value.name.startswith(reference.name) for value in result):
            result.add(Reference("unknown", f"attribute on {reference.name}"))

    def _slots(self, name: str) -> frozenset[str]:
        """The member names a class body declares in __slots__, a sequence or a documenting mapping."""
        return frozenset(
            item.literal for container in self._get((name, "__slots__")) if container.kind == "container"
            for item in self._get((container.name, "<keys>" if _mapping(container.receiver) else "<items>"))
            if item.literal is not None
        )

    def _descendants(self, name: str) -> tuple[str, ...]:
        """Every indexed class whose MRO has been seen to contain this one.

        Read from the reverse index _bases maintains rather than by walking
        every class, whose own bases resolve through the store: that walk
        depended on every base declaration in the tree and recursed through
        the attribute lookups those declarations need.
        """
        return tuple(self.subclasses.get(name, ()))

    def _has_method(self, reference: Reference, member: str) -> bool:
        """Whether an indexed class declares this protocol in its MRO."""
        return any(self._get((base, member)) for base in self._bases(reference.name)
                   if base in self.classes)

    def _provides(self, name: str, member: str) -> bool:
        """Whether instances of a source or standard-library class have this member."""
        if name in self.classes:
            return self._has_method(Reference("class", name), member)
        return member in _members(name)

    def _contract_free(self, values: Values) -> Values:
        """Drop protocol instances: a contract reference already stands for them."""
        return frozenset(value for value in values if not (
            value.kind == "instance" and value.name in self.classes
            and {"typing.Protocol", "typing_extensions.Protocol"}.intersection(self._bases(value.name))
        ))

    def _store(self, receivers: Values, member: str, values: Values, node: ast.AST) -> None:
        """Keep a container of the elements an inherited base stores for its instances."""
        self._set_attribute(receivers, member, self._container(
            node, "list", (self._protocol(values, "__iter__", node),)), node, base=True)

    def _set_attribute(self, receivers: Values, member: str, values: Values, node: ast.AST,
                       *, base: bool = False) -> None:
        """Follow a declared setter, or retain an ordinary instance field."""
        for receiver in self._references(receivers):
            # policy-inventory-exempt: mechanism-internal; reason=module and function namespaces hold plain attributes, not instance fields; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._set_attribute
            if receiver.kind in {"module", "function"}:
                self._put((receiver.name, member), values)
                continue
            # policy-inventory-exempt: mechanism-internal; reason=only class and instance references own indexed attribute assignments; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._set_attribute
            if receiver.kind not in {"class", "instance"} or receiver.name not in self.classes:
                if self._reporting and receiver.kind != "unreachable":
                    self.open.add(self._where(node, "unresolved attribute receiver"))
                continue
            if receiver.kind == "instance" and not base and self._has_method(receiver, "__setattr__"):
                self._call(self._attribute(frozenset({receiver}), "__setattr__", node),
                           [frozenset({Reference("instance", "builtins.str", literal=member)}), values], {}, node)
                continue
            setters: set[Reference] = set()
            for owner in self._bases(receiver.name):
                members = self._references(self._get((owner, member)))
                if members:
                    for descriptor in members:
                        if descriptor.kind == "instance" and self._has_method(descriptor, "__set__"):
                            setters.update(self._attribute(frozenset({descriptor}), "__set__", node))
                    break
            if receiver.kind == "instance" and setters:
                self._call(frozenset(setters), [frozenset({receiver}), values], {}, node)
            else:
                slot = f"<field:{member}>" if receiver.kind == "instance" else member
                self._put((receiver.name, slot), values)

    def _where(self, node: ast.AST, reason: str) -> str:
        cached = self.unparsed.get(id(node))
        if cached is None or cached[0] is not node:
            cached = self.unparsed[id(node)] = node, ast.unparse(node)
        return f"{self.current}:{getattr(node, 'lineno', 0)}: {reason} ({cached[1]})"

    def _key(self, node: ast.AST | None) -> str:
        """Join equal literal keys using Python's own mapping equality."""
        if node is None:
            return "<unknown-items>"
        cached = self.literal_keys.get(id(node))
        if cached is None or cached[0] is not node:
            try:
                index = self.container_keys.setdefault(ast.literal_eval(node), len(self.container_keys))
                key = f"<key:{index}>"
            except (ValueError, TypeError):
                key = "<unknown-items>"
            cached = self.literal_keys[id(node)] = node, key
        return cached[1]

    def _container(self, node: ast.AST, kind: str, elements: Iterable[Values] = (),
                   *, keys: Values = frozenset(), positions: bool = False, owner: str | None = None) -> Values:
        """Keep one finite allocation site and the values that can flow into it.

        `kind` is the value's own type: a bare builtin name for a source
        literal, or a qualified name for a declared one, whose members then
        decide which operations the value admits.
        """
        # PyCG keeps container allocations and content pointers in its assignment graph:
        # https://github.com/vitsalis/PyCG/blob/8d5dc40837803beef1d8d379fbf2cdad6cd94641/pycg/processing/postprocessor.py
        owner = self.current if owner is None else owner
        receiver = kind if "." in kind else "builtins." + kind
        name = f"{owner}.<container@{getattr(node, 'lineno', 0)}:{getattr(node, 'col_offset', 0)}:{receiver}>"
        reference = Reference("container", name, receiver)
        self.containers[name] = reference
        if positions:
            self.positioned.add(name)
        elements = tuple(elements)
        for index, values in enumerate(elements):
            self._put((name, "<items>"), values)
            if positions:
                self._put((name, str(index)), values)
                for offset in (index, index - len(elements)):
                    self._put((name, f"<key:{self.container_keys.setdefault(offset, len(self.container_keys))}>"), values)
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
        stored = keys if _mapping(container.receiver) else items
        if method == "__iter__":
            # iter(x) answers an ITERATOR over the elements, which is what a
            # source __iter__ returns too, so both paths unwrap alike.
            return self._container(node, "collections.abc.Iterator", (stored,))
        if method == "__next__":
            return stored
        key = self._key(node.slice if isinstance(node, ast.Subscript) else
                        node.args[0] if isinstance(node, ast.Call) and node.args else None)
        selected = items if key == "<unknown-items>" else self._get((name, key)) | self._get((name, "<unknown-items>"))
        # policy-inventory-exempt: mechanism-internal; reason=these builtin methods read a stored element; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"__getitem__", "pop"}:
            if method == "pop" and not _mapping(container.receiver):
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
        if method in {"append", "add", "insert", "set", "__setitem__"}:
            # policy-inventory-exempt: mechanism-internal; reason=these two builtin mutations name their position in the second argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
            index = int(method in {"insert", "__setitem__"})
            if len(positional) > index:
                self._put((name, "<items>"), positional[index])
                self._put((name, key if method == "__setitem__" and _mapping(container.receiver)
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
                    if _mapping(container.receiver) and value.kind == "container" and _mapping(value.receiver):
                        self._put((name, "<items>"), self._get((value.name, "<items>")))
                        self._put((name, "<unknown-items>"), self._get((value.name, "<items>")))
                        self._put((name, "<keys>"), self._get((value.name, "<keys>")))
                    else:
                        values = self._protocol(frozenset({value}), "__iter__", node)
                        if _mapping(container.receiver):
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
            return self._container(node, container.receiver, (items,), keys=keys)
        # Removing or reordering values cannot remove a possible call from a
        # flow-insensitive graph. sort still invokes its declared key function.
        # policy-inventory-exempt: mechanism-internal; reason=these builtin mutations add no elements but sort invokes its key callback; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._container_call
        if method in {"clear", "remove", "discard", "reverse", "sort", "reset", "__delitem__"}:
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

    def _forwarder(self, scope: _Scope) -> tuple[str, tuple[int, ...]] | None:
        """The attribute intrinsic a body only forwards its parameters to."""
        if scope.name not in self.forwarders:
            self.forwarders[scope.name] = None
            statements = [statement for statement in scope.statements
                          if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant))]
            parameters = [parameter.arg for parameter in scope.parameters]
            call = statements[0].value if len(statements) == 1 and isinstance(statements[0], (ast.Expr, ast.Return)) else None
            root = call.func if isinstance(call, ast.Call) else None
            while isinstance(root, ast.Attribute):
                root = root.value
            names = [argument.id for argument in call.args if isinstance(argument, ast.Name)] if isinstance(call, ast.Call) else []
            if (isinstance(call, ast.Call) and isinstance(root, ast.Name) and root.id not in parameters
                    and not call.keywords and len(names) == len(call.args)
                    and all(name in parameters for name in names)):
                self.forwarders[scope.name] = call.func, tuple(parameters.index(name) for name in names)
        shape = self.forwarders[scope.name]
        if shape is None:
            return None
        callee, indices = shape
        resolved = {reference.name for reference in self._value(callee, scope)}
        if len(resolved) != 1 or not resolved <= _ATTRIBUTE_INTRINSICS:
            return None
        return next(iter(resolved)), indices

    def _bind(self, name: str, scope: _Scope, arguments: list[Values],
              keywords: dict[str, Values], node: ast.AST) -> None:
        """Bind actual arguments to their parameters, as Python's call does.

        The positional parameters take the leading actuals; a *args parameter
        is the TUPLE of the rest and a **kwargs parameter the DICT of the
        keywords no parameter names, rather than each extra actual joined
        into the parameter itself.
        https://docs.python.org/3.14/reference/expressions.html#calls
        """
        signature = scope.arguments
        assert signature is not None  # nosec B101 # only a callable scope is called
        positional = [*signature.posonlyargs, *signature.args]
        annotations = {parameter.arg: parameter.annotation for parameter in scope.parameters}
        for parameter, actual in zip(positional, arguments, strict=False):
            self._put((name, parameter.arg), self._declared_values(actual, parameter.annotation, scope))
        for parameter_name, actual in keywords.items():
            # policy-inventory-exempt: mechanism-internal; reason=a variadic parameter is bound as a whole, never by a caller's keyword; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._bind
            if parameter_name in annotations and parameter_name not in {
                getattr(signature.vararg, "arg", None), getattr(signature.kwarg, "arg", None)}:
                self._put((name, parameter_name), self._declared_values(actual, annotations[parameter_name], scope))
        if signature.vararg is not None:
            extra = [self._declared_values(actual, signature.vararg.annotation, scope)
                     for actual in arguments[len(positional):]]
            self._put((name, signature.vararg.arg), self._container(node, "tuple", extra, positions=True))
        if signature.kwarg is not None:
            rest = [self._declared_values(actual, signature.kwarg.annotation, scope)
                    for parameter_name, actual in keywords.items() if parameter_name not in annotations]
            self._put((name, signature.kwarg.arg), self._container(
                node, "dict", rest, keys=frozenset({Reference("instance", "builtins.str")})))

    def _protocol(self, values: Values, name: str, node: ast.AST) -> Values:
        yielded: set[Reference] = set()
        for reference in values:
            if reference.kind == "generator":
                self.targets.add(reference.name)
                yielded.update(self._get((reference.name, "<yield>")))
        concrete = frozenset(reference for reference in values
                             if reference.kind != "generator" and (reference.kind != "instance" or not reference.name.startswith("builtins.")))
        # Bottom means no fact yet. It must not become an object that survives
        # after a generator's actual yielded receivers arrive at the fixed point.
        if any(reference.kind == "instance" and reference.name.startswith("builtins.") for reference in values):
            yielded.add(Reference("instance", "builtins.object"))
        if concrete:
            answered = self._call(self._attribute(concrete, name, node), [], {}, node)
            # policy-inventory-exempt: mechanism-internal; reason=these two protocols answer an iterator whose elements are what a loop binds; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._protocol
            if name in {"__iter__", "__aiter__"}:
                answered = frozenset(value for reference in answered for value in (
                    self._get((reference.name, "<items>")) | self._get((reference.name, "<unknown-items>"))
                    if reference.kind == "container" else (reference,)
                ))
            yielded.update(answered)
        return frozenset(yielded)

    def _external_call(self, reference: Reference, positional: list[Values],
                       keywords: dict[str, Values], node: ast.AST) -> Values:
        """Judge a call on a value outside the analysed tree by what it names."""
        result: set[Reference] = set()
        name = reference.name + ("." + reference.member if reference.member else "")
        root = name.split(".")[0]
        owner, _, member = name.rpartition(".")
        if member == "__init__" and owner in _INHERITED_STORAGE and positional:
            # super().__init__(items) inside the subclass's own method.
            self._store(self._get((self.current, "self")), _INHERITED_STORAGE[owner], positional[0], node)
        if reference.member == "*":
            # A member no standard-library type declares was written
            # by something else, so what it holds is unknown.
            reason = self._where(node, f"external value {name}")
            self.open.add(reason)
            return frozenset({Reference("unknown", reason)})
        if root == "janus_swi":
            self.native.add(self._where(node, name))
        elif root not in sys.stdlib_module_names and root != "builtins":
            self.open.add(self._where(node, f"external call {name}"))
        # policy-inventory-exempt: mechanism-internal; reason=builtin container constructors retain the elements supplied by their input iterable; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._external_call
        if name in {"builtins.list", "builtins.tuple", "builtins.set", "builtins.frozenset", "builtins.dict"}:
            kind = name.removeprefix("builtins.")
            container = self._container(node, kind)
            if kind == "dict":
                self._call(self._attribute(container, "update", node), positional, keywords, node)
            elif positional:
                items = self._protocol(positional[0], "__iter__", node)
                container = self._container(node, kind, (items,))
            return container
        # type(x) answers the class of x; type(name, bases, namespace) makes a
        # class whose members resolve through the bases it is given.
        # https://docs.python.org/3.14/library/functions.html#type
        if name == "builtins.type" and positional:
            if len(positional) == 1:
                return frozenset(
                    Reference("class", reference.name) if reference.kind == "instance" else reference
                    for reference in positional[0])
            return frozenset(reference for base in positional[1]
                             for reference in (self._get((base.name, "<items>")) if base.kind == "container" else (base,)))
        # policy-inventory-exempt: mechanism-internal; reason=typing identity helpers return their second argument unchanged; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._external_call
        if name in {"typing.cast", "typing.assert_type"} and len(positional) > 1:
            result.update(positional[1])
        # policy-inventory-exempt: mechanism-internal; reason=ordinary and deferred module loaders resolve the literal module argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._external_call
        elif name in {"importlib.import_module", "metta._lazy.lazy"}:
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                result.update(self._symbol(node.args[0].value))
        # policy-inventory-exempt: mechanism-internal; reason=both attribute helpers access the member named by their second argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._external_call
        elif name in {"builtins.getattr", "builtins.hasattr", "builtins.object.__getattribute__",
                      "builtins.setattr", "builtins.object.__setattr__"} and len(positional) > 1:
            names = {value.literal for value in positional[1] if value.literal is not None}
            for member in names:
                # policy-inventory-exempt: mechanism-internal; reason=these two attribute helpers write the member named by their second argument; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._external_call
                if name in {"builtins.setattr", "builtins.object.__setattr__"} and len(positional) > 2:
                    self._set_attribute(positional[0], member, positional[2], node,
                                        base=name == "builtins.object.__setattr__")
                    result.add(Reference("instance", "builtins.NoneType"))
                else:
                    result.update(self._attribute(positional[0], member, node))
                    # getattr(x, "y", default) answers the default when the
                    # member is absent.
                    if name == "builtins.getattr" and len(positional) > 2:
                        result.update(positional[2])
            if any(value.literal is None for value in positional[1]):
                reason = self._where(node, "dynamic attribute")
                self.open.add(reason)
                result.add(Reference("unknown", reason))
        # policy-inventory-exempt: mechanism-internal; reason=iter and next carry the iterated elements through the container model; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._external_call
        elif name in {"builtins.iter", "builtins.next"} and positional:
            if name == "builtins.iter":
                result.update(self._container(node, "collections.abc.Iterator",
                                              (self._protocol(positional[0], "__iter__", node),)))
            else:
                result.update(self._protocol(positional[0], "__next__", node))
                result.update(positional[1] if len(positional) > 1 else frozenset())
        else:
            # A standard-library call invokes exactly the arguments
            # typeshed declares Callable, read from the shipped table
            # rather than listed by hand, so sorted(key=) and
            # atexit.register run their callback and callable() does not.
            protocols = {"builtins.len": "__len__", "builtins.bool": "__bool__",
                         "builtins.list": "__iter__", "builtins.tuple": "__iter__",
                         "builtins.set": "__iter__", "builtins.sorted": "__iter__"}
            if name in protocols and positional:
                self._protocol(positional[0], protocols[name], node)
            positions, invoked = INVOCATIONS.get(name, (frozenset(), frozenset()))
            for argument in (*(positional[index] for index in positions if index < len(positional)),
                             *(keywords[parameter] for parameter in invoked if parameter in keywords)):
                self._call(argument, [], {}, node)
            target = getattr(builtins, name.removeprefix("builtins."), None) if root == "builtins" else None
            if isinstance(target, type):
                result.add(Reference("instance", name))
            else:
                result.add(Reference("opaque", "result of " + name))
        return frozenset(result)

    def _call(self, values: Values, positional: list[Values], keywords: dict[str, Values], node: ast.AST) -> Values:
        result: set[Reference] = set()
        references = self._references(values)
        if not references and self._reporting:
            self.open.add(self._where(node, "unresolved call target"))
        for reference in references:
            if reference.kind == "unreachable":
                continue
            if reference.kind == "parameter":
                reason = reference.name + ("." + reference.member if reference.member else "")
                site = self._where(node, reason)
                self.open.add(site)
                if reference.member or "__call__" in reference.operations:
                    self.contracts.add(ContractCall(site, reference.name, reference.receiver))
                # What a supplied value answers is supplied too, so it carries
                # the same contract rather than becoming a separate defect.
                result.add(Reference("parameter", reference.name, reference.receiver, "*"))
                continue
            if reference.kind == "container_method":
                result.update(self._container_call(reference, positional, keywords, node))
                continue
            if reference.kind == "namespace_item":
                key = node.slice if isinstance(node, ast.Subscript) else node.args[0] if isinstance(node, ast.Call) and node.args else None
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    if key.value in self._slots(reference.name):
                        result.add(Reference("slot", reference.name, member=key.value))
                    else:
                        result.update(self._references(self._get((reference.name, key.value))))
                else:
                    reason = self._where(node, "dynamic attribute")
                    self.open.add(reason)
                    result.add(Reference("unknown", reason))
                continue
            if reference.kind == "slot_set":
                if len(positional) > 1:
                    self._set_attribute(positional[0], reference.member, positional[1], node, base=True)
                result.add(Reference("instance", "builtins.NoneType"))
                continue
            if reference.kind == "slot_get":
                if positional:
                    result.update(self._attribute(positional[0], reference.member, node))
                continue
            if reference.kind == "class":
                instance = Reference("instance", reference.name)
                result.add(instance)
                constructors = self._attribute(frozenset({instance}), "__init__", node)
                self._call(constructors, positional, keywords, node)
                storage = next((_INHERITED_STORAGE[base] for base in self._bases(reference.name)
                                if base in _INHERITED_STORAGE), None)
                if storage is not None and positional:
                    self._store(frozenset({instance}), storage, positional[0], node)
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
                signature = scope.arguments
                forwarded = (self._forwarder(scope) if name not in self.forwarding
                             and signature is not None and not (signature.vararg or signature.kwarg) else None)
                if forwarded is not None:
                    intrinsic, indices = forwarded
                    parameters = [parameter.arg for parameter in scope.parameters]
                    supplied = [arguments[index] if index < len(arguments)
                                else keywords.get(parameters[index], frozenset()) for index in indices]
                    self.forwarding.add(name)
                    try:
                        result.update(self._call(frozenset({Reference("external", intrinsic)}), supplied, {}, node))
                    finally:
                        self.forwarding.discard(name)
                    continue
                self._bind(name, scope, arguments, keywords, node)
                native = name.startswith(("metta._binding.runtime.Runtime.", "metta._binding.runtime.JanusBridge."))
                abstract = any(isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                               and statement.value.value is Ellipsis for statement in scope.statements)
                if native:
                    self.native.add(self._where(node, name))
                elif abstract:
                    self.open.add(self._where(node, f"abstract or external body {name}"))
                else:
                    self.targets.add(name)
                    if name not in self.facts:
                        self._schedule(name)
                if name in self.generators:
                    result.add(Reference("generator", name))
                else:
                    returned = self._get((name, "<return>"))
                    declared = self._returns(scope)
                    result.update(frozenset().union(*(self._annotation(node_, scope) for node_ in declared))
                                  if native or abstract
                                  else frozenset().union(*(self._declared_values(returned, node_, scope)
                                                           for node_ in declared)))
                continue
            if reference.kind == "external":
                result.update(self._external_call(reference, positional, keywords, node))
                continue
            if reference.kind == "opaque":
                # A value the standard library made, of a type this analysis
                # does not model. Nothing from the analysed tree reached it
                # except its own arguments, which are invoked above, so
                # operating on it is host work rather than an open boundary.
                result.add(reference)
            elif reference.kind == "unknown":
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
            return frozenset({Reference("instance", "builtins." + type(node.value).__name__,
                                        literal=node.value if isinstance(node.value, str) else None)})
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
            self._set_attribute(self._value(node.value, scope), node.attr, values, node)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for index, element in enumerate(node.elts):
                members = frozenset(value for reference in values for value in (
                    (self._get((reference.name, str(index) if reference.name in self.positioned else "<items>"))
                     | self._get((reference.name, "<unknown-items>")))
                    if reference.kind == "container" else self._protocol(frozenset({reference}), "__iter__", node)
                ))
                self._assign(element, members, scope)
        elif isinstance(node, ast.Subscript):
            self._call(self._attribute(self._value(node.value, scope), "__setitem__", node),
                       [self._value(node.slice, scope), values], {}, node)
        elif isinstance(node, ast.Starred):
            self._assign(node.value, values, scope)

    def _restrict(self, slot: Slot, admits: Callable[[Reference], bool]) -> None:
        """Narrow a slot for the current branch; a branch no value reaches is unreachable.

        An empty narrowing would read as "nothing is known" at the next use
        and be reported as an unresolved call, when what the test showed is
        that no value of this slot enters the branch at all.
        """
        values = self._get(slot)
        kept = frozenset(reference for reference in values if reference.kind == "unreachable" or admits(reference))
        self.narrowed[slot] = kept if kept or not values else frozenset({Reference("unreachable", ":".join(slot))})

    def _callable(self, reference: Reference) -> bool | None:
        """Whether a value is callable; None when the analysis cannot tell."""
        # policy-inventory-exempt: mechanism-internal; reason=these reference variants are callable by construction; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._callable
        if reference.kind in {"function", "bound", "class", "container_method", "slot_set", "slot_get", "namespace_item"}:
            return True
        if reference.kind == "parameter":
            return True if "__call__" in reference.operations else None if reference.member else False
        if reference.kind == "instance":
            if reference.name in self.classes:
                return self._has_method(reference, "__call__")
            return "__call__" in _members(reference.name) if _stdlib_object(reference.name) is not None else None
        # policy-inventory-exempt: mechanism-internal; reason=containers, namespaces and slot descriptors are values, never callables; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._callable
        if reference.kind in {"container", "namespace", "slot", "generator"}:
            return False
        return None

    def _narrow(self, test: ast.expr, scope: _Scope, *, truth: bool) -> None:
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            self._narrow(test.operand, scope, truth=not truth)
        elif (isinstance(test, ast.Call) and len(test.args) == 1 and isinstance(test.args[0], ast.Name)
              and {reference.name for reference in self._value(test.func, scope)} == {"builtins.callable"}):
            slot = self._slot(scope, test.args[0].id)
            admitted = {truth, None}
            self._restrict(slot, lambda reference: self._callable(reference) in admitted)
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

                def admits(reference: Reference) -> bool:
                    # A supplied contract survives a positive test only where
                    # an instance of the tested class can implement every
                    # operation the contract declares.
                    if reference.kind == "unknown":
                        return True
                    if reference.kind == "parameter":
                        return not truth or any(all(self._provides(name, operation) for operation in reference.operations)
                                                for name in classes)
                    return matches(reference) == truth
                self._restrict(slot, admits)
                if truth:
                    # A value of unknown structure that passes the test is an
                    # instance of the tested class from here on, as a type
                    # checker narrows Any; a container class holds it as its
                    # elements, since what it iterates is still unknown.
                    narrowed = self.narrowed[slot]
                    unknowns = frozenset(reference for reference in narrowed if reference.kind == "unknown")
                    if unknowns:
                        typed: set[Reference] = set()
                        for name in classes:
                            shape = _shape(name)
                            # policy-inventory-exempt: mechanism-internal; reason=these two shapes name a class or an awaited value rather than a container; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._narrow
                            if shape is not None and shape[0] not in {"class", "awaited"}:
                                typed.update(self._container(test, shape[1], (unknowns,), keys=unknowns))
                            else:
                                typed.add(Reference("instance", name))
                        self.narrowed[slot] = (narrowed - unknowns) | frozenset(typed)
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.left, (ast.Name, ast.Attribute)):
            right = test.comparators[0]
            if isinstance(right, ast.Constant) and right.value is None and isinstance(test.ops[0], (ast.Is, ast.IsNot)):
                keep_none = truth == isinstance(test.ops[0], ast.Is)
                if isinstance(test.left, ast.Name):
                    slots = [self._slot(scope, test.left.id)]
                else:
                    # `x.attr is None` narrows the field wherever a class x can
                    # be, or a subclass of it, holds one.
                    slots = [(holder, f"<field:{test.left.attr}>")
                             for receiver in self._value(test.left.value, scope)
                             if receiver.kind == "instance" and receiver.name in self.classes
                             for holder in (*self._bases(receiver.name), *self._descendants(receiver.name))]
                for slot in slots:
                    self._restrict(slot, lambda reference: (reference.name == "builtins.NoneType") == keep_none)

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
                    qualified = imported + "." + alias.name
                    resolved = self._symbol(qualified)
                    # A store-dependent re-export stays symbolic until it resolves.
                    # policy-inventory-exempt: mechanism-internal; reason=these four reference variants resolve to the same value at every read; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._statement
                    value = next(iter(resolved)) if len(resolved) == 1 and next(iter(resolved)).kind in {
                        "function", "class", "module", "external"} else Reference("symbol", qualified)
                self._put(self._slot(scope, local), frozenset({value}))
            return
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            values = (self._annotation(node.annotation, scope)
                      if isinstance(node, ast.AnnAssign) and node.value is None
                      else self._value(node.value, scope))
            if isinstance(node, ast.AnnAssign) and node.value is not None:
                values = self._declared_values(values, node.annotation, scope)
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
            # A branch that always leaves the block carries the opposite test
            # onto the statements after the if, as a type checker's early
            # exit does; both leaving means nothing follows.
            leaves = [_terminates(node.body), _terminates(node.orelse)]
            if leaves.count(True) == 1:
                self._narrow(node.test, scope, truth=leaves.index(False) == 0)
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
        self.targets, self.native, self.open, self.contracts = set(), set(), set(), set()
        for index, parameter in enumerate(scope.parameters):
            declared = self._declarations(scope, parameter)
            operations = frozenset().union(*(self._parameter_contract(node, scope) for node in declared))
            annotated = frozenset().union(*(self._annotation(node, scope) for node in declared))
            if self._final and scope.name in self.entries and operations:
                # A union keeps its concrete alternatives beside the contract,
                # and an Any alternative keeps its unknown structure.
                values = frozenset({Reference("parameter", f"supplied parameter {scope.name}.{parameter.arg}",
                                              " | ".join(dict.fromkeys(ast.unparse(node) for node in declared if node is not None)),
                                              operations=operations)})
                values |= self._contract_free(annotated)
                if any(self._unstructured(node, scope) for node in declared):
                    values |= frozenset({Reference("unknown", f"supplied parameter {scope.name}.{parameter.arg}")})
            elif not self._final or operations or scope.name not in self.entries:
                values = frozenset()
            else:
                values = annotated
            signature = scope.arguments
            # policy-inventory-exempt: mechanism-internal; reason=the two variadic parameters hold a container of what the caller passed; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._evaluate
            if signature is not None and values and parameter in {signature.vararg, signature.kwarg}:
                # A declaration on *args or **kwargs describes each element.
                values = self._container(parameter, "tuple" if parameter is signature.vararg else "dict", (values,),
                                         keys=frozenset({Reference("instance", "builtins.str")}))
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
        self.facts[scope.name] = Calls(frozenset(self.targets), frozenset(self.native), frozenset(self.open),
                                      frozenset(self.contracts))
        self.current = ""

    def _complete_annotations(self) -> bool:
        """Complete absent helper values only after caller propagation settles."""
        pending: list[tuple[Slot, Values]] = []
        for name in tuple(self.facts):
            scope = self.scopes[name]
            if name not in self.entries:
                for parameter in scope.parameters:
                    slot = name, parameter.arg
                    declared = self._declarations(scope, parameter)
                    if not self._get(slot) and not any(self._parameter_contract(node, scope) for node in declared):
                        values = frozenset().union(*(self._annotation(node, scope) for node in declared))
                        if values:
                            pending.append((slot, values))
            slot = name, "<return>"
            if name in self.functions and name not in self.generators and not self._get(slot):
                values = frozenset().union(*(self._annotation(node, scope) for node in self._returns(scope)))
                if values:
                    pending.append((slot, values))
        # A batch is one declaration frontier. Filling an earlier scope cannot
        # change which later scope was empty at this same fixed point.
        for slot, values in pending:
            self._put(slot, values)
        return bool(pending or self.queue)

    def solve(self) -> Mapping[str, Calls]:
        """Resolve available targets, then propagate explicit entry-point unknowns."""
        for final in (False, True):
            self._final = final
            self.memos.clear()
            self.memo_readers.clear()
            self._schedule_declarations()
            for name in sorted(self.facts):
                self._schedule(name)
            while True:
                while self.queue:
                    name = self.queue.popleft()
                    self.queued.remove(name)
                    self._evaluate(self.scopes[name])
                if not final or not self._complete_annotations():
                    break
        # Report missing declarations against the completed graph. A missing
        # field during propagation is not a permanent possible receiver.
        self._reporting = True
        self.memos.clear()
        self.memo_readers.clear()
        for name in tuple(self.facts):
            self._evaluate(self.scopes[name])
        return {name: self.facts[name] for name in sorted(self.functions.intersection(self.facts))}
