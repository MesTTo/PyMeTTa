"""Purpose: Python functions compiled into MeTTa equations, so a program can
be written in the language its author, human or model, is fluent in, and run
as PeTTa. The source is read with ast, never traced: tracing loses branches,
which is torch.jit.script's own reason for reading syntax. Three rules hold
the subset together: syntax outside it is a CompileError naming the construct,
the line, and what to write instead; every supported construct has one MeTTa
spelling; and a free identifier must be a
parameter, a known function, or read as a data constructor, so a compiled
body is pure atoms that any evaluator can take whole.
Guarantees:
  - Defined.doc and Defined.__doc__ expose the first compiled clause's cleaned
    docstring after the twin dispatcher contains that clause [tested:
    test_one_docstring_reaches_help_dot_doc_and_get_doc;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - local annotated assignments resolve through a syntax-limited namespace
    reader and compile to enforceable in-place type claims [tested:
    test_an_annotated_binding_emits_its_claim; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - source spans, source docstrings, lexical captures, and call purity are
    derived from the parsed function and exposed as immutable facts [tested:
    test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``yield from`` delegates only a statically known-nondeterministic call
    and refuses an ambiguous engine call instead of silently splicing it
    [tested:
    test_yield_from_a_call_delegates_only_when_nondeterminism_is_known;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - calling a Defined object evaluates its application except in a rules
    builder's scope-local staging context [tested:
    test_calling_a_defined_object_evaluates_and_an_unmatched_call_answers_itself,
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - flat independent yield statements compile to separate equation bodies,
    while control-flow yields retain one superpose body [tested:
    test_flat_generator_emits_one_equation_per_yield,
    test_loop_yields_remain_one_superpose_equation; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import inspect
import textwrap
import types
from collections.abc import Callable
from typing import Any, NamedTuple, cast

from ._define_expression import ExpressionCompilerMixin
from ._define_facts import DefinitionFacts, SourceSpan, derive_definition_facts
from ._define_loops import LoopCompilerMixin
from ._define_statements import StatementCompilerMixin, _is_generator, _superpose
from ._define_twins import (
    _python_twin,
)
from ._rules import _defined_calls_are_staged
from ._space_objects import _stats_active
from ._type_annotations import type_atoms_for
from .atoms import Atom, Expression, Grounded, Symbol, Variable, _encode, _map_atoms
from .errors import CompileError
from .results import Answers

__all__ = ["Defined", "DefinitionFacts", "PrologBacked", "SourceSpan", "compile_function"]



def _provided[T](value: T | None, default: T) -> T:
    return default if value is None else value


def _never(_name: str) -> bool:
    return False


def _deferred_main_engine_answers(space: Any, term: Expression):
    """Delay one eager main-engine evaluation until the first answer pull."""
    yield from space.eval(term)


def _builtins_namespace() -> dict[str, Any]:
    return __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)


def _annotation_resolver(fn: types.FunctionType) -> Callable[[ast.expr], Atom]:  # noqa: C901  -- _annotation_resolver keeps the annotation namespace and its resolvers together so its branches share one state
    """Resolve local annotation syntax without executing arbitrary source."""
    nonlocals: dict[str, Any] = {}
    for name, cell in zip(fn.__code__.co_freevars, fn.__closure__ or (), strict=True):
        try:
            nonlocals[name] = cell.cell_contents
        except ValueError:
            # A decorator is compiling the recursive function before Python
            # assigns its name into the closure cell. It cannot resolve an
            # annotation from that empty cell and does not need to.
            continue
    namespace = {
        **_builtins_namespace(),
        **fn.__globals__,
        **nonlocals,
    }

    def resolve(node: ast.expr) -> Any:  # noqa: C901  -- resolve keeps the annotation syntax forms together so its branches share one state
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
            # policy-inventory-exempt: mechanism-internal; reason=only these three modules define the subscripts that are typing constructors, so subscripting anything else would run user code while resolving an annotation; evidence=bindings/python/petta/define.py:_annotation_resolver
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
        alternatives = type_atoms_for(resolve(node))
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

    return to_atom


def _initial_scope(params: list[str] | dict[str, str]) -> dict[str, str]:
    return params.copy() if isinstance(params, dict) else {param: param for param in params}


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

    Calling the name evaluates its application and returns every engine
    answer; applying ``S[name]`` stages the term explicitly. The Python body
    stays reachable as ``.py``, with recursion inside it resolving to itself.
    That pair is a differential oracle carried in one object: ``fact(5)``
    against ``fact.py(5)``, for every ground input.
    """

    __slots__ = (
        "__name__",
        "__wrapped__",
        "_py",
        "_uses_main_engine",
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

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
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
        self._uses_main_engine = False
        self.space = space
        self.doc = inspect.getdoc(py)
        # The prelude operations the equations lean on: empty means the
        # compiled source runs on any evaluator; named means it needs this
        # runtime's registered operations.
        self.runtime_ops = runtime_ops
        self.facts = facts
        self.__name__ = name
        self.__wrapped__ = py

    def __call__(self, *args: Any) -> Expression | Answers[Any]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        if len(args) != len(self.params):
            msg = f"{self.name} takes {len(self.params)} argument(s), got {len(args)}"
            raise TypeError(
                msg
            )
        term = Expression([Symbol(self.name), *(_encode(a) for a in args)])
        if _defined_calls_are_staged():
            return term
        if self._uses_main_engine or _stats_active():
            # SWI answer tables belong to the main engine. A child engine is
            # the right suspension mechanism for ordinary lazy evaluation,
            # but a cached definition must populate the table cache_info()
            # subsequently reads [tested:
            # test_a_cached_definition_tables_and_answers_from_its_trie;
            # commit=WORKTREE].
            return Answers(
                _deferred_main_engine_answers(self.space, term),
                space=self.space.name,
                target=term,
            )
        return self.space.answers(term)

    @property
    def py(self) -> Callable[P, R]:
        """The ordinary Python function, recursion included."""
        return self._py

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
        """Whether every source call is a local or declared-pure call."""
        return self.facts.pure if self.facts is not None else None

    @property
    def head(self) -> Expression:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return Expression(
            [Symbol(self.name), *(self.patterns.get(p, Variable(p)) for p in self.params)]
        )

    def source(self) -> str:
        """Every equation in this clause unit as MeTTa source."""
        return "\n".join(f"(= {self.head} {body})" for body in self.bodies)

    def cache_clear(self) -> None:
        """Drop this definition's table, functools.lru_cache's own name.

        The table is the engine's, so this is `(table-clear <head>)` and
        nothing more; calling it on a definition that was never cached is the
        engine's answer to that, not an error invented here.
        """
        self.space.eval(Expression([Symbol("table-clear"), self.head]))

    def cache_info(self) -> dict[str, int]:
        """The table's counters, functools.lru_cache's own name.

        The keys are the engine's, not lru_cache's, because they are what a
        TABLE has and a fixed-size cache does not: `tables`, `answers`,
        `complete-call`, `invalidated` and `reevaluated`. Borrowing hits and
        misses for them would be a translation nobody asked for
        [source: lib/lib_tabling.pl, metta_table_statistics].
        """
        answers = self.space.eval(Expression([Symbol("table-stats"), self.head]))
        if not answers:
            return {}
        return {
            str(row[0]): int(row[1])
            for row in answers[0]
            if isinstance(row, Expression) and len(row) == 2
        }

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"<defined {self.name}({', '.join(self.params)}) = {self.body}>"


class PrologBacked[**P, R](Defined[P, R]):
    """A function that exists twice, as Prolog and as Python.

    The same pair as Defined and for the same reason, with the fast side
    written in Prolog instead of compiled from the Python. Rewriting a
    defined function in Prolog for speed used to mean deleting the Python,
    and the differential oracle went with it; here the Python stays as the
    reference the fast one is checked against.

    There is no compiled body to print, so source() answers where the
    Prolog came from.
    """

    __slots__ = ("origin",)

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
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
        """Where the fast side came from, there being no equation to show."""
        return f"% {self.name}/{len(self.params) + 1} registered from {self.origin}"

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
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
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, (ast.Yield, ast.YieldFrom))
        for statement in body
    )


def compile_function(
    fn: types.FunctionType,
    known: Callable[[str], bool],
    nondet: Callable[[str], bool] | None = None,
    pure: Callable[[str], bool] | None = None,
    metta_name: str | None = None,
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
    """
    if not isinstance(fn, types.FunctionType):
        msg = f"define expects a Python function, got {type(fn).__name__}"
        raise TypeError(msg)
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
        raise CompileError(
            msg, construct="def"
        )
    if isinstance(definition, ast.AsyncFunctionDef):
        msg = "an async function has no MeTTa equation; register it as an operation instead"
        raise CompileError(
            msg,
            construct="async def",
            line=definition.lineno,
        )

    params, patterns = _parameters(definition)
    # A literal-patterned position is fixed by the head, so it is not a
    # variable in the body's scope; naming it there would shadow the match.
    scope = [p for p in params if p not in patterns]
    closure_names = set(fn.__code__.co_freevars)

    def host(identifier: str) -> bool:
        return identifier in fn.__globals__ or identifier in closure_names

    compiler = _Compiler(
        metta_name or fn.__name__,
        scope,
        known,
        nondet=nondet,
        pyname=fn.__name__,
        host=host,
        annotation_resolver=_annotation_resolver(fn),
    )
    generator = _is_generator(definition)
    body: Atom
    if generator:
        # A generator is nondeterminism: each yield is one answer, which is
        # exactly what superpose spells; branches contribute their own
        # superpositions and evaluation flattens them.
        answers = compiler.yield_answers(definition.body)
        body = _superpose(answers)
        equation_bodies = tuple(answers) if _is_flat_yield_sequence(definition.body) else (body,)
    else:
        body = compiler.block(definition.body)
        equation_bodies = (body,)
    facts = derive_definition_facts(
        fn,
        definition,
        source=source,
        source_lines=source_lines,
        first_line=first_line,
        known=known,
        pure=_provided(pure, _never),
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
            and isinstance(default.value, (bool, int, float, str))
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
        aux: list | None = None,
        lifted: dict | None = None,
        closer: Callable[[_Compiler], Atom] | None = None,
        pyname: str | None = None,
        host: Callable[[str], bool] | None = None,
        runtime_ops: set[str] | None = None,
        hazards: set[str] | None = None,
        annotation_resolver: Callable[[ast.expr], Atom] | None = None,
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
        # What a block falling off its end means: None is the function-level
        # reading (a missing return is a refusal); a loop body's closer
        # builds the recursive call from the scope at that point.
        self.closer = closer
        # The scope NAMES that closer reads, visible to state analysis: a
        # nested loop must carry them even when its own syntax never
        # mentions them, or the enclosing recursion loses its state.
        self.closer_names: list[str] = []
        self._annotation_resolver = annotation_resolver

    def annotation_atom(self, node: ast.expr) -> Atom:
        if self._annotation_resolver is None:
            msg = "this compiler has no local annotation namespace"
            raise CompileError(
                msg,
                construct="annotation",
                line=node.lineno,
            )
        return self._annotation_resolver(node)

    def nondet(self, called: str) -> bool:
        lifted = self.lifted.get(called)
        if lifted is not None:
            return lifted[2]
        return self._given_nondet(called)

    def _fork(self) -> _Compiler:
        """A compiler for one branch: its own scope, the shared minted set."""
        return self._nested_compiler(self.scope.copy())

    def _nested_compiler(self, scope: dict[str, str]) -> _Compiler:
        nested = _Compiler(
            self.name,
            scope,
            self.known,
            used=self.used,
            nondet=self._given_nondet,
            aux=self.aux,
            lifted=self.lifted,
            closer=self.closer,
            pyname=self.pyname,
            host=self.host,
            runtime_ops=self.runtime_ops,
            hazards=self.hazards,
            annotation_resolver=self._annotation_resolver,
        )
        nested.closer_names = self.closer_names.copy()
        return nested

    def _inner(self, extra: list[str]) -> _Compiler:
        """A compiler for a nested binder (lambda, comprehension): the outer
        scope plus the binder's own parameters, shadowing by name.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        scope = self.scope.copy()
        scope.update({p: p for p in extra})
        return self._nested_compiler(scope)

    def _equation_compiler(self, params: list[str], closer=None) -> _Compiler:
        """A compiler for a NEW equation (a loop helper, a lifted def):
        fresh variable namespace, shared aux and lifted registries.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _Compiler(
            self.name,
            params,
            self.known,
            used=None,
            nondet=self._given_nondet,
            aux=self.aux,
            lifted=self.lifted,
            closer=closer,
            pyname=self.pyname,
            host=self.host,
            runtime_ops=self.runtime_ops,
            hazards=self.hazards,
            annotation_resolver=self._annotation_resolver,
        )

    def _iteration(self, iter_node: ast.expr, var: str, body: Atom) -> Expression:
        """`for var in iter_node` around a compiled body.

        A call to a known-nondeterministic name IS the iteration: binding it
        forks once per answer. Anything else evaluates to an expression whose
        elements superpose.
        """
        if (
            isinstance(iter_node, ast.Call)
            and isinstance(iter_node.func, ast.Name)
            and self.nondet(iter_node.func.id)
        ):
            return Expression([Symbol("let"), Variable(var), self.expression(iter_node), body])
        source = self.expression(iter_node)
        return Expression([Symbol("let"), Variable(var), Expression([Symbol("superpose"), source]), body])

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
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            called = value.func.id
            if called in self._builtins and called not in self.scope:
                return Expression([Symbol("superpose"), self.expression(value)])
            if called in (self.pyname, self.name) or self.nondet(called):
                return self.expression(value)
            if called in self.lifted or self.known(called):
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
        if name not in self.scope and name not in self.used:
            variable = name
        else:
            n = 2
            while f"{name}-{n}" in self.used:
                n += 1
            variable = f"{name}-{n}"
        self.scope[name] = variable
        self.used.add(variable)
        return variable

    def _python_resolvable(self, identifier: str) -> bool:
        """Whether the twin could resolve this callee: a host binding or a
        Python builtin. An engine-only name makes the twin unrunnable.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self.host(identifier) or identifier in self._builtins

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
