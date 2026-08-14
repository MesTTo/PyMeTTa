"""Purpose: lower Python expressions into equivalent MeTTa atom trees.
Guarantees:
  - supported expression lowerings preserve Python value and short-circuit
    semantics [tested test_boolean_operators_answer_the_operand,
    test_fstrings_str_round_range_slices]
  - unsupported expressions raise CompileError with their source construct
    [tested test_refusals_name_construct_and_line]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
from collections.abc import Callable

from ._define_context import CompilerContext
from .atoms import Atom, Expr, Gnd, Sym, Var
from .errors import CompileError

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
    ast.MatMult: "register a matrix multiply with @m.register_op, or use pettorch's matmul",
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


class ExpressionCompilerMixin(CompilerContext):
    def expression(self, node: ast.expr) -> Atom:
        method = getattr(self, f"_x_{type(node).__name__}", None)
        if method is None:
            raise CompileError(
                f"{type(node).__name__} has no MeTTa equivalent in the compiled subset",
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
        if node.id in (self.pyname, self.name):
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
                f"{_INSTEAD.get(type(node.op), 'Register an operation with @m.register_op for it')}",
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
        terms = [self.expression(v) for v in (node.left, *node.comparators)]
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
        links = [
            self._compare_link(op_node, terms[i], terms[i + 1], node.lineno)
            for i, op_node in enumerate(node.ops)
        ]
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
            folded = Expr([Sym("let*"), Expr([Expr([Var(temp), term])]), chosen])
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
        return Expr(
            [Sym("|->"), Expr([Var(p) for p in params]), inner.expression(node.body)]
        )

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

    def _comprehension(self, generators: list[ast.comprehension], elt: ast.expr, line: int) -> Atom:
        gen = generators[0]
        var = _name_of(gen.target, line)
        # The source reads in THIS scope: a later clause's source may use an
        # earlier clause's variable, but never its own.
        source = self.expression(gen.iter)
        inner = self._inner([var])
        for condition in gen.ifs:
            predicate = Expr([Sym("|->"), Expr([Var(var)]), inner._truthy(condition)])
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
            return Expr([Sym("superpose"), Expr([self.expression(a) for a in node.args])])
        if node.func.id in self.lifted:
            # A lifted inner def: its free names travel as leading
            # arguments, read from the scope AT THE CALL, Python's rule.
            mangled, lifted_names, _ = self.lifted[node.func.id]
            missing = [n for n in lifted_names if n not in self.scope]
            if missing:
                raise CompileError(
                    f"{node.func.id!r} closes over {missing} which are not in scope here",
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
        if not args:
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
            lower = self.expression(node.slice.lower) if node.slice.lower is not None else no_bound
            upper = self.expression(node.slice.upper) if node.slice.upper is not None else no_bound
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
                    "match with three arguments names its space first, as a "
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
                if not isinstance(spec, ast.JoinedStr):
                    raise CompileError(
                        "a computed f-string format spec has no lowering; "
                        "write the spec literally, as in {x:.2f}",
                        construct="f-string",
                        line=node.lineno,
                    )
                literal_parts: list[str] = []
                for format_piece in spec.values:
                    if not (
                        isinstance(format_piece, ast.Constant)
                        and isinstance(format_piece.value, str)
                    ):
                        raise CompileError(
                            "a computed f-string format spec has no lowering; "
                            "write the spec literally, as in {x:.2f}",
                            construct="f-string",
                            line=node.lineno,
                        )
                    literal_parts.append(format_piece.value)
                literal = "".join(literal_parts)
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

    def __init__(self, outer: CompilerContext):
        self.outer = outer
        self.bound: list[str] = []

    def expression(self, node: ast.expr) -> Atom:
        if isinstance(node, ast.Name):
            if node.id in self.outer.scope:
                return Var(self.outer.scope[node.id])
            if (
                node.id[:1].islower()
                and not self.outer.known(node.id)
                and node.id != self.outer.name
            ):
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
                Var(self.outer.scope[head_id]) if head_id in self.outer.scope else Sym(head_id)
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
    "len": ExpressionCompilerMixin._py_len,
    "abs": ExpressionCompilerMixin._py_abs,
    "min": ExpressionCompilerMixin._py_min,
    "max": ExpressionCompilerMixin._py_max,
    "sum": ExpressionCompilerMixin._py_sum,
    "sorted": ExpressionCompilerMixin._py_sorted,
    "pow": ExpressionCompilerMixin._py_pow,
    "str": ExpressionCompilerMixin._py_str_builtin,
    "repr": ExpressionCompilerMixin._py_repr_builtin,
    "round": ExpressionCompilerMixin._py_round,
    "range": ExpressionCompilerMixin._py_range,
}


def _name_of(target: ast.expr, line: int | None) -> str:
    if isinstance(target, ast.Name):
        return target.id
    raise CompileError(
        "a compiled body binds plain names; destructuring and attribute "
        "assignment have no let* form",
        construct="assignment target",
        line=line,
    )
