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
  - assignment and augmented assignment to a closed-over ``State.value``
    lower to ``change-state!`` while preserving Python's read-before-write
    order [tested: test_compiled_state_properties_round_trip_through_engine_heads;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - assertions continue on truth and otherwise answer ``(Error call reason)``,
    including message and generator continuations [tested:
    test_compiled_assert_lowers_to_the_error_algebra;
    commit=6a695598aaf5951530cb8efe9afe46977afe541c]
  - except arms retain the live exception class objects resolved at compile
    time rather than reducing identity to a class name [tested:
    test_compiled_except_uses_exception_class_identity_not_bare_name;
    commit=e7919ef660e1c2b31a307187c0237823daccdbd4]
  - non-space augmented assignments use Python's in-place protocol and carry
    local container species across SSA rebinding [tested:
    test_compiled_operators_follow_python_protocols_and_result_species;
    commit=e3787593132a7ece2d300397045f7415709847c9]
  - ``del space[pattern]`` removes every snapshotted match while annotated
    space ``-=`` removes one, with missing removals kept loud [tested:
    test_compiled_removal_statements_preserve_one_many_missing_and_target_scope;
    commit=6a695598aaf5951530cb8efe9afe46977afe541c]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
from collections.abc import Callable

from ._define_context import CompilerContext, next_aux_serial
from ._define_expression import _NATIVE_BINOPS, _name_of
from .atoms import Atom, Expression, Grounded, Handle, Symbol, Variable
from .errors import CompileError


def _walrus_roots(head: ast.stmt) -> list[ast.expr]:
    """The statement's once-evaluated expressions, where hoisting is lawful."""
    if isinstance(head, ast.Return) and head.value is not None:
        return [head.value]
    if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return [] if head.value is None else [head.value]
    if isinstance(head, ast.Expr):
        return [head.value]
    if isinstance(head, ast.If):
        return [head.test]
    if isinstance(head, ast.For):
        return [head.iter]
    if isinstance(head, ast.Match):
        return [head.subject]
    if isinstance(head, ast.While):
        for sub in ast.walk(head.test):
            if isinstance(sub, ast.NamedExpr):
                msg = (
                    "a walrus in a while test would rebind per iteration; "
                    "bind inside the loop body instead"
                )
                raise CompileError(
                    msg,
                    construct="walrus",
                    line=sub.lineno,
                )
    return []


def _hoistable_walruses(
    head: ast.stmt, builder_rooted: Callable[[ast.AST], bool]
) -> list[ast.NamedExpr]:
    """Every walrus in the statement's hoistable expressions, in order.

    Hoistable positions evaluate exactly once before the statement acts:
    a return or yield value, a binding's right side, a bare expression, an
    if test, a for iterable, a match subject. A while test re-evaluates
    per iteration and a nested scope (lambda, def, comprehension) owns its
    body, so a walrus there refuses with its own remedy instead of
    hoisting wrongly. A BUILT TERM is a third boundary: inside S.f(...)
    the walrus value is data the term carries, so hoisting it into an
    evaluating let ran (+ $x 1) with $x unbound where the term meant to
    hold that expression [measured 2026-08-24 by the spaces twins agent:
    the hoisted binding jumped the match that binds $x and the engine
    refused "+ ran backwards"].
    """
    roots = _walrus_roots(head)
    found: list[ast.NamedExpr] = []

    def collect(node: ast.AST) -> None:
        # Postorder: children before parents, left to right, which is both
        # sibling evaluation order and inner-before-container for nesting.
        if builder_rooted(node):
            for sub in ast.walk(node):
                if isinstance(sub, ast.NamedExpr):
                    msg = (
                        "a walrus inside a built term is data the term "
                        "carries, not a binding this statement can hoist; "
                        "bind the value on its own line before the "
                        "statement, or keep the engine's own let inside "
                        "the term"
                    )
                    raise CompileError(
                        msg,
                        construct="walrus",
                        line=sub.lineno,
                    )
            return
        if isinstance(
            node,
            (
                ast.Lambda,
                ast.FunctionDef,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
            ),
        ):
            for sub in ast.walk(node):
                if isinstance(sub, ast.NamedExpr):
                    msg = (
                        "a walrus inside a nested scope leaks its binding "
                        "past what compiles here; bind before the "
                        "expression instead"
                    )
                    raise CompileError(
                        msg,
                        construct="walrus",
                        line=sub.lineno,
                    )
            return
        for child in ast.iter_child_nodes(node):
            collect(child)
        if isinstance(node, ast.NamedExpr):
            found.append(node)

    for root in roots:
        collect(root)
    return found


def _replace_walrus(head: ast.stmt, walrus: ast.NamedExpr, target: str) -> None:
    """Swap one walrus node for a plain load of its bound name."""
    load = ast.copy_location(ast.Name(id=target, ctx=ast.Load()), walrus)
    for parent in ast.walk(head):
        for field, child in ast.iter_fields(parent):
            if child is walrus:
                setattr(parent, field, load)
                return
            if isinstance(child, list):
                for index, item in enumerate(child):
                    if item is walrus:
                        child[index] = load
                        return


def _space_valued(value: Atom) -> bool:
    """Whether a compiled binding value is a SPACE.

    A handle, or a term whose head mints or reads one; decides whether +=
    on the bound name means the write door or arithmetic. A dict-space IS
    a space, so every space door works on a dict local too.
    """
    if isinstance(value, Handle):
        return True
    if isinstance(value, Expression) and value.children:
        head = value.children[0]
        # policy-inventory-exempt: mechanism-internal; reason=the three heads that mint or read a space in a compiled binding decide the += write-door reading and are not a value vocabulary; evidence=extensions/python/metta/_define_statements.py:_space_valued
        return isinstance(head, Symbol) and head.name in {
            "context-space",
            "new-space",
            "dict-space",
        }
    return False


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

        walruses = _hoistable_walruses(head, self._builder_rooted)
        if walruses:
            return self._walrus_block(walruses, head, rest)

        if isinstance(head, ast.Return):
            return self._return_statement(head, rest)

        if isinstance(head, ast.Assert):
            return self._assert_statement(head, rest)

        if isinstance(head, ast.Delete):
            return self._delete_statement(head, rest)

        if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            return self._bound_block(head, rest)

        if isinstance(head, (ast.If, ast.While, ast.For, ast.FunctionDef, ast.Match, ast.With)):
            return self._compound_statement(head, rest)

        if isinstance(head, ast.Raise):
            return self._raise_statement(head, rest)

        if isinstance(head, ast.Try):
            return self._try_statement(head, rest)

        if isinstance(head, ast.TypeAlias):
            return self._type_alias_statement(head, rest)

        if isinstance(head, (ast.Global, ast.Nonlocal)):
            return self._scope_pragma_statement(head, rest)

        if isinstance(head, ast.ClassDef):
            msg = (
                f"a class defined inside a compiled body would mint a new "
                f"class per application; classes are declarations here, so "
                f"define {head.name!r} at module level and register it with "
                f"@space.define"
            )
            raise CompileError(msg, construct="class", line=head.lineno)

        if isinstance(head, ast.TryStar):
            msg = (
                "except* groups exceptions across concurrent tasks, which a "
                "compiled equation does not stage; catch the members with a "
                "plain try/except"
            )
            raise CompileError(msg, construct="except*", line=head.lineno)

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
            f"subset, which covers expressions, assignment, if/else, match, "
            f"try/except, raise, loops, return, yield, lambda and "
            f"comprehensions"
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

    def _assert_statement(self, node: ast.Assert, rest: list[ast.stmt]) -> Atom:
        """Continue on a true condition and produce the language's Error value."""
        return self._assertion(node, self.block(rest))

    def _assertion(self, node: ast.Assert, continuation: Atom) -> Expression:
        """Build one lazy failure branch shared by value and generator blocks."""
        culprit = self._diagnostic_term(node.test)
        if node.msg is None:
            failure: Atom = Expression([Symbol("Error"), culprit, Symbol("AssertionError")])
        else:
            reason_name = self._temp("assert-reason")
            reason = Variable(reason_name)
            failure = Expression(
                [
                    Symbol("let*"),
                    Expression([Expression([reason, self.expression(node.msg)])]),
                    Expression([Symbol("Error"), culprit, reason]),
                ]
            )
        return Expression([Symbol("if"), self._truthy(node.test), continuation, failure])

    def _raise_statement(self, node: ast.Raise, rest: list[ast.stmt]) -> Atom:
        """`raise` produces an error through the prelude's throw.

        A produced error finishes the enclosing call and travels exactly as
        an engine-raised one, so `raise` closes its branch the way `return`
        does. A raised class call islands into the live exception instance,
        so what an outer `except ... as e` binds is the object Python would
        have bound. A bare `raise` re-throws the error atom of the
        innermost enclosing except arm, and refuses elsewhere with
        Python's own no-active-exception rule.
        """
        if rest:
            msg = "statements after `raise` are unreachable and have no equation"
            raise CompileError(msg, construct="raise", line=rest[0].lineno)
        if node.exc is None:
            key = self.handler_error
            if key is None or key not in self.scope:
                msg = (
                    "a bare `raise` re-raises only inside an except arm; "
                    "there is no active exception here (Python's own rule)"
                )
                raise CompileError(msg, construct="raise", line=node.lineno)
            return Expression([Symbol("throw"), Variable(self.scope[key])])
        payload = self.expression(node.exc)
        if node.cause is not None:
            # `raise X from C` carries its cause STRUCTURALLY: the term
            # says what caused what, the mettafied reading of __cause__,
            # and except arms classify through the wrapper.
            if isinstance(node.cause, ast.Constant) and node.cause.value is None:
                cause: Atom = Grounded(None)
            else:
                cause = self.expression(node.cause)
            payload = Expression([Symbol("caused-by"), payload, cause])
        return Expression([Symbol("throw"), payload])

    def _try_statement(self, node: ast.Try, rest: list[ast.stmt]) -> Atom:
        """Python's try, carried by the engine's own error algebra.

        The body runs under `catch`, which reifies a host exception and
        passes any other value through, so one binding sees both error
        lanes: a produced error is already an (Error ...) answer, data is
        itself. `if-error` splits the lanes. Each `except` arm asks
        py-except-match against Python's own class lattice; an unmatched
        error re-throws; a matched arm binds `as` through
        py-except-payload, so a raised instance is what the handler holds.
        Success falls through a serialed tag tuple carrying the body's
        bindings to the continuation (blocks-as-functions, as the loops
        compile), which is also what lets a `return` inside the body pass
        untagged through the case fallback, exactly as Python returns past
        the rest of the function. `finally` wraps the whole dispatch in a
        second catch under the same tag discipline, so it runs on success,
        on a matched arm, on an unmatched error, on a return, and on an
        error a handler itself produced.
        """
        k_params = self._try_carried_names(node, rest)
        continue_to = self._try_continuation(node, rest, k_params)
        # A finally block's bindings are definite (the effect lane is
        # linear), so they override at the exit and the tag need not carry
        # them; every other carried name rides the tag tuple.
        fin_stores: set[str] = set()
        for piece in node.finalbody:
            for sub in ast.walk(piece):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    fin_stores.add(sub.id)
        tag_params = [name for name in k_params if name not in fin_stores]
        tag = f"{self.name}--try-ok-{next_aux_serial()}"
        fell_through = [False]

        def tagged(compiler: CompilerContext) -> Expression:
            fell_through[0] = True
            return Expression(
                [
                    Symbol(tag),
                    *self._carried_variables(compiler, tag_params, node.lineno),
                ]
            )

        # With a finally, no path continues directly: success and handler
        # arms settle into the tag, and the continuation runs at the EXIT,
        # after the finally, which is Python's own order.
        settled = tagged if node.finalbody else continue_to

        body_compiler = self._fork()
        body_compiler.closer = tagged
        body_compiler.closer_names = tag_params.copy()
        # Bindings inside the body trap error data and produce it, so an
        # assignment whose right side errors aborts to the arms exactly as
        # Python's raise would (see CompilerContext.in_try_body).
        body_compiler.in_try_body = True
        body = body_compiler.block(node.body)

        result_name = self._temp("try-result")
        result = Variable(result_name)

        success: Atom
        if fell_through[0]:
            success = self._try_success_arm(node, tag_params, tag, result, settled)
        elif node.orelse:
            # else runs only when the body falls through, and this body
            # closes every path, the unreachable-arm rule match uses.
            msg = "an else arm after a try whose body always closes is unreachable"
            raise CompileError(msg, construct="try", line=node.orelse[0].lineno)
        else:
            # Every body path returned or raised: a non-error value IS the
            # answer, passing through exactly as Python returns past the
            # rest of the function.
            success = result
        handlers = self._try_handler_chain(node, tag_params, result_name, result, settled)
        dispatch = Expression([Symbol("if-error"), result, handlers, success])
        caught = Expression([Symbol("catch"), body])
        if not node.finalbody:
            return Expression(
                [
                    Symbol("let*"),
                    Expression([Expression([result, caught])]),
                    dispatch,
                ]
            )
        return self._try_finally(
            node,
            tag_params=tag_params,
            tag=tag,
            result=result,
            caught=caught,
            dispatch=dispatch,
            continue_to=continue_to,
            fell=fell_through[0],
        )

    def _try_carried_names(self, node: ast.Try, rest: list[ast.stmt]) -> list[str]:
        """The names the continuation needs: what the rest or the enclosing
        closer reads, restricted to names either already in scope or bound
        somewhere inside the try, in first-read order.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

        def stores(pieces: tuple[ast.AST, ...]) -> set[str]:
            found: set[str] = set()
            for piece in pieces:
                for sub in ast.walk(piece):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        found.add(sub.id)
            return found

        body_stored = stores(tuple(node.body))
        stored = body_stored | stores((*node.handlers, *node.orelse, *node.finalbody))
        carried: list[str] = []

        def collect(pieces: list[ast.stmt], bound: set[str]) -> None:
            for statement in pieces:
                for sub in ast.walk(statement):
                    if (
                        isinstance(sub, ast.Name)
                        and isinstance(sub.ctx, ast.Load)
                        and (sub.id in self.scope or sub.id in bound)
                        and sub.id not in carried
                    ):
                        carried.append(sub.id)

        # The else arm runs in the success destructure, so what it reads
        # of the BODY's bindings must ride the tag; its own bindings are
        # its own. The rest may read any arm's bindings.
        collect(node.orelse, body_stored)
        collect(rest, stored)
        for name in self.closer_names:
            if name in self.scope and name not in carried:
                carried.append(name)
        return carried

    def _carried_variables(
        self, compiler: CompilerContext, k_params: list[str], line: int | None
    ) -> list[Atom]:
        variables: list[Atom] = []
        for name in k_params:
            variable = compiler.scope.get(name)
            if variable is None:
                msg = (
                    f"{name!r} is read after the try but is not bound on "
                    f"every path reaching that read (Python's own "
                    f"possibly-unbound rule); bind it before the try or in "
                    f"every arm"
                )
                raise CompileError(msg, construct="try", line=line)
            variables.append(Variable(variable))
        return variables

    def _try_continuation(
        self, node: ast.Try, rest: list[ast.stmt], k_params: list[str]
    ) -> Callable[[CompilerContext], Atom]:
        """What a successful or handled path continues INTO: the lifted
        rest as its own equation, the enclosing closer, or a refusal that
        fires only if some path actually falls through.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if rest:
            helper = f"{self.name}--after-try-{next_aux_serial()}"
            equation_compiler = self._equation_compiler(k_params)
            equation_compiler.closer = self.closer
            equation_compiler.closer_names = self.closer_names.copy()
            head = Expression([Symbol(helper), *(Variable(n) for n in k_params)])
            self.aux.append(Expression([Symbol("="), head, equation_compiler.block(rest)]))

            def continue_to(compiler: CompilerContext) -> Atom:
                return Expression(
                    [
                        Symbol(helper),
                        *self._carried_variables(compiler, k_params, node.lineno),
                    ]
                )

            return continue_to
        if self.closer is not None:
            return self.closer

        def refuse(compiler: CompilerContext) -> Atom:
            del compiler
            msg = (
                f"{self.name} falls through its try with nothing after it; "
                f"return in the body or the else arm, or continue the block"
            )
            raise CompileError(msg, construct="try", line=node.lineno)

        return refuse

    def _try_success_arm(
        self,
        node: ast.Try,
        tag_params: list[str],
        tag: str,
        result: Variable,
        settled: Callable[[CompilerContext], Atom],
    ) -> Expression:
        arm_compiler = self._fork()
        pattern = Expression([Symbol(tag), *(Variable(arm_compiler._bind(n)) for n in tag_params)])
        if node.orelse:
            # else compiles OUTSIDE the catch: an exception it raises is
            # not this try's to handle, exactly Python's rule; under a
            # finally it re-settles into the tag with its own bindings.
            arm_compiler.closer = settled
            arm_compiler.closer_names = tag_params.copy()
            arm = arm_compiler.block(node.orelse)
        else:
            arm = settled(arm_compiler)
        passthrough = Variable(self._temp("try-value"))
        return Expression(
            [
                Symbol("case"),
                result,
                Expression(
                    [
                        Expression([pattern, arm]),
                        Expression([passthrough, passthrough]),
                    ]
                ),
            ]
        )

    def _try_handler_chain(
        self,
        node: ast.Try,
        tag_params: list[str],
        result_name: str,
        result: Variable,
        settled: Callable[[CompilerContext], Atom],
    ) -> Atom:
        chain: Atom = Expression([Symbol("throw"), result])
        for handler in reversed(node.handlers):
            handler_compiler = self._fork()
            error_key = f"except-error-{next_aux_serial()}"
            handler_compiler.handler_error = error_key
            handler_compiler.scope[error_key] = result_name
            handler_compiler.closer = settled
            handler_compiler.closer_names = [*tag_params, error_key]
            if handler.name is not None:
                bound = handler_compiler._bind(handler.name)
                self.runtime_ops.add("error-payload")
                arm: Atom = Expression(
                    [
                        Symbol("let"),
                        Variable(bound),
                        Expression([Symbol("error-payload"), result]),
                        handler_compiler.block(handler.body),
                    ]
                )
            else:
                arm = handler_compiler.block(handler.body)
            if handler.type is None:
                chain = arm
                continue
            self.runtime_ops.add("except")
            test = Expression(
                [
                    Symbol("except"),
                    result,
                    self._except_classinfo(handler.type),
                ]
            )
            chain = Expression([Symbol("if"), test, arm, chain])
        return chain

    def _except_classinfo(self, node: ast.expr) -> Atom:
        """The exception kind an except arm names, METTAFIED: the class's
        live object, or a grounded tuple of live objects for a tuple arm. The
        arm's spelling is validated at compile time and the runtime can use
        Python's identity-preserving isinstance lattice directly.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if isinstance(node, ast.Tuple):
            return Grounded(tuple(self._except_class_value(element) for element in node.elts))
        return Grounded(self._except_class_value(node))

    def _except_class_value(self, node: ast.expr) -> type:
        value: object = None
        if isinstance(node, ast.Name):
            value = self.host_value(node.id)
            if not isinstance(value, type):
                value = self._builtins.get(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            owner = self.host_value(node.value.id)
            value = getattr(owner, node.attr, None)
        if isinstance(value, type) and issubclass(value, BaseException):
            return value
        msg = (
            f"except {ast.unparse(node)} does not name an exception class "
            f"this function can see; catching classes that do not inherit "
            f"from BaseException is not allowed (Python's own rule)"
        )
        raise CompileError(msg, construct="except", line=node.lineno)

    def _try_finally(
        self,
        node: ast.Try,
        *,
        tag_params: list[str],
        tag: str,
        result: Variable,
        caught: Expression,
        dispatch: Atom,
        continue_to: Callable[[CompilerContext], Atom],
        fell: bool,
    ) -> Expression:
        """finally, in Python's own order: settle, run it, then exit.

        The dispatch settles into a done-tag under a second catch, the
        finally's effects run, and only then the exit reads the outcome:
        an escaped error re-throws AFTER the finally ran, a return value
        passes through, and a fall-through destructures the ok-tag and
        continues — with the finally's own definite bindings overriding
        the carried ones, since Python runs them later.
        """
        done = f"{self.name}--try-done-{next_aux_serial()}"
        value = Variable(self._temp("try-outcome"))
        wrapped = Expression(
            [
                Symbol("catch"),
                Expression([Symbol("let"), value, dispatch, Expression([Symbol(done), value])]),
            ]
        )
        settled = Variable(self._temp("try-settled"))
        unwrapped = Variable(self._temp("try-unwrapped"))
        escaped = Variable(self._temp("try-escaped"))
        returned = Variable(self._temp("try-returned"))

        def after_finally(compiler: CompilerContext) -> Atom:
            # Built AFTER the finally's bindings joined the compiler's
            # scope, so the continuation reads them as overrides. A body
            # whose every path closed can never settle into the ok tag,
            # so the outcome passes straight through then.
            if fell:
                exit_arm = compiler._fork()
                ok_pattern = Expression(
                    [Symbol(tag), *(Variable(exit_arm._bind(n)) for n in tag_params)]
                )
                inner_exit: Atom = Expression(
                    [
                        Symbol("case"),
                        unwrapped,
                        Expression(
                            [
                                Expression([ok_pattern, continue_to(exit_arm)]),
                                Expression([returned, returned]),
                            ]
                        ),
                    ]
                )
            else:
                inner_exit = unwrapped
            return Expression(
                [
                    Symbol("case"),
                    settled,
                    Expression(
                        [
                            Expression([Expression([Symbol(done), unwrapped]), inner_exit]),
                            Expression([escaped, Expression([Symbol("throw"), escaped])]),
                        ]
                    ),
                ]
            )

        self._refuse_stale_finally_reads(node)
        fin_compiler = self._fork()
        fin = fin_compiler._effect_block(node.finalbody, after_finally)
        return Expression(
            [
                Symbol("let*"),
                Expression(
                    [
                        Expression([result, caught]),
                        Expression([settled, wrapped]),
                    ]
                ),
                fin,
            ]
        )

    def _refuse_stale_finally_reads(self, node: ast.Try) -> None:
        """A finally reading a name the try rebinds would read the PRE-try
        binding here, since the arms' scopes have settled by the time it
        runs; that silent staleness refuses loudly instead. Reading a name
        the finally itself bound first stays lawful, and so does every
        name the try leaves alone.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        rebound: set[str] = set()
        for piece in (*node.body, *node.handlers, *node.orelse):
            for sub in ast.walk(piece):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    rebound.add(sub.id)
        fin_bound: set[str] = set()
        for statement in node.finalbody:
            # A statement's reads happen before its own bindings land, so
            # `x = x + 1` reads first: loads check before stores register.
            for sub in ast.walk(statement):
                if (
                    isinstance(sub, ast.Name)
                    and isinstance(sub.ctx, ast.Load)
                    and sub.id in rebound
                    and sub.id not in fin_bound
                ):
                    msg = (
                        f"finally reads {sub.id!r}, which the try rebinds; "
                        f"the settled binding is not visible here, so read "
                        f"it after the try, or bind what finally needs "
                        f"before the try"
                    )
                    raise CompileError(msg, construct="finally", line=sub.lineno)
            for sub in ast.walk(statement):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    fin_bound.add(sub.id)

    def _effect_block(
        self,
        statements: list[ast.stmt],
        continuation: Callable[[CompilerContext], Atom],
    ) -> Atom:
        """Statements run for their effect, sequenced before a continuation.

        The finally lane: expressions bind to a discard, bindings stay
        local until the continuation thunk reads them, and a raise
        replaces the in-flight outcome, which is Python's own (notorious)
        finally semantics. A `return` here would swallow the outcome
        silently and keeps a refusal.
        """
        statements = [s for s in statements if not _is_docstring(s)]
        if not statements:
            return continuation(self)
        head, rest = statements[0], statements[1:]
        if isinstance(head, ast.Return):
            msg = (
                "`return` inside finally would swallow the try's outcome "
                "silently; return after the try instead"
            )
            raise CompileError(msg, construct="finally", line=head.lineno)
        if isinstance(head, ast.Raise):
            return self._raise_statement(head, rest)
        if isinstance(head, ast.Expr):
            # The probe READS the effect's answer, keeping it live (a
            # binding nothing reads is eliminable) and producing a failure
            # instead of burying it, Python's own finally-error rule.
            effect = Variable(self._temp("effect"))
            return Expression(
                [
                    Symbol("let*"),
                    Expression([Expression([effect, self.expression(head.value)])]),
                    Expression(
                        [
                            Symbol("if-error"),
                            effect,
                            Expression([Symbol("throw"), effect]),
                            self._effect_block(rest, continuation),
                        ]
                    ),
                ]
            )
        if isinstance(head, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            pattern, bound = self._binding(head)
            return Expression(
                [
                    Symbol("let*"),
                    Expression([Expression([pattern, bound])]),
                    self._effect_block(rest, continuation),
                ]
            )
        msg = (
            f"{type(head).__name__} has no place in a compiled finally, "
            f"which sequences expressions, bindings and raise"
        )
        raise CompileError(msg, construct="finally", line=head.lineno)

    def _type_alias_statement(self, node: ast.TypeAlias, rest: list[ast.stmt]) -> Atom:
        """`type X = T` is a rewrite rule, exactly as it reads.

        The alias becomes equations on its own name, one per type
        alternative, stored with the definition's other auxiliary
        equations; a union alias is several clauses, MeTTa's own
        nondeterministic rewrite. Annotations after it mention the name
        symbolically and the engine rewrites it. A parametric alias would
        need type variables the local annotation resolver cannot carry,
        so it names the general door instead.
        """
        if node.type_params:
            msg = (
                "a parametric `type` alias has no local lowering; write its "
                "equations with equation() on the alias name instead"
            )
            raise CompileError(msg, construct="type alias", line=node.lineno)
        name = node.name.id
        alternatives = self.annotation_alternatives(node.value)
        for alternative in alternatives:
            self.aux.append(Expression([Symbol("="), Symbol(name), alternative]))
        self.type_aliases[name] = alternatives
        return self.block(rest)

    def _scope_pragma_statement(
        self, node: ast.Global | ast.Nonlocal, rest: list[ast.stmt]
    ) -> Atom:
        """`global` is a pragma: its names read and write the live module.

        Reads already island against the live binding; the declaration
        makes assignment island too, writing globals() at application
        time in binding order. `nonlocal` rebinds an enclosing function
        frame, which a stored equation outlives, so it keeps a refusal.
        """
        if isinstance(node, ast.Nonlocal):
            msg = (
                "`nonlocal` rebinds an enclosing function frame, which a "
                "stored equation outlives; lift the state into a State "
                "cell or a space"
            )
            raise CompileError(msg, construct="nonlocal", line=node.lineno)
        self.pragma_globals.update(node.names)
        return self.block(rest)

    def _global_write(
        self,
        name: str,
        value_node: ast.expr,
        head: ast.stmt,
        rest: list[ast.stmt],
        *,
        inplace_op: ast.operator | None = None,
    ) -> Expression:
        """One declared-global assignment: bind the compiled value, then
        island the write so globals() moves at application time.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self.function is None:
            msg = "a global write has no source function"
            raise CompileError(msg, construct="global", line=head.lineno)
        holder = f"_global_write_{next_aux_serial()}"
        bound = Variable(self._bind(holder))
        # The write crosses through the ops lane with the module dict
        # grounded BY REFERENCE at compile time: an island's globals() can
        # be a replica in the engine's callback context, while a grounded
        # reference reaches the live module wherever the op runs. The
        # error probe keeps the effect live and produces a host failure.
        self.runtime_ops.add("py-global-write")
        write = Expression(
            [
                Symbol("py-global-write"),
                Grounded(self.function.__globals__),
                Grounded(name),
                bound,
            ]
        )
        written = Variable(self._temp("global-written"))
        value = self.expression(value_node)
        if inplace_op is not None:
            current = self.expression(
                ast.copy_location(ast.Name(id=name, ctx=ast.Load()), value_node)
            )
            value = self._inplace_atom(
                inplace_op,
                current,
                value,
                getattr(head, "lineno", None),
            )
        return Expression(
            [
                Symbol("let*"),
                Expression(
                    [
                        Expression([bound, value]),
                        Expression([written, write]),
                    ]
                ),
                Expression(
                    [
                        Symbol("if-error"),
                        written,
                        Expression([Symbol("throw"), written]),
                        self.block(rest),
                    ]
                ),
            ]
        )

    def _delete_statement(self, node: ast.Delete, rest: list[ast.stmt]) -> Atom:
        """Sequence each pattern deletion before the block's continuation."""
        continuation = self.block(rest)
        for target in reversed(node.targets):
            result = Variable(self._temp("delete-result"))
            continuation = Expression(
                [
                    Symbol("let*"),
                    Expression([Expression([result, self._delete_target(target)])]),
                    Expression([Symbol("if-error"), result, result, continuation]),
                ]
            )
        return continuation

    def _delete_target(self, target: ast.expr) -> Expression:
        """Snapshot one subscript pattern, refuse empty, then remove every row."""
        if not isinstance(target, ast.Subscript) or isinstance(target.slice, ast.Slice):
            msg = "a compiled del target is space[pattern], with one nonslice pattern"
            raise CompileError(
                msg,
                construct="delete",
                line=getattr(target, "lineno", None),
            )
        if isinstance(target.value, ast.Name) and target.value.id in self.dict_locals:
            # del d[k] on a dict local is lib_dict's remove: exact on the
            # key's pair, and an absent key is an ordinary answer rather
            # than a failure, the library's own stated semantics.
            self.libraries.add("dict")
            return Expression(
                [
                    Symbol("dict-remove"),
                    Variable(self.scope[target.value.id]),
                    self.expression(target.slice),
                ]
            )

        space = Variable(self._temp("delete-space"))
        pattern = Variable(self._temp("delete-pattern"))
        matches = Variable(self._temp("delete-matches"))
        item = Variable(self._temp("delete-item"))
        removed = Variable(self._temp("delete-map"))
        removal = Expression([Symbol("remove-atom"), space, item])
        missing = Expression(
            [
                Symbol("Error"),
                Expression([Symbol("remove-atom"), space, pattern]),
                Grounded("remove-atom: atom is not in the space"),
            ]
        )
        remove_all = Expression(
            [
                Symbol("let*"),
                Expression(
                    [
                        Expression(
                            [
                                removed,
                                Expression([Symbol("map-atom"), matches, item, removal]),
                            ]
                        )
                    ]
                ),
                Expression([]),
            ]
        )
        return Expression(
            [
                Symbol("let*"),
                Expression(
                    [
                        Expression([space, self.expression(target.value)]),
                        Expression([pattern, self.expression(target.slice)]),
                        Expression(
                            [
                                matches,
                                Expression(
                                    [
                                        Symbol("collapse"),
                                        Expression([Symbol("match"), space, pattern, pattern]),
                                    ]
                                ),
                            ]
                        ),
                    ]
                ),
                Expression(
                    [
                        Symbol("if"),
                        Expression([Symbol("=="), matches, Expression([])]),
                        missing,
                        remove_all,
                    ]
                ),
            ]
        )

    def _builder_rooted(self, node: ast.AST) -> bool:
        """Whether this subtree BUILDS a term: an S-rooted call, whose
        interior is quoted data and therefore the walrus boundary above.

        Only S: a V-rooted call is a runtime higher-order APPLICATION
        (`V.f(x)` applies whatever `$f` holds), and fn-rooted calls are
        engine calls, so both evaluate their arguments and a walrus there
        hoists lawfully.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not isinstance(node, ast.Call):
            return False
        root = node.func
        while isinstance(root, (ast.Attribute, ast.Subscript)):
            root = root.value
        return (
            isinstance(root, ast.Name)
            and root.id == "S"
            and root.id in self.builders
            and root.id not in self.scope
        )

    def _walrus_block(
        self,
        walruses: list[ast.NamedExpr],
        head: ast.stmt,
        rest: list[ast.stmt],
    ) -> Expression:
        """Hoist `name := value` bindings ahead of their statement.

        Python's own let expression: PEP 572 binds to the enclosing
        function scope, which is exactly a let* chain around the
        statement's continuation, so `(y := f(x)) + y` compiles as the
        binding then the sum, and the name stays visible to the rest of
        the block. Each walrus node is REPLACED IN PLACE by a plain name
        load before the statement compiles.
        """
        pairs = []
        for walrus in walruses:
            target = walrus.target.id
            value = self.expression(walrus.value)
            spacey = _space_valued(value) or (
                isinstance(walrus.value, ast.Name) and walrus.value.id in self.space_locals
            )
            if spacey:
                self.space_locals.add(target)
            else:
                self.space_locals.discard(target)
            dictish = self._dict_atom(value) or (
                isinstance(walrus.value, ast.Name) and walrus.value.id in self.dict_locals
            )
            if dictish:
                self.dict_locals.add(target)
            else:
                self.dict_locals.discard(target)
            kind = self._container_kind(walrus.value)
            if kind is None:
                self.container_locals.pop(target, None)
            else:
                self.container_locals[target] = kind
            variable = Variable(self._bind(target))
            pairs.append(Expression([variable, value]))
            _replace_walrus(head, walrus, target)
        continuation = self.block([head, *rest])
        if self.in_try_body:
            for pair in reversed(pairs):
                bound = pair.children[0]
                continuation = Expression(
                    [
                        Symbol("if-error"),
                        bound,
                        Expression([Symbol("throw"), bound]),
                        continuation,
                    ]
                )
        return Expression([Symbol("let*"), Expression(pairs), continuation])

    def _bound_block(
        self,
        head: ast.Assign | ast.AnnAssign | ast.AugAssign,
        rest: list[ast.stmt],
    ) -> Expression:
        pragma_target = self._pragma_write_target(head)
        if pragma_target is not None:
            name, value_node, inplace_op = pragma_target
            return self._global_write(
                name,
                value_node,
                head,
                rest,
                inplace_op=inplace_op,
            )
        dict_write = self._dict_write(head, rest)
        if dict_write is not None:
            return dict_write
        if (
            isinstance(head, ast.AugAssign)
            and isinstance(head.target, ast.Name)
            and head.target.id in self.space_locals
            and head.target.id not in self.container_locals
            and isinstance(head.op, ast.Sub)
        ):
            removal = self._space_augmented_removal(head, self.block(rest))
            if removal is None:
                msg = "a guarded space-local augmented removal lowered to nothing"
                raise AssertionError(msg)
            return removal
        pattern, value = self._binding(head)
        continuation = self.block(rest)
        if self.in_try_body:
            # Inside a try body, a binding whose right side answered error
            # data produces it, so the arms see what Python's raise would
            # have thrown instead of the tag carrying the error out.
            if isinstance(pattern, Variable):
                rows = Expression([Expression([pattern, value])])
                probe: Atom = pattern
            else:
                held = Variable(self._temp("try-bound"))
                rows = Expression([Expression([held, value]), Expression([pattern, held])])
                probe = held
            trapped = Expression(
                [
                    Symbol("if-error"),
                    probe,
                    Expression([Symbol("throw"), probe]),
                    continuation,
                ]
            )
            return Expression([Symbol("let*"), rows, trapped])
        return Expression(
            [Symbol("let*"), Expression([Expression([pattern, value])]), continuation]
        )

    def _dict_write(
        self,
        head: ast.Assign | ast.AnnAssign | ast.AugAssign,
        rest: list[ast.stmt],
    ) -> Expression | None:
        """``d[k] = v`` on a dict local is lib_dict's put: replace-or-insert.

        The augmented form desugars through get-value, so ``d[k] += 1``
        reads the pair and puts the sum; an absent key answers nothing and
        the emptiness propagates, the library's own absence semantics.
        """
        value_node: ast.expr | None
        if isinstance(head, ast.Assign):
            if len(head.targets) != 1:
                return None
            target: ast.expr = head.targets[0]
            value_node = head.value
        else:
            target = head.target
            value_node = head.value
        if value_node is None:
            return None
        if not (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id in self.dict_locals
            and not isinstance(target.slice, ast.Slice)
        ):
            return None
        holder = Variable(self.scope[target.value.id])
        key = self.expression(target.slice)
        if isinstance(head, ast.AugAssign):
            self.libraries.add("dict")
            read = Expression([Symbol("get-value"), holder, key])
            value = self._inplace_atom(head.op, read, self.expression(value_node), head.lineno)
        else:
            value = self.expression(value_node)
        self.libraries.add("dict")
        discard = Variable(self._bind("_"))
        write = Expression([Symbol("dict-put"), holder, key, value])
        return Expression(
            [
                Symbol("let*"),
                Expression([Expression([discard, write])]),
                self.block(rest),
            ]
        )

    def _pragma_write_target(
        self, head: ast.Assign | ast.AnnAssign | ast.AugAssign
    ) -> tuple[str, ast.expr, ast.operator | None] | None:
        """A declared-global assignment's name and value expression.

        An augmented assignment desugars to a read-then-write of the live
        global, whose read islands like any other global read, so
        `count += 1` under `global count` moves the module's own binding.
        """
        value: ast.expr | None
        if isinstance(head, ast.Assign):
            if len(head.targets) != 1 or not isinstance(head.targets[0], ast.Name):
                return None
            target = head.targets[0].id
            value = head.value
        elif isinstance(head.target, ast.Name):
            target = head.target.id
            value = head.value
        else:
            return None
        if target not in self.pragma_globals or value is None:
            return None
        inplace_op = head.op if isinstance(head, ast.AugAssign) else None
        return target, value, inplace_op

    def _space_augmented_removal(
        self, head: ast.AugAssign, continuation: Atom
    ) -> Expression | None:
        """Subtract one occurrence from a known space, propagating a bad-space Error.

        `-=` is Python's in-place DIFFERENCE over a MULTISET, and Python's own
        multiset is collections.Counter, whose `-=` subtracts the multiplicity
        given rather than clearing the key. It compiles to `subtract-atom`,
        the engine head with exactly that grain, so the operator means the
        same thing inside a compiled body as it does on the Python surface;
        the drain is `del space[pattern]` and `remove-atom`, and
        `space.remove(atom)` is the grain that also reports what it found.

        The if-error still stands because a bad first argument is still an
        error: `subtract-atom` refuses a non-space, and refuses an unbound
        atom rather than reading it as every atom at once.
        """
        if not (
            isinstance(head.target, ast.Name)
            and head.target.id in self.space_locals
            and head.target.id not in self.container_locals
            and isinstance(head.op, ast.Sub)
        ):
            return None
        result = Variable(self._temp("remove-result"))
        removal = Expression(
            [
                Symbol("subtract-atom"),
                Variable(self.scope[head.target.id]),
                self.expression(head.value),
            ]
        )
        return Expression(
            [
                Symbol("let*"),
                Expression([Expression([result, removal])]),
                Expression([Symbol("if-error"), result, result, continuation]),
            ]
        )

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
        binding = self._state_binding_target(head)
        if binding is not None:
            state_cell, state_target = binding
            if isinstance(head, ast.AugAssign):
                current_node = ast.copy_location(
                    ast.Attribute(
                        value=state_target.value,
                        attr=state_target.attr,
                        ctx=ast.Load(),
                    ),
                    state_target,
                )
                state_value = self._inplace_atom(
                    head.op,
                    self.expression(current_node),
                    self.expression(head.value),
                    head.lineno,
                )
            else:
                value_node = head.value
                if value_node is None:
                    msg = "an annotation without a value writes no State cell"
                    raise CompileError(
                        msg,
                        construct="annotation",
                        line=head.lineno,
                    )
                state_value = self.expression(value_node)
            discard = Variable(self._bind("_"))
            return discard, Expression([Symbol("change-state!"), state_cell, state_value])

        value: Atom
        native_augassign = False
        if isinstance(head, ast.AugAssign):
            target_name = _name_of(head.target, head.lineno)
            if target_name not in self.scope:
                held = self.host_value(target_name)
                if isinstance(held, Handle):
                    msg = (
                        f"{target_name!r} is a space held outside this body, "
                        f"and += cannot rebind a closure (Python's own rule); "
                        f"write the door itself, "
                        f"fn.add_atom({target_name}, <atom>), or take the "
                        f"space as a parameter"
                    )
                else:
                    msg = f"{target_name!r} is augmented before it is bound"
                raise CompileError(
                    msg,
                    construct="augmented assignment",
                    line=head.lineno,
                )
            if target_name in self.space_locals and target_name not in self.container_locals:
                # On a space, += and -= ARE the write doors, never
                # arithmetic: the miscompile stored (+ $s atom), answered
                # True, and wrote nothing. The write executes under a
                # throwaway binding and the space name keeps its variable.
                # The same pair the statement path emits, so a write
                # inside a bound block means what it means outside one:
                # -= subtracts ONE occurrence, and the drain is del.
                doors = {ast.Add: "add-atom", ast.Sub: "subtract-atom"}
                door = doors.get(type(head.op))
                if door is None:
                    op_word = type(head.op).__name__
                    msg = (
                        f"{target_name!r} holds a space, which takes += "
                        f"(add-atom) and -= (subtract-atom); {op_word} has no "
                        f"space meaning"
                    )
                    raise CompileError(
                        msg,
                        construct="augmented assignment",
                        line=head.lineno,
                    )
                value = Expression(
                    [
                        Symbol(door),
                        Variable(self.scope[target_name]),
                        self.expression(head.value),
                    ]
                )
                target = "_"
            else:
                left_kind = self.container_locals.get(target_name)
                right_kind = self._container_kind(head.value)
                native_augassign = (
                    target_name in self.number_locals
                    and self._native_number(head.value)
                    and type(head.op) in _NATIVE_BINOPS
                )
                if native_augassign:
                    value = self._binop_atom(
                        head.op,
                        Variable(self.scope[target_name]),
                        self.expression(head.value),
                        head.lineno,
                        native=True,
                    )
                else:
                    value = self._inplace_atom(
                        head.op,
                        self._operator_operand(Variable(self.scope[target_name]), left_kind),
                        self._operator_operand(self.expression(head.value), right_kind),
                        head.lineno,
                        left_kind=left_kind,
                        right_kind=right_kind,
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
        if not isinstance(head, ast.AugAssign):
            source_node = head.value
            assert source_node is not None
            spacey = _space_valued(value) or (
                isinstance(source_node, ast.Name) and source_node.id in self.space_locals
            )
            if spacey:
                self.space_locals.add(target)
            else:
                self.space_locals.discard(target)
            dictish = self._dict_atom(value) or (
                isinstance(source_node, ast.Name) and source_node.id in self.dict_locals
            )
            if dictish:
                self.dict_locals.add(target)
            else:
                self.dict_locals.discard(target)
            kind = self._container_kind(source_node)
            if kind is None:
                self.container_locals.pop(target, None)
            else:
                self.container_locals[target] = kind
            annotated_number = isinstance(head, ast.AnnAssign) and self.annotation_is_native_number(
                head.annotation
            )
            if annotated_number or self._native_number(source_node):
                self.number_locals.add(target)
            else:
                self.number_locals.discard(target)
        elif target != "_":
            if native_augassign:
                self.number_locals.add(target)
            else:
                self.number_locals.discard(target)
        variable: Atom = Variable(self._bind(target))
        if isinstance(head, ast.AnnAssign):
            claim = Expression([Symbol(":"), variable, self.annotation_atom(head.annotation)])
            variable = Expression([Symbol("__metta_typed_binding__"), claim])
        return variable, value

    def _state_binding_target(
        self,
        head: ast.Assign | ast.AnnAssign | ast.AugAssign,
    ) -> tuple[Atom, ast.Attribute] | None:
        """The live State cell targeted by one property assignment, and the
        attribute node that named it.

        The node comes back with the cell because only this walk knows the
        target was `cell.value`: _state_cell answers None for every other
        shape, so handing the Attribute over carries that fact to the caller
        instead of leaving it to restate the narrowing.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if isinstance(head, ast.Assign):
            if len(head.targets) != 1:
                return None
            target = head.targets[0]
        else:
            target = head.target
        cell = self._state_cell(target)
        if cell is None or not isinstance(target, ast.Attribute):
            return None
        return cell, target

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

        if isinstance(head, ast.Assert):
            continuation = _superpose(self.yield_answers(rest))
            return [self._assertion(head, continuation)]

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

        if isinstance(head, ast.Raise):
            # Answers yielded before the raise stay delivered and the raise
            # branch answers its produced error, Python's own generator
            # order.
            return [self._raise_statement(head, rest)]

        if isinstance(head, ast.Try):
            msg = (
                "try around a yield interleaves answers with catching, "
                "which a compiled superposition does not stage; move the "
                "try into a helper the yield calls"
            )
            raise CompileError(msg, construct="try", line=head.lineno)

        msg = (
            f"{type(head).__name__} has no place in a compiled generator, "
            f"which covers yield, assignment, if/else and raise"
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
        if (
            isinstance(head, ast.AugAssign)
            and isinstance(head.target, ast.Name)
            and head.target.id in self.space_locals
            and isinstance(head.op, ast.Sub)
        ):
            removal = self._space_augmented_removal(head, _superpose(self.yield_answers(rest)))
            if removal is None:
                msg = "a guarded space-local augmented removal lowered to nothing"
                raise AssertionError(msg)
            return [removal]
        pattern, value = self._binding(head)
        tail = _superpose(self.yield_answers(rest))
        return [Expression([Symbol("let*"), Expression([Expression([pattern, value])]), tail])]

    def _yield_if(self, head: ast.If, rest: list[ast.stmt]) -> list[Atom]:
        # A raising branch CLOSES the generator, so the statements after
        # the if belong only to the branches that fall through, which is
        # Python's own order: yields before a raise stay delivered and
        # nothing after it runs.
        then_closes = bool(head.body) and isinstance(head.body[-1], ast.Raise)
        else_closes = bool(head.orelse) and isinstance(head.orelse[-1], ast.Raise)
        if not then_closes and not else_closes:
            then = _superpose(self._fork().yield_answers(head.body))
            otherwise = (
                _superpose(self._fork().yield_answers(head.orelse))
                if head.orelse
                else Expression([Symbol("empty")])
            )
            chooser = Expression([Symbol("if"), self._truthy(head.test), then, otherwise])
            return [chooser, *self._yield_tail(rest)]
        if then_closes and else_closes and rest:
            msg = "statements after an if whose branches both raise are unreachable"
            raise CompileError(msg, construct="if", line=rest[0].lineno)
        then_band = head.body if then_closes else [*head.body, *rest]
        else_band = (
            [*head.orelse, *rest] if then_closes and not else_closes else head.orelse or rest
        )
        then = _superpose(self._fork().yield_answers(then_band))
        otherwise = (
            _superpose(self._fork().yield_answers(else_band))
            if else_band
            else Expression([Symbol("empty")])
        )
        return [Expression([Symbol("if"), self._truthy(head.test), then, otherwise])]

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
        # Structural position: the host-island fallback is off while a case
        # pattern compiles, exactly as in match-call patterns.
        prior = self.compiler._in_pattern
        self.compiler._in_pattern = True
        try:
            return self._case_pattern(node)
        finally:
            self.compiler._in_pattern = prior

    def _case_pattern(self, node: ast.pattern) -> Atom:
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
