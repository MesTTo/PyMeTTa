"""Purpose: install compiled Python functions and class declarations into a space.
Guarantees:
  - install_define keeps stacked clauses in Python first-match order [tested
    test_literal_defaults_are_head_patterns_and_clauses_stack]
  - clear_definitions removes process bookkeeping with the equations it
    describes [tested test_reflection_facts_follow_a_dropped_space]
Guarded by:
  - _DEFINE_LOCK serializes equation installation, reflection, and process
    bookkeeping for every space [tested test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import builtins as _builtins
import inspect as _inspect
import threading
import types
from typing import Any

from . import convert as _convert
from . import ops as _ops_module
from ._define_twins import (
    append_twin_clause,
    hazard_twin,
    replace_twin_clause,
    twin_dispatcher,
)
from ._ops import REGISTRY
from .atoms import Atom, Expr, Gnd, Sym, Var, alpha_eq, encode
from .define import (
    Defined,
    canonical_aux_set,
    compile_function,
)
from .errors import CompileError
from .ops import (
    class_declarations,
    declaration_exprs,
    referenced_classes,
    resolved_annotations,
)

_DEFINE_CLAUSES: dict[tuple[str, str], list[dict[str, Any]]] = {}
_DECLARED_DEFINES: dict[tuple[str, str], bool] = {}
_DEFINED_GENERATORS: set[tuple[str, str]] = set()
_DEFINE_LOCK = threading.RLock()


def clear_definitions(space: Any) -> None:
    """Clear one space and the process state describing its definitions."""
    with _DEFINE_LOCK:
        space.runtime.must("petta_py_clear(Space)", Space=space.space_name)
        for registry in (_DEFINE_CLAUSES, _DECLARED_DEFINES):
            for key in [key for key in registry if key[0] == space.space_name]:
                del registry[key]
        for key in [key for key in _DEFINED_GENERATORS if key[0] == space.space_name]:
            _DEFINED_GENERATORS.discard(key)
        if space.space_name != _ops_module.REFLECTION_SPACE:
            space.runtime.must("petta_py_reflect_clear_defined(Space)", Space=space.space_name)


def install_define(space: Any, fn: types.FunctionType):
    """Install one compiled function while serializing shared definition state."""
    with _DEFINE_LOCK:
        return _install_define_locked(space, fn)


def _install_define_locked(space: Any, fn: types.FunctionType):
    """Compile a Python function into MeTTa equations, decorator-style.

    Written for whoever is fluent in Python rather than s-expressions:
    the body is read as syntax and lowered deterministically, refusals
    name the construct, the line and what to write instead, and the
    original stays reachable as .py, a twin the equations can be checked
    against on any ground input.

        @m.define
        def add_one(n):
            return n + 1

        m.run("!(add-one 5)")       # [[6]]
        add_one.py(5)               # 6, ordinary Python

    The equation name follows the operation naming rule: underscores
    in the Python name become hyphens in MeTTa.

    A generator compiles to nondeterminism (each yield one answer), a
    lambda to the engine's own |->, a comprehension to map-atom and
    filter-atom, and match(Pattern(x, y), template) to a match against
    the running space, lowercase free names in the pattern binding as
    variables.
    """
    if not isinstance(fn, types.FunctionType):
        raise TypeError(f"define expects a Python function, got {type(fn).__name__}")

    def nondet(called: str) -> bool:
        for spelling in (called, called.replace("_", "-")):
            operation = REGISTRY.get(spelling)
            if operation is not None and operation.kind in ("many", "raw_many"):
                return True
            if (space.space_name, spelling) in _DEFINED_GENERATORS:
                return True
        return False

    # The equation's name follows the operation rule: underscores read
    # as hyphens, one policy across both decorators.
    name = fn.__name__.replace("_", "-")
    compiled = compile_function(fn, known=space.is_function, nondet=nondet, metta_name=name)
    params, patterns, body = compiled.params, compiled.patterns, compiled.body
    # Clause stacking is per (space, name), process-wide: equations live
    # in the space, not in whichever MeTTa instance happened to add them.
    earlier = _DEFINE_CLAUSES.setdefault((space.space_name, name), [])
    first_clause = not earlier
    if not earlier and space.is_function_here(name):
        raise CompileError(
            f"{name!r} is already a function this space answers (an "
            f"engine builtin, an operation, or an equation): defining it "
            f"would stack a clause onto it and the existing definition "
            f"would keep answering first. Pick another name, or add the "
            f"equation deliberately with m.run.",
            construct="name collision",
        )
    if patterns and any(not clause["patterns"] for clause in earlier):
        raise CompileError(
            f"a clause of {name} with a literal head comes after the "
            f"general clause, which already matches everything; define "
            f"the general clause last",
            construct="clause order",
        )
    for clause in earlier:
        earlier_patterns = clause["patterns"]
        if len(earlier_patterns) < len(patterns) and all(
            patterns.get(param) == value for param, value in earlier_patterns.items()
        ):
            raise CompileError(
                f"a clause of {name} fixes every literal from an earlier "
                f"head and adds more literals, so the earlier clause "
                f"already answers every input this clause could match; "
                f"put the more specific clause first",
                construct="clause order",
            )
    # MeTTa equations are alternatives, and a Python author stacking
    # clauses means first-match, so each clause is guarded against every
    # earlier literal head it would otherwise also answer for. The guard
    # is ordinary MeTTa, visible in .source(), never a hidden rule.
    body = _guard_against(body, [clause["patterns"] for clause in earlier], patterns, params)
    head = Expr([Sym(name), *(patterns.get(p, Var(p)) for p in params)])
    equation = Expr([Sym("="), head, body])
    dispatcher = twin_dispatcher(fn)
    # Idempotence compares the main equation and all helper equations with
    # auxiliary names canonicalized. A loop-body-only or lifted-body-only
    # change must replace the old clause and its old helpers.
    equations = (equation, *compiled.aux)
    canonical = canonical_aux_set(equations, name)
    clause_twin = (
        hazard_twin(name, compiled.hazards, patterns, params) if compiled.hazards else compiled.twin
    )
    replaced = None
    for position, clause in enumerate(earlier):
        old_equations = (clause["equation"], *clause.get("aux", ()))
        old_canonical = canonical_aux_set(old_equations, name)
        if len(old_canonical) == len(canonical) and all(
            alpha_eq(old, new) for old, new in zip(old_canonical, canonical, strict=True)
        ):
            # The identical clause again, a re-run cell or module
            # reload: adding it would duplicate answers, so it stands.
            return Defined(
                name,
                params,
                body,
                dispatcher,
                space,
                patterns=patterns,
                runtime_ops=compiled.runtime_ops,
            )
        if clause["patterns"] == patterns:
            replaced = position
    if replaced is not None:
        # The same head with a new body is a redefinition of that
        # clause, the notebook reading; the old equation goes, the new
        # one takes its place in both the space and the twin dispatch.
        space.remove(earlier[replaced]["equation"])
        for helper_equation in earlier[replaced].get("aux", ()):
            space.remove(helper_equation)
        earlier[replaced] = {
            "patterns": dict(patterns),
            "equation": equation,
            "aux": tuple(compiled.aux),
        }
        replace_twin_clause(dispatcher, replaced, clause_twin)
    else:
        earlier.append(
            {
                "patterns": dict(patterns),
                "equation": equation,
                "aux": tuple(compiled.aux),
            }
        )
        append_twin_clause(dispatcher, clause_twin)
    for helper_equation in compiled.aux:
        space.add(helper_equation)
    space.add(equation)
    if first_clause:
        # The function reflects into the library's own space, one fact
        # per (space, name), following the space through clear().
        space.runtime.must(
            "petta_py_add(Space, W)",
            Space=_ops_module.REFLECTION_SPACE,
            W=Expr([Sym("defined"), Sym(space.space_name), Sym(name)]).to_wire(),
        )
    # Annotations declare the type, exactly as they do for operations,
    # once per name so stacked clauses do not repeat the declaration.
    annotated = resolved_annotations(fn)
    if any(k != "return" for k in annotated) and not _DECLARED_DEFINES.get(
        (space.space_name, name)
    ):
        annotations = [annotated.get(p, _inspect.Parameter.empty) for p in params]
        ret_annotation = annotated.get("return", _inspect.Parameter.empty)
        for declaration in declaration_exprs(name, annotations, ret_annotation):
            space.add(declaration)
        for cls in referenced_classes([*annotations, ret_annotation]):
            for extra in class_declarations(cls):
                space.add(extra)
        _DECLARED_DEFINES[(space.space_name, name)] = True
    if compiled.generator:
        _DEFINED_GENERATORS.add((space.space_name, name))
    return Defined(
        name,
        params,
        body,
        dispatcher,
        space,
        patterns=patterns,
        runtime_ops=compiled.runtime_ops,
    )


def install_type(
    space: Any,
    cls: _builtins.type | None = None,
    *,
    accessors: bool = True,
    methods: bool = True,
):
    """Declare a Python class INTO this space, decorator-style: the
    (: ...) declarations land as atoms, an expression-image class
    (a dataclass, a NamedTuple) gains one accessor equation per
    field, and its own METHODS register as MeTTa functions, so the
    class crosses with its behavior, not only its structure.

        @m.type
        @dataclass
        class Point:
            x: float
            y: float
            def norm(self) -> float:
                return (space.x ** 2 + space.y ** 2) ** 0.5

        m.run("!(Point-x (Point 3.0 4.0))")        # [[3.0]]
        m.run("!(Point-norm (Point 3.0 4.0))")     # [[5.0]]

    A method receives the instance whether it arrives as a
    constructor TERM (rebuilt through the translator) or as a live
    handle, and a result the translator knows projects back as a
    term, so a method answering the class answers something MeTTa
    keeps matching and Python builds back. An equation over the
    constructor is then a method written in MeTTa itself, on equal
    footing. An Enum declares its members; get-type sees them all.
    Returns the class, so it stacks under @dataclass.
    """

    def apply(target: _builtins.type) -> _builtins.type:
        registration = _convert.ensure_registered(target)
        for declaration in _convert.declarations(target):
            space.add(declaration)
        if accessors and registration.image == "expression" and registration.fields:
            constructor = registration.type_name
            fields = registration.fields
            variables = [Var(f"f{i}") for i in range(1, len(fields) + 1)]
            for position, field_name in enumerate(fields):
                head = Expr(
                    [
                        Sym(f"{constructor}-{field_name}"),
                        Expr([Sym(constructor), *variables]),
                    ]
                )
                space.add(Expr([Sym("="), head, variables[position]]))
        if methods:
            _register_methods(space, target, registration.type_name)
        return target

    return apply(cls) if cls is not None else apply


def _register_methods(space: Any, target: _builtins.type, type_name: str) -> None:
    """Every method the class itself defines, as a MeTTa function
    named {Type}-{method}: the instance argument accepts a
    constructor term (rebuilt through the translator) or a live
    handle, and results the translator knows project back to terms."""

    def projectable(value: Any) -> Any:
        try:
            _convert.ensure_registered(type(value))
        except TypeError:
            return value
        return _convert.project(value).atom

    def wrapper_for(fn):
        def call(instance, *args):
            subject = (
                _convert.build(instance, target)
                if isinstance(instance, Expr)
                else (instance.value if isinstance(instance, Gnd) else instance)
            )
            values = [a.value if isinstance(a, Gnd) else a for a in args]
            result = fn(subject, *values)
            if result is None:
                return None
            if isinstance(result, Atom):
                return result
            if isinstance(result, (bool, int, float, str)):
                return encode(result)
            return projectable(result)

        return call

    for method_name, fn in vars(target).items():
        if method_name.startswith("_") or not _inspect.isfunction(fn):
            continue
        parameters = list(_inspect.signature(fn).parameters.values())[1:]
        required = sum(1 for p in parameters if p.default is _inspect.Parameter.empty)
        arities = list(range(1 + required, len(parameters) + 2))
        space.register_op(
            wrapper_for(fn),
            name=f"{type_name}-{method_name}".replace("_", "-"),
            typed=False,
            pass_atoms=True,
            arities=arities,
        )


def _guard_against(body: Atom, earlier: list, patterns: dict, params: list) -> Atom:
    """The current clause's body, declining every earlier literal head.

    For each earlier clause, the inputs it claims are the positions it fixed
    with literals; when this clause leaves all of those positions variable,
    the two overlap, and this clause answers (empty) there, so dispatch reads
    first-match the way the stacked Python reads. define() refuses a later
    head that fixes every literal in an earlier head because no variable is
    available for a conditional guard.
    """
    for earlier_patterns in earlier:
        if not earlier_patterns:
            continue
        overlapping = all(
            p not in patterns or patterns[p] == v for p, v in earlier_patterns.items()
        )
        contested = [p for p in earlier_patterns if p not in patterns]
        if not overlapping or not contested:
            continue
        first, *remaining = contested
        condition: Atom = Expr([Sym("=="), Var(first), earlier_patterns[first]])
        for p in remaining:
            test = Expr([Sym("=="), Var(p), earlier_patterns[p]])
            condition = Expr([Sym("and"), condition, test])
        body = Expr([Sym("if"), condition, Expr([Sym("empty")]), body])
    return body
