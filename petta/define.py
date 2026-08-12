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
  Future Enhancements: f-string lowering once the engine grows a string
    formatting builtin worth targeting; today the refusal names str-append
    operations instead.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
import types
from collections.abc import Callable
from typing import Any

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


class Defined:
    """A function that exists twice: as MeTTa equations and as Python.

    Calling the name builds the term, exactly as applying a symbol does; the
    Python body stays reachable as `.py`, with recursion inside it resolving
    to itself. That pair is a differential oracle carried in one object:
    m.eval(fact(5)) against fact.py(5), for every ground input.
    """

    __slots__ = ("name", "params", "body", "_py", "space", "doc", "__name__", "__wrapped__")

    def __init__(self, name: str, params: list[str], body: Atom, py: Callable, space: Any):
        self.name = name
        self.params = params
        self.body = body
        self._py = py
        self.space = space
        self.doc = py.__doc__
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
        return Expr([Sym(self.name), *(Var(p) for p in self.params)])

    def source(self) -> str:
        """The equation as MeTTa source."""
        return f"(= {self.head} {self.body})"

    def __repr__(self) -> str:
        return f"<defined {self.name}({', '.join(self.params)}) = {self.body}>"


def compile_function(fn: Callable, known: Callable[[str], bool]) -> tuple[list[str], Atom, Callable]:
    """Read a function's source into (parameters, MeTTa body, Python twin).

    `known` answers whether a free identifier names a function the engine
    knows, which separates a call to another definition from a closure over
    a host value.
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

    params = _parameters(definition)
    compiler = _Compiler(fn.__name__, params, known)
    if _is_generator(definition):
        # A generator is nondeterminism: each yield is one answer, which is
        # exactly what superpose spells; branches contribute their own
        # superpositions and evaluation flattens them.
        answers = compiler.yield_answers(definition.body)
        body = _superpose(answers)
    else:
        body = compiler.block(definition.body)
    return params, body, _python_twin(fn)


def _is_generator(node: ast.FunctionDef) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _parameters(node: ast.FunctionDef) -> list[str]:
    a = node.args
    if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs:
        raise CompileError(
            "a compiled function takes plain positional parameters; *args, "
            "**kwargs and keyword-only parameters have no MeTTa equivalent",
            construct="arguments",
            line=node.lineno,
        )
    if a.defaults:
        raise CompileError(
            "a compiled function has no default arguments; an equation's head "
            "is one arity. Define two functions, or register an operation.",
            construct="defaults",
            line=node.lineno,
        )
    return [arg.arg for arg in a.args]


def _python_twin(fn: Callable) -> Callable:
    """The same body with the function's own name bound to itself, so
    recursion inside the twin reaches the twin rather than the term builder."""
    globals_ = dict(fn.__globals__)
    name = fn.__name__
    closure = fn.__closure__
    freevars = fn.__code__.co_freevars

    cell: types.CellType | None = None
    if name in freevars and closure is not None:
        cells = list(closure)
        cell = types.CellType()
        cells[freevars.index(name)] = cell
        closure = tuple(cells)

    twin = types.FunctionType(
        fn.__code__, globals_, name=name, argdefs=fn.__defaults__, closure=closure
    )
    twin.__doc__ = fn.__doc__
    globals_[name] = twin
    if cell is not None:
        cell.cell_contents = twin
    return twin


class _Compiler(ast.NodeVisitor):
    """Python syntax to MeTTa terms, one construct at a time."""

    def __init__(self, name: str, params: list[str], known: Callable[[str], bool]):
        self.name = name
        self.scope = list(params)
        self.known = known

    # ------------------------------------------------------------- statements

    def block(self, statements: list[ast.stmt]) -> Atom:
        """A statement list folded into one term: assignments become let*
        bindings around what follows, if/return close the branch."""
        statements = [s for s in statements if not _is_docstring(s)]
        if not statements:
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

        if isinstance(head, (ast.Assign, ast.AnnAssign)):
            target, value = self._binding(head)
            return Expr([Sym("let*"), Expr([Expr([Var(target), value])]), self.block(rest)])

        if isinstance(head, ast.If):
            return self.if_statement(head, rest, self.block)

        if isinstance(head, (ast.While, ast.For)):
            raise CompileError(
                f"`{type(head).__name__.lower()}` has no equation; write the "
                f"loop as recursion (define a helper that calls itself), or as "
                f"a comprehension over map-atom/filter-atom, or register the "
                f"whole function as an operation with @m.op",
                construct=type(head).__name__,
                line=head.lineno,
            )

        raise CompileError(
            f"{type(head).__name__} has no MeTTa equivalent in the compiled "
            f"subset, which covers expressions, assignment, if/else, return, "
            f"yield, lambda and comprehensions",
            construct=type(head).__name__,
            line=head.lineno,
        )

    def _binding(self, head: ast.Assign | ast.AnnAssign) -> tuple[str, Atom]:
        if isinstance(head, ast.AnnAssign):
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
        self.scope.append(target)
        return target, value

    def if_statement(self, node: ast.If, rest: list[ast.stmt], continue_with) -> Atom:
        test = self.expression(node.test)
        then = continue_with(node.body)
        if node.orelse:
            otherwise = continue_with(node.orelse)
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
            otherwise = continue_with(rest)
        else:
            raise CompileError(
                "an `if` with no `else` and nothing after it leaves one branch "
                "without a value; MeTTa's two-armed `if` needs both",
                construct="if",
                line=node.lineno,
            )
        return Expr([Sym("if"), test, then, otherwise])

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
            raise CompileError(
                "`yield from` has no equation; yield each answer, or register "
                "the generator as an operation with @m.op, where it is native "
                "nondeterminism",
                construct="yield from",
                line=head.lineno,
            )

        if isinstance(head, (ast.Assign, ast.AnnAssign)):
            target, value = self._binding(head)
            tail = _superpose(self.yield_answers(rest))
            return [Expr([Sym("let*"), Expr([Expr([Var(target), value])]), tail])]

        if isinstance(head, ast.If):
            then = _superpose(self.yield_answers(head.body))
            otherwise = (
                _superpose(self.yield_answers(head.orelse))
                if head.orelse
                else Expr([Sym("empty")])
            )
            chooser = Expr([Sym("if"), self.expression(head.test), then, otherwise])
            return [chooser, *(self.yield_answers(rest) if rest else [])]

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
            return Var(node.id)
        if node.id == self.name or node.id in _MAGIC or self.known(node.id):
            return Sym(node.id)
        # Python cannot spell a hyphen, and the engine's own names carry
        # them, so sqrt_math reaches sqrt-math when that is what exists.
        hyphenated = node.id.replace("_", "-")
        if hyphenated != node.id and self.known(hyphenated):
            return Sym(hyphenated)
        if node.id[:1].isupper():
            # The constructor convention: a capitalized free name is data,
            # (Parent $x $y) in a pattern or a tag in an answer.
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
            return Expr([Sym("not"), self.expression(node.operand)])
        if isinstance(node.op, ast.UAdd):
            return self.expression(node.operand)
        raise CompileError(
            f"the unary operator {type(node.op).__name__} has no MeTTa "
            f"function. {_INSTEAD.get(type(node.op), '')}",
            construct=type(node.op).__name__,
            line=node.lineno,
        )

    def _x_Compare(self, node: ast.Compare) -> Atom:
        if len(node.ops) != 1:
            raise CompileError(
                "a chained comparison such as a < b < c has no single MeTTa "
                "term; write (a < b) and (b < c)",
                construct="chained comparison",
                line=node.lineno,
            )
        op = _COMPARE.get(type(node.ops[0]))
        if op is None:
            raise CompileError(
                f"the comparison {type(node.ops[0]).__name__} has no MeTTa function",
                construct=type(node.ops[0]).__name__,
                line=node.lineno,
            )
        return Expr([Sym(op), self.expression(node.left), self.expression(node.comparators[0])])

    def _x_BoolOp(self, node: ast.BoolOp) -> Atom:
        # Python's and/or short-circuit; the engine's are strict. The faithful
        # spelling is if, which evaluates one arm: a and b is (if a b False),
        # a or b is (if a True b), for boolean-valued operands.
        terms = [self.expression(v) for v in node.values]
        folded = terms[-1]
        for term in reversed(terms[:-1]):
            if isinstance(node.op, ast.And):
                folded = Expr([Sym("if"), term, folded, Gnd(False)])
            else:
                folded = Expr([Sym("if"), term, Gnd(True), folded])
        return folded

    def _x_IfExp(self, node: ast.IfExp) -> Atom:
        return Expr(
            [
                Sym("if"),
                self.expression(node.test),
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
        inner = _Compiler(self.name, self.scope + params, self.known)
        body = inner.expression(node.body)
        return Expr([Sym("|->"), Expr([Var(p) for p in params]), body])

    def _x_ListComp(self, node: ast.ListComp) -> Atom:
        """[f(x) for x in xs] is (map-atom xs (|-> ($x) (f $x))), with an
        if-filter composing through filter-atom first."""
        if len(node.generators) != 1:
            raise CompileError(
                "a comprehension with several `for` clauses has no single "
                "map-atom form; nest comprehensions or write recursion",
                construct="comprehension",
                line=node.lineno,
            )
        gen = node.generators[0]
        if gen.is_async:
            raise CompileError(
                "an async comprehension has no equation",
                construct="comprehension",
                line=node.lineno,
            )
        var = _name_of(gen.target, node.lineno)
        source: Atom = self.expression(gen.iter)
        inner = _Compiler(self.name, self.scope + [var], self.known)
        for condition in gen.ifs:
            predicate = Expr(
                [Sym("|->"), Expr([Var(var)]), inner.expression(condition)]
            )
            source = Expr([Sym("filter-atom"), source, predicate])
        mapper = Expr([Sym("|->"), Expr([Var(var)]), inner.expression(node.elt)])
        return Expr([Sym("map-atom"), source, mapper])

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
        callee = self._x_Name(node.func)
        return Expr([callee, *(self.expression(a) for a in node.args)])

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
        self.scope.extend(n for n in pattern_scope.bound if n not in self.scope)
        template = self.expression(template_node)
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
        raise CompileError(
            "an f-string has no MeTTa lowering here; build text with repr and "
            "concat, or register a formatting operation with @m.op",
            construct="f-string",
            line=node.lineno,
        )


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
                return Var(node.id)
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
            head: Atom = Var(head_id) if head_id in self.outer.scope else Sym(head_id)
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


def _superpose(answers: list[Atom]) -> Expr:
    """The answers as one superposition, flattened where a member already is one."""
    flat: list[Atom] = []
    for a in answers:
        if isinstance(a, Expr) and a.head == Sym("superpose") and len(a) == 2:
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
