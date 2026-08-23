"""Purpose: lower Python statement blocks, lifted definitions, and yield blocks.
Guarantees:
  - assignments lower to ordered let* bindings [tested
    test_bindings_become_let_star]
  - generator statements preserve answer order and reject return values
    [tested test_generator_with_branches]
  - Python match arms compile to one ordered case tower, including captures,
    dotted value patterns, guards, alternatives, as-bindings, and fallback
    [tested: test_match_statement_lowers_to_one_ordered_case_tower;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - a star pattern lowers to the engine's segment variable, named through
    (:seg $x) and anonymous through ... [tested:
    test_match_star_lowers_to_a_segment_variable,
    test_a_case_star_pattern_binds_the_rest; commit=a3dff3abc83b9d82f3652093246e1d693d526cdb]
  - a final ``with space.limits(stack=N)`` block compiles to the scoped
    ``stack-limit`` pragma contract [tested:
    test_compiled_stack_limit_uses_the_scoped_pragma_contract;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - an annotated assignment lowers its target as an in-place type claim in
    ordinary and generator blocks, using an internal marker so source-level
    colon patterns remain data [tested:
    test_an_annotated_binding_emits_its_claim,
    translator_typed_let:a_source_colon_pair_stays_a_pattern;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast

from ._define_context import CompilerContext, next_aux_serial
from ._define_expression import _name_of
from .atoms import Atom, Expression, Grounded, Handle, Symbol, Variable
from .errors import CompileError


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


class StatementCompilerMixin(CompilerContext):
    def block(self, statements: list[ast.stmt]) -> Atom:
        """A statement list folded into one term: assignments become let*
        bindings around what follows, if/return close the branch, and a loop
        becomes its own tail-recursive equation whose parameters are the
        loop state, with everything after the loop living in the equation's
        exit branch, Appel's blocks-as-functions.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        statements = [s for s in statements if not _is_docstring(s)]
        if not statements:
            if self.closer is not None:
                return self.closer(self)
            msg = f"{self.name} has no body to compile"
            raise CompileError(msg, construct="body")
        head, rest = statements[0], statements[1:]

        if isinstance(head, ast.Return):
            return self._return_statement(head, rest)

        if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            return self._bound_block(head, rest)

        if isinstance(head, (ast.If, ast.While, ast.For, ast.FunctionDef, ast.Match, ast.With)):
            return self._compound_statement(head, rest)

        if isinstance(head, (ast.Break, ast.Continue)):
            msg = (
                f"`{type(head).__name__.lower()}` has no equation here; fold "
                f"the exit condition into the loop's test, or return"
            )
            raise CompileError(
                msg,
                construct=type(head).__name__.lower(),
                line=head.lineno,
            )

        msg = (
            f"{type(head).__name__} has no MeTTa equivalent in the compiled "
            f"subset, which covers expressions, assignment, if/else, return, "
            f"yield, lambda and comprehensions"
        )
        raise CompileError(
            msg,
            construct=type(head).__name__,
            line=head.lineno,
        )

    def _return_statement(self, head: ast.Return, rest: list[ast.stmt]) -> Atom:
        if rest:
            msg = "statements after `return` are unreachable and have no equation"
            raise CompileError(
                msg,
                construct="return",
                line=rest[0].lineno,
            )
        if head.value is None:
            msg = "a compiled function returns a value; a bare `return` has nothing to rewrite to"
            raise CompileError(
                msg,
                construct="return",
                line=head.lineno,
            )
        return self.expression(head.value)

    def _bound_block(
        self,
        head: ast.Assign | ast.AnnAssign | ast.AugAssign,
        rest: list[ast.stmt],
    ) -> Expression:
        pattern, value = self._binding(head)
        return Expression([Symbol("let*"), Expression([Expression([pattern, value])]), self.block(rest)])

    def _compound_statement(
        self,
        head: ast.If | ast.While | ast.For | ast.FunctionDef | ast.Match | ast.With,
        rest: list[ast.stmt],
    ) -> Atom:
        if isinstance(head, ast.If):
            return self.if_statement(head, rest, lambda compiler, body: compiler.block(body))
        if isinstance(head, ast.While):
            return self._while_statement(head, rest)
        if isinstance(head, ast.For):
            return self._for_statement(head, rest)
        if isinstance(head, ast.Match):
            return self._match_statement(head, rest)
        if isinstance(head, ast.With):
            return self._limits_statement(head, rest)
        self._lift_definition(head)
        return self.block(rest)

    def _match_statement(self, node: ast.Match, rest: list[ast.stmt]) -> Atom:
        """Compile ordered Python patterns into nested engine ``case`` rows.

        Each arm owns a forked SSA scope. Guard failure jumps to the first
        row after the whole arm, so an OR-pattern never retries another
        alternative after its guard has already run. The subject is bound
        once before the tower, matching Python even when it is a call.
        """
        subject_name = self._temp("match-subject")
        subject = Variable(subject_name)
        subject_value = self.expression(node.subject)

        if rest and _is_irrefutable(node.cases[-1].pattern):
            msg = "statements after an exhaustive match are unreachable"
            raise CompileError(msg, construct="match", line=rest[0].lineno)
        if rest:
            fallback = self._fork().block(rest)
        elif self.closer is not None:
            fallback = self.closer(self._fork())
        else:
            fallback = Expression([Symbol("empty")])

        for case in reversed(node.cases):
            after_arm = fallback
            alternatives = (
                list(case.pattern.patterns)
                if isinstance(case.pattern, ast.MatchOr)
                else [case.pattern]
            )
            for pattern_node in reversed(alternatives):
                compiler = self._fork()
                pattern_scope = _StatementPattern(compiler)
                pattern = pattern_scope.pattern(pattern_node)
                arm = compiler.block(case.body)
                if case.guard is not None:
                    arm = Expression([Symbol("if"), compiler._truthy(case.guard), arm, after_arm])
                arm = pattern_scope.wrap_as_bindings(subject, arm)
                fallback = _case_row(subject, pattern, arm, fallback)

        return Expression(
            [
                Symbol("let*"),
                Expression([Expression([subject, subject_value])]),
                fallback,
            ]
        )

    def _limits_statement(self, node: ast.With, rest: list[ast.stmt]) -> Atom:
        """Lower a final Space.limits block to the engine's scoped pragma."""
        if rest:
            msg = "statements after a compiled limits block are unreachable"
            raise CompileError(msg, construct="with limits", line=rest[0].lineno)
        if len(node.items) != 1 or node.items[0].optional_vars is not None:
            raise _limits_compile_error(node.lineno)
        context = node.items[0].context_expr
        if not (
            isinstance(context, ast.Call)
            and isinstance(context.func, ast.Attribute)
            and isinstance(context.func.value, ast.Name)
            and context.func.attr == "limits"
            and isinstance(self.host_value(context.func.value.id), Handle)
            and not context.args
        ):
            raise _limits_compile_error(node.lineno)
        keys = {
            "timeout": "max-time",
            "inferences": "max-inferences",
            "stack": "stack-limit",
        }
        settings: list[Expression] = []
        for keyword in context.keywords:
            key = keys.get(keyword.arg or "")
            if key is None or not isinstance(keyword.value, ast.Constant):
                raise _limits_compile_error(node.lineno)
            value = keyword.value.value
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise _limits_compile_error(node.lineno)
            if keyword.arg != "timeout" and not isinstance(value, int):
                raise _limits_compile_error(node.lineno)
            settings.append(Expression([Symbol(key), Grounded(value)]))
        if not settings:
            raise _limits_compile_error(node.lineno)
        return Expression(
            [
                Symbol("with-pragma!"),
                Expression(settings),
                self._fork().block(node.body),
            ]
        )

    def _binding(
        self,
        head: ast.Assign | ast.AnnAssign | ast.AugAssign,
    ) -> tuple[Atom, Atom]:
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
                msg = f"{target_name!r} is augmented before it is bound"
                raise CompileError(
                    msg,
                    construct="augmented assignment",
                    line=head.lineno,
                )
            target = target_name
        elif isinstance(head, ast.AnnAssign):
            if head.value is None:
                msg = "an annotation without a value binds nothing"
                raise CompileError(
                    msg,
                    construct="annotation",
                    line=head.lineno,
                )
            target = _name_of(head.target, head.lineno)
            value = self.expression(head.value)
        else:
            target = _single_target(head)
            value = self.expression(head.value)
        variable: Atom = Variable(self._bind(target))
        if isinstance(head, ast.AnnAssign):
            claim = Expression([Symbol(":"), variable, self.annotation_atom(head.annotation)])
            variable = Expression([Symbol("__petta_typed_binding__"), claim])
        return variable, value

    def if_statement(self, node: ast.If, rest: list[ast.stmt], continue_with) -> Atom:
        test = self._truthy(node.test)
        # Each arm compiles in its own forked scope: a rebind inside one arm
        # must not rename what the other arm, or anything after, reads.
        then = continue_with(self._fork(), node.body)
        if node.orelse:
            otherwise = continue_with(self._fork(), node.orelse)
            if rest:
                msg = "statements after an if/else where both branches close are unreachable"
                raise CompileError(
                    msg,
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
            msg = (
                "an `if` with no `else` and nothing after it leaves one branch "
                "without a value; MeTTa's two-armed `if` needs both"
            )
            raise CompileError(
                msg,
                construct="if",
                line=node.lineno,
            )
        return Expression([Symbol("if"), test, then, otherwise])

    def _lift_definition(self, node: ast.FunctionDef) -> None:
        """A nested def, lambda-lifted (Johnsson): its free outer names
        become leading parameters, the equation joins the definition's own,
        and every call site prepends the lifted names' current variables,
        which is Python's late binding resolved per call.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _validate_nested_signature(node)
        params = [arg.arg for arg in node.args.args]
        lifted = _lifted_names(node, self.scope, params)
        mangled = f"{self.name}--{node.name}-{next_aux_serial()}"
        generator = _is_generator(node)
        self.lifted[node.name] = (mangled, lifted, generator)

        inner = self._equation_compiler(lifted + params)
        body: Atom = (
            _superpose(inner.yield_answers(node.body)) if generator else inner.block(node.body)
        )
        head = Expression([Symbol(mangled), *(Variable(n) for n in lifted + params)])
        self.aux.append(Expression([Symbol("="), head, body]))

    def yield_answers(self, statements: list[ast.stmt]) -> list[Atom]:
        """A generator body as a list of answer terms.

        Every yield contributes one answer; an if contributes one term
        choosing between its branches' superpositions and never closes the
        block, since both branches fall through in Python; a binding wraps
        everything after it in let*, whose value superposes the tail.
        """
        statements = [s for s in statements if not _is_docstring(s)]
        if not statements:
            msg = f"{self.name} yields nothing"
            raise CompileError(msg, construct="body")
        head, rest = statements[0], statements[1:]

        if isinstance(head, ast.Expr):
            return self._yield_expression(head, rest)

        if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            return self._yield_binding(head, rest)

        if isinstance(head, ast.If):
            return self._yield_if(head, rest)

        if isinstance(head, ast.For):
            return self._yield_for(head, rest)

        if isinstance(head, ast.Return):
            msg = "a generator answers through yield; `return` inside one has no equation"
            raise CompileError(
                msg,
                construct="return",
                line=head.lineno,
            )

        msg = (
            f"{type(head).__name__} has no place in a compiled generator, "
            f"which covers yield, assignment and if/else"
        )
        raise CompileError(
            msg,
            construct=type(head).__name__,
            line=head.lineno,
        )

    def _yield_expression(self, head: ast.Expr, rest: list[ast.stmt]) -> list[Atom]:
        if isinstance(head.value, ast.Yield):
            if head.value.value is None:
                msg = "a bare `yield` has no value to answer"
                raise CompileError(
                    msg,
                    construct="yield",
                    line=head.lineno,
                )
            return [self.expression(head.value.value), *self._yield_tail(rest)]
        if isinstance(head.value, ast.YieldFrom):
            return [self._yield_from(head.value), *self._yield_tail(rest)]
        msg = (
            f"{type(head).__name__} has no place in a compiled generator, "
            "which covers yield, assignment and if/else"
        )
        raise CompileError(
            msg,
            construct=type(head).__name__,
            line=head.lineno,
        )

    def _yield_binding(
        self,
        head: ast.Assign | ast.AnnAssign | ast.AugAssign,
        rest: list[ast.stmt],
    ) -> list[Atom]:
        pattern, value = self._binding(head)
        tail = _superpose(self.yield_answers(rest))
        return [Expression([Symbol("let*"), Expression([Expression([pattern, value])]), tail])]

    def _yield_if(self, head: ast.If, rest: list[ast.stmt]) -> list[Atom]:
        then = _superpose(self._fork().yield_answers(head.body))
        otherwise = (
            _superpose(self._fork().yield_answers(head.orelse))
            if head.orelse
            else Expression([Symbol("empty")])
        )
        chooser = Expression([Symbol("if"), self._truthy(head.test), then, otherwise])
        return [chooser, *self._yield_tail(rest)]

    def _yield_for(self, head: ast.For, rest: list[ast.stmt]) -> list[Atom]:
        # `for x in e: <yields>` is iteration as nondeterminism: bind x to
        # each element of e through superpose, answer the body for each. The
        # loop never closes the block, exactly as in Python.
        if head.orelse:
            msg = (
                "`for ... else` has no equation; the else arm runs on "
                "non-break exit and this subset has no break"
            )
            raise CompileError(
                msg,
                construct="for-else",
                line=head.lineno,
            )
        body_compiler = self._fork()
        variable = body_compiler._bind(_name_of(head.target, head.lineno))
        body = _superpose(body_compiler.yield_answers(head.body))
        looped = self._iteration(head.iter, variable, body)
        return [looped, *self._yield_tail(rest)]

    def _yield_tail(self, rest: list[ast.stmt]) -> list[Atom]:
        return self.yield_answers(rest) if rest else []


def _superpose(answers: list[Atom]) -> Expression:
    """The answers as one superposition, flattened where a member already is
    one over literal alternatives; (superpose $x) over a bound value stays
    whole, since only an expression of alternatives can splice.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    flat: list[Atom] = []
    for a in answers:
        if (
            isinstance(a, Expression)
            and a.head == Symbol("superpose")
            and len(a) == 2
            and isinstance(a[1], Expression)
        ):
            flat.extend(a[1])
        else:
            flat.append(a)
    return Expression([Symbol("superpose"), Expression(flat)])


class _StatementPattern:
    """Compile one Python case pattern and remember its whole-value binds."""

    def __init__(self, compiler: CompilerContext):
        self.compiler = compiler
        self.as_variables: list[Variable] = []

    def pattern(self, node: ast.pattern) -> Atom:
        if isinstance(node, ast.MatchValue):
            return self.compiler.expression(node.value)
        if isinstance(node, ast.MatchSingleton):
            return self._singleton(node)
        if isinstance(node, ast.MatchSequence):
            return Expression([self.pattern(part) for part in node.patterns])
        if isinstance(node, ast.MatchClass):
            return self._class(node)
        if isinstance(node, ast.MatchAs):
            return self._as(node)
        if isinstance(node, ast.MatchStar):
            return self._star(node)
        if isinstance(node, ast.MatchMapping):
            msg = "mapping patterns need an engine dictionary image; match positional terms instead"
            raise CompileError(msg, construct="match mapping", line=node.lineno)
        if isinstance(node, ast.MatchOr):
            msg = "OR patterns are compiled by the enclosing ordered case arm"
            raise CompileError(msg, construct="match pattern", line=node.lineno)
        msg = f"{type(node).__name__} has no MeTTa case-pattern image"
        raise CompileError(msg, construct="match pattern", line=getattr(node, "lineno", None))

    def _star(self, node: ast.MatchStar) -> Atom:
        """A star pattern is a SEGMENT VARIABLE, the variable's fifth face.

        ``case (S.Order, id, *rest):`` binds ``rest`` to the run of children the
        fixed part left over, which is Kutsia's final-position fragment exactly:
        the gap is the last child of its own pattern, the arm's subject is a
        value and therefore carries no gap of its own, and the answer is unitary
        [source: LeaTTa MettaHyperonFull/Core/SeqFragment.lean, seqFinitary?].
        Python's own grammar gives us the linearity the law wants for free,
        since a sequence pattern admits at most one star.

        ``*_`` needs no name, and the engine's anonymous gap is exactly that: an
        occurrence whose run is consumed and discarded, distinct from every
        other occurrence.
        """
        if node.name is None:
            return Symbol("...")
        return Expression([Symbol(":seg"), Variable(self.compiler._bind(node.name))])

    def _singleton(self, node: ast.MatchSingleton) -> Atom:
        if isinstance(node.value, bool):
            return Grounded(node.value)
        msg = "None has no MeTTa case value; use a data symbol such as Nil"
        raise CompileError(msg, construct="match pattern", line=node.lineno)

    def _class(self, node: ast.MatchClass) -> Atom:
        if node.kwd_attrs:
            msg = (
                "keyword class patterns have no positional MeTTa image; "
                "match the constructor's positional fields"
            )
            raise CompileError(msg, construct="match pattern", line=node.lineno)
        return Expression(
            [self.compiler.expression(node.cls), *(self.pattern(p) for p in node.patterns)]
        )

    def _as(self, node: ast.MatchAs) -> Atom:
        inner = Variable("_") if node.pattern is None else self.pattern(node.pattern)
        if node.name is None:
            return inner
        variable = Variable(self.compiler._bind(node.name))
        if node.pattern is None:
            return variable
        self.as_variables.append(variable)
        return inner

    def wrap_as_bindings(self, subject: Atom, body: Atom) -> Atom:
        for variable in reversed(self.as_variables):
            body = Expression([Symbol("let"), variable, subject, body])
        return body


def _case_row(subject: Atom, pattern: Atom, body: Atom, fallback: Atom) -> Expression:
    rows = Expression(
        [
            Expression([pattern, body]),
            Expression([Variable("_"), fallback]),
        ]
    )
    return Expression([Symbol("case"), subject, rows])


def _is_irrefutable(pattern: ast.pattern) -> bool:
    return isinstance(pattern, ast.MatchAs) and pattern.pattern is None


def _limits_compile_error(line: int) -> CompileError:
    return CompileError(
        "a compiled with-block is space.limits() with positive literal "
        "timeout=, inferences=, or stack= bounds and no `as` target",
        construct="with limits",
        line=line,
    )


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _single_target(node: ast.Assign) -> str:
    if len(node.targets) != 1:
        msg = "a chained assignment binds several names at once and has no let* form"
        raise CompileError(
            msg,
            construct="assignment",
            line=node.lineno,
        )
    return _name_of(node.targets[0], node.lineno)


def _validate_nested_signature(node: ast.FunctionDef) -> None:
    if node.args.defaults or node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
        msg = (
            "a nested def takes plain positional parameters; defaults "
            "belong on top-level clauses, where they are head patterns"
        )
        raise CompileError(
            msg,
            construct="nested def",
            line=node.lineno,
        )


def _lifted_names(node: ast.FunctionDef, scope: dict[str, str], params: list[str]) -> list[str]:
    return list(
        dict.fromkeys(
            sub.id
            for sub in ast.walk(node)
            if isinstance(sub, ast.Name)
            and isinstance(sub.ctx, ast.Load)
            and sub.id in scope
            and sub.id not in params
        )
    )
