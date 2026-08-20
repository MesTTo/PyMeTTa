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
    test_one_docstring_reaches_help_dot_doc_and_get_doc; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
import inspect
import textwrap
import types
from collections.abc import Callable
from typing import Any, Generic, NamedTuple, ParamSpec, TypeVar, cast

from ._define_expression import ExpressionCompilerMixin
from ._define_loops import LoopCompilerMixin
from ._define_statements import StatementCompilerMixin, _is_generator, _superpose
from ._define_twins import (
    _python_twin,
)
from .atoms import Atom, Expr, Gnd, Sym, Var, encode, map_atoms
from .errors import CompileError

__all__ = ["Defined", "PrologBacked", "compile_function"]

_T = TypeVar("_T")
_P = ParamSpec("_P")
_R = TypeVar("_R")


def _provided(value: _T | None, default: _T) -> _T:
    return default if value is None else value


def _never(_name: str) -> bool:
    return False


def _builtins_namespace() -> dict[str, Any]:
    return __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)


def _initial_scope(params: list[str] | dict[str, str]) -> dict[str, str]:
    return params.copy() if isinstance(params, dict) else {param: param for param in params}


def canonical_aux(equation: Expr, name: str) -> Expr:
    """The equation with its auxiliary names serial-independent, for
    comparing a re-defined clause against the recorded one: every symbol
    `name--kind-N` becomes `name--kind` numbered by first appearance."""
    return canonical_aux_set((equation,), name)[0]


def canonical_aux_set(equations: tuple[Expr, ...], name: str) -> tuple[Expr, ...]:
    """Canonicalize a main equation and all its helper equations together.

    One shared name mapping preserves references between the main equation,
    loop helpers, and lifted definitions. Comparing the whole tuple detects a
    change that exists only in a helper body.
    """
    mapping: dict[str, str] = {}

    def rename(atom: Atom) -> Atom:
        if isinstance(atom, Sym) and atom.name.startswith(f"{name}--"):
            if atom.name not in mapping:
                stem = atom.name.rsplit("-", 1)[0]
                mapping[atom.name] = f"{stem}-{len(mapping) + 1}"
            return Sym(mapping[atom.name])
        return atom

    return tuple(cast(Expr, map_atoms(equation, rename)) for equation in equations)


class Defined(Generic[_P, _R]):
    """A function that exists twice: as MeTTa equations and as Python.

    Calling the name builds the term, exactly as applying a symbol does; the
    Python body stays reachable as `.py`, with recursion inside it resolving
    to itself. That pair is a differential oracle carried in one object:
    m.eval(fact(5)) against fact.py(5), for every ground input.
    """

    __slots__ = (
        "__name__",
        "__wrapped__",
        "_py",
        "body",
        "doc",
        "name",
        "params",
        "patterns",
        "runtime_ops",
        "space",
    )

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
    ):
        self.name = name
        self.params = params
        self.patterns = dict(patterns or {})
        self.body = body
        self._py = py
        self.space = space
        self.doc = inspect.getdoc(py)
        # The prelude operations the equations lean on: empty means the
        # compiled source runs on any evaluator; named means it needs this
        # runtime's registered operations.
        self.runtime_ops = runtime_ops
        self.__name__ = name
        self.__wrapped__ = py

    def __call__(self, *args: Any) -> Expr:
        if len(args) != len(self.params):
            raise TypeError(
                f"{self.name} takes {len(self.params)} argument(s), got {len(args)}"
            )
        return Expr([Sym(self.name), *(encode(a) for a in args)])

    @property
    def py(self) -> Callable[_P, _R]:
        """The ordinary Python function, recursion included."""
        return self._py

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        """The canonical first clause's cleaned Python docstring."""
        return self.doc

    @property
    def head(self) -> Expr:
        return Expr(
            [Sym(self.name), *(self.patterns.get(p, Var(p)) for p in self.params)]
        )

    def source(self) -> str:
        """The equation as MeTTa source."""
        return f"(= {self.head} {self.body})"

    def __repr__(self) -> str:
        return f"<defined {self.name}({', '.join(self.params)}) = {self.body}>"


class PrologBacked(Defined[_P, _R]):
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
        """Where the fast side came from, there being no equation to show."""
        return f"% {self.name}/{len(self.params) + 1} registered from {self.origin}"

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
    twin: Callable
    generator: bool
    aux: list[Expr]
    runtime_ops: frozenset[str]
    hazards: frozenset[str]


def compile_function(
    fn: types.FunctionType,
    known: Callable[[str], bool],
    nondet: Callable[[str], bool] | None = None,
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
        raise TypeError(f"define expects a Python function, got {type(fn).__name__}")
    try:
        source = textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError) as exc:
        raise CompileError(
            f"the source of {fn.__name__} is not available, so it cannot be "
            f"compiled. Define it in a file rather than a bare REPL, or write "
            f"the equation as MeTTa source with m.run.",
            construct="source",
        ) from exc

    tree = ast.parse(source)
    definition = tree.body[0]
    if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise CompileError(
            f"{fn.__name__} is not a function definition", construct="def"
        )
    if isinstance(definition, ast.AsyncFunctionDef):
        raise CompileError(
            "an async function has no MeTTa equation; register it as an operation instead",
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
    )
    generator = _is_generator(definition)
    body: Atom
    if generator:
        # A generator is nondeterminism: each yield is one answer, which is
        # exactly what superpose spells; branches contribute their own
        # superpositions and evaluation flattens them.
        answers = compiler.yield_answers(definition.body)
        body = _superpose(answers)
    else:
        body = compiler.block(definition.body)
    return Compiled(
        params,
        patterns,
        body,
        _python_twin(fn, patterns),
        generator,
        compiler.aux,
        frozenset(compiler.runtime_ops),
        frozenset(compiler.hazards),
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
        raise CompileError(
            "a compiled function takes plain positional parameters; *args, "
            "**kwargs and keyword-only parameters have no MeTTa equivalent",
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
            raise CompileError(
                "a default here is a head pattern, so it must be a literal: "
                "def fib(n=0) makes an equation matching 0. For an optional "
                "argument, define two functions or register an operation.",
                construct="defaults",
                line=node.lineno,
            )
        patterns[arg.arg] = Gnd(default.value)
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
        self.aux: list[Expr] = _provided(aux, [])
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

    def nondet(self, called: str) -> bool:
        lifted = self.lifted.get(called)
        if lifted is not None:
            return lifted[2]
        return self._given_nondet(called)

    def _fork(self) -> _Compiler:
        """A compiler for one branch: its own scope, the shared minted set."""
        forked = _Compiler(
            self.name,
            self.scope.copy(),
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
        )
        forked.closer_names = self.closer_names.copy()
        return forked

    def _inner(self, extra: list[str]) -> _Compiler:
        """A compiler for a nested binder (lambda, comprehension): the outer
        scope plus the binder's own parameters, shadowing by name."""
        scope = self.scope.copy()
        scope.update({p: p for p in extra})
        inner = _Compiler(
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
        )
        inner.closer_names = self.closer_names.copy()
        return inner

    def _equation_compiler(self, params: list[str], closer=None) -> _Compiler:
        """A compiler for a NEW equation (a loop helper, a lifted def):
        fresh variable namespace, shared aux and lifted registries."""
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
        )

    def _iteration(self, iter_node: ast.expr, var: str, body: Atom) -> Expr:
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
            return Expr([Sym("let"), Var(var), self.expression(iter_node), body])
        source = self.expression(iter_node)
        return Expr([Sym("let"), Var(var), Expr([Sym("superpose"), source]), body])

    def _yield_from(self, node: ast.YieldFrom) -> Atom:
        """`yield from e`: a nondeterministic call answers directly, one
        yield per answer; any other iterable superposes its elements."""
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and self.nondet(value.func.id)
        ):
            return self.expression(value)
        return Expr([Sym("superpose"), self.expression(value)])

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
        Python builtin. An engine-only name makes the twin unrunnable."""
        return self.host(identifier) or identifier in self._builtins

    def _temp(self, base: str) -> str:
        """A fresh variable for the compiler's own use, outside any Python
        name's scope; the hyphen in the spelling keeps it unreachable."""
        n = 2
        while f"{base}-{n}" in self.used:
            n += 1
        variable = f"{base}-{n}"
        self.used.add(variable)
        return variable
