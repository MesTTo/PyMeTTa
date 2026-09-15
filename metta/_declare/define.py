"""Purpose: Python functions compiled into MeTTa equations, so a program can
be written in the language its author, human or model, is fluent in, and run
as MeTTa. The source is read with ast, never traced: tracing loses branches,
which is torch.jit.script's own reason for reading syntax. Three rules hold
the subset together: syntax outside it is a CompileError naming the construct,
the line, and what to write instead; every supported construct has one MeTTa
spelling; and a free identifier must be a parameter, a known function, or
read as a data constructor. A compiled body is a complete atom tree, and any
runtime-backed Python semantics it needs are declared as visible operations.
Guarantees:
  - local annotation claims and source type aliases admit the same container
    images as runtime_type_atoms at call boundaries, preserving scalar claims
    [tested: test_local_alias_accepts_its_structural_and_borrowed_images;
    commit=f5bfd15c1dee2b5a42ac3e0f2c6ef48688c5753c].
  - keyword collectors materialize once before a generator's shared answers
    [tested: test_compiled_generator_answers_share_one_keyword_dictionary;
    commit=1796cf0f581aa767db9289b807f66238cb747065]
  - literal head parameters remain values in body scopes and independent
    generator equations [tested: test_literal_head_values_reach_compiled_bodies;
    test_each_generator_equation_binds_its_literal_head; commit=5e3e9bce79f9ad71d61096256bbda8b249f8de8c]
  - source parameters and SSA bindings retain underscore identity in every
    nested compiler scope [tested:
    test_python_underscore_bindings_retain_their_values; commit=69d1511c099eb6aa80c38d898da49487c42470f0]
  - class methods use the ordinary body compiler with their written argument
    contract and explicit receiver [tested:
    test_class_methods_keep_full_python_signatures_and_native_bodies; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
  - None has the same literal head-pattern meaning as other function defaults
    [tested: test_none_literal_is_also_a_default_head_pattern; commit=dbe6c7de5f35e7c0c8ef5259ebfb6d67ee3ebbc0]
  - importing a declaration or library module first completes in both lazy
    and eager modes [tested: test_each_module_imports_first_in_a_fresh_process;
    commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
  - ``async def`` refuses with both executable alternatives: ``@op`` returns
    a FutureSpace, while ``aio.AsyncMeTTa.call`` keeps orchestration in the
    host event loop [tested:
    test_define_async_refusal_names_both_actionable_remedies; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - the compiler resolves exact standard-module attribute callables from a
    function's globals and populated closure cells, while operator callables
    retain Python's protocol semantics [tested:
    test_callable_mentions_share_operator_and_fourteen_math_names,
    test_compiled_callable_mentions_preserve_python_call_semantics;
    commit=e3787593132a7ece2d300397045f7415709847c9]
  - Defined.doc and Defined.__doc__ expose the first compiled clause's cleaned
    docstring after the twin dispatcher contains that clause [tested:
    test_one_docstring_reaches_help_dot_doc_and_get_doc;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - local annotated assignments resolve through a syntax-limited namespace
    reader and compile to enforceable in-place type claims [tested:
    test_an_annotated_binding_emits_its_claim; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - source spans, source docstrings, lexical captures, and the strongest call effect are
    derived from the parsed function and exposed as immutable facts [tested:
    test_a_definition_joins_every_called_operations_effect; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - ``yield from`` delegates only a statically known-nondeterministic call
    and refuses an ambiguous engine call instead of silently splicing it
    [tested:
    test_yield_from_a_call_delegates_only_when_nondeterminism_is_known;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - namespace builders are recognized by lexical identity and mapped catalog
    callees keep their nondeterministic role [tested:
    test_rejected_attributes_never_execute_host_objects,
    test_mapped_nondeterministic_calls_keep_their_call_role; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - calling a Defined object evaluates its application except in a rules
    builder's scope-local staging context [tested:
    test_calling_a_defined_object_evaluates_and_an_unmatched_call_answers_itself,
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Python argument values enter native functions after source binding, while
    rule variables retain their staged call terms [tested:
    test_python_call_values_preserve_expression_arguments,
    test_computed_receivers_preserve_their_stored_syntax,
    test_the_staging_split_folds_ground_calls_and_stages_op_terms; commit=310a9d8b547a77412a518a37ab79fba073eb22ac]
  - flat independent yield statements compile to separate equation bodies,
    while control-flow yields retain one superpose body [tested:
    test_flat_generator_emits_one_equation_per_yield,
    test_loop_yields_remain_one_superpose_equation; commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - a host-bound sibling Defined resolves to its declared MeTTa name inside a
    compiled body, while self-recursion remains runnable by the Python twin
    [tested: test_compiled_body_calls_renamed_defined_sibling,
    test_compiled_calls_share_the_installed_name_resolver; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - ordinary Defined calls keep the held evaluation cursor inside a stats
    scope, so a bounded view suspends an endless producer [tested:
    test_function_calls_suspend_endless_producers; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - a successful module-level call remains lawful and records one advisory
    lint event [tested: test_a_module_level_defined_call_is_linted_not_refused;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - cached definitions enter the compiled-call dispatch path and expose their
    bag-preserving memo store, reached through lib_memo's own forms
    [tested: test_a_cached_definition_preserves_duplicate_answers;
    commit=8d6131a9d9902c67ce8cac71e96e8362a8713561]
  - exact ``py(expr)`` marker bindings become application-time host islands
    carrying current SSA locals, live globals, source spans and loop context
    [tested: test_py_host_island_executes_per_engine_application,
    test_py_host_island_inside_loops_emits_exact_findings; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - nested compiler contexts preserve local container species for Python
    operator dispatch [tested:
    test_compiled_operators_follow_python_protocols_and_result_species;
    commit=e3787593132a7ece2d300397045f7415709847c9]
  - a parameter whose resolved annotation names ``Space`` enters statement
    lowering as a space handle, so its augmented removal cannot become
    arithmetic [tested:
    test_compiled_removal_statements_preserve_one_many_missing_and_target_scope;
    commit=79e9635b6c20e046ace8fc82bd3edf062c7ae9b2]
  - known call-site keywords bind to the definition's parameter order both at
    the live call and inside compiled bodies [tested:
    test_known_call_site_keywords_bind_to_positional_metta_arguments;
    commit=c2ad5892fbfdd690dd7e9b507e76e87d7d1376d1]
  - a live Defined call reads the shared deprecation catalog after staging
    has finished and warns with its since/remedy declaration [tested:
    test_deprecation_catalog_rows_drive_warnings_and_explanations;
    commit=d74e2e828cd9272882dcf907cfaf095d2d147ce0]
  - Defined and PrologBacked source is always MeTTa text, with a Prolog-backed
    origin represented by a MeTTa comment, and rich notebooks escape that
    source [tested:
    test_a_definition_may_be_written_in_prolog_with_the_python_as_reference,
    test_defined_rich_repr_shows_escaped_source; commit=42502e9d4a7fedd419856d5e6a1c291fc18ba644]
  - compile_function raises sys.audit("metta.host", "compile", qualname)
    before it reads a function's source, so the third host door is auditable
    with the other two [tested: test_the_compile_door_raises_its_event;
    commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import html
import inspect
import sys
import textwrap
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple, cast

import metta._declare.functions as _functions
import metta._declare.rules as _declare_rules_module
from metta._atoms.calls import bind_positional_call
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    S,
    Symbol,
    V,
    Variable,
    _encode,
    _map_atoms,
    _variables,
)
from metta._atoms.names import binding_name, resolve_known_name
from metta._catalog.annotations import runtime_type_atoms
from metta._catalog.call_values import apply_sources
from metta._catalog.fn import fn as fn_namespace
from metta._compile import records as _records
from metta._compile.expressions import ExpressionCompilerMixin
from metta._compile.facts import DefinitionFacts, SourceSpan, derive_definition_facts
from metta._compile.islands import py as _py_marker
from metta._compile.loops import LoopCompilerMixin
from metta._compile.statements import StatementCompilerMixin, _is_generator, _superpose
from metta._compile.twins import _python_twin
from metta._declare import call_syntax
from metta._errors.errors import CompileError, with_coordinates
from metta._spaces.intents import record_event_at_frame, record_sync_engine_call
from metta._spaces.results import Answers
from metta.vocabularies import EffectClass

__all__ = ["Defined", "DefinitionFacts", "PrologBacked", "SourceSpan", "compile_function"]


def _provided[T](value: T | None, default: T) -> T:
    return default if value is None else value


def _never(_name: str) -> bool:
    return False


def _unknown_effect(_name: str) -> EffectClass:
    return EffectClass.oracleIO


def _builtins_namespace() -> dict[str, Any]:
    return __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)


_MISSING_HOST = object()


def _function_namespace(fn: types.FunctionType) -> dict[str, Any]:
    """Globals, builtins, closure cells, and type parameters visible to ``fn``.

    ``def mid[T](x: T) -> T`` places ``T`` in the PEP 695 type-parameter
    scope, which sits between the closure and the local scope and appears in
    neither ``__globals__`` nor ``__closure__``; only ``__type_params__``
    carries it. Leaving it out made the eager ``Space``-annotation check
    refuse every generic definition with "the local annotation name 'T' is
    not available" [tested: test_a_pep695_type_parameter_resolves_in_annotations].
    """
    nonlocals: dict[str, Any] = {}
    for name, cell in zip(fn.__code__.co_freevars, fn.__closure__ or (), strict=True):
        try:
            nonlocals[name] = cell.cell_contents
        except ValueError:
            continue
    type_params = {parameter.__name__: parameter for parameter in fn.__type_params__}
    return {**_builtins_namespace(), **fn.__globals__, **nonlocals, **type_params}


def _annotation_resolver(
    fn: types.FunctionType,
) -> tuple[
    Callable[[ast.expr], Atom],
    Callable[[ast.expr], list[Atom]],
    Callable[[ast.expr], Any],
]:
    """Resolve local annotation syntax without executing arbitrary source.

    The single-claim and source-alias readers use runtime_type_atoms, as call
    signatures do, so a container's structural image satisfies its claim.
    Written Python types still supply optional static proofs separately.
    """
    namespace = _function_namespace(fn)
    # PEP 649 gives annotation-only local names their own closure. Reading its
    # cells preserves that lexical environment without evaluating annotations.
    # https://peps.python.org/pep-0649/#compiler-generated-annotate-functions
    annotate = getattr(fn, "__annotate__", None)
    if isinstance(annotate, types.FunctionType):
        for name, cell in zip(annotate.__code__.co_freevars, annotate.__closure__ or (), strict=True):
            try:
                namespace[name] = cell.cell_contents
            except ValueError:
                continue

    def resolve(node: ast.expr) -> Any:
        if isinstance(node, ast.Name):
            if node.id not in namespace:
                msg = f"the local annotation name {node.id!r} is not available"
                raise CompileError(
                    msg,
                    construct="annotation",
                    line=node.lineno,
                )
            return namespace[node.id]
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Tuple):
            return tuple(resolve(item) for item in node.elts)
        if isinstance(node, ast.Attribute):
            owner = resolve(node.value)
            if isinstance(owner, types.ModuleType):
                values = vars(owner)
                if node.attr in values:
                    return values[node.attr]
            elif isinstance(owner, type):
                value = inspect.getattr_static(owner, node.attr, None)
                if isinstance(value, type):
                    return value
            msg = (
                f"the local annotation attribute {ast.unparse(node)!r} is not a "
                "module or nested type"
            )
            raise CompileError(
                msg,
                construct="annotation",
                line=node.lineno,
            )
        if isinstance(node, ast.Subscript):
            target = resolve(node.value)
            target_module = getattr(target, "__module__", "")
            # policy-inventory-exempt: mechanism-internal; reason=only these three modules define the subscripts that are typing constructors, so subscripting anything else would run user code while resolving an annotation; evidence=extensions/python/metta/_declare/define.py:_annotation_resolver
            if target_module not in {"builtins", "typing", "collections.abc"}:
                msg = (
                    f"the local annotation {ast.unparse(node)!r} would execute "
                    "a user subscript; use a named type instead"
                )
                raise CompileError(
                    msg,
                    construct="annotation",
                    line=node.lineno,
                )
            argument = resolve(node.slice)
            try:
                return target[argument]
            except (KeyError, TypeError, ValueError) as exc:
                msg = f"the local annotation {ast.unparse(node)!r} is invalid: {exc}"
                raise CompileError(
                    msg,
                    construct="annotation",
                    line=node.lineno,
                ) from exc
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = resolve(node.left)
            right = resolve(node.right)
            if not all(
                isinstance(value, type) or getattr(value, "__module__", "") == "typing"
                for value in (left, right)
            ):
                msg = f"the local annotation {ast.unparse(node)!r} is not a type union"
                raise CompileError(
                    msg,
                    construct="annotation",
                    line=node.lineno,
                )
            return left | right
        msg = (
            f"{type(node).__name__} is not allowed in a local annotation; "
            "use a type name or a standard typing subscript"
        )
        raise CompileError(
            msg,
            construct="annotation",
            line=getattr(node, "lineno", None),
        )

    def to_atom(node: ast.expr) -> Atom:
        alternatives = runtime_type_atoms(resolve(node))
        if len(alternatives) != 1:
            msg = (
                f"the local annotation {ast.unparse(node)!r} names "
                f"{len(alternatives)} alternative types; bind one type here"
            )
            raise CompileError(
                msg,
                construct="annotation",
                line=node.lineno,
            )
        return alternatives[0]

    def to_alternatives(node: ast.expr) -> list[Atom]:
        return runtime_type_atoms(resolve(node))

    return to_atom, to_alternatives, resolve


def _initial_scope(params: list[str] | dict[str, str]) -> dict[str, str]:
    return params.copy() if isinstance(params, dict) else {param: binding_name(param) for param in params}


def canonical_aux_set(equations: tuple[Expression, ...], name: str) -> tuple[Expression, ...]:
    """Canonicalize a main equation and all its helper equations together.

    One shared name mapping preserves references between the main equation,
    loop helpers, and lifted definitions. Comparing the whole tuple detects a
    change that exists only in a helper body.
    """
    mapping: dict[str, str] = {}

    def rename(atom: Atom) -> Atom:
        if isinstance(atom, Symbol) and atom.name.startswith(f"{name}--"):
            if atom.name not in mapping:
                stem = atom.name.rsplit("-", 1)[0]
                mapping[atom.name] = f"{stem}-{len(mapping) + 1}"
            return Symbol(mapping[atom.name])
        return atom

    return tuple(cast(Expression, _map_atoms(equation, rename)) for equation in equations)


class Defined[**P, R]:
    """A function that exists twice: as MeTTa equations and as Python.

    Calling the name applies it to encoded argument values and returns every
    engine answer; applying ``S[name]`` stages the term explicitly. The Python body
    stays reachable as ``.py``, with recursion inside it resolving to itself.
    That pair is a differential oracle carried in one object: ``fact(5)``
    against ``fact.py(5)``, for every ground input.
    """

    __slots__ = (
        "__name__",
        "__wrapped__",
        "_py",
        "bodies",
        "body",
        "doc",
        "facts",
        "name",
        "params",
        "patterns",
        "runtime_ops",
        "space",
    )

    def __metta__(self) -> Symbol:
        """Mentioning a function is holding its symbol (guide 3.1).

        A Defined placed in term position encodes as its own head, so
        ``S.memoize(add, 2)`` builds ``(memoize add 2)`` rather than boxing
        the callable; ``G(add)`` stays the explicit spelling for the live
        object.
        """
        return Symbol(self.name)

    def __init__(
        self,
        name: str,
        params: list[str],
        # None only for PrologBacked below, whose fast side is a registered
        # predicate rather than a compiled equation; it overrides both of the
        # readers.
        body: Atom | None,
        py: Callable,
        space: Any,
        *,
        patterns: dict[str, Atom] | None = None,
        runtime_ops: frozenset[str] = frozenset(),
        facts: DefinitionFacts | None = None,
        bodies: tuple[Atom, ...] | None = None,
    ):
        self.name = name
        self.params = params
        self.patterns = dict(patterns or {})
        self.body = body
        self.bodies = () if body is None else (bodies or (body,))
        self._py = py
        self.space = space
        self.doc = inspect.getdoc(py)
        # The prelude operations the equations lean on: empty means the
        # compiled source runs on any evaluator; named means it needs this
        # runtime's registered operations.
        self.runtime_ops = runtime_ops
        self.facts = facts
        self.__name__ = name
        self.__wrapped__ = py

    def __call__(self, *args: Any, **kwargs: Any) -> Atom | Answers[Any]:
        if kwargs:
            args = bind_positional_call(self.name, self.params, args, kwargs)
        if len(args) != len(self.params):
            msg = f"{self.name} takes {len(self.params)} argument(s), got {len(args)}"
            raise TypeError(msg)
        caller = inspect.currentframe()
        caller = None if caller is None else caller.f_back
        if caller is not None:
            record_sync_engine_call(self.space, self.name, caller)
            if caller.f_code.co_name == "<module>":
                record_event_at_frame(
                    self.space,
                    "module-level-defined-call",
                    self.name,
                    caller,
                )
        head = Symbol(self.name)
        term = Expression([head, *(_encode(a) for a in args)])
        staged = _declare_rules_module._defined_calls_are_staged()
        # Rule variables stage the written application. Ground calls evaluate
        # their argument values; a single answer can be folded into the law.
        if staged and _variables(term):
            return term
        application = apply_sources(head, tuple(Expression([S.noeval, value]) for value in term.args))
        if staged:
            folded = list(self.space.answers(application))
            if len(folded) == 1:
                return _encode(folded[0])
            # Keep the original term when folding would discard multiplicity.
            return term
        _functions._warn_deprecated(self.space, self.name, stacklevel=3)
        return self.space.answers(application)

    @property
    def py(self) -> Callable[P, R]:
        """The ordinary Python function, recursion included."""
        return self._py

    # astroid synthesises __annotations__ into every class's locals, so an
    # intentional override of it reads as a second definition of a name this
    # class never wrote; the pragma is that reading, not a silenced clash.
    @property
    # pylint: disable-next=function-redefined
    def __annotations__(self) -> dict[str, Any]:  # type: ignore[override]
        """The definition's annotations, as the twin carries them.

        `typing.get_type_hints(defined)` reads this attribute and follows
        `__wrapped__` for the globals, so the declared `Annotated` types are
        reachable from the head itself
        [tested: test_a_twin_carries_the_definitions_resolved_annotations].
        """
        return dict(getattr(self._py, "__annotations__", {}))

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        """The canonical first clause's cleaned Python docstring."""
        return self.doc

    @property
    def source_span(self) -> SourceSpan | None:
        """Absolute coordinates of the compiled Python definition."""
        return self.facts.source_span if self.facts is not None else None

    @property
    def free_variables(self) -> tuple[str, ...]:
        """Lexical captures reported by Python's symbol table."""
        return self.facts.free_variables if self.facts is not None else ()

    @property
    def pure(self) -> bool | None:
        """Whether every source call is structurally pure."""
        return self.facts.pure if self.facts is not None else None

    @property
    def effect(self) -> EffectClass | None:
        """The strongest effect reached by this compiled clause."""
        return self.facts.effect if self.facts is not None else None

    @property
    def head(self) -> Expression:
        return Expression(
            [Symbol(self.name), *(self.patterns.get(p, Variable(binding_name(p))) for p in self.params)]
        )

    def source(self) -> str:
        """Every equation in this clause unit as MeTTa source."""
        return "\n".join(f"(= {self.head} {body})" for body in self.bodies)

    def _repr_html_(self) -> str:
        """Show this definition's MeTTa equations in rich notebooks."""
        return f"<pre>{html.escape(self.source())}</pre>"

    def __repr__(self) -> str:
        return f"<defined {self.name}({', '.join(self.params)}) = {self.body}>"


class PrologBacked[**P, R](Defined[P, R]):
    """A function that exists twice, as Prolog and as Python.

    The same pair as Defined and for the same reason, with the fast side
    written in Prolog instead of compiled from the Python. Rewriting a
    defined function in Prolog for speed used to mean deleting the Python,
    and the differential oracle went with it; here the Python stays as the
    reference the fast one is checked against.

    There is no compiled body to print, so source() answers a MeTTa comment
    naming where the Prolog came from.
    """

    __slots__ = ("origin",)

    def __init__(
        self,
        name: str,
        params: list[str],
        py: Callable,
        space: Any,
        origin: str,
    ):
        super().__init__(name, params, None, py, space)
        self.origin = origin

    def source(self) -> str:
        """Name the fast side's origin as a MeTTa comment."""
        description = f"{self.name}/{len(self.params) + 1} registered from {self.origin}"
        return "\n".join(f"; {line}" for line in description.splitlines())

    def __repr__(self) -> str:
        return (
            f"<defined {self.name}({', '.join(self.params)}) "
            f"in prolog from {self.origin}, python twin as .py>"
        )


class Compiled(NamedTuple):
    """Everything one clause compiles to."""

    params: list[str]
    patterns: dict[str, Atom]
    body: Atom
    equation_bodies: tuple[Atom, ...]
    twin: Callable
    generator: bool
    aux: list[Expression]
    runtime_ops: frozenset[str]
    hazards: frozenset[str]
    facts: DefinitionFacts
    libraries: frozenset[str] = frozenset()
    class_dependencies: frozenset[type] = frozenset()


def _is_flat_yield_sequence(statements: list[ast.stmt]) -> bool:
    """Whether each non-docstring top-level statement is one yield site."""
    body = statements
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return bool(body) and all(
        isinstance(statement, ast.Expr) and isinstance(statement.value, (ast.Yield, ast.YieldFrom))
        for statement in body
    )


def compile_function(
    fn: types.FunctionType,
    known: Callable[[str], bool],
    nondet: Callable[[str], bool] | None = None,
    effect: Callable[[str], EffectClass] | None = None,
    metta_name: str | None = None,
    *,
    returns_bool: Callable[[str], bool] | None = None,
    defined_name: Callable[[object], str | None] | None = None,
    call_parameters: Callable[[str, int], tuple[str, ...] | None] | None = None,
    signature: inspect.Signature | None = None,
    class_context: type | None = None,
    method_receiver: str | None = None,
    native_result_types: tuple[Atom, ...] = (),
) -> Compiled:
    """Read a function's source into a Compiled clause.

    The auxiliary equations are the loops' tail-recursive helpers and the
    lifted inner definitions, ready to add before the main equation.
    runtime_ops names the prelude operations the equations lean on, and
    hazards the reasons the Python twin cannot run (a match, a minted
    constructor, an engine-only callee): calling such a twin raises with
    the reasons rather than failing on a NameError.

    `known` answers whether a free identifier names a function the engine
    knows, which separates a call to another definition from a closure over
    a host value. `nondet` answers whether a name is known to answer
    nondeterministically, which decides how `for` and `yield from` iterate
    a call to it. `metta_name` is the equation's own name; it defaults to
    the Python name verbatim, since nothing here rewrites a name the
    author wrote.

    `native_result_types` is the result contract the caller will publish.
    Parameter entry work uses its Atom mask to execute allocation while
    preserving the native result quotation.
    """
    if not isinstance(fn, types.FunctionType):
        msg = f"define expects a Python function, got {type(fn).__name__}"
        raise TypeError(msg)
    # The third host door, beside `py-atom` and `load`: this reads a
    # function's source and compiles host expressions inside it into values
    # the engine will apply. Raised before the read for the reason PEP 578
    # gives, so a hook can refuse; the payload names the function rather than
    # carrying its source, which is what identifies it in a log.
    sys.audit("metta.host", "compile", f"{fn.__module__}.{fn.__qualname__}")
    try:
        source_lines, first_line = inspect.getsourcelines(fn)
        source = textwrap.dedent("".join(source_lines))
    except (OSError, TypeError) as exc:
        msg = (
            f"the source of {fn.__name__} is not available, so it cannot be "
            f"compiled. Define it in a file rather than a bare REPL, or write "
            f"the equation as MeTTa source with m.run."
        )
        raise CompileError(
            msg,
            construct="source",
        ) from exc

    tree = ast.parse(source)
    definition = tree.body[0]
    if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        msg = f"{fn.__name__} is not a function definition"
        raise CompileError(msg, construct="def")
    if isinstance(definition, ast.AsyncFunctionDef):
        msg = (
            "an async function has no MeTTa equation; register it with "
            "@space.op(effect=...) to answer a FutureSpace, or run host-side "
            "async orchestration through aio.AsyncMeTTa.call"
        )
        raise CompileError(
            msg,
            construct="async def",
            line=definition.lineno,
        )

    source_path = inspect.getsourcefile(fn) or inspect.getfile(fn)
    if not (source_path.startswith("<") and source_path.endswith(">")):
        source_path = str(Path(source_path).resolve())

    try:
        # A declaration that has already bound Python's call grammar supplies
        # its complete positional layout. Literal defaults remain patterns
        # only for the ordinary equation-definition notation.
        params, patterns = (
            _parameters(definition) if signature is None
            else (list(signature.parameters), {})
        )
        # The head fixes literal inputs; the body still has their local names.
        # Bind those values after lowering so every nested scope sees them.
        scope = _initial_scope(params)
        entry_bindings = {} if signature is None else call_syntax.parameter_scope(signature, scope)
        namespace = _function_namespace(fn)
        closure_names = set(fn.__code__.co_freevars)
        closure_values: dict[str, Any] = {}
        for identifier, cell in zip(fn.__code__.co_freevars, fn.__closure__ or (), strict=True):
            try:
                closure_values[identifier] = cell.cell_contents
            except ValueError:
                continue
        host_values = fn.__globals__ | closure_values
        builders = frozenset(
            identifier
            for identifier, expected in {"S": S, "V": V, "fn": fn_namespace}.items()
            if host_values.get(identifier) is expected
        )

        def host(identifier: str) -> bool:
            return identifier in host_values or identifier in closure_names

        def host_value(identifier: str) -> Any:
            return namespace.get(identifier, _MISSING_HOST)

        annotation_resolver, annotation_alternatives, annotation_value = _annotation_resolver(fn)

        def annotation_is_native_number(annotation: ast.expr | None) -> bool:
            if annotation is None:
                return False
            try:
                # policy-inventory-exempt: mechanism-internal; reason=exact built-in int and float annotations are the compiler's proof for pure engine numeric lowering; evidence=extensions/python/metta/_declare/define.py:annotation_is_native_number
                return annotation_value(annotation) in {int, float}
            except CompileError:
                # Numeric lowering is an optional proof. The established
                # annotation consumer below still owns strict diagnostics.
                return False

        arguments = [
            *definition.args.posonlyargs, *definition.args.args,
            *definition.args.kwonlyargs,
        ]
        number_parameters = {
            argument.arg
            for argument in arguments
            if annotation_is_native_number(argument.annotation)
        }
        number_return = annotation_is_native_number(definition.returns)

        def annotation_names_space(annotation: ast.expr) -> bool:
            # This eager probe only decides whether a parameter is a space
            # handle. A STRUCTURED annotation the resolver cannot name (a
            # subscripted domain builder, a spelling outside the typing
            # whitelist) is simply not one; the strict refusal still runs
            # wherever the annotation is consumed as a type. A bare NAME that
            # resolves nowhere keeps the loud refusal: `target: Space` with the
            # import missing must not silently turn the body's removal
            # statements into arithmetic
            # [tested: test_an_unresolvable_annotation_is_not_a_space_parameter].
            try:
                return annotation_resolver(annotation) == Symbol("SpaceType")
            except CompileError:
                if isinstance(annotation, ast.Name):
                    raise
                return False

        space_parameters = {
            argument.arg
            for argument in arguments
            if argument.annotation is not None and annotation_names_space(argument.annotation)
        }
        record_parameters = {}
        for argument in arguments:
            if argument.annotation is None:
                continue
            try:
                owner = _records.declared(annotation_value(argument.annotation))
            except CompileError:
                # A Python class is an optional receiver proof. Atom-valued
                # annotations keep their ordinary declaration-time meaning.
                continue
            if owner is not None:
                record_parameters[argument.arg] = owner.cls
        if class_context is not None and method_receiver is not None:
            record_parameters[method_receiver] = class_context
        containers = {} if signature is None else {
            name: "tuple" if parameter.kind is inspect.Parameter.VAR_POSITIONAL else "dict"
            for name, parameter in signature.parameters.items()
            if parameter.kind in (
                inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD
            )
        }
        dictionaries = {name for name, kind in containers.items() if kind == "dict"}
        compiler = _Compiler(
            metta_name or fn.__name__,
            scope,
            known,
            nondet=nondet,
            returns_bool=returns_bool,
            pyname=fn.__name__,
            host=host,
            builders=builders,
            host_value=host_value,
            defined_name=defined_name,
            annotation_resolver=annotation_resolver,
            annotation_value=annotation_value,
            function=fn,
            source=source,
            source_path=source_path,
            first_line=first_line,
            call_parameters=call_parameters,
            signature_params=tuple(params),
            space_locals=space_parameters,
            number_locals=number_parameters,
            number_return=number_return,
            annotation_alternatives=annotation_alternatives,
            record_locals=record_parameters,
            class_context=class_context,
            method_receiver=method_receiver,
            container_locals=containers,
            dict_locals=dictionaries,
            libraries={"dict"} if dictionaries else set(),
        )
        compiler.class_dependencies.update(compiler.record_locals.values())
        generator = _is_generator(definition)
        body: Atom
        if generator:
            # A generator is nondeterminism: each yield is one answer, which is
            # exactly what superpose spells; branches contribute their own
            # superpositions and evaluation flattens them.
            answers = compiler.yield_answers(definition.body)
            body = _superpose(answers)
            equation_bodies = (
                tuple(answers) if _is_flat_yield_sequence(definition.body) else (body,)
            )
        else:
            body = compiler.block(definition.body)
            equation_bodies = (body,)
        if entry_bindings:
            body = call_syntax.parameter_body(body, entry_bindings, native_result_types)
            equation_bodies = (body,)
        written_body = body
        body = _bind_head_parameters(body, patterns)
        equation_bodies = tuple(
            body if equation is written_body else _bind_head_parameters(equation, patterns)
            for equation in equation_bodies
        )
    except CompileError as refusal:
        # Statement walls raise with the function-relative line alone;
        # the caret block is derived once here from the held source
        # rather than threaded through every raise site.
        raise with_coordinates(
            refusal,
            source=source,
            first_line=first_line,
            path=source_path,
            function=fn.__name__,
        ) from refusal.__cause__
    facts = derive_definition_facts(
        fn,
        definition,
        source=source,
        source_lines=source_lines,
        first_line=first_line,
        known=known,
        effect=_provided(effect, _unknown_effect),
        host_island_names=frozenset(
            identifier for identifier, value in namespace.items() if value is _py_marker
        ),
        space_locals=compiler.space_locals,
    )
    twin = _python_twin(fn, patterns)
    twin.__doc__ = facts.doc
    return Compiled(
        params,
        patterns,
        body,
        equation_bodies,
        twin,
        generator,
        compiler.aux,
        frozenset(compiler.runtime_ops),
        frozenset(compiler.hazards),
        facts,
        frozenset(compiler.libraries),
        frozenset((*compiler.class_dependencies, *compiler.record_locals.values())),
    )


def _parameters(node: ast.FunctionDef) -> tuple[list[str], dict[str, Atom]]:
    """Parameter names, plus head patterns spelled as literal defaults.

    A literal default is not a Python default here: it is the equation's head
    pattern for that position, so stacked definitions read as clauses:

        def fib(n=0): return 0
        def fib(n=1): return 1
        def fib(n):   return fib(n - 1) + fib(n - 2)

    Clause order is definition order, the engine's own rule. A non-literal
    default stays refused, since an arbitrary object has no head pattern.
    """
    a = node.args
    if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs:
        msg = (
            "a compiled function takes plain positional parameters; *args, "
            "**kwargs and keyword-only parameters have no MeTTa equivalent"
        )
        raise CompileError(
            msg,
            construct="arguments",
            line=node.lineno,
        )
    params = [arg.arg for arg in a.args]
    patterns: dict[str, Atom] = {}
    for arg, default in zip(reversed(a.args), reversed(a.defaults), strict=False):
        if not (
            isinstance(default, ast.Constant)
            and (default.value is None or isinstance(default.value, (bool, int, float, str)))
        ):
            msg = (
                "a default here is a head pattern, so it must be a literal: "
                "def fib(n=0) makes an equation matching 0. For an optional "
                "argument, define two functions or register an operation."
            )
            raise CompileError(
                msg,
                construct="defaults",
                line=node.lineno,
            )
        patterns[arg.arg] = Grounded(default.value)
    return params, patterns


def _bind_head_parameters(body: Atom, patterns: dict[str, Atom]) -> Atom:
    """Give a body's referenced literal parameters their matched values."""
    if not patterns:
        return body
    variables = set(_variables(body))
    for name, value in reversed(patterns.items()):
        variable = binding_name(name)
        if variable in variables:
            body = Expression([
                S.let, Variable(variable), Expression([S.noeval, value]), body,
            ])
    return body


class _Compiler(
    StatementCompilerMixin, LoopCompilerMixin, ExpressionCompilerMixin, ast.NodeVisitor
):
    """Python syntax to MeTTa terms, one construct at a time.

    scope maps each Python name to the MeTTa variable currently holding it.
    Rebinding a name mints a fresh variable (x, then x-2, then x-3), the
    static-single-assignment discipline: a let* pair whose sides share a
    variable would unify them, so `x = x + 1` must bind a new name. The
    minted names carry a hyphen, which no Python identifier can, so they
    never collide with source names. Branches fork the scope, since a
    rebind inside one arm must not leak into the other.
    """

    def __init__(
        self,
        name: str,
        params: list[str] | dict[str, str],
        known: Callable[[str], bool],
        *,
        used: set[str] | None = None,
        nondet: Callable[[str], bool] | None = None,
        returns_bool: Callable[[str], bool] | None = None,
        aux: list | None = None,
        lifted: dict | None = None,
        closer: Callable[[_Compiler], Atom] | None = None,
        pyname: str | None = None,
        host: Callable[[str], bool] | None = None,
        builders: frozenset[str] = frozenset(),
        host_value: Callable[[str], Any] | None = None,
        defined_name: Callable[[object], str | None] | None = None,
        call_parameters: Callable[[str, int], tuple[str, ...] | None] | None = None,
        signature_params: tuple[str, ...] = (),
        runtime_ops: set[str] | None = None,
        hazards: set[str] | None = None,
        annotation_resolver: Callable[[ast.expr], Atom] | None = None,
        annotation_alternatives: Callable[[ast.expr], list[Atom]] | None = None,
        annotation_value: Callable[[ast.expr], Any] | None = None,
        space_locals: set[str] | None = None,
        function: types.FunctionType | None = None,
        source: str = "",
        source_path: str = "<unknown>",
        first_line: int = 1,
        loop_depth: int = 0,
        handler_error: str | None = None,
        in_try_body: bool = False,
        type_aliases: dict[str, list[Atom]] | None = None,
        pragma_globals: set[str] | None = None,
        libraries: set[str] | None = None,
        dict_locals: set[str] | None = None,
        container_locals: dict[str, str] | None = None,
        number_locals: set[str] | None = None,
        number_return: bool = False,
        record_locals: dict[str, type] | None = None,
        class_context: type | None = None,
        class_dependencies: set[type] | None = None,
        construction: tuple[Any, str] | None = None,
        constructor_return: Callable[[_Compiler], Atom] | None = None,
        method_receiver: str | None = None,
    ):
        self.name = name
        # The Python spelling of the definition's own name, for recursion
        # written the way the author wrote it; self.name is the MeTTa one.
        self.pyname = pyname or name
        self._builtins = _builtins_namespace()
        # Whether an identifier resolves to a host binding (a global or a
        # closure cell): a capitalized name that does is a module constant,
        # not a data constructor, and compiles to a refusal.
        self.host = _provided(host, _never)
        self.builders = builders
        self.host_value = _provided(host_value, lambda _name: _MISSING_HOST)
        self.defined_name = _provided(defined_name, lambda _value: None)
        self._given_call_parameters = _provided(call_parameters, lambda _name, _arity: None)
        self.signature_params = signature_params
        # The prelude operations this definition leans on, and the reasons
        # its Python twin cannot run (a match, a constructor); both shared
        # across every compiler of the definition, like aux.
        self.runtime_ops: set[str] = _provided(runtime_ops, set())
        self.hazards: set[str] = _provided(hazards, set())
        self.scope = _initial_scope(params)
        self.known = known
        # Whether a name is known to answer nondeterministically (a compiled
        # generator or a generator operation): iterating one binds the call
        # directly, since the call itself is the fork.
        self._given_nondet = _provided(nondet, _never)
        self.returns_bool = _provided(returns_bool, _never)
        # Every variable name any compiler of this definition has minted;
        # shared across forks so two branches never mint the same fresh name.
        self.used: set[str] = _provided(used, set(self.scope.values()))
        # Auxiliary equations this definition grows: loop helpers and lifted
        # inner definitions, shared by every compiler of the definition.
        self.aux: list[Expression] = _provided(aux, [])
        # Python name -> (equation name, lifted outer names, is_generator)
        # for inner defs; a call site prepends the lifted names' CURRENT
        # variables, which is Python's own late binding, resolved per call.
        self.lifted: dict[str, tuple[str, list[str], bool]] = _provided(lifted, {})
        # What a block falling off its end means: an absent closer returns
        # the Python None value; a loop body's closer
        # builds the recursive call from the scope at that point.
        self.closer = closer
        # The scope NAMES that closer reads, visible to state analysis: a
        # nested loop must carry them even when its own syntax never
        # mentions them, or the enclosing recursion loses its state.
        self.closer_names: list[str] = []
        self._annotation_resolver = annotation_resolver
        self._annotation_alternatives = annotation_alternatives
        self._annotation_value = annotation_value
        self.function = function
        self.source = source
        self.source_path = source_path
        self.first_line = first_line
        self.loop_depth = loop_depth
        # The innermost enclosing except arm's error key (lexical), the
        # definition's `type` aliases, and its `global` pragma names; the
        # last two are shared across every compiler of the definition.
        self.handler_error = handler_error
        self.in_try_body = in_try_body
        self.type_aliases: dict[str, list[Atom]] = _provided(type_aliases, {})
        self.pragma_globals: set[str] = _provided(pragma_globals, set())
        # Library aliases the equations lean on, definition-shared; and the
        # locals holding a dict-space, forked like space_locals.
        self.libraries: set[str] = _provided(libraries, set())
        self.dict_locals: set[str] = _provided(dict_locals, set())
        self.container_locals: dict[str, str] = _provided(container_locals, {})
        self.number_locals: set[str] = _provided(number_locals, set())
        self.number_return = number_return
        self.record_locals = _provided(record_locals, {})
        self.class_context = class_context
        self.class_dependencies = _provided(class_dependencies, set())
        self.construction = construction
        self.constructor_return = constructor_return
        self.method_receiver = method_receiver
        # Local names currently bound to a SPACE value: (context-space),
        # (new-space ...) or a closure handle. += and -= on one of these
        # are write operations, never arithmetic; forks copy the set the
        # way they copy scope, since an arm's binding must not leak.
        self.space_locals: set[str] = _provided(space_locals, set())

    def annotation_atom(self, node: ast.expr) -> Atom:
        if isinstance(node, ast.Name) and node.id in self.type_aliases:
            # A single-type alias inlines its atom, since the in-place
            # claim checker reads atoms rather than rewriting; a union
            # alias stays the symbol its equations define.
            alternatives = self.type_aliases[node.id]
            if len(alternatives) == 1:
                return alternatives[0]
            return Symbol(node.id)
        if self._annotation_resolver is None:
            msg = "this compiler has no local annotation namespace"
            raise CompileError(
                msg,
                construct="annotation",
                line=node.lineno,
            )
        return self._annotation_resolver(node)

    def annotation_alternatives(self, node: ast.expr) -> list[Atom]:
        if self._annotation_alternatives is None:
            msg = "this compiler has no local annotation namespace"
            raise CompileError(
                msg,
                construct="annotation",
                line=node.lineno,
            )
        return self._annotation_alternatives(node)

    def annotation_is_native_number(self, node: ast.expr) -> bool:
        """Whether an annotation resolves to exact built-in int or float."""
        if self._annotation_value is None:
            return False
        try:
            # policy-inventory-exempt: mechanism-internal; reason=exact built-in int and float annotations are the compiler context's proof for pure engine numeric lowering; evidence=extensions/python/metta/_declare/define.py:annotation_is_native_number
            return self._annotation_value(node) in {int, float}
        except CompileError:
            # The ordinary annotation consumer below owns strict diagnostics;
            # this optional proof only decides whether a pure fast path is safe.
            return False

    def nondet(self, called: str) -> bool:
        lifted = self.lifted.get(called)
        if lifted is not None:
            return lifted[2]
        return self._given_nondet(called)

    def _resolved_call_name(self, called: str) -> str:
        """Apply the compiled body's exact-then-mapped callee rule."""
        return self._resolved_name(called) or called

    def _resolved_name(self, identifier: str) -> str | None:
        """Use one resolver for recursive, sibling, and catalog names."""
        if identifier in self.lifted:
            return identifier
        if identifier in (self.pyname, self.name):
            return self.name
        if defined_name := self._bound_defined_name(identifier):
            return defined_name
        return resolve_known_name(
            identifier,
            self.known,
            allow_mapped=not self.host(identifier),
        )

    def _bound_defined_name(self, identifier: str) -> str | None:
        """The MeTTa name carried by a lexically bound Defined, if any."""
        value = self.host_value(identifier)
        return value.name if isinstance(value, Defined) else self.defined_name(value)

    def call_parameters(self, called: str, arity: int) -> tuple[str, ...] | None:
        """Return positional parameter names only when this call shape is known."""
        if called == self.name and arity == len(self.signature_params):
            return self.signature_params
        return self._given_call_parameters(called, arity)

    def _bound_call_parameters(self, identifier: str, arity: int) -> tuple[str, ...] | None:
        """Read parameters only from an exact lexically bound Defined value."""
        value = self.host_value(identifier)
        if isinstance(value, Defined) and arity == len(value.params):
            return tuple(value.params)
        return None

    def _fork(self) -> _Compiler:
        """A compiler for one branch: its own scope, the shared minted set."""
        return self._nested_compiler(self.scope.copy())

    def _nested_compiler(self, scope: dict[str, str]) -> _Compiler:
        nested = self._child_compiler(
            scope,
            used=self.used,
            closer=self.closer,
            space_locals=self.space_locals.copy(),
        )
        nested.closer_names = self.closer_names.copy()
        return nested

    def _inner(self, extra: list[str]) -> _Compiler:
        """A compiler for a nested binder (lambda, comprehension): the outer
        scope plus fresh parameters. Native variables share by identity across
        the whole term, so a shadow must not reuse the outer variable.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        nested = self._nested_compiler(self.scope.copy())
        nested.number_locals.difference_update(extra)
        nested.space_locals.difference_update(extra)
        nested.dict_locals.difference_update(extra)
        for name in extra:
            nested._bind(name)
            nested.container_locals.pop(name, None)
            nested.record_locals.pop(name, None)
        return nested

    def _equation_compiler(self, params: list[str], closer=None) -> _Compiler:
        """A compiler for a NEW equation (a loop helper, a lifted def):
        fresh variable namespace, shared aux and lifted registries.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._child_compiler(params, used=None, closer=closer)

    def _child_compiler(
        self,
        params: list[str] | dict[str, str],
        *,
        used: set[str] | None,
        closer: Callable[[_Compiler], Atom] | None,
        space_locals: set[str] | None = None,
        dict_locals: set[str] | None = None,
        container_locals: dict[str, str] | None = None,
        number_locals: set[str] | None = None,
    ) -> _Compiler:
        """Propagate shared definition context into every compiler child."""
        return _Compiler(
            self.name,
            params,
            self.known,
            used=used,
            nondet=self._given_nondet,
            returns_bool=self.returns_bool,
            aux=self.aux,
            lifted=self.lifted,
            closer=closer,
            pyname=self.pyname,
            host=self.host,
            builders=self.builders,
            host_value=self.host_value,
            defined_name=self.defined_name,
            call_parameters=self._given_call_parameters,
            signature_params=self.signature_params,
            runtime_ops=self.runtime_ops,
            hazards=self.hazards,
            annotation_resolver=self._annotation_resolver,
            annotation_alternatives=self._annotation_alternatives,
            annotation_value=self._annotation_value,
            space_locals=space_locals,
            function=self.function,
            source=self.source,
            source_path=self.source_path,
            first_line=self.first_line,
            loop_depth=self.loop_depth,
            handler_error=self.handler_error,
            in_try_body=self.in_try_body,
            type_aliases=self.type_aliases,
            pragma_globals=self.pragma_globals,
            libraries=self.libraries,
            dict_locals=dict_locals if dict_locals is not None else self.dict_locals.copy(),
            container_locals=container_locals
            if container_locals is not None
            else self.container_locals.copy(),
            number_locals=number_locals if number_locals is not None else self.number_locals.copy(),
            number_return=self.number_return,
            record_locals=self.record_locals.copy(),
            class_context=self.class_context,
            class_dependencies=self.class_dependencies,
            construction=self.construction,
            constructor_return=self.constructor_return,
            method_receiver=self.method_receiver,
        )

    def _iteration(self, iter_node: ast.expr, var: str, body: Atom) -> Expression:
        """`for var in iter_node` around a compiled body.

        A call to a known-nondeterministic name IS the iteration: binding it
        forks once per answer. Anything else evaluates to an expression whose
        elements superpose.
        """
        if _records.answer_stream(self, iter_node):
            return Expression([Symbol("let"), Variable(var), self.expression(iter_node), body])
        source = self.expression(iter_node)
        return Expression(
            [Symbol("let"), Variable(var), Expression([Symbol("superpose"), source]), body]
        )

    def _yield_from(self, node: ast.YieldFrom) -> Atom:
        """Delegate known generators and refuse call-shaped ambiguity.

        ``superpose`` expands an expression's children, so wrapping an engine
        call silently splices its function name and arguments. Delegating every
        call is also wrong: a deterministic call may return iterable data.
        Self-recursion is a generator while its body compiles, and registered
        many-answer operations carry explicit nondeterminism metadata. Every
        other known engine call must choose one of the two unambiguous forms
        named by the refusal.
        """
        value = node.value
        if _records.answer_stream(self, value):
            return self.expression(value)
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            called = value.func.id
            resolved = self._resolved_call_name(called)
            if called in self._builtins and called not in self.scope:
                return Expression([Symbol("superpose"), self.expression(value)])
            if resolved in (self.pyname, self.name) or self.nondet(resolved):
                return self.expression(value)
            if called in self.lifted or self.known(resolved):
                self.expression(value)  # Validate the call before the ruling.
                msg = (
                    f"yield from {called}(...) cannot tell whether to delegate "
                    "engine answers or iterate returned data; use "
                    f"yield {called}(...) to delegate answers, or bind the "
                    "returned data and then yield from that value"
                )
                raise CompileError(
                    msg,
                    construct="yield from call",
                    line=node.lineno,
                )
        return Expression([Symbol("superpose"), self.expression(value)])

    def _bind(self, name: str) -> str:
        """The MeTTa variable a (re)binding of name writes to."""
        base = binding_name(name)
        if name not in self.scope and base not in self.used:
            variable = base
        else:
            n = 2
            while f"{base}-{n}" in self.used:
                n += 1
            variable = f"{base}-{n}"
        self.scope[name] = variable
        self.used.add(variable)
        return variable

    def _python_resolvable(self, identifier: str) -> bool:
        """Whether the twin could resolve this callee: a host binding or a
        Python builtin. An engine-only name makes the twin unrunnable.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return (
            identifier in (self.pyname, self.name)
            or self.host(identifier)
            or identifier in self._builtins
        )

    def _temp(self, base: str) -> str:
        """A fresh variable for the compiler's own use, outside any Python
        name's scope; the hyphen in the spelling keeps it unreachable.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        n = 2
        while f"{base}-{n}" in self.used:
            n += 1
        variable = f"{base}-{n}"
        self.used.add(variable)
        return variable
