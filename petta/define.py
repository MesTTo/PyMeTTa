"""Purpose: Python functions compiled into MeTTa equations, so a program can
be written in the language its author, human or model, is fluent in, and run
as PeTTa. The source is read with ast, never traced: tracing loses branches,
which is torch.jit.script's own reason for reading syntax. Three rules hold
the subset together: syntax outside it is a CompileError naming the construct,
the line, and what to write instead; every supported construct has one MeTTa
spelling; and a free identifier must be a
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
from typing import Any, NamedTuple, cast

from ._define_expression import ExpressionCompilerMixin, _name_of
from ._define_twins import (
    _python_twin,
    hazard_twin,
    twin_dispatcher,
)
from .atoms import Atom, Expr, Gnd, Sym, Var, encode, map_atoms
from .errors import CompileError

__all__ = ["Defined", "compile_function"]

# Auxiliary equation names (loop helpers, lifted defs) carry a process-wide
# serial, so no two compilations ever share one and re-adding never stacks a
# clause onto an old helper. Idempotence comparison canonicalizes them away.
_AUX_NAMES = itertools.count(1)


def _recursion_closer(helper: str, state: list[str], prefix: list):
    """What a loop body's fall-through means: one more round, with each
    state name's CURRENT variable at that point in the body."""

    def recur(compiler: "_Compiler") -> Expr:
        return Expr([Sym(helper), *prefix, *(Var(compiler.scope[n]) for n in state)])

    return recur


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


class Defined:
    """A function that exists twice: as MeTTa equations and as Python.

    Calling the name builds the term, exactly as applying a symbol does; the
    Python body stays reachable as `.py`, with recursion inside it resolving
    to itself. That pair is a differential oracle carried in one object:
    m.eval(fact(5)) against fact.py(5), for every ground input.
    """

    __slots__ = (
        "name",
        "params",
        "patterns",
        "body",
        "_py",
        "space",
        "doc",
        "runtime_ops",
        "__name__",
        "__wrapped__",
    )

    def __init__(
        self,
        name: str,
        params: list[str],
        body: Atom,
        py: Callable,
        space: Any,
        patterns: dict[str, Atom] | None = None,
        runtime_ops: frozenset[str] = frozenset(),
    ):
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
        return Expr([Sym(self.name), *(self.patterns.get(p, Var(p)) for p in self.params)])

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
    the Python name with underscores as hyphens, the operation rule.
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
        raise CompileError(f"{fn.__name__} is not a function definition", construct="def")
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
        metta_name or fn.__name__.replace("_", "-"),
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


def _is_generator(node: ast.FunctionDef) -> bool:
    """Whether THIS function yields: a nested def's yields are its own."""
    stack: list[ast.AST] = list(node.body)
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
        if not (
            isinstance(default, ast.Constant) and isinstance(default.value, (bool, int, float, str))
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


class _Compiler(ExpressionCompilerMixin, ast.NodeVisitor):
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
        self.lifted: dict[str, tuple[str, list[str], bool]] = lifted if lifted is not None else {}
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
                    "statements after an if/else where both branches close are unreachable",
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
                elif isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name):
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
        self.aux.append(Expr([Sym("="), head, Expr([Sym("if"), test, body, exit_branch])]))
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
        state = [n for n in self._loop_state([*node.body, *rest]) if n != target]
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
        self.aux.append(Expr([Sym("="), head, Expr([Sym("if"), test, exit_branch, body])]))
        source = self._materialized(node.iter)
        return Expr([Sym(helper), source, *(Var(self.scope[n]) for n in state)])

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
        body: Atom
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
                "a generator answers through yield; `return` inside one has no equation",
                construct="return",
                line=head.lineno,
            )

        raise CompileError(
            f"{type(head).__name__} has no place in a compiled generator, "
            f"which covers yield, assignment and if/else",
            construct=type(head).__name__,
            line=head.lineno,
        )


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
