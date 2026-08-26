"""Purpose: lower Python for and while statements into tail-recursive equations.
Guarantees:
  - nested loops carry every outer state value they read [tested
    test_nested_loops_carry_the_outer_state]
  - compiled loops execute without growing the Python or Prolog stack
    [tested test_loops_run_in_constant_stack]
  - mechanically mapped generator calls remain nondeterministic loop sources
    [tested: test_mapped_nondeterministic_calls_keep_their_call_role;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - host islands in repeated tests and bodies retain loop context for lint,
    while a top-level iterable and the post-loop continuation do not [tested:
    test_py_host_island_inside_loops_emits_exact_findings; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast

from ._define_context import CompilerContext, next_aux_serial
from ._define_expression import _name_of
from .atoms import Atom, Expression, Symbol, Variable
from .errors import CompileError


def _recursion_closer(helper: str, state: list[str]):
    """What a loop body's fall-through means: one more round, with each
    state name's CURRENT variable at that point in the body.

    Every argument is resolved through the scope, the loop's own remaining
    sequence included. Holding that one as a fixed variable instead read the
    outer loop's tail in the inner loop's equation, where the name belongs to
    the inner loop, so a nested for resumed the outer loop on its own tail.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def recur(compiler: CompilerContext) -> Expression:
        return Expression([Symbol(helper), *(Variable(compiler.scope[n]) for n in state)])

    return recur


class LoopCompilerMixin(CompilerContext):
    def _free_reads(self, nodes: list) -> list[str]:
        """Scope names the nodes read, first-appearance order: the loop
        state, since a name never read again need not be carried. An
        augmented assignment's target is a read too: x *= 2 reads x.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
        will read, which the syntax of `nodes` cannot show.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        state = self._free_reads(nodes)
        for name in self.closer_names:
            if name in self.scope and name not in state:
                state.append(name)
        return state

    def _while_statement(self, node: ast.While, rest: list[ast.stmt]) -> Atom:
        """The loop as its own tail-recursive equation: parameters are the
        loop state, the test chooses between one more round and the exit,
        and the statements after the loop ARE the exit branch. With no break
        in the subset, a while-else always runs, so it prefixes the rest.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        rest = node.orelse.copy() + rest
        state = self._loop_state([node.test, *node.body, *rest])
        helper = f"{self.name}--loop-{next_aux_serial()}"

        equation_compiler = self._equation_compiler(state)
        equation_compiler.closer_names = state.copy()
        recur = _recursion_closer(helper, state)
        body_compiler = equation_compiler._fork()
        body_compiler.loop_depth += 1
        body_compiler.closer = recur
        exit_compiler = equation_compiler._fork()
        # The exit continues whatever the enclosing block was continuing.
        exit_compiler.closer = self.closer

        test_compiler = equation_compiler._fork()
        test_compiler.loop_depth += 1
        test = test_compiler._truthy(node.test)
        body = body_compiler.block(node.body)
        exit_branch = exit_compiler.block(rest)
        head = Expression([Symbol(helper), *(Variable(n) for n in state)])
        self.aux.append(
            Expression([Symbol("="), head, Expression([Symbol("if"), test, body, exit_branch])])
        )
        return Expression([Symbol(helper), *(Variable(self.scope[n]) for n in state)])

    def _for_statement(self, node: ast.For, rest: list[ast.stmt]) -> Atom:
        """For x in e: the same equation over the remaining elements,
        decons-atom peeling one per round. A nondeterministic source
        collapses first, which is Python's own single pass over it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        target = _name_of(node.target, node.lineno)
        rest = node.orelse.copy() + rest
        if target in self._free_reads(rest) or target in self.closer_names:
            msg = (
                f"{target!r} is read after the loop, where Python would hold "
                f"the last element; bind that value to its own name inside "
                f"the loop instead"
            )
            raise CompileError(
                msg,
                construct="for",
                line=node.lineno,
            )
        state = [n for n in self._loop_state([*node.body, *rest]) if n != target]
        helper = f"{self.name}--each-{next_aux_serial()}"
        sequence = "loop-rest"

        equation_compiler = self._equation_compiler([sequence, *state])
        equation_compiler.closer_names = state.copy()
        body_compiler = equation_compiler._fork()
        body_compiler.loop_depth += 1
        variable = body_compiler._bind(target)
        tail = body_compiler._temp("tail")
        # The remaining sequence is loop state like any other: a construct
        # nested in the body compiles into its own equation, and the
        # continuation it captures resumes THIS loop on THIS tail, so the
        # tail has to travel there as a parameter. It enters scope under its
        # own variable name, which no Python identifier can spell.
        body_compiler.scope[tail] = tail
        body_compiler.closer_names = [tail, *state]
        body_compiler.closer = _recursion_closer(helper, [tail, *state])
        exit_compiler = equation_compiler._fork()
        exit_compiler.closer = self.closer

        body = Expression(
            [
                Symbol("let"),
                Expression([Variable(variable), Variable(tail)]),
                Expression([Symbol("decons-atom"), Variable(sequence)]),
                body_compiler.block(node.body),
            ]
        )
        exit_branch = exit_compiler.block(rest)
        head = Expression([Symbol(helper), Variable(sequence), *(Variable(n) for n in state)])
        test = Expression([Symbol("=="), Variable(sequence), Expression([])])
        self.aux.append(
            Expression([Symbol("="), head, Expression([Symbol("if"), test, exit_branch, body])])
        )
        source = self._materialized(node.iter)
        return Expression([Symbol(helper), source, *(Variable(self.scope[n]) for n in state)])

    def _materialized(self, iter_node: ast.expr) -> Atom:
        """An iterable as one expression value: a nondeterministic call's
        answers collapse into a tuple, anything else already is its value.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if (
            isinstance(iter_node, ast.Call)
            and isinstance(iter_node.func, ast.Name)
            and self.nondet(self._resolved_call_name(iter_node.func.id))
        ):
            return Expression([Symbol("collapse"), self.expression(iter_node)])
        return self.expression(iter_node)
