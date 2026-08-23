"""Purpose: install compiled Python functions and class declarations into a space.
Guarantees:
  - ``install_type`` is the class branch behind ``Space.define`` [tested:
    test_define_absorbs_class_declaration_and_frees_space_type;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - install_define keeps stacked clauses in Python first-match order [tested
    test_literal_defaults_are_head_patterns_and_clauses_stack]
  - clauses at different arities under one MeTTa name stack instead of
    replacing one another [tested:
    test_define_supports_one_name_at_multiple_arities; commit=WORKTREE]
  - clear_definitions removes process bookkeeping with the equations it
    describes [tested test_reflection_facts_follow_a_dropped_space]
  - a definition is exposed only after its first twin clause exists, and its
    canonical first-clause documentation follows replacement and clearing
    [tested: test_one_docstring_reaches_help_dot_doc_and_get_doc;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - source spans, AST documentation, free variables, and derived purity
    replace atomically across clause replacement and leave reflection on
    clear [tested: test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - generated class-method operations declare their Atom delivery policy in
    &petta rather than passing a boolean registration flag [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - an annotation-derived declaration lands before the equation it governs
    and rolls back if equation publication fails [tested:
    test_a_declared_output_type_takes_effect_through_the_decorator_door,
    test_failed_equation_publication_rolls_back_its_early_declaration;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every flat-yield equation is stored and replaced as one atomic clause
    unit [tested: test_same_head_redefinition_replaces_the_whole_yield_unit;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
Guarded by:
  - _DEFINE_LOCK serializes equation installation, reflection, and process
    bookkeeping for every space [tested test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import builtins as _builtins
import importlib as _importlib
import inspect as _inspect
import os
import threading
import types
from collections.abc import Callable
from functools import partial
from typing import Any

from . import ops as _ops_module
from ._define_twins import (
    append_twin_clause,
    replace_twin_clause,
    select_clause_twin,
    twin_dispatcher,
)
from ._documentation import documentation_atom
from ._ops import REGISTRY
from .atoms import Atom, Expression, Grounded, S, Symbol, Variable, _alpha_eq, _encode, _expr
from .define import (
    Compiled,
    Defined,
    PrologBacked,
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
_DEFINE_DOCUMENTATION: dict[tuple[str, str], Expression] = {}
_DEFINE_REFLECTION: dict[tuple[str, str], tuple[Expression, ...]] = {}
_DEFINE_FACT_REFS: dict[str, int] = {}
_DEFINE_LOCK = threading.RLock()


def _convert_api():
    """Load structural conversion only for class-backed definitions."""
    return _importlib.import_module(f"{__package__}.convert")


def clear_definitions(space: Any) -> None:
    """Clear one space and the process state describing its definitions."""
    with _DEFINE_LOCK:
        space.runtime.must("petta_py_clear(Space)", Space=space.name)
        for key in [key for key in _DEFINE_REFLECTION if key[0] == space.name]:
            for fact in _DEFINE_REFLECTION.pop(key):
                _release_definition_fact(space, fact)
        for registry in (_DEFINE_CLAUSES, _DECLARED_DEFINES, _DEFINE_DOCUMENTATION):
            for key in [key for key in registry if key[0] == space.name]:
                del registry[key]
        _DEFINED_GENERATORS.difference_update(
            {key for key in _DEFINED_GENERATORS if key[0] == space.name}
        )


def install_define(space: Any, fn: Callable[..., Any], name: str | None = None):
    """Install one compiled function while serializing shared definition state."""
    with _DEFINE_LOCK:
        return _install_define_locked(space, fn, name)


def install_prolog_define(
    space: Any, fn: Callable[..., Any], prolog: Any, name: str | None = None
):
    """Register the Prolog side and keep the Python as the reference twin.

    Nothing of the Python is compiled: the registered predicate IS the
    function, and defining the same name from both would stack a second
    clause the first would keep answering ahead of.
    """
    if not isinstance(fn, types.FunctionType):
        msg = f"define expects a Python function, got {type(fn).__name__}"
        raise TypeError(msg)
    name = name or fn.__name__
    origin = os.fspath(prolog)
    registered = space.register_prolog(path=origin)
    if name not in registered:
        msg = (
            f"{origin} does not register {name!r}, which is the MeTTa name of "
            f"{fn.__name__}; it registered {', '.join(sorted(registered)) or 'nothing'}. "
            f"A twin has to name the predicate it is the reference for."
        )
        raise CompileError(
            msg,
            construct="prolog twin",
        )
    params = list(_inspect.signature(fn).parameters)
    _refuse_mismatched_twin_arity(space, name, params, origin)
    return PrologBacked(name, params, fn, space, origin)


def _refuse_mismatched_twin_arity(
    space: Any, name: str, params: list[str], origin: str
) -> None:
    """A twin of a different shape is not a twin, and would only ever be
    found by a caller. The predicate takes one argument per parameter plus
    the output, which is the convention every registered predicate follows.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    expected = len(params) + 1
    _, _, shapes, _ = space.runtime.apply_must("petta_py_function_shape", name)
    arities = [int(arity) for arity, _speedup, _indexed in shapes]
    if arities and expected not in arities:
        msg = (
            f"{name} in {origin} takes {' or '.join(str(a) for a in sorted(arities))} "
            f"argument(s), but its Python twin takes {len(params)}, so the "
            f"predicate would need arity {expected}: inputs then one output."
        )
        raise CompileError(
            msg,
            construct="prolog twin",
        )


def _is_nondeterministic(space: Any, called: str) -> bool:
    """Whether a registered operation or compiled definition has many answers."""
    operation = REGISTRY.get(called)
    if operation is not None and operation.kind in ("many", "raw_many"):
        return True
    return (space.name, called) in _DEFINED_GENERATORS


def _is_pure(space: Any, called: str) -> bool:
    """Whether the engine's declaration set says this callee is immutable."""
    return bool(space.runtime.once("seam:pure_operation(Name)", Name=called))


def _validate_clause_order(
    space: Any,
    name: str,
    patterns: dict[str, Atom],
    arity: int,
    earlier: list[dict[str, Any]],
) -> None:
    """Refuse collisions and clauses hidden by an earlier Python head."""
    if not earlier and space.is_function_here(name):
        msg = (
            f"{name!r} is already a function this space answers (an "
            f"engine builtin, an operation, or an equation): defining it "
            f"would stack a clause onto it and the existing definition "
            f"would keep answering first. Pick another name, or add the "
            f"equation deliberately with m.run."
        )
        raise CompileError(
            msg,
            construct="name collision",
        )
    same_arity = [clause for clause in earlier if clause["arity"] == arity]
    if patterns and any(not clause["patterns"] for clause in same_arity):
        msg = (
            f"a clause of {name} with a literal head comes after the "
            f"general clause, which already matches everything; define "
            f"the general clause last"
        )
        raise CompileError(
            msg,
            construct="clause order",
        )
    for clause in same_arity:
        earlier_patterns = clause["patterns"]
        if len(earlier_patterns) < len(patterns) and all(
            patterns.get(param) == value for param, value in earlier_patterns.items()
        ):
            msg = (
                f"a clause of {name} fixes every literal from an earlier "
                f"head and adds more literals, so the earlier clause "
                f"already answers every input this clause could match; "
                f"put the more specific clause first"
            )
            raise CompileError(
                msg,
                construct="clause order",
            )


def _same_clause(clause: dict[str, Any], canonical: tuple[Expression, ...], name: str) -> bool:
    old_equations = (*clause["equations"], *clause.get("aux", ()))
    old_canonical = canonical_aux_set(old_equations, name)
    return len(old_canonical) == len(canonical) and all(
        _alpha_eq(old, new) for old, new in zip(old_canonical, canonical, strict=True)
    )


def _locate_clause(
    earlier: list[dict[str, Any]],
    patterns: dict[str, Atom],
    arity: int,
    canonical: tuple[Expression, ...],
    name: str,
) -> tuple[bool, int | None]:
    """Return whether the clause is identical and which matching head it replaces."""
    replaced = None
    for position, clause in enumerate(earlier):
        if _same_clause(clause, canonical, name):
            return True, position
        if clause["arity"] == arity and clause["patterns"] == patterns:
            replaced = position
    return False, replaced


def _defined_result(
    space: Any,
    name: str,
    compiled: Compiled,
    bodies: tuple[Atom, ...],
    dispatcher: Any,
) -> Defined:
    body = bodies[0] if len(bodies) == 1 else Expression([Symbol("superpose"), Expression(bodies)])
    return Defined(
        name,
        compiled.params,
        body,
        dispatcher,
        space,
        patterns=compiled.patterns,
        runtime_ops=compiled.runtime_ops,
        facts=compiled.facts,
        bodies=bodies,
    )


def _store_clause(
    space: Any,
    earlier: list[dict[str, Any]],
    *,
    patterns: dict[str, Atom],
    equations: tuple[Expression, ...],
    compiled: Compiled,
    dispatcher: Any,
    clause_twin: Any,
    replaced: int | None,
) -> None:
    record = _clause_record(patterns, equations, compiled)
    previous_atoms: list[Expression] = []
    if replaced is not None:
        previous = earlier[replaced]
        previous_atoms = [*previous.get("aux", ()), *previous["equations"]]
        for atom in previous_atoms:
            space.remove(atom)
    added: list[Expression] = []
    try:
        for atom in (*compiled.aux, *equations):
            space.add(atom)
            added.append(atom)
    except BaseException:
        for atom in reversed(added):
            space.remove(atom)
        for atom in previous_atoms:
            space.add(atom)
        raise
    if replaced is None:
        earlier.append(record)
        append_twin_clause(dispatcher, clause_twin)
    else:
        earlier[replaced] = record
        replace_twin_clause(dispatcher, replaced, clause_twin)


def _clause_record(
    patterns: dict[str, Atom], equations: tuple[Expression, ...], compiled: Compiled
) -> dict[str, Any]:
    return {
        "arity": len(compiled.params),
        "patterns": patterns.copy(),
        "equations": equations,
        "aux": tuple(compiled.aux),
        "facts": compiled.facts,
    }


def _definition_facts(space: Any, name: str, clauses: list[dict[str, Any]]) -> tuple[Expression, ...]:
    """The aggregate reflection of every live clause under one name."""
    facts: list[Expression] = [Expression([Symbol("defined"), Symbol(space.name), Symbol(name)])]
    for clause in clauses:
        derived = clause["facts"]
        span = derived.source_span
        facts.append(
            Expression(
                [
                    Symbol("source-span"),
                    Symbol(space.name),
                    Symbol(name),
                    Grounded(span.path),
                    Grounded(span.start_line),
                    Grounded(span.start_column),
                    Grounded(span.end_line),
                    Grounded(span.end_column),
                ]
            )
        )
    facts.extend(
        Expression(
            [
                Symbol("free-variable"),
                Symbol(space.name),
                Symbol(name),
                Symbol(free_variable),
            ]
        )
        for free_variable in sorted(
            {variable for clause in clauses for variable in clause["facts"].free_variables}
        )
    )
    if clauses and all(clause["facts"].pure for clause in clauses):
        facts.append(Expression([Symbol("effect"), Symbol(name), Symbol("immutable")]))
    return tuple(dict.fromkeys(facts))


def _retain_definition_fact(space: Any, fact: Expression) -> None:
    key = str(fact)
    count = _DEFINE_FACT_REFS.get(key, 0)
    if count == 0:
        space.runtime.must(
            "petta_py_add(Space, W)",
            Space=_ops_module._REFLECTION_SPACE,
            W=fact.to_wire(),
        )
    _DEFINE_FACT_REFS[key] = count + 1


def _release_definition_fact(space: Any, fact: Expression) -> None:
    key = str(fact)
    count = _DEFINE_FACT_REFS.get(key, 0)
    if count <= 1:
        _DEFINE_FACT_REFS.pop(key, None)
        space.runtime.once(
            "petta_py_remove(Space, W, _)",
            Space=_ops_module._REFLECTION_SPACE,
            W=fact.to_wire(),
        )
    else:
        _DEFINE_FACT_REFS[key] = count - 1


def _sync_definition_facts(space: Any, name: str, clauses: list[dict[str, Any]]) -> None:
    """Replace a definition's reflected facts, restoring the old set on error."""
    key = (space.name, name)
    previous = _DEFINE_REFLECTION.get(key, ())
    current = _definition_facts(space, name, clauses)
    retained: list[Expression] = []
    released: list[Expression] = []
    try:
        for fact in current:
            if fact not in previous:
                _retain_definition_fact(space, fact)
                retained.append(fact)
        for fact in previous:
            if fact not in current:
                _release_definition_fact(space, fact)
                released.append(fact)
    except BaseException:
        for fact in reversed(released):
            _retain_definition_fact(space, fact)
        for fact in reversed(retained):
            _release_definition_fact(space, fact)
        raise
    _DEFINE_REFLECTION[key] = current


def _document_definition(space: Any, name: str, dispatcher: Any) -> None:
    """Publish the dispatcher's canonical first-clause documentation."""
    key = (space.name, name)
    previous = _DEFINE_DOCUMENTATION.get(key)
    current = documentation_atom(name, dispatcher)
    if current == previous:
        return
    if current is not None:
        space.add(current)
        _DEFINE_DOCUMENTATION[key] = current
    else:
        _DEFINE_DOCUMENTATION.pop(key, None)
    if previous is not None:
        space.remove(previous)


def _declare_definition(
    space: Any,
    fn: types.FunctionType,
    name: str,
    params: list[str],
) -> tuple[Expression, ...]:
    annotated = resolved_annotations(fn)
    key = (space.name, name)
    if not any(label != "return" for label in annotated) or _DECLARED_DEFINES.get(key):
        return ()
    annotations = [annotated.get(param, _inspect.Parameter.empty) for param in params]
    ret_annotation = annotated.get("return", _inspect.Parameter.empty)
    declarations = [*declaration_exprs(name, annotations, ret_annotation)]
    for cls in referenced_classes([*annotations, ret_annotation]):
        declarations.extend(class_declarations(cls))
    added: list[Expression] = []
    try:
        for declaration in declarations:
            space.add(declaration)
            added.append(declaration)
    except BaseException:
        for declaration in reversed(added):
            space.remove(declaration)
        raise
    _DECLARED_DEFINES[key] = True
    return tuple(added)


def _install_define_locked(space: Any, fn: Callable[..., Any], name: str | None = None):
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

    The equation's name is the Python name, verbatim. Hyphens are the
    MeTTa convention and Python cannot spell one, so a hyphenated name is
    asked for rather than inferred: @m.define(name="add-one"). Nothing is
    rewritten behind the author's back.

    A generator compiles to nondeterminism (each yield one answer), a
    lambda to the engine's own |->, a comprehension to map-atom and
    filter-atom, and match(Pattern(x, y), template) to a match against
    the running space, lowercase free names in the pattern binding as
    variables.
    """
    if not isinstance(fn, types.FunctionType):
        msg = f"define expects a Python function, got {type(fn).__name__}"
        raise TypeError(msg)

    # The equation's name is the Python name, verbatim, or the one asked
    # for: one policy across both decorators, and neither rewrites what the
    # author wrote.
    name = name or fn.__name__
    compiled = compile_function(
        fn,
        known=space.is_function,
        nondet=partial(_is_nondeterministic, space),
        pure=partial(_is_pure, space),
        metta_name=name,
    )
    params, patterns = compiled.params, compiled.patterns
    # Clause stacking is per (space, name), process-wide: equations live
    # in the space, not in whichever MeTTa instance happened to add them.
    earlier = _DEFINE_CLAUSES.setdefault((space.name, name), [])
    _validate_clause_order(space, name, patterns, len(params), earlier)
    # MeTTa equations are alternatives, and a Python author stacking
    # clauses means first-match, so each clause is guarded against every
    # earlier literal head it would otherwise also answer for. The guard
    # is ordinary MeTTa, visible in .source(), never a hidden rule.
    bodies = tuple(
        _guard_against(body, [clause["patterns"] for clause in earlier], patterns)
        for body in compiled.equation_bodies
    )
    head = Expression([Symbol(name), *(patterns.get(p, Variable(p)) for p in params)])
    equations = tuple(Expression([Symbol("="), head, body]) for body in bodies)
    dispatcher = twin_dispatcher(fn)
    # Idempotence compares the main equation and all helper equations with
    # auxiliary names canonicalized. A loop-body-only or lifted-body-only
    # change must replace the old clause and its old helpers.
    canonical = canonical_aux_set((*equations, *compiled.aux), name)
    clause_twin = select_clause_twin(
        name,
        compiled.twin,
        compiled.hazards,
        patterns,
        params,
    )
    clause_twin.__doc__ = compiled.facts.doc
    duplicate, replaced = _locate_clause(
        earlier, patterns, len(params), canonical, name
    )
    if duplicate:
        # A re-run cell or module reload must not duplicate answers.
        if replaced is None:
            msg = "a duplicate clause has no replacement index"
            raise RuntimeError(msg)
        prospective = earlier.copy()
        prospective[replaced] = earlier[replaced] | {
            "facts": compiled.facts,
        }
        _sync_definition_facts(space, name, prospective)
        earlier[replaced]["facts"] = compiled.facts
        replace_twin_clause(dispatcher, replaced, clause_twin)
        _document_definition(space, name, dispatcher)
        return _defined_result(space, name, compiled, bodies, dispatcher)
    prospective = earlier.copy()
    record = _clause_record(patterns, equations, compiled)
    if replaced is None:
        prospective.append(record)
    else:
        prospective[replaced] = record
    _sync_definition_facts(space, name, prospective)
    declared: tuple[Expression, ...] = ()
    try:
        declared = _declare_definition(space, fn, name, params)
        _store_clause(
            space,
            earlier,
            patterns=patterns,
            equations=equations,
            compiled=compiled,
            dispatcher=dispatcher,
            clause_twin=clause_twin,
            replaced=replaced,
        )
    except BaseException:
        for declaration in reversed(declared):
            space.remove(declaration)
        if declared:
            _DECLARED_DEFINES.pop((space.name, name), None)
        _sync_definition_facts(space, name, earlier)
        raise
    defined = _defined_result(space, name, compiled, bodies, dispatcher)
    _document_definition(space, name, dispatcher)
    if compiled.generator:
        _DEFINED_GENERATORS.add((space.name, name))
    return defined


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

        @m.define
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
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def apply(target: _builtins.type) -> _builtins.type:
        convert = _convert_api()
        registration = convert.ensure_registered(target)
        for declaration in convert.declarations(target):
            space.add(declaration)
        if accessors and registration.image == "expression" and registration.fields:
            constructor = registration.type_name
            fields = registration.fields
            _variables = [Variable(f"f{i}") for i in range(1, len(fields) + 1)]
            for position, field_name in enumerate(fields):
                head = Expression(
                    [
                        Symbol(f"{constructor}-{field_name}"),
                        Expression([Symbol(constructor), *_variables]),
                    ]
                )
                space.add(Expression([Symbol("="), head, _variables[position]]))
        if methods:
            _register_methods(space, target, registration.type_name)
        return target

    return apply(cls) if cls is not None else apply


def _register_methods(space: Any, target: _builtins.type, type_name: str) -> None:
    """Every method the class itself defines, as a MeTTa function
    named {Type}-{method}: the instance argument accepts a
    constructor term (rebuilt through the translator) or a live
    handle, and results the translator knows project back to terms.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def projectable(value: Any) -> Any:
        try:
            _convert_api().ensure_registered(type(value))
        except TypeError:
            return value
        return _convert_api().project(value).atom

    def wrapper_for(fn):
        def call(instance, *args):
            subject = (
                _convert_api().build(instance, target)
                if isinstance(instance, Expression)
                else (instance.value if isinstance(instance, Grounded) else instance)
            )
            values = [a.value if isinstance(a, Grounded) else a for a in args]
            result = fn(subject, *values)
            if result is None:
                return None
            if isinstance(result, Atom):
                return result
            if isinstance(result, (bool, int, float, str)):
                return _encode(result)
            return projectable(result)

        return call

    for method_name, fn in vars(target).items():
        if method_name.startswith("_") or not _inspect.isfunction(fn):
            continue
        parameters = list(_inspect.signature(fn).parameters.values())[1:]
        required = sum(1 for p in parameters if p.default is _inspect.Parameter.empty)
        arities = list(range(1 + required, len(parameters) + 2))
        operation_name = f"{type_name}-{method_name}"
        space.op(
            wrapper_for(fn),
            name=operation_name,
            declarations=[
                _expr(S.arguments, S[operation_name], S.atoms)
            ],
            arities=arities,
        )


def _guard_against(body: Atom, earlier: list, patterns: dict) -> Atom:
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
        condition: Atom = Expression([Symbol("=="), Variable(first), earlier_patterns[first]])
        for p in remaining:
            test = Expression([Symbol("=="), Variable(p), earlier_patterns[p]])
            condition = Expression([Symbol("and"), condition, test])
        body = Expression([Symbol("if"), condition, Expression([Symbol("empty")]), body])
    return body
