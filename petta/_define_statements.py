"""Purpose: lower Python statement blocks, lifted definitions, and yield blocks.
Guarantees:
  - assignments lower to ordered let* bindings [tested
    test_bindings_become_let_star]
  - generator statements preserve answer order and reject return values
    [tested test_generator_with_branches]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
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
