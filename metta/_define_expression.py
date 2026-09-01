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
  - the composite operator word ``neg`` lowers to ``(- 0 x)`` at both S and
    fn call doors [tested: test_compiled_operator_word_calls_preserve_composite_images;
    commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - a host-bound Defined mention lowers to the sibling's declared MeTTa name
    [tested: test_compiled_body_calls_renamed_defined_sibling;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - host-bound and parameter-carried space handles remain operands of compiled
    match calls [tested: test_compiled_match_accepts_space_handles;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - calls whose declared output is Bool remain direct conditions rather than
    acquiring py-truthy [tested:
    test_compiled_boolean_call_is_a_direct_condition; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - pre-add verdict builders are known expression-position callees inside a
    compiled judge [tested: test_pre_add_compiles_the_four_verdict_judge;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - imported ``functools.reduce`` lowers named reducers to ``foldl-atom`` and
    lambdas to its explicit accumulator/item template [tested:
    test_reduce_lowers_named_and_lambda_reducers; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - a four-argument bare unify call lowers to the engine's protected special
    form rather than resolving as a host closure [tested:
    test_expression_position_unify_uses_the_engine_conditional_in_both_contexts;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - a closed-over State mention and its ``.value`` property lower to the
    engine cell handle and ``get-state`` rather than host attribute access
    [tested: test_compiled_state_properties_round_trip_through_engine_heads;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - exact ``py(expr)`` marker calls and unmarked host expressions lower to
    the same application-time grounded islands, with nothing executed at
    compile time and the loud refusal kept for names that resolve nowhere
    [tested: test_py_host_island_executes_per_engine_application,
    test_unknown_host_callee_islands_implicitly; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - keyword-bearing calls whose parameter names are known lower to positional
    applications; a host callee keeps its keywords by islanding whole, and an
    engine head with unknown keywords still refuses toward the positional
    spelling [tested: test_known_call_site_keywords_bind_to_positional_metta_arguments,
    test_unknown_symbol_keywords_refuse_with_the_positional_remedy;
    commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - compiled Python operators invoke the live Python data model, including
    reflected, in-place, unary, and rich-comparison protocols [tested:
    test_compiled_operators_follow_python_protocols_and_result_species;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import builtins
import functools
import math
import types
from collections.abc import Callable

from ._call_binding import bind_positional_call, refuse_unknown_keywords
from ._callable_mentions import (
    callable_arities,
    callable_mention,
    operator_callable_selector,
)
from ._define_context import CompilerContext, next_aux_serial
from ._host_island import _HostIsland
from ._host_island import py as _py_marker
from ._name_mapping import (
    OperatorRecipe,
    attribute_name,
    operator_attribute_target,
    resolve_known_name,
)
from ._state import State
from .atoms import Atom, Expression, Grounded, Handle, Symbol, Variable
from .errors import CompileError, character_column

# Python syntax to the exact ``operator`` protocol selector consumed by the
# compiler-only py-operator operation. Operand kinds are application-time
# facts, so choosing a numeric engine head here would silently bypass Python's
# container and reflected methods.
_BINOPS = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "truediv",
    ast.FloorDiv: "floordiv",
    ast.Mod: "mod",
    ast.Pow: "pow",
    ast.MatMult: "matmul",
    ast.BitAnd: "and",
    ast.BitOr: "or",
    ast.BitXor: "xor",
    ast.LShift: "lshift",
    ast.RShift: "rshift",
}

# Exact int/float annotations are a semantic promise strong enough to retain
# the engine's pure numeric heads. Untyped operands cannot use these: Python
# may dispatch a reflected or container protocol at application time. Power
# stays on the protocol path because an integral negative exponent changes
# the result species, the divergence that repaired check_twin exposed.
_NATIVE_BINOPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "floor-div",
    ast.Mod: "%",
}

# Comparison syntax also follows the Python protocol. Equality is included:
# __eq__ and __ne__ may return arbitrary objects, and only a surrounding test
# position is entitled to ask for their truth value.
_COMPARE = {
    ast.Eq: "eq",
    ast.NotEq: "ne",
    ast.Lt: "lt",
    ast.Gt: "gt",
    ast.LtE: "le",
    ast.GtE: "ge",
}

_NATIVE_COMPARE = {
    ast.Lt: "<",
    ast.Gt: ">",
    ast.LtE: "<=",
    ast.GtE: ">=",
}

_SOURCE_COMPARE = {
    **_NATIVE_COMPARE,
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.In: "in",
    ast.NotIn: "not-in",
}

_INPLACE_BINOPS = {
    ast.Add: "iadd",
    ast.Sub: "isub",
    ast.Mult: "imul",
    ast.Div: "itruediv",
    ast.FloorDiv: "ifloordiv",
    ast.Mod: "imod",
    ast.Pow: "ipow",
    ast.MatMult: "imatmul",
    ast.BitAnd: "iand",
    ast.BitOr: "ior",
    ast.BitXor: "ixor",
    ast.LShift: "ilshift",
    ast.RShift: "irshift",
}

# Names with special meaning inside a compiled body. `match` runs a pattern
# against the running space, nondeterminism and verdict forms pass through,
# and `empty` answers nothing.
_MAGIC = ("accept", "collapse", "drop", "empty", "match", "refuse", "superpose", "unify")


class ExpressionCompilerMixin(CompilerContext):
    def _stage(self, head: str, *rest: Atom) -> Callable[[Atom], Atom]:
        """One collection stage over a list this compiler will name for it.

        The stage is built as a function of the name rather than of the source,
        because `_piped` decides where the name comes from: a source that is
        already a variable is used directly and one that is a call is bound
        with `let` first.
        """

        def stage(held: Atom) -> Atom:
            return Expression([Symbol(head), held, *rest])

        return stage

    def _piped(self, source: Atom, stages: list[Callable[[Atom], Atom]]) -> Atom:
        """Compose collection stages over a source, naming the value between them.

        map-atom, filter-atom and foldl-atom declare their list parameter
        `Expression`, and an Expression parameter is the evaluation mask: the
        operand crosses AS WRITTEN [source: LeaTTa
        MettaHyperonFull/Core/Modifiers.lean, declaredTypeEvaluates]. A
        comprehension's source, and each stage's own answer, is a call, so
        writing one straight into the next stage's list position would fold
        over the parts of the unrun call. Naming it with `let` is what the
        reference's own stdlib does at every such site.

        A source that is ALREADY a variable needs no name. The binder carries a
        hyphen, which Python cannot spell, so it can never shadow a variable
        the author wrote, and the serial is process-unique so nested
        comprehensions do not collide
        [tested tests/test_define.py::test_fstrings_str_round_range_slices,
        tests/test_fuzz_define.py::test_collection_bridge_agrees].
        """
        if not stages:
            return source
        head, rest = stages[0], stages[1:]
        if isinstance(source, Variable):
            return self._piped(head(source), rest)
        held = Variable(f"held-source-{next_aux_serial()}")
        return Expression([Symbol("let"), held, source, self._piped(head(held), rest)])

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
        if isinstance(host_value, State):
            return host_value.__metta__()
        known = self._known_symbol(node.id)
        if known is not None:
            return known
        if node.id in self.pragma_globals and not self._in_pattern and self.function is not None:
            # A declared global reads through the ops lane against the
            # module dict grounded by reference, the write's own channel,
            # so reads and writes meet the same live binding; a missing
            # name raises Python's own NameError at application time.
            self.runtime_ops.add("py-global-read")
            return Expression(
                [
                    Symbol("py-global-read"),
                    Grounded(self.function.__globals__),
                    Grounded(node.id),
                ]
            )
        if self.host(node.id) and not self._in_pattern:
            # A held host value reads as an implicit island: the equation
            # carries the author's own name, evaluated at application time
            # against the live binding, exactly as py(name) would spell
            # it. A pattern position stays structural and keeps its
            # refusal.
            return self._implicit_island(node)
        if node.id[:1].isupper():
            return self._constructor_symbol(node)
        msg = (
            f"{node.id!r} is not a parameter of {self.name}, not a function "
            f"the engine knows, not a capitalized data constructor, and not "
            f"a host binding this function can see. Define {node.id!r} "
            f"first, pass it as an argument, use fn.{node.id} for a catalog "
            f"function, or S.{node.id} for data. Bare calls ask for "
            f"{node.id!r} and then {attribute_name(node.id)!r}; neither "
            f"exists here."
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

    @staticmethod
    def _operator_word_target(node: ast.Attribute) -> str | OperatorRecipe | None:
        """Resolve one operator word at an S/fn attribute mention.

        The word table first, exactly as _atom_namespace consults it, so
        S.eq is == at the live factory AND inside a compiled body, and
        fn.eq resolves through the catalog's own ==. The bracket door stays
        exact by construction (only the attribute branch consults), V never
        consults (V.eq is the variable $eq), and an unsettled composite word
        refuses here as a CompileError the way every other refusal does.
        """
        try:
            return operator_attribute_target(node.attr)
        except AttributeError as refusal:
            raise CompileError(
                str(refusal),
                construct="operator word",
                line=node.lineno,
            ) from refusal

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
                # policy-inventory-exempt: mechanism-internal; reason=S V and fn are the three fixed quotation-tier builders recognized by compiled-body syntax rather than selectable runtime policy; evidence=extensions/python/metta/_define_expression.py:_mention
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
            # V never consults the word table: V.eq is the variable $eq.
            return Variable(target)
        if isinstance(node, ast.Attribute):
            operator_target = self._operator_word_target(node)
            if isinstance(operator_target, OperatorRecipe):
                msg = (
                    f"{ast.unparse(node)} is the composite image "
                    f"{operator_target.image}; call it with one operand"
                )
                raise CompileError(
                    msg,
                    construct="operator word",
                    line=node.lineno,
                )
            target = operator_target or target
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
        state_cell = self._state_cell(node)
        if state_cell is not None:
            return Expression([Symbol("get-state"), state_cell])
        root: ast.expr = node
        while isinstance(root, (ast.Attribute, ast.Subscript, ast.Call)):
            root = root.func if isinstance(root, ast.Call) else root.value
        if (
            isinstance(root, ast.Name)
            and (root.id in self.scope or self.host(root.id))
            and not self._in_pattern
        ):
            # Attribute access on a compiled local or a host binding is host
            # behavior the author wrote: it islands whole, running against
            # the application-time value, method calls included.
            return self._implicit_island(node)
        msg = (
            f"{ast.unparse(node)!r} is host attribute access on a name this "
            "function cannot see. Use S, V, or fn without shadowing, or "
            "register a plain-name operation."
        )
        raise CompileError(msg, construct="attribute", line=node.lineno)

    def _state_cell(self, node: ast.expr) -> Atom | None:
        """Resolve exactly ``closed_over_state.value`` to its engine cell."""
        if (
            not isinstance(node, ast.Attribute)
            or node.attr != "value"
            or not isinstance(node.value, ast.Name)
            or node.value.id in self.scope
        ):
            return None
        held = self.host_value(node.value.id)
        return held.__metta__() if isinstance(held, State) else None

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
        native = self._native_number(node.left) and self._native_number(node.right)
        left_kind = self._container_kind(node.left)
        right_kind = self._container_kind(node.right)
        return self._binop_atom(
            node.op,
            self.expression(node.left)
            if native
            else self._operator_operand(self.expression(node.left), left_kind),
            self.expression(node.right)
            if native
            else self._operator_operand(self.expression(node.right), right_kind),
            node.lineno,
            left_kind=left_kind,
            right_kind=right_kind,
            native=native,
        )

    def _binop_atom(
        self,
        op: ast.operator,
        left: Atom,
        right: Atom,
        line: int | None,
        *,
        left_kind: str | None = None,
        right_kind: str | None = None,
        native: bool = False,
    ) -> Atom:
        """Lower one binary operation over already-compiled operands.

        Augmented-assignment desugaring shares the exact operator lowering.
        """
        native_head = _NATIVE_BINOPS.get(type(op))
        if native and native_head is not None:
            return self._native_binop(op, native_head, left, right)
        selector = _BINOPS.get(type(op))
        if selector is None:
            msg = (
                f"the operator {type(op).__name__} has no MeTTa function. "
                "Register an operation with @m.op for it"
            )
            raise CompileError(
                msg,
                construct=type(op).__name__,
                line=line,
            )
        applied = self._python_operator(selector, left, right)
        if left_kind in {"set", "dict"} or right_kind in {"set", "dict"}:
            return self._restore_mapping_container(applied)
        return applied

    def _native_binop(
        self, op: ast.operator, head: str, left: Atom, right: Atom
    ) -> Atom:
        """Lower a declared int/float operation to its pure engine head."""
        if isinstance(op, ast.Div):
            left = Expression([Symbol("*"), Grounded(1.0), left])
        return Expression([Symbol(head), left, right])

    def _inplace_atom(
        self,
        op: ast.operator,
        left: Atom,
        right: Atom,
        line: int | None,
        *,
        left_kind: str | None = None,
        right_kind: str | None = None,
    ) -> Atom:
        """Apply Python's in-place protocol, preserving a returned replacement."""
        selector = _INPLACE_BINOPS.get(type(op))
        if selector is None:
            msg = f"the in-place operator {type(op).__name__} has no Python bridge"
            raise CompileError(
                msg,
                construct="augmented assignment",
                line=line,
            )
        applied = self._python_operator(selector, left, right)
        if left_kind in {"set", "dict"} or right_kind in {"set", "dict"}:
            return self._restore_mapping_container(applied)
        return applied

    def _python_operator(self, selector: str, *operands: Atom) -> Expression:
        """Apply one fixed Python operator to evaluated Atom operands."""
        self.runtime_ops.add("py-operator")
        return Expression([Symbol("py-operator"), Symbol(selector), *operands])

    def _native_number(self, node: ast.expr) -> bool:
        """Whether this expression is constrained to a native int/float."""
        if isinstance(node, ast.Constant):
            return type(node.value) in {int, float}
        if isinstance(node, ast.Name):
            return node.id in self.number_locals
        if isinstance(node, ast.UnaryOp):
            return isinstance(node.op, (ast.UAdd, ast.USub)) and self._native_number(node.operand)
        if isinstance(node, ast.BinOp):
            return (
                type(node.op) in _NATIVE_BINOPS
                and self._native_number(node.left)
                and self._native_number(node.right)
            )
        if isinstance(node, ast.IfExp):
            return self._native_number(node.body) and self._native_number(node.orelse)
        return (
            self.number_return
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and self._resolved_call_name(node.func.id) == self.name
        )

    def _diagnostic_term(self, node: ast.expr) -> Atom:
        """Preserve source operator spelling inside non-evaluated diagnostics."""
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            head = _SOURCE_COMPARE.get(type(node.ops[0]))
            if head is not None:
                return Expression(
                    [
                        Symbol(head),
                        self.expression(node.left),
                        self.expression(node.comparators[0]),
                    ]
                )
        return self.expression(node)

    def _operator_operand(self, operand: Atom, kind: str | None) -> Atom:
        """Restore a literal/local container species before Python dispatch."""
        if kind == "list":
            return Expression([Symbol("py-list"), operand])
        if kind in {"set", "dict"}:
            self.libraries.add("dict")
            pairs = Expression([Symbol("dict-pairs"), operand])
            if kind == "set":
                self.runtime_ops.add("py-set")
                return Expression([Symbol("py-set"), pairs])
            return Expression([Symbol("py-dict"), pairs])
        return operand

    def _restore_mapping_container(self, value: Atom) -> Atom:
        """Return Python set/dict results to their established space image."""
        held = Variable(self._temp("container-result"))
        self.runtime_ops.update({"py-container-kind", "py-set-pairs", "py-dict-pairs"})
        self.libraries.add("dict")
        kind = Expression([Symbol("py-container-kind"), held])
        set_image = Expression(
            [
                Symbol("dict-space"),
                Expression([Symbol("py-set-pairs"), held]),
            ]
        )
        dict_image = Expression(
            [
                Symbol("dict-space"),
                Expression([Symbol("py-dict-pairs"), held]),
            ]
        )
        restored = Expression(
            [
                Symbol("if"),
                Expression([Symbol("=="), kind, Symbol("set")]),
                set_image,
                Expression(
                    [
                        Symbol("if"),
                        Expression([Symbol("=="), kind, Symbol("dict")]),
                        dict_image,
                        held,
                    ]
                ),
            ]
        )
        return Expression(
            [
                Symbol("let*"),
                Expression([Expression([held, value])]),
                restored,
            ]
        )

    def _x_UnaryOp(self, node: ast.UnaryOp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        if isinstance(node.op, ast.USub):
            operand = node.operand
            if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)):
                return Grounded(-operand.value)
            if self._native_number(operand):
                return Expression([Symbol("-"), Grounded(0), self.expression(operand)])
            return self._python_operator("neg", self.expression(operand))
        if isinstance(node.op, ast.Not):
            # Python's not is truthiness negated, over any value.
            return Expression([Symbol("not"), self._truthy(node.operand)])
        if isinstance(node.op, ast.UAdd):
            if self._native_number(node.operand):
                return self.expression(node.operand)
            return self._python_operator("pos", self.expression(node.operand))
        if isinstance(node.op, ast.Invert):
            return self._python_operator("invert", self.expression(node.operand))
        msg = (
            f"the unary operator {type(node.op).__name__} has no MeTTa "
            "function. Register an operation with @m.op for it"
        )
        raise CompileError(
            msg,
            construct=type(node.op).__name__,
            line=node.lineno,
        )

    def _x_Compare(self, node: ast.Compare) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        nodes = (node.left, *node.comparators)
        terms = [self.expression(value) for value in nodes]
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
            self._compare_link(
                op_node,
                terms[i],
                terms[i + 1],
                node.lineno,
                native=(
                    type(op_node) in _NATIVE_COMPARE
                    and self._native_number(nodes[i])
                    and self._native_number(nodes[i + 1])
                ),
            )
            for i, op_node in enumerate(node.ops)
        ]
        folded = links[-1]
        for link in reversed(links[:-1]):
            # Comparisons may answer arbitrary objects. Python truth-tests an
            # intermediate result once and, like ``and``, returns that result
            # itself when it is false rather than replacing it with False.
            held = Variable(self._temp("comparison-result"))
            self.runtime_ops.add("py-truthy")
            folded = Expression(
                [
                    Symbol("let*"),
                    Expression([Expression([held, link])]),
                    Expression(
                        [
                            Symbol("if"),
                            Expression([Symbol("py-truthy"), held]),
                            folded,
                            held,
                        ]
                    ),
                ]
            )
        for temp, value in reversed(bindings):
            folded = Expression(
                [Symbol("let*"), Expression([Expression([Variable(temp), value])]), folded]
            )
        return folded

    def _truthy(self, node: ast.expr) -> Atom:
        """A test position: Python decides by truthiness, so anything not
        already boolean-valued by its syntax wraps in py-truthy, whose
        answer IS bool() of the value. Only `not` and declared Bool-returning
        engine calls stay bare; rich comparisons may return other objects.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        term = self.expression(node)
        if (
            isinstance(node, ast.Compare)
            and all(type(op) in _NATIVE_COMPARE for op in node.ops)
            and all(self._native_number(value) for value in (node.left, *node.comparators))
        ):
            return term
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return term
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return term
        if (
            isinstance(term, Expression)
            and term.children
            and isinstance(term.children[0], Symbol)
            and self.returns_bool(term.children[0].name)
        ):
            return term
        self.runtime_ops.add("py-truthy")
        return Expression([Symbol("py-truthy"), term])

    def _compare_link(
        self,
        op_node: ast.cmpop,
        left: Atom,
        right: Atom,
        line: int | None,
        *,
        native: bool = False,
    ) -> Atom:
        """One comparison through Python's live rich-comparison protocol.

        Membership is intrinsically boolean and retains its dedicated bridge;
        every rich comparison may return an arbitrary object, which a caller
        truth-tests only when its surrounding syntax demands it.
        """
        if isinstance(op_node, ast.In):
            if self._dict_atom(right):
                self.libraries.add("dict")
                return Expression([Symbol("dict-has"), right, left])
            self.runtime_ops.add("py-in")
            return Expression([Symbol("py-in"), left, right])
        if isinstance(op_node, ast.NotIn):
            if self._dict_atom(right):
                self.libraries.add("dict")
                return Expression([Symbol("not"), Expression([Symbol("dict-has"), right, left])])
            self.runtime_ops.add("py-in")
            return Expression([Symbol("not"), Expression([Symbol("py-in"), left, right])])
        if native:
            return Expression([Symbol(_NATIVE_COMPARE[type(op_node)]), left, right])
        selector = _COMPARE.get(type(op_node))
        if selector is None:
            msg = f"the comparison {type(op_node).__name__} has no MeTTa function"
            raise CompileError(
                msg,
                construct=type(op_node).__name__,
                line=line,
            )
        return self._python_operator(selector, left, right)

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
        self._refuse_async_generators(node.generators, node.lineno)
        return self._comprehension(node.generators, node.elt, node.lineno)

    def _comprehension(self, generators: list[ast.comprehension], elt: ast.expr, line: int) -> Atom:
        gen = generators[0]
        var = _name_of(gen.target, line)
        # The source reads in THIS scope: a later clause's source may use an
        # earlier clause's variable, but never its own.
        source = self.expression(gen.iter)
        inner = self._inner([var])
        inner.loop_depth += 1
        stages = [
            self._stage(
                "filter-atom",
                Expression([Symbol("|->"), Expression([Variable(var)]), inner._truthy(condition)]),
            )
            for condition in gen.ifs
        ]
        if len(generators) == 1:
            mapper = Expression([Symbol("|->"), Expression([Variable(var)]), inner.expression(elt)])
            return self._piped(source, [*stages, self._stage("map-atom", mapper)])
        nested = inner._comprehension(generators[1:], elt, line)
        mapper = Expression([Symbol("|->"), Expression([Variable(var)]), nested])
        return self._piped(
            source,
            [
                *stages,
                self._stage("map-atom", mapper),
                self._stage("foldl-atom", Expression([]), Symbol("union-atom")),
            ],
        )

    def _x_DictComp(self, node: ast.DictComp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        """{k: v for ...} is the dict story's own lowering target: the
        comprehension builds the expression of (key value) pairs and
        dict-space reads it back, exactly as test_dict_story pins.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self._refuse_async_generators(node.generators, node.lineno)
        pair = ast.copy_location(ast.Tuple(elts=[node.key, node.value], ctx=ast.Load()), node)
        ast.fix_missing_locations(pair)
        return self._dict_space(self._comprehension(node.generators, pair, node.lineno))

    def _x_SetComp(self, node: ast.SetComp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        """{e for ...} is the dict comprehension to True, Python's kinship."""
        self._refuse_async_generators(node.generators, node.lineno)
        pair = ast.copy_location(
            ast.Tuple(elts=[node.elt, ast.Constant(value=True)], ctx=ast.Load()),
            node,
        )
        ast.fix_missing_locations(pair)
        return self._dict_space(self._comprehension(node.generators, pair, node.lineno))

    def _refuse_async_generators(self, generators: list[ast.comprehension], line: int) -> None:
        for gen in generators:
            if gen.is_async:
                msg = "an async comprehension has no equation"
                raise CompileError(msg, construct="comprehension", line=line)

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
        if self._is_host_island_marker(node.func):
            return self._host_island_call(node)
        if self._is_functools_reduce(node.func):
            return self._reduce_call(node)
        composite = self._composite_operator_call(node)
        if composite is not None:
            return composite
        if node.keywords:
            return self._keyword_call(node)
        mentioned = self._mention(node.func)
        if mentioned is not None:
            return Expression([mentioned, *(self.expression(a) for a in node.args)])
        if isinstance(node.func, ast.Attribute):
            dict_method = self._dict_method_call(node)
            if dict_method is not None:
                return dict_method
            return self._mentioned_attribute_call(node)
        func = self._plain_call_name(node)
        if func.id == "match":
            return self._match_call(node)
        if func.id == "unify":
            return Expression([Symbol("unify"), *self._args(node, 4, "unify")])
        if func.id == "alpha" and func.id not in self.scope:
            # =alpha's nearest-relative spelling: `=` sits outside Python's
            # identifier grammar, so the bare name drops the marker the way
            # eq() does for ==. fn["=alpha"] stays the exact door, and
            # Atom.alpha() builds the same term on the atom tier.
            return Expression([Symbol("=alpha"), *self._args(node, 2, "alpha")])
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
        if self._islands_implicitly(func.id):
            return self._implicit_island(node)
        try:
            callee = self._x_Name(func)
        except CompileError as error:
            if error.construct == "free identifier":
                raise self._unknown_host_callee(node, node) from None
            raise
        return Expression([callee, *(self.expression(a) for a in node.args)])

    def _is_host_island_marker(self, node: ast.expr) -> bool:
        """Recognize the public marker by identity, including an import alias."""
        return (
            isinstance(node, ast.Name)
            and node.id not in self.scope
            and self.host_value(node.id) is _py_marker
        )

    def _islands_implicitly(self, name: str) -> bool:
        """Whether a call to NAME is the fallback law's implicit island.

        A host or builtin callable with no engine meaning runs the
        author's own Python at application time, so int(x) is Python's
        int. Exact catalog names still win, and an exception class stays
        OUT of this lane: ValueError("why") METTAFIES through the
        constructor path into the (ValueError "why") term, matched by
        except arms on its own name.
        """
        if name in self.scope or name in _MAGIC:
            return False
        if not (self.host(name) or name in self._builtins):
            return False
        return self._resolved_name(name) is None and not self._builtin_exception(name)

    def _builtin_exception(self, name: str) -> bool:
        value = self._builtins.get(name)
        return isinstance(value, type) and issubclass(value, BaseException)

    def _host_island_call(self, node: ast.Call) -> Atom:
        """Compile the enclosed Python expression without executing it now."""
        if node.keywords or len(node.args) != 1:
            msg = "py(...) marks exactly one host expression and takes no keyword arguments"
            raise CompileError(
                msg,
                construct="py host island",
                line=node.lineno,
            )
        return self._island(node.args[0], marked=True)

    def _implicit_island(self, node: ast.expr) -> Atom:
        """A host expression islanded without a marker, the fallback lane.

        Anything the vocabulary does not lower natively runs as the
        author's own Python at application time, exactly as if they had
        written py(...) around it: an unknown host call, a host attribute
        read, a container literal. The equation still shows the island as
        an applicable grounded atom, so nothing is hidden from the space,
        and the lint layer records the same source span and loop context
        the explicit marker records.
        """
        return self._island(node, marked=False)

    def _island(self, expression: ast.expr, *, marked: bool) -> Atom:
        if self.function is None:
            msg = "a host island has no source function"
            raise RuntimeError(msg)
        runtime_names = tuple(
            dict.fromkeys(
                candidate.id
                for candidate in ast.walk(expression)
                if isinstance(candidate, ast.Name)
                and isinstance(candidate.ctx, ast.Load)
                and candidate.id in self.scope
            )
        )
        island = _HostIsland(
            self.function,
            expression,
            runtime_names,
            source=self.source,
            path=self.source_path,
            first_line=self.first_line,
            in_loop=self.loop_depth > 0,
            marked=marked,
        )
        return Expression(
            [Grounded(island), *(Variable(self.scope[name]) for name in runtime_names)]
        )

    def _unknown_host_callee(
        self,
        expression: ast.expr,
        call: ast.Call,
    ) -> CompileError:
        """A compiler-grade refusal for an implicit host boundary crossing."""
        called = ast.unparse(call)
        host_expression = ast.unparse(expression)
        message = "\n".join(
            (
                f"refused: `{called}` is an unknown callee",
                "host attribute and computed calls do not cross into Python implicitly",
                "remedy: extract the host call into an operation and call it by name:",
                '   |     @metta.op(effect="oracleIO")',
                "   |     def host_call(...): ...",
                "or mark the host expression in place:",
                f"   |     return py({host_expression})",
            )
        )
        lines = self.source.splitlines()
        source_line = lines[call.lineno - 1] if 0 < call.lineno <= len(lines) else ""
        start = character_column(source_line, call.col_offset)
        end_offset = (
            call.end_col_offset
            if call.end_lineno == call.lineno and call.end_col_offset is not None
            else len(source_line.encode("utf-8"))
        )
        end = character_column(source_line, end_offset)
        return CompileError(
            message,
            construct="unknown callee",
            line=self.first_line + call.lineno - 1,
            path=self.source_path,
            source_line=source_line,
            column=start,
            end_column=end,
            function=self.pyname,
            annotation="not a parameter, a known function, or a data constructor",
        )

    def _keyword_call(self, node: ast.Call) -> Atom:
        """Place keywords against a known signature before emitting the term."""
        if any(isinstance(argument, ast.Starred) for argument in node.args) or any(
            keyword.arg is None for keyword in node.keywords
        ):
            msg = "compiled call-site keywords do not accept *args or **kwargs expansion"
            raise CompileError(msg, construct="keyword argument", line=node.lineno)

        display = ast.unparse(node.func)
        total = len(node.args) + len(node.keywords)
        parameters: tuple[str, ...] | None = None
        callee: Atom | None = None
        if isinstance(node.func, ast.Name):
            resolved = self._resolved_name(node.func.id)
            if resolved is not None:
                parameters = self._bound_call_parameters(node.func.id, total)
                if parameters is None:
                    parameters = self.call_parameters(resolved, total)
                callee = self._x_Name(node.func)
        else:
            mentioned = self._mention(node.func)
            if isinstance(mentioned, Symbol):
                callee = mentioned
                if self._builder_root(node.func) == "fn":
                    parameters = self.call_parameters(mentioned.name, total)

        if parameters is None or callee is None:
            root: ast.expr = node.func
            while isinstance(root, (ast.Attribute, ast.Subscript)):
                root = root.value
            if isinstance(root, ast.Name) and (root.id in self.scope or self.host(root.id)):
                # A host call keeps its keywords by islanding whole: the
                # author's own call runs at application time, and Python
                # itself places the keywords.
                return self._implicit_island(node)
            refusal = refuse_unknown_keywords(
                display, tuple(keyword.arg for keyword in node.keywords if keyword.arg)
            )
            raise CompileError(str(refusal), construct="keyword argument", line=node.lineno)
        try:
            ordered = bind_positional_call(
                display,
                parameters,
                node.args,
                {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg},
            )
        except TypeError as error:
            raise CompileError(
                str(error), construct="keyword argument", line=node.lineno
            ) from error
        return Expression([callee, *(self.expression(argument) for argument in ordered)])

    @staticmethod
    def _builder_root(node: ast.expr) -> str | None:
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.value, ast.Name):
            return node.value.id
        return None

    def _composite_operator_call(self, node: ast.Call) -> Atom | None:
        """Lower an unshadowed S/fn call whose operator image is a recipe."""
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            # policy-inventory-exempt: mechanism-internal; reason=the two namespace-builder identities the compiler recognises lexically, a grammar fact rather than a selectable policy; evidence=extensions/python/tests/ch11_python_as_a_notation/test_mention_doors.py:test_rejected_attributes_never_execute_host_objects
            and func.value.id in {"S", "fn"}
            and func.value.id not in self.scope
            and func.value.id in self.builders
        ):
            return None
        target = self._operator_word_target(func)
        if not isinstance(target, OperatorRecipe):
            return None
        if node.keywords or len(node.args) != 1:
            msg = f"{ast.unparse(func)} compiles with exactly one positional operand"
            raise CompileError(msg, construct="operator word", line=node.lineno)
        return target(self.expression(node.args[0]))

    def _is_functools_reduce(self, node: ast.expr) -> bool:
        """Recognize the imported callable by identity, including an alias."""
        if isinstance(node, ast.Name):
            return node.id not in self.scope and self.host_value(node.id) is functools.reduce
        if not (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id not in self.scope
        ):
            return False
        owner = self.host_value(node.value.id)
        return (
            isinstance(owner, types.ModuleType) and vars(owner).get(node.attr) is functools.reduce
        )

    def _reduce_call(self, node: ast.Call) -> Atom:
        """Lower Python's seeded left fold to foldl-atom's two forms."""
        if node.keywords or len(node.args) != 3:
            msg = "functools.reduce() compiles with a reducer, values, and an initial value"
            raise CompileError(msg, construct="reduce", line=node.lineno)
        reducer_node, values_node, initial_node = node.args
        values = self.expression(values_node)
        initial = self.expression(initial_node)
        if isinstance(reducer_node, ast.Lambda):
            arguments = reducer_node.args
            extras = (
                arguments.vararg,
                arguments.kwarg,
                arguments.kwonlyargs,
                arguments.defaults,
                arguments.posonlyargs,
            )
            if len(arguments.args) != 2 or any(extras):
                msg = "a reduce lambda takes exactly accumulator and item"
                raise CompileError(msg, construct="reduce lambda", line=reducer_node.lineno)
            accumulator, item = (argument.arg for argument in arguments.args)
            inner = self._inner([accumulator, item])
            body = inner.expression(reducer_node.body)
            return self._piped(
                values,
                [
                    self._stage(
                        "foldl-atom",
                        initial,
                        Variable(accumulator),
                        Variable(item),
                        body,
                    )
                ],
            )
        return self._piped(
            values,
            [self._stage("foldl-atom", initial, self._reduce_function(reducer_node))],
        )

    def _reduce_function(self, node: ast.expr) -> Atom:
        """Resolve a named engine reducer or an exact standard callable mention."""
        value: object | None = None
        if isinstance(node, ast.Name) and node.id not in self.scope:
            value = self.host_value(node.id)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id not in self.scope
        ):
            owner = self.host_value(node.value.id)
            if isinstance(owner, types.ModuleType):
                value = vars(owner).get(node.attr)
        mention = callable_mention(value)
        return Symbol(mention) if mention is not None else self.expression(node)

    def _mentioned_attribute_call(self, node: ast.Call) -> Atom:
        """Lower a standard callable reached through its actual host module.

        Anything outside the standard-mention table is host behavior the
        author wrote and islands whole: a third-party call, keywords, a
        chained owner, an arity the mention cannot carry. The island runs
        the exact call at application time, so Python's own errors arrive
        where Python would raise them.
        """
        func = node.func
        if not node.keywords and isinstance(func, ast.Attribute):
            root = func.value
            if isinstance(root, ast.Name):
                owner = self.host_value(root.id)
                if isinstance(owner, types.ModuleType):
                    value = vars(owner).get(func.attr)
                    mention = callable_mention(value)
                    arities = callable_arities(value)
                    if mention is not None and arities is not None and len(node.args) in arities:
                        arguments = [self.expression(argument) for argument in node.args]
                        return self._adapt_mentioned_call(value, mention, arguments)
        return self._implicit_island(node)

    def _adapt_mentioned_call(
        self, value: object, mention: str, arguments: list[Atom]
    ) -> Expression:
        """Preserve Python semantics where an engine mention orders or types differently."""
        selector = operator_callable_selector(value)
        if selector is not None:
            return self._python_operator(selector, *arguments)
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
        return Expression([Symbol(mention), *arguments])

    def _plain_call_name(self, node: ast.Call) -> ast.Name:
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
            raise self._unknown_host_callee(node, node)
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
        (xs,) = self._args(node, 1, "len")
        if self._dict_atom(xs):
            # len of a dict-space is lib_dict's own size.
            self.libraries.add("dict")
            return Expression([Symbol("dict-size"), xs])
        # py-len is Python's len: expressions AND strings, since which one
        # arrives is a runtime fact.
        self.runtime_ops.add("py-len")
        return Expression([Symbol("py-len"), xs])

    def _py_abs(self, node: ast.Call) -> Atom:
        (x,) = self._args(node, 1, "abs")
        return self._python_operator("abs", x)

    def _py_min(self, node: ast.Call) -> Atom:
        return self._extremum(node, "min")

    def _py_max(self, node: ast.Call) -> Atom:
        return self._extremum(node, "max")

    def _extremum(self, node: ast.Call, which: str) -> Atom:
        args = self._args(node, None, which)
        if not args:
            msg = f"{which}() needs arguments"
            raise CompileError(msg, construct=which, line=node.lineno)
        if len(args) == 1:
            return self._python_operator(which, args[0])
        folded = self._python_operator(which, args[0], args[1])
        for argument in args[2:]:
            folded = self._python_operator(which, folded, argument)
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
        return self._python_operator("sum", *args)

    def _py_sorted(self, node: ast.Call) -> Atom:
        (xs,) = self._args(node, 1, "sorted")
        return self._python_operator("sorted", xs)

    def _py_pow(self, node: ast.Call) -> Atom:
        base, exponent = self._args(node, 2, "pow")
        return self._python_operator("pow", base, exponent)

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

    def _dict_atom(self, atom: Atom) -> bool:
        """Whether a compiled operand holds a dict-space."""
        if isinstance(atom, Expression) and atom.children:
            head = atom.children[0]
            return isinstance(head, Symbol) and head.name == "dict-space"
        if isinstance(atom, Variable):
            return any(
                python_name in self.dict_locals
                for python_name, variable in self.scope.items()
                if variable == atom.name
            )
        return False

    def _container_kind(self, node: ast.expr) -> str | None:
        """Recover a Python container species that its Atom image erases."""
        if isinstance(node, ast.Name):
            return self.container_locals.get(node.id)
        if isinstance(node, (ast.List, ast.ListComp)):
            return "list"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, (ast.Set, ast.SetComp)):
            return "set"
        if isinstance(node, (ast.Dict, ast.DictComp)):
            return "dict"
        if isinstance(node, ast.NamedExpr):
            return self._container_kind(node.value)
        if isinstance(node, ast.IfExp):
            body = self._container_kind(node.body)
            return body if body == self._container_kind(node.orelse) else None
        if isinstance(node, ast.BoolOp):
            kinds = {self._container_kind(value) for value in node.values}
            return kinds.pop() if len(kinds) == 1 else None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in self.scope and node.func.id in {
                "dict",
                "list",
                "set",
                "tuple",
            }:
                return node.func.id
            if node.func.id == "sorted" and node.func.id not in self.scope:
                return "list"
        if not isinstance(node, ast.BinOp):
            return None
        left = self._container_kind(node.left)
        right = self._container_kind(node.right)
        if left == right == "set" and isinstance(
            node.op, (ast.Sub, ast.BitAnd, ast.BitOr, ast.BitXor)
        ):
            return "set"
        if left == right == "dict" and isinstance(node.op, ast.BitOr):
            return "dict"
        if left == right and left in {"list", "tuple"} and isinstance(node.op, ast.Add):
            return left
        if isinstance(node.op, ast.Mult):
            if left in {"list", "tuple"} and _literal_integer(node.right):
                return left
            if right in {"list", "tuple"} and _literal_integer(node.left):
                return right
        return None

    def _x_Subscript(self, node: ast.Subscript) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        mention = self._mention(node)
        if mention is not None:
            return mention
        source = self.expression(node.value)
        if not isinstance(node.slice, ast.Slice) and self._dict_atom(source):
            # The get on a dict-space is lib_dict's own: the matching pair
            # releases its value, and a missing key answers nothing.
            self.libraries.add("dict")
            return Expression([Symbol("get-value"), source, self.expression(node.slice)])
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
        """A literal mapping METTAFIES: a dict is a SPACE of (key value) atoms.

        lib_dict's own decision, measured against the opaque handle, the
        live view, and a native type in its header: the literal lowers to
        ``(dict-space ((k v) ...))``, a lookup is get-value, membership is
        dict-has, and every space operation works on it. The image is a
        SNAPSHOT of a mutable value, as the library states; a dict the
        Python side keeps mutating crosses as ``py({...})``, the handle
        image, or through ``view``. Duplicate literal keys keep the last
        pair, Python's own rule, and a ``**spread`` is host behavior that
        islands whole.
        """
        pairs: dict[Atom, Atom] = {}
        for key_node, value_node in zip(node.keys, node.values, strict=True):
            if key_node is None:
                return self._implicit_island(node)
            pairs[self.expression(key_node)] = self.expression(value_node)
        return self._dict_space(
            Expression([Expression([key, value]) for key, value in pairs.items()])
        )

    def _x_Set(self, node: ast.Set) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        """A literal set is a dict to True, Python's own kinship."""
        members: dict[Atom, Atom] = {
            self.expression(element): Grounded(True)  # noqa: FBT003  -- the boolean literal is atom data at this site, not a behavior switch
            for element in node.elts
        }
        return self._dict_space(
            Expression([Expression([member, truth]) for member, truth in members.items()])
        )

    def _dict_space(self, pairs: Atom) -> Expression:
        """One dict-space call, with the library dependency recorded."""
        self.libraries.add("dict")
        return Expression([Symbol("dict-space"), pairs])

    # A dict-local's Python methods, on lib_dict's own vocabulary: views
    # answer one element per solution the way get-atoms does, and .get is
    # get-value's own empty-on-absence contract.
    _DICT_METHODS = {  # noqa: RUF012  -- class-level constant table, never mutated
        "keys": "get-keys",
        "values": "dict-values",
        "items": "dict-pairs",
    }

    def _dict_method_call(self, node: ast.Call) -> Atom | None:
        func = node.func
        if not isinstance(func, ast.Attribute):
            return None
        owner = func.value
        if not (
            isinstance(owner, ast.Name)
            and owner.id in self.dict_locals
            and owner.id in self.scope
            and not node.keywords
        ):
            return None
        holder = Variable(self.scope[owner.id])
        if func.attr in self._DICT_METHODS and not node.args:
            self.libraries.add("dict")
            return Expression([Symbol(self._DICT_METHODS[func.attr]), holder])
        if func.attr == "get" and len(node.args) == 1:
            self.libraries.add("dict")
            return Expression([Symbol("get-value"), holder, self.expression(node.args[0])])
        return None

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
        # A pattern is structural: while one compiles, the host-island
        # fallback is off, so a host name here keeps its loud refusal
        # instead of burying a grounded island in a match position.
        prior = self.outer._in_pattern
        self.outer._in_pattern = True
        try:
            return self._pattern_expression(node)
        finally:
            self.outer._in_pattern = prior

    def _pattern_expression(self, node: ast.expr) -> Atom:
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


def _literal_integer(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    )


def _computed_format_error(line: int) -> CompileError:
    return CompileError(
        "a computed f-string format spec has no lowering; write the spec literally, as in {x:.2f}",
        construct="f-string",
        line=line,
    )
