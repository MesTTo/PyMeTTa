"""Purpose: lower Python statement blocks, lifted definitions, and yield blocks.
Guarantees:
  - assignments lower to ordered let* bindings [tested
    test_bindings_become_let_star]
  - generator statements preserve answer order and reject return values
    [tested test_generator_with_branches]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import ast

from ._define_context import CompilerContext, next_aux_serial
from ._define_expression import _name_of
from .atoms import Atom, Expr, Sym, Var
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
        """
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

        if isinstance(head, (ast.If, ast.While, ast.For, ast.FunctionDef)):
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
    ) -> Expr:
        variable, value = self._binding(head)
        return Expr([Sym("let*"), Expr([Expr([Var(variable), value])]), self.block(rest)])

    def _compound_statement(
        self,
        head: ast.If | ast.While | ast.For | ast.FunctionDef,
        rest: list[ast.stmt],
    ) -> Atom:
        if isinstance(head, ast.If):
            return self.if_statement(head, rest, lambda compiler, body: compiler.block(body))
        if isinstance(head, ast.While):
            return self._while_statement(head, rest)
        if isinstance(head, ast.For):
            return self._for_statement(head, rest)
        self._lift_definition(head)
        return self.block(rest)

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
        return self._bind(target), value

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
        return Expr([Sym("if"), test, then, otherwise])

    def _lift_definition(self, node: ast.FunctionDef) -> None:
        """A nested def, lambda-lifted (Johnsson): its free outer names
        become leading parameters, the equation joins the definition's own,
        and every call site prepends the lifted names' current variables,
        which is Python's late binding resolved per call.
        """
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
        head = Expr([Sym(mangled), *(Var(n) for n in lifted + params)])
        self.aux.append(Expr([Sym("="), head, body]))

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
        variable, value = self._binding(head)
        tail = _superpose(self.yield_answers(rest))
        return [Expr([Sym("let*"), Expr([Expr([Var(variable), value])]), tail])]

    def _yield_if(self, head: ast.If, rest: list[ast.stmt]) -> list[Atom]:
        then = _superpose(self._fork().yield_answers(head.body))
        otherwise = (
            _superpose(self._fork().yield_answers(head.orelse))
            if head.orelse
            else Expr([Sym("empty")])
        )
        chooser = Expr([Sym("if"), self._truthy(head.test), then, otherwise])
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


def _superpose(answers: list[Atom]) -> Expr:
    """The answers as one superposition, flattened where a member already is
    one over literal alternatives; (superpose $x) over a bound value stays
    whole, since only an expression of alternatives can splice.
    """
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
