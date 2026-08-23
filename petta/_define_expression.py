"""Purpose: lower Python expressions into equivalent MeTTa atom trees.
Guarantees:
  - calls through standard ``math`` and ``operator`` module attributes lower
    through the shared callable mentions while adapters preserve Python call
    order and result kinds [tested:
    test_callable_mentions_share_operator_and_fourteen_math_names,
    test_compiled_callable_mentions_preserve_python_call_semantics;
    commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
  - supported expression lowerings preserve Python value and short-circuit
    semantics [tested test_boolean_operators_answer_the_operand,
    test_fstrings_str_round_range_slices]
  - unsupported expressions raise CompileError with their source construct
    [tested test_refusals_name_construct_and_line]
  - statically bound S, V, and fn builders lower as mentions while bare
    callees ask for exact, hyphenated, then banged catalog spellings [tested:
    test_compiled_bodies_reach_all_four_mention_families,
    test_banged_catalog_names_take_the_mechanical_fallback; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - a host-bound Defined mention lowers to the sibling's declared MeTTa name
    [tested: test_compiled_body_calls_renamed_defined_sibling;
    commit=WORKTREE]
  - host-bound and parameter-carried space handles remain operands of compiled
    match calls [tested: test_compiled_match_accepts_space_handles;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import builtins
import math
import operator
import types
from collections.abc import Callable

from ._callable_mentions import callable_arities, callable_mention
from ._define_context import CompilerContext
from ._name_mapping import attribute_name, resolve_known_name
from .atoms import Atom, Expression, Grounded, Handle, Symbol, Variable
from .errors import CompileError

# Python operator to the MeTTa function the engine registers for it. Every
# entry is a name engine/metta.pl puts through register_fun/1, and every mapping
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
    ast.MatMult: "register a matrix multiply with @m.op, or use pettorch's matmul",
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
        if isinstance(node, ast.Attribute):
            return self._attribute(node)
        method = getattr(self, f"_x_{type(node).__name__}", None)
        if method is None:
            msg = f"{type(node).__name__} has no MeTTa equivalent in the compiled subset"
            raise CompileError(
                msg,
                construct=type(node).__name__,
                line=getattr(node, "lineno", None),
            )
        return method(node)

    def _x_Constant(self, node: ast.Constant) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        if isinstance(node.value, (bool, int, float, str)):
            return Grounded(node.value)
        if node.value is None:
            msg = (
                "None has no MeTTa value; answer nothing by yielding nothing, "
                "or return a symbol such as Nil and match on it"
            )
            raise CompileError(
                msg,
                construct="None",
                line=node.lineno,
            )
        msg = f"the constant {node.value!r} has no grounded MeTTa form"
        raise CompileError(
            msg,
            construct="constant",
            line=node.lineno,
        )

    def _x_Name(self, node: ast.Name) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        if node.id in self.scope:
            return Variable(self.scope[node.id])
        if node.id in _MAGIC:
            return Symbol(node.id)
        host_value = self.host_value(node.id)
        if isinstance(host_value, Handle):
            return host_value
        known = self._known_symbol(node.id)
        if known is not None:
            return known
        if node.id[:1].isupper():
            return self._constructor_symbol(node)
        msg = (
            f"{node.id!r} is not a parameter of {self.name}, not a function "
            f"the engine knows, and not a capitalized data constructor. "
            f"A compiled body is pure atoms; closing over a host value would "
            f"pin it to this process. Define {node.id!r} first, pass it as an "
            f"argument, use fn.{node.id} for a catalog function, or S.{node.id} "
            f"for data. Bare calls ask for {node.id!r} and then "
            f"{attribute_name(node.id)!r}; neither exists here."
        )
        raise CompileError(
            msg,
            construct="free identifier",
            line=node.lineno,
        )

    def _known_symbol(self, identifier: str) -> Symbol | None:
        # Exact catalog names win. A host binding blocks only the fallback:
        # silently choosing sc-edge-to over a Python sc_edge_to object would
        # cross the quotation boundary by surprise. The explicit fn door
        # disambiguates it. This follows CPython's scope-first ordering and
        # SQLAlchemy's expression-object precedent without copying its open
        # ended func namespace. [source:
        # https://docs.python.org/3/reference/executionmodel.html#binding-of-names;
        # commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
        resolved = self._resolved_name(identifier)
        if resolved is None:
            return None
        if not self._python_resolvable(identifier):
            self.hazards.add(f"the engine function {resolved}")
        return Symbol(resolved)

    def _mention(self, node: ast.expr) -> Atom | None:
        """Recognize one statically bound S, V, or fn mention from syntax.

        The compiler never calls getattr on the host object. Like Lisp
        quasiquote and MetaOCaml quotation, the builder marks a staged term;
        only an explicit variable identity or catalog name enters the IR.
        [source: https://www.lispworks.com/documentation/HyperSpec/Body/02_df.htm;
        commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
        """
        root: ast.Name
        exact = False
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            root = node.value
            target = attribute_name(node.attr)
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            root = node.value
            if not (isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
                # policy-inventory-exempt: mechanism-internal; reason=S V and fn are the three fixed quotation-tier builders recognized by compiled-body syntax rather than selectable runtime policy; evidence=bindings/python/petta/_define_expression.py:_mention
                if root.id in {"S", "V", "fn"}:
                    msg = f"{root.id}[...] takes a literal exact target name"
                    raise CompileError(
                        msg,
                        construct="exact name",
                        line=node.lineno,
                    )
                return None
            target = node.slice.value
            exact = True
        else:
            return None
        if root.id in self.scope or root.id not in self.builders:
            return None
        if root.id == "V":
            return Variable(target)
        if root.id == "fn":
            resolved = resolve_known_name(
                target,
                self.known,
                allow_mapped=not exact,
                allow_bang=not exact,
            )
            if resolved is None:
                spelling = f"fn[{target!r}]" if exact else ast.unparse(node)
                msg = f"{spelling} names no target function in this space's catalog"
                raise CompileError(
                    msg,
                    construct="function mention",
                    line=node.lineno,
                )
            return Symbol(resolved)
        return Symbol(target)

    def _attribute(self, node: ast.Attribute) -> Atom:
        """Lower a quotation-tier attribute and refuse host attributes."""
        mention = self._mention(node)
        if mention is not None:
            return mention
        msg = (
            f"{ast.unparse(node)!r} is host attribute access, not a compiled "
            "atom. Use S, V, or fn without shadowing, or register a plain-name operation."
        )
        raise CompileError(msg, construct="attribute", line=node.lineno)

    def _constructor_symbol(self, node: ast.Name) -> Symbol:
        if self.host(node.id):
            msg = (
                f"{node.id!r} is a module binding, not a data "
                f"constructor: compiling it as a symbol would drop its "
                f"value silently. Pass it as an argument, or inline the "
                f"literal."
            )
            raise CompileError(
                msg,
                construct="host binding",
                line=node.lineno,
            )
        # The constructor convention: a capitalized free name is data,
        # (Parent $x $y) in a pattern or a tag in an answer. Data has
        # no Python value, so the twin cannot run a body that mints it.
        self.hazards.add(f"the constructor {node.id}")
        return Symbol(node.id)

    def _x_BinOp(self, node: ast.BinOp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        if isinstance(node.op, ast.Div):
            # Coercing the left side keeps an exact integer quotient a float,
            # which is what Python's / answers: 6 / 2 is 3.0, never 3.
            left = Expression([Symbol("*"), Grounded(1.0), self.expression(node.left)])
            return Expression([Symbol("/"), left, self.expression(node.right)])
        op = _BINOPS.get(type(node.op))
        if op is None:
            msg = (
                f"the operator {type(node.op).__name__} has no MeTTa function. "
                f"{_INSTEAD.get(type(node.op), 'Register an operation with @m.op for it')}"
            )
            raise CompileError(
                msg,
                construct=type(node.op).__name__,
                line=node.lineno,
            )
        return Expression([Symbol(op), self.expression(node.left), self.expression(node.right)])

    def _x_UnaryOp(self, node: ast.UnaryOp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        if isinstance(node.op, ast.USub):
            operand = node.operand
            if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)):
                return Grounded(-operand.value)
            return Expression([Symbol("-"), Grounded(0), self.expression(operand)])
        if isinstance(node.op, ast.Not):
            # Python's not is truthiness negated, over any value.
            return Expression([Symbol("not"), self._truthy(node.operand)])
        if isinstance(node.op, ast.UAdd):
            return self.expression(node.operand)
        msg = (
            f"the unary operator {type(node.op).__name__} has no MeTTa "
            f"function. {_INSTEAD.get(type(node.op), '')}"
        )
        raise CompileError(
            msg,
            construct=type(node.op).__name__,
            line=node.lineno,
        )

    def _x_Compare(self, node: ast.Compare) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        terms = [self.expression(v) for v in (node.left, *node.comparators)]
        # A middle operand of a chain is read by two links; Python evaluates
        # it once, so anything that is not already a leaf binds to a
        # temporary before any link is built. Minted names carry a hyphen,
        # unreachable from Python identifiers.
        bindings: list[tuple[str, Atom]] = []
        for i in range(1, len(terms) - 1):
            if not isinstance(terms[i], (Variable, Symbol, Grounded)):
                temp = self._temp("cmp")
                bindings.append((temp, terms[i]))
                terms[i] = Variable(temp)
        links = [
            self._compare_link(op_node, terms[i], terms[i + 1], node.lineno)
            for i, op_node in enumerate(node.ops)
        ]
        folded = links[-1]
        for link in reversed(links[:-1]):
            # The chain short-circuits exactly as Python's does.
            folded = Expression([Symbol("if"), link, folded, Grounded(False)])  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        for temp, value in reversed(bindings):
            folded = Expression(
                [Symbol("let*"), Expression([Expression([Variable(temp), value])]), folded]
            )
        return folded

    def _truthy(self, node: ast.expr) -> Atom:
        """A test position: Python decides by truthiness, so anything not
        already boolean-valued by its syntax wraps in py-truthy, whose
        answer IS bool() of the value. A comparison or a `not` stays bare.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if isinstance(node, ast.Compare):
            return self.expression(node)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self.expression(node)
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return Grounded(node.value)
        self.runtime_ops.add("py-truthy")
        return Expression([Symbol("py-truthy"), self.expression(node)])

    def _compare_link(self, op_node: ast.cmpop, left: Atom, right: Atom, line) -> Atom:
        """One comparison: order through the engine's numeric functions,
        equality and membership through the prelude, so mixed numeric types
        and containers answer exactly what Python answers.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if isinstance(op_node, ast.Eq):
            self.runtime_ops.add("py-eq")
            return Expression([Symbol("py-eq"), left, right])
        if isinstance(op_node, ast.NotEq):
            self.runtime_ops.add("py-eq")
            return Expression([Symbol("not"), Expression([Symbol("py-eq"), left, right])])
        if isinstance(op_node, ast.In):
            self.runtime_ops.add("py-in")
            return Expression([Symbol("py-in"), left, right])
        if isinstance(op_node, ast.NotIn):
            self.runtime_ops.add("py-in")
            return Expression([Symbol("not"), Expression([Symbol("py-in"), left, right])])
        op = _COMPARE.get(type(op_node))
        if op is None:
            msg = f"the comparison {type(op_node).__name__} has no MeTTa function"
            raise CompileError(
                msg,
                construct=type(op_node).__name__,
                line=line,
            )
        return Expression([Symbol(op), left, right])

    def _x_BoolOp(self, node: ast.BoolOp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        # Python's and/or short-circuit AND answer the deciding operand
        # itself (3 or 7 is 3), so each step binds its operand once and
        # chooses by truthiness. Exactly Python, exactly once each.
        self.runtime_ops.add("py-truthy")
        folded = self.expression(node.values[-1])
        for value in reversed(node.values[:-1]):
            term = self.expression(value)
            temp = self._temp("bool")
            test = Expression([Symbol("py-truthy"), Variable(temp)])
            if isinstance(node.op, ast.And):
                chosen = Expression([Symbol("if"), test, folded, Variable(temp)])
            else:
                chosen = Expression([Symbol("if"), test, Variable(temp), folded])
            folded = Expression(
                [Symbol("let*"), Expression([Expression([Variable(temp), term])]), chosen]
            )
        return folded

    def _x_IfExp(self, node: ast.IfExp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        return Expression(
            [
                Symbol("if"),
                self._truthy(node.test),
                self.expression(node.body),
                self.expression(node.orelse),
            ]
        )

    def _x_Lambda(self, node: ast.Lambda) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        """A lambda is the engine's own first-class |->."""
        a = node.args
        if a.vararg or a.kwarg or a.kwonlyargs or a.defaults or a.posonlyargs:
            msg = "a compiled lambda takes plain positional parameters"
            raise CompileError(
                msg,
                construct="lambda",
                line=node.lineno,
            )
        params = [arg.arg for arg in a.args]
        inner = self._inner(params)
        return Expression(
            [Symbol("|->"), Expression([Variable(p) for p in params]), inner.expression(node.body)]
        )

    def _x_ListComp(self, node: ast.ListComp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        """[f(x) for x in xs] is (map-atom xs (|-> ($x) (f $x))), an
        if-filter composing through filter-atom first. Several `for`
        clauses nest the maps, each outer level flattening its nested
        answers with a left union-atom fold, so the elements arrive in
        Python's own order.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        for gen in node.generators:
            if gen.is_async:
                msg = "an async comprehension has no equation"
                raise CompileError(
                    msg,
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
            predicate = Expression(
                [Symbol("|->"), Expression([Variable(var)]), inner._truthy(condition)]
            )
            source = Expression([Symbol("filter-atom"), source, predicate])
        if len(generators) == 1:
            mapper = Expression([Symbol("|->"), Expression([Variable(var)]), inner.expression(elt)])
            return Expression([Symbol("map-atom"), source, mapper])
        nested = inner._comprehension(generators[1:], elt, line)
        mapper = Expression([Symbol("|->"), Expression([Variable(var)]), nested])
        return Expression(
            [
                Symbol("foldl-atom"),
                Expression([Symbol("map-atom"), source, mapper]),
                Expression([]),
                Symbol("union-atom"),
            ]
        )

    def _x_GeneratorExp(self, node: ast.GeneratorExp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        msg = (
            "a generator expression is lazy Python; write a list "
            "comprehension for map-atom, or a generator function for "
            "nondeterminism"
        )
        raise CompileError(
            msg,
            construct="generator expression",
            line=node.lineno,
        )

    def _x_Call(self, node: ast.Call) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        if node.keywords:
            msg = (
                "a call in a compiled body passes positional arguments; MeTTa "
                "application has no keywords"
            )
            raise CompileError(msg, construct="keyword argument", line=node.lineno)
        mentioned = self._mention(node.func)
        if mentioned is not None:
            return Expression([mentioned, *(self.expression(a) for a in node.args)])
        if isinstance(node.func, ast.Attribute):
            return self._mentioned_attribute_call(node)
        func = self._plain_call_name(node)
        if func.id == "match":
            return self._match_call(node)
        if func.id == "superpose":
            # superpose(a, b, c): one expression holding the alternatives.
            return Expression(
                [Symbol("superpose"), Expression([self.expression(a) for a in node.args])]
            )
        if func.id in self.lifted:
            return self._lifted_call(func.id, node)
        # Python's own builtins, where a name in scope has not shadowed them,
        # bridge to the engine functions that mean the same thing.
        if func.id in _PYBUILTIN_CALLS and func.id not in self.scope:
            return _PYBUILTIN_CALLS[func.id](self, node)
        callee = self._x_Name(func)
        return Expression([callee, *(self.expression(a) for a in node.args)])

    def _mentioned_attribute_call(self, node: ast.Call) -> Atom:
        """Lower a standard callable reached through its actual host module."""
        if node.keywords:
            msg = "a standard callable in a compiled body takes positional arguments"
            raise CompileError(msg, construct="keyword argument", line=node.lineno)
        if not isinstance(node.func, ast.Attribute):
            raise self._attribute_call_error(node)
        owner_node = node.func.value
        if not isinstance(owner_node, ast.Name):
            raise self._attribute_call_error(node)
        owner = self.host_value(owner_node.id)
        if not isinstance(owner, types.ModuleType):
            raise self._attribute_call_error(node)
        value = vars(owner).get(node.func.attr)
        mention = callable_mention(value)
        if mention is None:
            raise self._attribute_call_error(node)
        arities = callable_arities(value)
        if arities is None or len(node.args) not in arities:
            expected = " or ".join(str(arity) for arity in arities or ())
            msg = f"{owner_node.id}.{node.func.attr}() compiles with {expected} argument(s)"
            raise CompileError(msg, construct="call", line=node.lineno)
        arguments = [self.expression(argument) for argument in node.args]
        return self._adapt_mentioned_call(value, mention, arguments)

    def _adapt_mentioned_call(
        self, value: object, mention: str, arguments: list[Atom]
    ) -> Expression:
        """Preserve Python semantics where an engine mention orders or types differently."""
        if value is math.log:
            arguments = (
                [Grounded(math.e), arguments[0]]
                if len(arguments) == 1
                else [arguments[1], arguments[0]]
            )
        elif value is math.fabs:
            arguments[0] = Expression([Symbol("*"), Grounded(1.0), arguments[0]])
        elif value is builtins.round:
            self.runtime_ops.add("py-round")
            mention = "py-round"
        elif value is operator.truediv:
            arguments[0] = Expression([Symbol("*"), Grounded(1.0), arguments[0]])
        return Expression([Symbol(mention), *arguments])

    @staticmethod
    def _attribute_call_error(node: ast.Call) -> CompileError:
        return CompileError(
            "an attribute call compiles only when it resolves to a standard "
            "operator or math function with a MeTTa mention; register other "
            "methods as operations and call them by name",
            construct="call",
            line=node.lineno,
        )

    @staticmethod
    def _plain_call_name(node: ast.Call) -> ast.Name:
        if node.keywords:
            msg = (
                "a call in a compiled body passes positional arguments; MeTTa "
                "application has no keywords"
            )
            raise CompileError(
                msg,
                construct="keyword argument",
                line=node.lineno,
            )
        if not isinstance(node.func, ast.Name):
            msg = (
                "a compiled body calls a plain name; attribute and computed "
                "calls have no equation. Register the object's method as an "
                "operation and call it by name."
            )
            raise CompileError(
                msg,
                construct="call",
                line=node.lineno,
            )
        return node.func

    def _lifted_call(self, name: str, node: ast.Call) -> Expression:
        # A lifted inner def's free names travel as leading arguments, read
        # from the scope at the call, which is Python's late-binding rule.
        mangled, lifted_names, _ = self.lifted[name]
        missing = [identifier for identifier in lifted_names if identifier not in self.scope]
        if missing:
            msg = f"{name!r} closes over {missing} which are not in scope here"
            raise CompileError(
                msg,
                construct="nested def",
                line=node.lineno,
            )
        return Expression(
            [
                Symbol(mangled),
                *(Variable(self.scope[identifier]) for identifier in lifted_names),
                *(self.expression(argument) for argument in node.args),
            ]
        )

    def _args(self, node: ast.Call, count: int | None, name: str) -> list[Atom]:
        if count is not None and len(node.args) != count:
            msg = f"{name}() compiles with exactly {count} argument(s) here"
            raise CompileError(
                msg,
                construct=name,
                line=node.lineno,
            )
        return [self.expression(a) for a in node.args]

    def _py_len(self, node: ast.Call) -> Atom:
        # py-len is Python's len: expressions AND strings, since which one
        # arrives is a runtime fact.
        (xs,) = self._args(node, 1, "len")
        self.runtime_ops.add("py-len")
        return Expression([Symbol("py-len"), xs])

    def _py_abs(self, node: ast.Call) -> Atom:
        (x,) = self._args(node, 1, "abs")
        return Expression([Symbol("abs-math"), x])

    def _py_min(self, node: ast.Call) -> Atom:
        return self._extremum(node, "min")

    def _py_max(self, node: ast.Call) -> Atom:
        return self._extremum(node, "max")

    def _extremum(self, node: ast.Call, which: str) -> Atom:
        # min(xs) reads the elements of one expression; min(a, b, ...) folds
        # the engine's two-place min over the arguments, Python's own split.
        args = self._args(node, None, which)
        if not args:
            msg = f"{which}() needs arguments"
            raise CompileError(msg, construct=which, line=node.lineno)
        if len(args) == 1:
            return Expression([Symbol(f"{which}-atom"), args[0]])
        folded = args[-1]
        for term in reversed(args[:-1]):
            folded = Expression([Symbol(which), term, folded])
        return folded

    def _py_sum(self, node: ast.Call) -> Atom:
        args = self._args(node, None, "sum")
        if len(args) not in (1, 2):
            msg = "sum() takes an iterable and an optional start"
            raise CompileError(
                msg,
                construct="sum",
                line=node.lineno,
            )
        start: Atom = args[1] if len(args) == 2 else Grounded(0)
        return Expression([Symbol("foldl-atom"), args[0], start, Symbol("+")])

    def _py_sorted(self, node: ast.Call) -> Atom:
        (xs,) = self._args(node, 1, "sorted")
        return Expression([Symbol("sort-atom"), xs])

    def _py_pow(self, node: ast.Call) -> Atom:
        base, exponent = self._args(node, 2, "pow")
        return Expression([Symbol("pow-math"), base, exponent])

    def _py_str_builtin(self, node: ast.Call) -> Atom:
        (value,) = self._args(node, 1, "str")
        self.runtime_ops.add("py-str")
        return Expression([Symbol("py-str"), value])

    def _py_repr_builtin(self, node: ast.Call) -> Atom:
        (value,) = self._args(node, 1, "repr")
        self.runtime_ops.add("py-repr")
        return Expression([Symbol("py-repr"), value])

    def _py_round(self, node: ast.Call) -> Atom:
        args = self._args(node, None, "round")
        if len(args) not in (1, 2):
            msg = "round() takes a value and an optional digit count"
            raise CompileError(
                msg,
                construct="round",
                line=node.lineno,
            )
        # The prelude's py-round is Python's round, banker's rounding and
        # all; the engine's round-math rounds half away from zero.
        self.runtime_ops.add("py-round")
        return Expression([Symbol("py-round"), *args])

    def _py_range(self, node: ast.Call) -> Atom:
        args = self._args(node, None, "range")
        if len(args) not in (1, 2, 3):
            msg = "range() takes start, stop and an optional step"
            raise CompileError(
                msg,
                construct="range",
                line=node.lineno,
            )
        self.runtime_ops.add("py-range")
        return Expression([Symbol("py-range"), *args])

    def _x_Subscript(self, node: ast.Subscript) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        mention = self._mention(node)
        if mention is not None:
            return mention
        source = self.expression(node.value)
        if isinstance(node.slice, ast.Slice):
            if node.slice.step is not None:
                msg = (
                    "a stepped slice has no lowering; take a plain slice "
                    "and a comprehension, or an operation"
                )
                raise CompileError(
                    msg,
                    construct="slice",
                    line=node.lineno,
                )
            self.runtime_ops.add("py-slice")
            no_bound = Symbol("py-no-bound")
            lower = self.expression(node.slice.lower) if node.slice.lower is not None else no_bound
            upper = self.expression(node.slice.upper) if node.slice.upper is not None else no_bound
            return Expression([Symbol("py-slice"), source, lower, upper])
        # py-at is Python indexing itself: zero-based, negatives from the
        # end, strings included, an out-of-range index a loud error. No
        # engine fast path: index-atom cannot index a string, and whether a
        # value is one is a runtime fact.
        self.runtime_ops.add("py-at")
        return Expression([Symbol("py-at"), source, self.expression(node.slice)])

    def _match_call(self, node: ast.Call) -> Atom:
        """match(Pattern(...), template) runs against the running space;
        match(space, pattern, template) accepts a name or handle operand.
        Pattern variables are the names not otherwise bound, exactly as in
        source MeTTa.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        args = node.args
        if len(args) == 3:
            space_node, pattern_node, template_node = args
            if (
                isinstance(space_node, ast.Constant)
                and isinstance(space_node.value, str)
                and space_node.value.startswith("&")
            ):
                space: Atom = Symbol(space_node.value)
            else:
                space = self.expression(space_node)
            if not isinstance(space, (Handle, Variable)) and not (
                isinstance(space, Symbol) and space.name.startswith("&")
            ):
                msg = (
                    "match with three arguments takes a space handle, a space "
                    'parameter, or a name such as "&kb" first'
                )
                raise CompileError(
                    msg,
                    construct="match",
                    line=node.lineno,
                )
        elif len(args) == 2:
            pattern_node, template_node = args
            space = Expression([Symbol("context-space")])
        else:
            msg = "match takes (pattern, template) or (space, pattern, template)"
            raise CompileError(
                msg,
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
        return Expression([Symbol("match"), space, pattern, template])

    def _x_Tuple(self, node: ast.Tuple) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        return Expression([self.expression(e) for e in node.elts])

    def _x_List(self, node: ast.List) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        return Expression([self.expression(e) for e in node.elts])

    def _x_Dict(self, node: ast.Dict) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        msg = (
            "a dict literal has no MeTTa form; carry one whole with "
            "petta.ground(...) through an operation, or spell the pairs as an "
            "expression of (key value) pairs"
        )
        raise CompileError(
            msg,
            construct="dict",
            line=node.lineno,
        )

    def _x_JoinedStr(self, node: ast.JoinedStr) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        """An f-string joins its parts through the prelude: literal text as
        itself, {v} as py-str, {v!r} as py-repr, {v:spec} as py-format with
        a literal spec. Exactly Python's building, so the twin agrees to
        the character.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self.runtime_ops.add("py-str-join")
        parts = [self._fstring_piece(piece, node.lineno) for piece in node.values]
        return Expression([Symbol("py-str-join"), Expression(parts)])

    def _fstring_piece(self, piece: ast.expr, line: int) -> Atom:
        if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
            return Grounded(piece.value)
        if not isinstance(piece, ast.FormattedValue):
            msg = "this f-string part has no lowering"
            raise CompileError(
                msg,
                construct="f-string",
                line=line,
            )
        value = self.expression(piece.value)
        if piece.format_spec is not None:
            literal = self._literal_format_spec(piece.format_spec, line)
            self.runtime_ops.add("py-format")
            return Expression([Symbol("py-format"), value, Grounded(literal)])
        if piece.conversion == ord("r"):
            self.runtime_ops.add("py-repr")
            return Expression([Symbol("py-repr"), value])
        self.runtime_ops.add("py-str")
        return Expression([Symbol("py-str"), value])

    @staticmethod
    def _literal_format_spec(spec: ast.expr, line: int) -> str:
        if not isinstance(spec, ast.JoinedStr):
            raise _computed_format_error(line)
        literal_parts: list[str] = []
        for piece in spec.values:
            if not (isinstance(piece, ast.Constant) and isinstance(piece.value, str)):
                raise _computed_format_error(line)
            literal_parts.append(piece.value)
        return "".join(literal_parts)


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
        mention = self.outer._mention(node)
        if mention is not None:
            if (
                isinstance(mention, Variable)
                and mention.name not in self.outer.scope
                and mention.name not in self.bound
            ):
                self.bound.append(mention.name)
            return mention
        if isinstance(node, ast.Name):
            return self._name(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, (ast.Tuple, ast.List)):
            return Expression([self.expression(e) for e in node.elts])
        if isinstance(node, ast.Constant):
            return self.outer._x_Constant(node)
        msg = (
            f"{type(node).__name__} has no place in a match pattern, which is "
            f"structural: names, constructors, tuples and constants"
        )
        raise CompileError(
            msg,
            construct="pattern",
            line=getattr(node, "lineno", None),
        )

    def _name(self, node: ast.Name) -> Atom:
        if node.id in self.outer.scope:
            return Variable(self.outer.scope[node.id])
        if node.id[:1].islower() and not self.outer.known(node.id) and node.id != self.outer.name:
            if node.id not in self.bound:
                self.bound.append(node.id)
            return Variable(node.id)
        return self.outer._x_Name(node)

    def _call(self, node: ast.Call) -> Expression:
        mentioned = self.outer._mention(node.func)
        if mentioned is not None:
            if node.keywords:
                msg = "a pattern call passes positional arguments"
                raise CompileError(msg, construct="pattern", line=node.lineno)
            return Expression([mentioned, *(self.expression(argument) for argument in node.args)])
        if not isinstance(node.func, ast.Name):
            msg = "a pattern applies a plain constructor name"
            raise CompileError(
                msg,
                construct="pattern",
                line=node.lineno,
            )
        # The head position names the relation, whatever its case:
        # parent(gp, mid) matches (parent ...) atoms, so a lowercase head is
        # the relation symbol, not a fresh variable. A scoped head remains a
        # variable.
        head_id = node.func.id
        head: Atom = (
            Variable(self.outer.scope[head_id]) if head_id in self.outer.scope else Symbol(head_id)
        )
        return Expression([head, *(self.expression(argument) for argument in node.args)])


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
    msg = (
        "a compiled body binds plain names; destructuring and attribute "
        "assignment have no let* form"
    )
    raise CompileError(
        msg,
        construct="assignment target",
        line=line,
    )


def _computed_format_error(line: int) -> CompileError:
    return CompileError(
        "a computed f-string format spec has no lowering; write the spec literally, as in {x:.2f}",
        construct="f-string",
        line=line,
    )
