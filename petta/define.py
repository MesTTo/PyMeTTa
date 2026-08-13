"""Purpose: Python functions compiled into MeTTa equations, so a program can
be written in the language its author, human or model, is fluent in, and run
as PeTTa. The source is read with ast, never traced: tracing loses branches,
which is torch.jit.script's own reason for reading syntax. Three rules hold
the subset together: syntax outside it is a CompileError naming the construct,
the line, and what to write instead, never a silent fallback; every construct
in the subset has one MeTTa spelling; and a free identifier must be a
parameter, a known function, or read as a data constructor, so a compiled
body is pure atoms that any evaluator can take whole.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
import inspect
import itertools
import textwrap
import types
from collections.abc import Callable
from typing import Any, NamedTuple

from .atoms import Atom, Expr, Gnd, Sym, Var, encode
from .errors import CompileError

__all__ = ["Defined", "compile_function"]

# Python operator to the MeTTa function the engine registers for it. Every
# entry is a name src/metta.pl puts through register_fun/1, and every mapping
# was run on this engine: % follows the divisor's sign exactly as Python's
# does, and / is true division except that an exact quotient of two integers
# stays an integer ((/ 6 2) is 3 where Python says 3.0), so the lowering
# multiplies by 1.0 first and the Python twin agrees to the digit.
_BINOPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Mod: "%",
    ast.Pow: "pow-math",
}

_COMPARE = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.Gt: ">",
    ast.LtE: "<=",
    ast.GtE: ">=",
}

# What to write instead, where the engine could half-express the construct.
_INSTEAD = {
    ast.FloorDiv: "write floor_math(a / b): mapping // directly would return "
    "an integer where Python returns a float, and the Python twin has to "
    "agree on every input",
    ast.MatMult: "register a matrix multiply with @m.op, or use pettorch's "
    "matmul",
    ast.BitAnd: "use `and` on booleans; MeTTa has no bitwise operators",
    ast.BitOr: "use `or` on booleans; MeTTa has no bitwise operators",
    ast.BitXor: "MeTTa has no bitwise operators",
    ast.LShift: "MeTTa has no bitwise operators",
    ast.RShift: "MeTTa has no bitwise operators",
    ast.Invert: "MeTTa has no bitwise operators; `not` negates a boolean",
}

# Names with special meaning inside a compiled body. `match` runs a pattern
# against the running space, the nondeterminism trio passes through, and
# `empty` answers nothing.
_MAGIC = ("match", "superpose", "collapse", "empty")

# Auxiliary equation names (loop helpers, lifted defs) carry a process-wide
# serial, so no two compilations ever share one and re-adding never stacks a
# clause onto an old helper. Idempotence comparison canonicalizes them away.
_AUX_NAMES = itertools.count(1)


def _recursion_closer(helper: str, state: list[str], prefix: list):
    """What a loop body's fall-through means: one more round, with each
    state name's CURRENT variable at that point in the body."""

    def recur(compiler: "_Compiler") -> Expr:
        return Expr(
            [Sym(helper), *prefix, *(Var(compiler.scope[n]) for n in state)]
        )

    return recur


def canonical_aux(equation: Expr, name: str) -> Expr:
    """The equation with its auxiliary names serial-independent, for
    comparing a re-defined clause against the recorded one: every symbol
    `name--kind-N` becomes `name--kind` numbered by first appearance."""
    mapping: dict[str, str] = {}

    def walk(atom: Atom) -> Atom:
        if isinstance(atom, Sym) and atom.name.startswith(f"{name}--"):
            if atom.name not in mapping:
                stem = atom.name.rsplit("-", 1)[0]
                mapping[atom.name] = f"{stem}-{len(mapping) + 1}"
            return Sym(mapping[atom.name])
        if isinstance(atom, Expr):
            return Expr([walk(c) for c in atom])
        return atom

    return walk(equation)


class Defined:
    """A function that exists twice: as MeTTa equations and as Python.

    Calling the name builds the term, exactly as applying a symbol does; the
    Python body stays reachable as `.py`, with recursion inside it resolving
    to itself. That pair is a differential oracle carried in one object:
    m.eval(fact(5)) against fact.py(5), for every ground input.
    """

    __slots__ = (
        "name", "params", "patterns", "body", "_py", "space", "doc",
        "runtime_ops", "__name__", "__wrapped__",
    )

    def __init__(self, name: str, params: list[str], body: Atom, py: Callable, space: Any,
                 patterns: dict[str, Atom] | None = None,
                 runtime_ops: frozenset[str] = frozenset()):
        self.name = name
        self.params = params
        self.patterns = dict(patterns or {})
        self.body = body
        self._py = py
        self.space = space
        self.doc = py.__doc__
        # The prelude operations the equations lean on: empty means the
        # compiled source runs on any evaluator; named means it needs this
        # runtime's registered operations.
        self.runtime_ops = runtime_ops
        self.__name__ = name
        self.__wrapped__ = py

    def __call__(self, *args: Any) -> Expr:
        if len(args) != len(self.params):
            raise TypeError(f"{self.name} takes {len(self.params)} argument(s), got {len(args)}")
        return Expr([Sym(self.name), *(encode(a) for a in args)])

    @property
    def py(self) -> Callable:
        """The ordinary Python function, recursion included."""
        return self._py

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
    fn: Callable,
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
    the Python name with underscores as hyphens, the operation rule.
    """
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
        raise CompileError(f"{fn.__name__} is not a function definition", construct="def")
    if isinstance(definition, ast.AsyncFunctionDef):
        raise CompileError(
            "an async function has no MeTTa equation; register it as an "
            "operation instead",
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
        metta_name or fn.__name__.replace("_", "-"),
        scope,
        known,
        nondet=nondet,
        pyname=fn.__name__,
        host=host,
    )
    generator = _is_generator(definition)
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


def _is_generator(node: ast.FunctionDef) -> bool:
    """Whether THIS function yields: a nested def's yields are its own."""
    stack = list(node.body)
    while stack:
        sub = stack.pop()
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(sub, (ast.Yield, ast.YieldFrom)):
            return True
        stack.extend(ast.iter_child_nodes(sub))
    return False


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
    for arg, default in zip(reversed(a.args), reversed(a.defaults)):
        if not (isinstance(default, ast.Constant) and isinstance(default.value, (bool, int, float, str))):
            raise CompileError(
                "a default here is a head pattern, so it must be a literal: "
                "def fib(n=0) makes an equation matching 0. For an optional "
                "argument, define two functions or register an operation.",
                construct="defaults",
                line=node.lineno,
            )
        patterns[arg.arg] = Gnd(default.value)
    return params, patterns


class TwinDispatcher:
    """The Python twin of a possibly-stacked definition: clause twins in
    definition order, first whose head admits the arguments answers, the
    engine's own first-match reading that the guards compile. Twins of other
    definitions resolve to dispatchers too, so twins compose: a twin calling
    another defined name runs that name's Python, not a term builder."""

    __slots__ = ("name", "clauses")

    def __init__(self, name: str) -> None:
        self.name = name
        self.clauses: list[Callable] = []

    def __call__(self, *args: Any):
        for clause in self.clauses:
            try:
                return clause(*args)
            except _ClauseMiss:
                continue
        raise LookupError(f"{self.name}: no clause's head matches {args!r}")

    @property
    def __name__(self) -> str:
        return self.name

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        return self.clauses[0].__doc__ if self.clauses else None

    def __repr__(self) -> str:
        return f"<python twin of {self.name}, {len(self.clauses)} clause(s)>"


class _ClauseMiss(LookupError):
    """A clause twin refusing arguments its head does not match."""


# (id of a module's globals, name) -> the dispatcher every twin from that
# module resolves the name to; and per module, every twin-globals view built,
# so a later definition becomes visible to earlier twins, Python's own rule
# that a call resolves its callee at call time.
_TWIN_DISPATCHERS: dict[tuple[int, str], TwinDispatcher] = {}
_TWIN_VIEWS: dict[int, list[dict]] = {}


def hazard_twin(name: str, hazards: frozenset[str]) -> Callable:
    """The honest twin for a clause Python cannot run: calling it says
    exactly why, instead of failing on a NameError three frames deep."""

    def unrunnable(*_args, **_kwargs):
        reasons = ", ".join(sorted(hazards))
        raise RuntimeError(
            f"{name}.py cannot run this clause in Python: its body uses "
            f"{reasons}, which exist only in the engine. Evaluate through "
            f"the space instead: m.eval({name}(...))."
        )

    unrunnable.__name__ = name
    return unrunnable


def twin_dispatcher(fn: Callable) -> TwinDispatcher:
    """The dispatcher for fn's name in fn's module, created on first use and
    pushed into every twin-globals view of that module."""
    mid, name = id(fn.__globals__), fn.__name__
    dispatcher = _TWIN_DISPATCHERS.get((mid, name))
    if dispatcher is None:
        dispatcher = _TWIN_DISPATCHERS[(mid, name)] = TwinDispatcher(name)
        for view in _TWIN_VIEWS.get(mid, []):
            view[name] = dispatcher
    return dispatcher


def _python_twin(fn: Callable, patterns: dict[str, Atom] | None = None) -> Callable:
    """One clause's Python twin, head guard included.

    The twin's globals overlay every dispatcher this module has, its own
    name's first of all, so recursion reaches the dispatcher rather than the
    term builder, across clauses and across definitions. A clause with
    literal head patterns raises a clause miss when an argument misses one,
    and the dispatcher moves on.
    """
    globals_ = dict(fn.__globals__)
    mid = id(fn.__globals__)
    for (module_id, other), dispatcher in _TWIN_DISPATCHERS.items():
        if module_id == mid:
            globals_[other] = dispatcher
    _TWIN_VIEWS.setdefault(mid, []).append(globals_)

    name = fn.__name__
    own = twin_dispatcher(fn)
    globals_[name] = own

    closure = fn.__closure__
    freevars = fn.__code__.co_freevars
    if name in freevars and closure is not None:
        cells = list(closure)
        cell = types.CellType()
        cell.cell_contents = own
        cells[freevars.index(name)] = cell
        closure = tuple(cells)

    twin = types.FunctionType(
        fn.__code__, globals_, name=name, argdefs=fn.__defaults__, closure=closure
    )
    twin.__doc__ = fn.__doc__
    if not patterns:
        return twin

    order = list(inspect.signature(fn).parameters)

    def guarded(*args):
        for position, value in zip(order, args):
            expected = patterns.get(position)
            if expected is not None and expected != value:
                raise _ClauseMiss(
                    f"{name}: this clause's head matches {position}={expected}, "
                    f"not {value!r}"
                )
        return twin(*args)

    guarded.__name__ = name
    guarded.__doc__ = fn.__doc__
    return guarded


class _Compiler(ast.NodeVisitor):
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
        used: set[str] | None = None,
        nondet: Callable[[str], bool] | None = None,
        aux: list | None = None,
        lifted: dict | None = None,
        closer: Callable[["_Compiler"], Atom] | None = None,
        pyname: str | None = None,
        host: Callable[[str], bool] | None = None,
        runtime_ops: set[str] | None = None,
        hazards: set[str] | None = None,
    ):
        self.name = name
        # The Python spelling of the definition's own name, for recursion
        # written the way the author wrote it; self.name is the MeTTa one.
        self.pyname = pyname or name
        self._builtins = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
        # Whether an identifier resolves to a host binding (a global or a
        # closure cell): a capitalized name that does is a module constant,
        # not a data constructor, and compiles to a refusal.
        self.host = host or (lambda _: False)
        # The prelude operations this definition leans on, and the reasons
        # its Python twin cannot run (a match, a constructor); both shared
        # across every compiler of the definition, like aux.
        self.runtime_ops: set[str] = runtime_ops if runtime_ops is not None else set()
        self.hazards: set[str] = hazards if hazards is not None else set()
        self.scope: dict[str, str] = (
            dict(params) if isinstance(params, dict) else {p: p for p in params}
        )
        self.known = known
        # Whether a name is known to answer nondeterministically (a compiled
        # generator or a generator operation): iterating one binds the call
        # directly, since the call itself is the fork.
        self._given_nondet = nondet or (lambda _: False)
        # Every variable name any compiler of this definition has minted;
        # shared across forks so two branches never mint the same fresh name.
        self.used: set[str] = used if used is not None else set(self.scope.values())
        # Auxiliary equations this definition grows: loop helpers and lifted
        # inner definitions, shared by every compiler of the definition.
        self.aux: list[Expr] = aux if aux is not None else []
        # Python name -> (equation name, lifted outer names, is_generator)
        # for inner defs; a call site prepends the lifted names' CURRENT
        # variables, which is Python's own late binding, resolved per call.
        self.lifted: dict[str, tuple[str, list[str], bool]] = (
            lifted if lifted is not None else {}
        )
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

    def _fork(self) -> "_Compiler":
        """A compiler for one branch: its own scope, the shared minted set."""
        forked = _Compiler(
            self.name,
            dict(self.scope),
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
        forked.closer_names = list(self.closer_names)
        return forked

    def _inner(self, extra: list[str]) -> "_Compiler":
        """A compiler for a nested binder (lambda, comprehension): the outer
        scope plus the binder's own parameters, shadowing by name."""
        scope = dict(self.scope)
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
        inner.closer_names = list(self.closer_names)
        return inner

    def _equation_compiler(self, params: list[str], closer=None) -> "_Compiler":
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
        return Expr(
            [Sym("let"), Var(var), Expr([Sym("superpose"), source]), body]
        )

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

    # ------------------------------------------------------------- statements

    def block(self, statements: list[ast.stmt]) -> Atom:
        """A statement list folded into one term: assignments become let*
        bindings around what follows, if/return close the branch, and a loop
        becomes its own tail-recursive equation whose parameters are the
        loop state, with everything after the loop living in the equation's
        exit branch, Appel's blocks-as-functions."""
        statements = [s for s in statements if not _is_docstring(s)]
        if not statements:
            if self.closer is not None:
                return self.closer(self)
            raise CompileError(f"{self.name} has no body to compile", construct="body")
        head, rest = statements[0], statements[1:]

        if isinstance(head, ast.Return):
            if rest:
                raise CompileError(
                    "statements after `return` are unreachable and have no equation",
                    construct="return",
                    line=rest[0].lineno,
                )
            if head.value is None:
                raise CompileError(
                    "a compiled function returns a value; a bare `return` has "
                    "nothing to rewrite to",
                    construct="return",
                    line=head.lineno,
                )
            return self.expression(head.value)

        if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            variable, value = self._binding(head)
            return Expr([Sym("let*"), Expr([Expr([Var(variable), value])]), self.block(rest)])

        if isinstance(head, ast.If):
            return self.if_statement(head, rest, lambda c, stmts: c.block(stmts))

        if isinstance(head, ast.While):
            return self._while_statement(head, rest)

        if isinstance(head, ast.For):
            return self._for_statement(head, rest)

        if isinstance(head, ast.FunctionDef):
            self._lift_definition(head)
            return self.block(rest)

        if isinstance(head, (ast.Break, ast.Continue)):
            raise CompileError(
                f"`{type(head).__name__.lower()}` has no equation here; fold "
                f"the exit condition into the loop's test, or return",
                construct=type(head).__name__.lower(),
                line=head.lineno,
            )

        raise CompileError(
            f"{type(head).__name__} has no MeTTa equivalent in the compiled "
            f"subset, which covers expressions, assignment, if/else, return, "
            f"yield, lambda and comprehensions",
            construct=type(head).__name__,
            line=head.lineno,
        )

    def _binding(self, head: ast.Assign | ast.AnnAssign | ast.AugAssign) -> tuple[str, Atom]:
        """One binding: the MeTTa variable to write and the value term.

        The value compiles BEFORE the target rebinds, so `x = x + 1` reads
        the old x on the right and writes a fresh variable on the left.
        """
        if isinstance(head, ast.AugAssign):
            # x += e is x = x <op> e; the desugared node lowers identically.
            target_name = _name_of(head.target, head.lineno)
            value = self._x_BinOp(
                ast.BinOp(
                    left=ast.copy_location(ast.Name(id=target_name, ctx=ast.Load()), head),
                    op=head.op,
                    right=head.value,
                    lineno=head.lineno,
                    col_offset=head.col_offset,
                )
            )
            if target_name not in self.scope:
                raise CompileError(
                    f"{target_name!r} is augmented before it is bound",
                    construct="augmented assignment",
                    line=head.lineno,
                )
            target = target_name
        elif isinstance(head, ast.AnnAssign):
            if head.value is None:
                raise CompileError(
                    "an annotation without a value binds nothing",
                    construct="annotation",
                    line=head.lineno,
                )
            target = _name_of(head.target, head.lineno)
            value = self.expression(head.value)
        else:
            target = _single_target(head)
            value = self.expression(head.value)
        return self._bind(target), value

    def if_statement(self, node: ast.If, rest: list[ast.stmt], continue_with) -> Atom:
        test = self._truthy(node.test)
        # Each arm compiles in its own forked scope: a rebind inside one arm
        # must not rename what the other arm, or anything after, reads.
        then = continue_with(self._fork(), node.body)
        if node.orelse:
            otherwise = continue_with(self._fork(), node.orelse)
            if rest:
                raise CompileError(
                    "statements after an if/else where both branches close are "
                    "unreachable",
                    construct="if",
                    line=rest[0].lineno,
                )
        elif rest:
            # `if c: return a` followed by more statements: the rest is the
            # else branch, Python's own early-return shape.
            otherwise = continue_with(self._fork(), rest)
        elif self.closer is not None:
            # Inside a loop body, falling past the `if` continues the loop.
            otherwise = self.closer(self._fork())
        else:
            raise CompileError(
                "an `if` with no `else` and nothing after it leaves one branch "
                "without a value; MeTTa's two-armed `if` needs both",
                construct="if",
                line=node.lineno,
            )
        return Expr([Sym("if"), test, then, otherwise])

    # ------------------------------------------------------------------ loops

    def _free_reads(self, nodes: list) -> list[str]:
        """Scope names the nodes read, first-appearance order: the loop
        state, since a name never read again need not be carried. An
        augmented assignment's target is a read too: x *= 2 reads x."""
        found: list[str] = []

        def note(identifier: str) -> None:
            if identifier in self.scope and identifier not in found:
                found.append(identifier)

        for node in nodes:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    note(sub.id)
                elif isinstance(sub, ast.AugAssign) and isinstance(
                    sub.target, ast.Name
                ):
                    note(sub.target.id)
        return found

    def _loop_state(self, nodes: list) -> list[str]:
        """The state a loop helper carries: every scope name the loop or its
        continuation reads, plus whatever the enclosing continuation itself
        will read, which the syntax of `nodes` cannot show."""
        state = self._free_reads(nodes)
        for name in self.closer_names:
            if name in self.scope and name not in state:
                state.append(name)
        return state

    def _while_statement(self, node: ast.While, rest: list[ast.stmt]) -> Atom:
        """The loop as its own tail-recursive equation: parameters are the
        loop state, the test chooses between one more round and the exit,
        and the statements after the loop ARE the exit branch. With no break
        in the subset, a while-else always runs, so it prefixes the rest."""
        rest = list(node.orelse) + rest
        state = self._loop_state([node.test, *node.body, *rest])
        helper = f"{self.name}--loop-{next(_AUX_NAMES)}"

        equation_compiler = self._equation_compiler(state)
        equation_compiler.closer_names = list(state)
        recur = _recursion_closer(helper, state, prefix=[])
        body_compiler = equation_compiler._fork()
        body_compiler.closer = recur
        exit_compiler = equation_compiler._fork()
        # The exit continues whatever the enclosing block was continuing.
        exit_compiler.closer = self.closer

        test = equation_compiler._truthy(node.test)
        body = body_compiler.block(node.body)
        exit_branch = exit_compiler.block(rest)
        head = Expr([Sym(helper), *(Var(n) for n in state)])
        self.aux.append(
            Expr([Sym("="), head, Expr([Sym("if"), test, body, exit_branch])])
        )
        return Expr([Sym(helper), *(Var(self.scope[n]) for n in state)])

    def _for_statement(self, node: ast.For, rest: list[ast.stmt]) -> Atom:
        """for x in e: the same equation over the remaining elements,
        decons-atom peeling one per round. A nondeterministic source
        collapses first, which is Python's own single pass over it."""
        target = _name_of(node.target, node.lineno)
        rest = list(node.orelse) + rest
        if target in self._free_reads(rest) or target in self.closer_names:
            raise CompileError(
                f"{target!r} is read after the loop, where Python would hold "
                f"the last element; bind that value to its own name inside "
                f"the loop instead",
                construct="for",
                line=node.lineno,
            )
        state = [
            n
            for n in self._loop_state([*node.body, *rest])
            if n != target
        ]
        helper = f"{self.name}--each-{next(_AUX_NAMES)}"
        sequence = "loop-rest"

        equation_compiler = self._equation_compiler([sequence, *state])
        equation_compiler.closer_names = list(state)
        body_compiler = equation_compiler._fork()
        variable = body_compiler._bind(target)
        tail = body_compiler._temp("tail")
        body_compiler.closer = _recursion_closer(helper, state, prefix=[Var(tail)])
        exit_compiler = equation_compiler._fork()
        exit_compiler.closer = self.closer

        body = Expr(
            [
                Sym("let"),
                Expr([Var(variable), Var(tail)]),
                Expr([Sym("decons-atom"), Var(sequence)]),
                body_compiler.block(node.body),
            ]
        )
        exit_branch = exit_compiler.block(rest)
        head = Expr([Sym(helper), Var(sequence), *(Var(n) for n in state)])
        test = Expr([Sym("=="), Var(sequence), Expr([])])
        self.aux.append(
            Expr([Sym("="), head, Expr([Sym("if"), test, exit_branch, body])])
        )
        source = self._materialized(node.iter)
        return Expr(
            [Sym(helper), source, *(Var(self.scope[n]) for n in state)]
        )

    def _materialized(self, iter_node: ast.expr) -> Atom:
        """An iterable as one expression value: a nondeterministic call's
        answers collapse into a tuple, anything else already is its value."""
        if (
            isinstance(iter_node, ast.Call)
            and isinstance(iter_node.func, ast.Name)
            and self.nondet(iter_node.func.id)
        ):
            return Expr([Sym("collapse"), self.expression(iter_node)])
        return self.expression(iter_node)

    # ---------------------------------------------------- lifted definitions

    def _lift_definition(self, node: ast.FunctionDef) -> None:
        """A nested def, lambda-lifted (Johnsson): its free outer names
        become leading parameters, the equation joins the definition's own,
        and every call site prepends the lifted names' current variables,
        which is Python's late binding resolved per call."""
        if node.args.defaults or node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
            raise CompileError(
                "a nested def takes plain positional parameters; defaults "
                "belong on top-level clauses, where they are head patterns",
                construct="nested def",
                line=node.lineno,
            )
        params = [arg.arg for arg in node.args.args]
        lifted: list[str] = []
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Name)
                and isinstance(sub.ctx, ast.Load)
                and sub.id in self.scope
                and sub.id not in params
                and sub.id not in lifted
            ):
                lifted.append(sub.id)
        mangled = f"{self.name}--{node.name}-{next(_AUX_NAMES)}"
        generator = _is_generator(node)
        self.lifted[node.name] = (mangled, lifted, generator)

        inner = self._equation_compiler(lifted + params)
        if generator:
            body = _superpose(inner.yield_answers(node.body))
        else:
            body = inner.block(node.body)
        head = Expr([Sym(mangled), *(Var(n) for n in lifted + params)])
        self.aux.append(Expr([Sym("="), head, body]))

    # ----------------------------------------------------------- yield blocks

    def yield_answers(self, statements: list[ast.stmt]) -> list[Atom]:
        """A generator body as a list of answer terms.

        Every yield contributes one answer; an if contributes one term
        choosing between its branches' superpositions and never closes the
        block, since both branches fall through in Python; a binding wraps
        everything after it in let*, whose value superposes the tail.
        """
        statements = [s for s in statements if not _is_docstring(s)]
        if not statements:
            raise CompileError(f"{self.name} yields nothing", construct="body")
        head, rest = statements[0], statements[1:]

        if isinstance(head, ast.Expr) and isinstance(head.value, ast.Yield):
            if head.value.value is None:
                raise CompileError(
                    "a bare `yield` has no value to answer",
                    construct="yield",
                    line=head.lineno,
                )
            answer = self.expression(head.value.value)
            return [answer, *(self.yield_answers(rest) if rest else [])]

        if isinstance(head, ast.Expr) and isinstance(head.value, ast.YieldFrom):
            return [
                self._yield_from(head.value),
                *(self.yield_answers(rest) if rest else []),
            ]

        if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            variable, value = self._binding(head)
            tail = _superpose(self.yield_answers(rest))
            return [Expr([Sym("let*"), Expr([Expr([Var(variable), value])]), tail])]

        if isinstance(head, ast.If):
            then = _superpose(self._fork().yield_answers(head.body))
            otherwise = (
                _superpose(self._fork().yield_answers(head.orelse))
                if head.orelse
                else Expr([Sym("empty")])
            )
            chooser = Expr([Sym("if"), self._truthy(head.test), then, otherwise])
            return [chooser, *(self.yield_answers(rest) if rest else [])]

        if isinstance(head, ast.For):
            # `for x in e: <yields>` is iteration as nondeterminism: bind x
            # to each element of e through superpose, answer the body for
            # each. The loop never closes the block, exactly as in Python.
            if head.orelse:
                raise CompileError(
                    "`for ... else` has no equation; the else arm runs on "
                    "non-break exit and this subset has no break",
                    construct="for-else",
                    line=head.lineno,
                )
            body_compiler = self._fork()
            var = body_compiler._bind(_name_of(head.target, head.lineno))
            body = _superpose(body_compiler.yield_answers(head.body))
            looped = self._iteration(head.iter, var, body)
            return [looped, *(self.yield_answers(rest) if rest else [])]

        if isinstance(head, ast.Return):
            raise CompileError(
                "a generator answers through yield; `return` inside one has no "
                "equation",
                construct="return",
                line=head.lineno,
            )

        raise CompileError(
            f"{type(head).__name__} has no place in a compiled generator, "
            f"which covers yield, assignment and if/else",
            construct=type(head).__name__,
            line=head.lineno,
        )

    # ------------------------------------------------------------ expressions

    def expression(self, node: ast.expr) -> Atom:
        method = getattr(self, f"_x_{type(node).__name__}", None)
        if method is None:
            raise CompileError(
                f"{type(node).__name__} has no MeTTa equivalent in the "
                f"compiled subset",
                construct=type(node).__name__,
                line=getattr(node, "lineno", None),
            )
        return method(node)

    def _x_Constant(self, node: ast.Constant) -> Atom:
        if isinstance(node.value, (bool, int, float, str)):
            return Gnd(node.value)
        if node.value is None:
            raise CompileError(
                "None has no MeTTa value; answer nothing by yielding nothing, "
                "or return a symbol such as Nil and match on it",
                construct="None",
                line=node.lineno,
            )
        raise CompileError(
            f"the constant {node.value!r} has no grounded MeTTa form",
            construct="constant",
            line=node.lineno,
        )

    def _x_Name(self, node: ast.Name) -> Atom:
        if node.id in self.scope:
            return Var(self.scope[node.id])
        if node.id == self.pyname or node.id == self.name:
            # Recursion, in either spelling; the equation carries the MeTTa
            # name.
            return Sym(self.name)
        if node.id in _MAGIC:
            return Sym(node.id)
        if self.known(node.id):
            if not self._python_resolvable(node.id):
                self.hazards.add(f"the engine function {node.id}")
            return Sym(node.id)
        # Python cannot spell a hyphen, and the engine's own names carry
        # them, so sqrt_math reaches sqrt-math when that is what exists.
        hyphenated = node.id.replace("_", "-")
        if hyphenated != node.id and self.known(hyphenated):
            if not self._python_resolvable(node.id):
                self.hazards.add(f"the engine function {hyphenated}")
            return Sym(hyphenated)
        if node.id[:1].isupper():
            if self.host(node.id):
                raise CompileError(
                    f"{node.id!r} is a module binding, not a data "
                    f"constructor: compiling it as a symbol would drop its "
                    f"value silently. Pass it as an argument, or inline the "
                    f"literal.",
                    construct="host binding",
                    line=node.lineno,
                )
            # The constructor convention: a capitalized free name is data,
            # (Parent $x $y) in a pattern or a tag in an answer. Data has
            # no Python value, so the twin cannot run a body that mints it.
            self.hazards.add(f"the constructor {node.id}")
            return Sym(node.id)
        raise CompileError(
            f"{node.id!r} is not a parameter of {self.name}, not a function "
            f"the engine knows (as written or with underscores as hyphens), "
            f"and not a capitalized data constructor. A compiled body is pure "
            f"atoms; closing over a host value would pin it to this process. "
            f"Define {node.id!r} first, pass it as an argument, or capitalize "
            f"it if it is data.",
            construct="free identifier",
            line=node.lineno,
        )

    def _x_BinOp(self, node: ast.BinOp) -> Atom:
        if isinstance(node.op, ast.Div):
            # Coercing the left side keeps an exact integer quotient a float,
            # which is what Python's / answers: 6 / 2 is 3.0, never 3.
            left = Expr([Sym("*"), Gnd(1.0), self.expression(node.left)])
            return Expr([Sym("/"), left, self.expression(node.right)])
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise CompileError(
                f"the operator {type(node.op).__name__} has no MeTTa function. "
                f"{_INSTEAD.get(type(node.op), 'Register an operation with @m.op for it')}",
                construct=type(node.op).__name__,
                line=node.lineno,
            )
        return Expr([Sym(op), self.expression(node.left), self.expression(node.right)])

    def _x_UnaryOp(self, node: ast.UnaryOp) -> Atom:
        if isinstance(node.op, ast.USub):
            operand = node.operand
            if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)):
                return Gnd(-operand.value)
            return Expr([Sym("-"), Gnd(0), self.expression(operand)])
        if isinstance(node.op, ast.Not):
            # Python's not is truthiness negated, over any value.
            return Expr([Sym("not"), self._truthy(node.operand)])
        if isinstance(node.op, ast.UAdd):
            return self.expression(node.operand)
        raise CompileError(
            f"the unary operator {type(node.op).__name__} has no MeTTa "
            f"function. {_INSTEAD.get(type(node.op), '')}",
            construct=type(node.op).__name__,
            line=node.lineno,
        )

    def _x_Compare(self, node: ast.Compare) -> Atom:
        terms = [self.expression(v) for v in [node.left, *node.comparators]]
        # A middle operand of a chain is read by two links; Python evaluates
        # it once, so anything that is not already a leaf binds to a
        # temporary before any link is built. Minted names carry a hyphen,
        # unreachable from Python identifiers.
        bindings: list[tuple[str, Atom]] = []
        for i in range(1, len(terms) - 1):
            if not isinstance(terms[i], (Var, Sym, Gnd)):
                temp = self._temp("cmp")
                bindings.append((temp, terms[i]))
                terms[i] = Var(temp)
        links: list[Atom] = []
        for i, op_node in enumerate(node.ops):
            links.append(self._compare_link(op_node, terms[i], terms[i + 1], node.lineno))
        folded = links[-1]
        for link in reversed(links[:-1]):
            # The chain short-circuits exactly as Python's does.
            folded = Expr([Sym("if"), link, folded, Gnd(False)])
        for temp, value in reversed(bindings):
            folded = Expr([Sym("let*"), Expr([Expr([Var(temp), value])]), folded])
        return folded

    def _truthy(self, node: ast.expr) -> Atom:
        """A test position: Python decides by truthiness, so anything not
        already boolean-valued by its syntax wraps in py-truthy, whose
        answer IS bool() of the value. A comparison or a `not` stays bare."""
        if isinstance(node, ast.Compare):
            return self.expression(node)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self.expression(node)
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return Gnd(node.value)
        self.runtime_ops.add("py-truthy")
        return Expr([Sym("py-truthy"), self.expression(node)])

    def _compare_link(self, op_node: ast.cmpop, left: Atom, right: Atom, line) -> Atom:
        """One comparison: order through the engine's numeric functions,
        equality and membership through the prelude, so mixed numeric types
        and containers answer exactly what Python answers."""
        if isinstance(op_node, ast.Eq):
            self.runtime_ops.add("py-eq")
            return Expr([Sym("py-eq"), left, right])
        if isinstance(op_node, ast.NotEq):
            self.runtime_ops.add("py-eq")
            return Expr([Sym("not"), Expr([Sym("py-eq"), left, right])])
        if isinstance(op_node, ast.In):
            self.runtime_ops.add("py-in")
            return Expr([Sym("py-in"), left, right])
        if isinstance(op_node, ast.NotIn):
            self.runtime_ops.add("py-in")
            return Expr([Sym("not"), Expr([Sym("py-in"), left, right])])
        op = _COMPARE.get(type(op_node))
        if op is None:
            raise CompileError(
                f"the comparison {type(op_node).__name__} has no MeTTa function",
                construct=type(op_node).__name__,
                line=line,
            )
        return Expr([Sym(op), left, right])

    def _x_BoolOp(self, node: ast.BoolOp) -> Atom:
        # Python's and/or short-circuit AND answer the deciding operand
        # itself (3 or 7 is 3), so each step binds its operand once and
        # chooses by truthiness. Exactly Python, exactly once each.
        self.runtime_ops.add("py-truthy")
        folded = self.expression(node.values[-1])
        for value in reversed(node.values[:-1]):
            term = self.expression(value)
            temp = self._temp("bool")
            test = Expr([Sym("py-truthy"), Var(temp)])
            if isinstance(node.op, ast.And):
                chosen = Expr([Sym("if"), test, folded, Var(temp)])
            else:
                chosen = Expr([Sym("if"), test, Var(temp), folded])
            folded = Expr(
                [Sym("let*"), Expr([Expr([Var(temp), term])]), chosen]
            )
        return folded

    def _x_IfExp(self, node: ast.IfExp) -> Atom:
        return Expr(
            [
                Sym("if"),
                self._truthy(node.test),
                self.expression(node.body),
                self.expression(node.orelse),
            ]
        )

    def _x_Lambda(self, node: ast.Lambda) -> Atom:
        """A lambda is the engine's own first-class |->."""
        a = node.args
        if a.vararg or a.kwarg or a.kwonlyargs or a.defaults or a.posonlyargs:
            raise CompileError(
                "a compiled lambda takes plain positional parameters",
                construct="lambda",
                line=node.lineno,
            )
        params = [arg.arg for arg in a.args]
        inner = self._inner(params)
        body = inner.expression(node.body)
        return Expr([Sym("|->"), Expr([Var(p) for p in params]), body])

    def _x_ListComp(self, node: ast.ListComp) -> Atom:
        """[f(x) for x in xs] is (map-atom xs (|-> ($x) (f $x))), an
        if-filter composing through filter-atom first. Several `for`
        clauses nest the maps, each outer level flattening its nested
        answers with a left union-atom fold, so the elements arrive in
        Python's own order."""
        for gen in node.generators:
            if gen.is_async:
                raise CompileError(
                    "an async comprehension has no equation",
                    construct="comprehension",
                    line=node.lineno,
                )
        return self._comprehension(node.generators, node.elt, node.lineno)

    def _comprehension(
        self, generators: list[ast.comprehension], elt: ast.expr, line: int
    ) -> Atom:
        gen = generators[0]
        var = _name_of(gen.target, line)
        # The source reads in THIS scope: a later clause's source may use an
        # earlier clause's variable, but never its own.
        source = self.expression(gen.iter)
        inner = self._inner([var])
        for condition in gen.ifs:
            predicate = Expr(
                [Sym("|->"), Expr([Var(var)]), inner._truthy(condition)]
            )
            source = Expr([Sym("filter-atom"), source, predicate])
        if len(generators) == 1:
            mapper = Expr([Sym("|->"), Expr([Var(var)]), inner.expression(elt)])
            return Expr([Sym("map-atom"), source, mapper])
        nested = inner._comprehension(generators[1:], elt, line)
        mapper = Expr([Sym("|->"), Expr([Var(var)]), nested])
        return Expr(
            [
                Sym("foldl-atom"),
                Expr([Sym("map-atom"), source, mapper]),
                Expr([]),
                Sym("union-atom"),
            ]
        )

    def _x_GeneratorExp(self, node: ast.GeneratorExp) -> Atom:
        raise CompileError(
            "a generator expression is lazy Python; write a list "
            "comprehension for map-atom, or a generator function for "
            "nondeterminism",
            construct="generator expression",
            line=node.lineno,
        )

    def _x_Call(self, node: ast.Call) -> Atom:
        if node.keywords:
            raise CompileError(
                "a call in a compiled body passes positional arguments; MeTTa "
                "application has no keywords",
                construct="keyword argument",
                line=node.lineno,
            )
        if not isinstance(node.func, ast.Name):
            raise CompileError(
                "a compiled body calls a plain name; attribute and computed "
                "calls have no equation. Register the object's method as an "
                "operation and call it by name.",
                construct="call",
                line=node.lineno,
            )
        if node.func.id == "match":
            return self._match_call(node)
        if node.func.id == "superpose":
            # superpose(a, b, c): one expression holding the alternatives.
            return Expr(
                [Sym("superpose"), Expr([self.expression(a) for a in node.args])]
            )
        if node.func.id in self.lifted:
            # A lifted inner def: its free names travel as leading
            # arguments, read from the scope AT THE CALL, Python's rule.
            mangled, lifted_names, _ = self.lifted[node.func.id]
            missing = [n for n in lifted_names if n not in self.scope]
            if missing:
                raise CompileError(
                    f"{node.func.id!r} closes over {missing} which are not "
                    f"in scope here",
                    construct="nested def",
                    line=node.lineno,
                )
            return Expr(
                [
                    Sym(mangled),
                    *(Var(self.scope[n]) for n in lifted_names),
                    *(self.expression(a) for a in node.args),
                ]
            )
        # Python's own builtins, where a name in scope has not shadowed them,
        # bridge to the engine functions that mean the same thing.
        if node.func.id in _PYBUILTIN_CALLS and node.func.id not in self.scope:
            return _PYBUILTIN_CALLS[node.func.id](self, node)
        callee = self._x_Name(node.func)
        return Expr([callee, *(self.expression(a) for a in node.args)])

    # -------------------------------------------- Python builtins, bridged

    def _args(self, node: ast.Call, count: int | None, name: str) -> list[Atom]:
        if count is not None and len(node.args) != count:
            raise CompileError(
                f"{name}() compiles with exactly {count} argument(s) here",
                construct=name,
                line=node.lineno,
            )
        return [self.expression(a) for a in node.args]

    def _py_len(self, node: ast.Call) -> Atom:
        # py-len is Python's len: expressions AND strings, since which one
        # arrives is a runtime fact.
        (xs,) = self._args(node, 1, "len")
        self.runtime_ops.add("py-len")
        return Expr([Sym("py-len"), xs])

    def _py_abs(self, node: ast.Call) -> Atom:
        (x,) = self._args(node, 1, "abs")
        return Expr([Sym("abs-math"), x])

    def _py_min(self, node: ast.Call) -> Atom:
        return self._extremum(node, "min")

    def _py_max(self, node: ast.Call) -> Atom:
        return self._extremum(node, "max")

    def _extremum(self, node: ast.Call, which: str) -> Atom:
        # min(xs) reads the elements of one expression; min(a, b, ...) folds
        # the engine's two-place min over the arguments, Python's own split.
        args = self._args(node, None, which)
        if len(args) == 0:
            raise CompileError(f"{which}() needs arguments", construct=which, line=node.lineno)
        if len(args) == 1:
            return Expr([Sym(f"{which}-atom"), args[0]])
        folded = args[-1]
        for term in reversed(args[:-1]):
            folded = Expr([Sym(which), term, folded])
        return folded

    def _py_sum(self, node: ast.Call) -> Atom:
        args = self._args(node, None, "sum")
        if len(args) not in (1, 2):
            raise CompileError(
                "sum() takes an iterable and an optional start",
                construct="sum",
                line=node.lineno,
            )
        start: Atom = args[1] if len(args) == 2 else Gnd(0)
        return Expr([Sym("foldl-atom"), args[0], start, Sym("+")])

    def _py_sorted(self, node: ast.Call) -> Atom:
        (xs,) = self._args(node, 1, "sorted")
        return Expr([Sym("sort-atom"), xs])

    def _py_pow(self, node: ast.Call) -> Atom:
        base, exponent = self._args(node, 2, "pow")
        return Expr([Sym("pow-math"), base, exponent])

    def _py_str_builtin(self, node: ast.Call) -> Atom:
        (value,) = self._args(node, 1, "str")
        self.runtime_ops.add("py-str")
        return Expr([Sym("py-str"), value])

    def _py_repr_builtin(self, node: ast.Call) -> Atom:
        (value,) = self._args(node, 1, "repr")
        self.runtime_ops.add("py-repr")
        return Expr([Sym("py-repr"), value])

    def _py_round(self, node: ast.Call) -> Atom:
        args = self._args(node, None, "round")
        if len(args) not in (1, 2):
            raise CompileError(
                "round() takes a value and an optional digit count",
                construct="round",
                line=node.lineno,
            )
        # The prelude's py-round is Python's round, banker's rounding and
        # all; the engine's round-math rounds half away from zero.
        self.runtime_ops.add("py-round")
        return Expr([Sym("py-round"), *args])

    def _py_range(self, node: ast.Call) -> Atom:
        args = self._args(node, None, "range")
        if len(args) not in (1, 2, 3):
            raise CompileError(
                "range() takes start, stop and an optional step",
                construct="range",
                line=node.lineno,
            )
        self.runtime_ops.add("py-range")
        return Expr([Sym("py-range"), *args])

    def _x_Subscript(self, node: ast.Subscript) -> Atom:
        source = self.expression(node.value)
        if isinstance(node.slice, ast.Slice):
            if node.slice.step is not None:
                raise CompileError(
                    "a stepped slice has no lowering; take a plain slice "
                    "and a comprehension, or an operation",
                    construct="slice",
                    line=node.lineno,
                )
            self.runtime_ops.add("py-slice")
            no_bound = Sym("py-no-bound")
            lower = (
                self.expression(node.slice.lower)
                if node.slice.lower is not None
                else no_bound
            )
            upper = (
                self.expression(node.slice.upper)
                if node.slice.upper is not None
                else no_bound
            )
            return Expr([Sym("py-slice"), source, lower, upper])
        # py-at is Python indexing itself: zero-based, negatives from the
        # end, strings included, an out-of-range index a loud error. No
        # engine fast path: index-atom cannot index a string, and whether a
        # value is one is a runtime fact.
        self.runtime_ops.add("py-at")
        return Expr([Sym("py-at"), source, self.expression(node.slice)])

    def _match_call(self, node: ast.Call) -> Atom:
        """match(Pattern(...), template) runs against the running space;
        match("&name", pattern, template) names one. Pattern variables are
        the names not otherwise bound, exactly as in source MeTTa."""
        args = node.args
        if len(args) == 3:
            space_node, pattern_node, template_node = args
            if not (
                isinstance(space_node, ast.Constant)
                and isinstance(space_node.value, str)
                and space_node.value.startswith("&")
            ):
                raise CompileError(
                    'match with three arguments names its space first, as a '
                    'string: match("&kb", pattern, template)',
                    construct="match",
                    line=node.lineno,
                )
            space: Atom = Sym(space_node.value)
        elif len(args) == 2:
            pattern_node, template_node = args
            space = Expr([Sym("context-space")])
        else:
            raise CompileError(
                "match takes (pattern, template) or (space, pattern, template)",
                construct="match",
                line=node.lineno,
            )
        pattern_scope = _PatternScope(self)
        pattern = pattern_scope.expression(pattern_node)
        # Names the pattern bound are in scope for the template.
        for bound in pattern_scope.bound:
            if bound not in self.scope:
                self.scope[bound] = bound
                self.used.add(bound)
        template = self.expression(template_node)
        # A match reads the space; Python alone has nothing to run it on.
        self.hazards.add("a match against the space")
        return Expr([Sym("match"), space, pattern, template])

    def _x_Tuple(self, node: ast.Tuple) -> Atom:
        return Expr([self.expression(e) for e in node.elts])

    def _x_List(self, node: ast.List) -> Atom:
        return Expr([self.expression(e) for e in node.elts])

    def _x_Dict(self, node: ast.Dict) -> Atom:
        raise CompileError(
            "a dict literal has no MeTTa form; carry one whole with "
            "petta.val(...) through an operation, or spell the pairs as an "
            "expression of (key value) pairs",
            construct="dict",
            line=node.lineno,
        )

    def _x_JoinedStr(self, node: ast.JoinedStr) -> Atom:
        """An f-string joins its parts through the prelude: literal text as
        itself, {v} as py-str, {v!r} as py-repr, {v:spec} as py-format with
        a literal spec. Exactly Python's building, so the twin agrees to
        the character."""
        self.runtime_ops.add("py-str-join")
        parts: list[Atom] = []
        for piece in node.values:
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                parts.append(Gnd(piece.value))
                continue
            if not isinstance(piece, ast.FormattedValue):
                raise CompileError(
                    "this f-string part has no lowering",
                    construct="f-string",
                    line=node.lineno,
                )
            value = self.expression(piece.value)
            if piece.format_spec is not None:
                spec = piece.format_spec
                if not (
                    isinstance(spec, ast.JoinedStr)
                    and all(
                        isinstance(s, ast.Constant) and isinstance(s.value, str)
                        for s in spec.values
                    )
                ):
                    raise CompileError(
                        "a computed f-string format spec has no lowering; "
                        "write the spec literally, as in {x:.2f}",
                        construct="f-string",
                        line=node.lineno,
                    )
                literal = "".join(s.value for s in spec.values)
                self.runtime_ops.add("py-format")
                parts.append(Expr([Sym("py-format"), value, Gnd(literal)]))
            elif piece.conversion == ord("r"):
                self.runtime_ops.add("py-repr")
                parts.append(Expr([Sym("py-repr"), value]))
            else:
                self.runtime_ops.add("py-str")
                parts.append(Expr([Sym("py-str"), value]))
        return Expr([Sym("py-str-join"), Expr(parts)])


class _PatternScope:
    """Expression compilation inside a match pattern.

    A lowercase free name inside a pattern is a fresh variable the match may
    bind, which is what $x means in source; everything else compiles as
    usual. The names bound here flow into the template's scope.
    """

    def __init__(self, outer: _Compiler):
        self.outer = outer
        self.bound: list[str] = []

    def expression(self, node: ast.expr) -> Atom:
        if isinstance(node, ast.Name):
            if node.id in self.outer.scope:
                return Var(self.outer.scope[node.id])
            if node.id[:1].islower() and not self.outer.known(node.id) and node.id != self.outer.name:
                if node.id not in self.bound:
                    self.bound.append(node.id)
                return Var(node.id)
            return self.outer._x_Name(node)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise CompileError(
                    "a pattern applies a plain constructor name",
                    construct="pattern",
                    line=node.lineno,
                )
            # The head position names the relation, whatever its case:
            # parent(gp, mid) matches (parent ...) atoms, so a lowercase head
            # is the relation symbol, not a fresh variable; a head already in
            # scope stays the variable it is.
            head_id = node.func.id
            head: Atom = (
                Var(self.outer.scope[head_id])
                if head_id in self.outer.scope
                else Sym(head_id)
            )
            return Expr([head, *(self.expression(a) for a in node.args)])
        if isinstance(node, (ast.Tuple, ast.List)):
            return Expr([self.expression(e) for e in node.elts])
        if isinstance(node, ast.Constant):
            return self.outer._x_Constant(node)
        raise CompileError(
            f"{type(node).__name__} has no place in a match pattern, which is "
            f"structural: names, constructors, tuples and constants",
            construct="pattern",
            line=getattr(node, "lineno", None),
        )


# Python builtin -> its lowering. Consulted for a call to one of these names
# when no parameter shadows it; each maps to the engine function that means
# the same thing on the values this subset computes.
_PYBUILTIN_CALLS: dict[str, Callable] = {
    "len": _Compiler._py_len,
    "abs": _Compiler._py_abs,
    "min": _Compiler._py_min,
    "max": _Compiler._py_max,
    "sum": _Compiler._py_sum,
    "sorted": _Compiler._py_sorted,
    "pow": _Compiler._py_pow,
    "str": _Compiler._py_str_builtin,
    "repr": _Compiler._py_repr_builtin,
    "round": _Compiler._py_round,
    "range": _Compiler._py_range,
}


def _superpose(answers: list[Atom]) -> Expr:
    """The answers as one superposition, flattened where a member already is
    one over literal alternatives; (superpose $x) over a bound value stays
    whole, since only an expression of alternatives can splice."""
    flat: list[Atom] = []
    for a in answers:
        if (
            isinstance(a, Expr)
            and a.head == Sym("superpose")
            and len(a) == 2
            and isinstance(a[1], Expr)
        ):
            flat.extend(a[1])
        else:
            flat.append(a)
    return Expr([Sym("superpose"), Expr(flat)])


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _single_target(node: ast.Assign) -> str:
    if len(node.targets) != 1:
        raise CompileError(
            "a chained assignment binds several names at once and has no let* form",
            construct="assignment",
            line=node.lineno,
        )
    return _name_of(node.targets[0], node.lineno)


def _name_of(target: ast.expr, line: int | None) -> str:
    if isinstance(target, ast.Name):
        return target.id
    raise CompileError(
        "a compiled body binds plain names; destructuring and attribute "
        "assignment have no let* form",
        construct="assignment target",
        line=line,
    )
