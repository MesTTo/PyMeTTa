"""Purpose: rebuild native callable values with their lexical space.

Guarantees:
  - application evaluates the carried native value, including subsequent source
    rewrites [tested: test_native_callable_values_keep_their_lexical_program;
    commit=8e2b7e3024713881f716e3d3a6a995bdf7231397]
  - segment applications execute the constructed call and preserve captured
    arguments [tested: test_evaluated_native_lambdas_apply_their_assembled_arguments;
    commit=8e2b7e3024713881f716e3d3a6a995bdf7231397]
  - adding the current lexical home retains the source lambda's contract
    [tested: test_native_callable_contracts_survive_lexical_wrapping;
    commit=WORKTREE]
Owns resources:
  - the callable image contains its lexical home and captured receiver, so
    scope retention follows the ordinary native value graph [tested:
    test_a_kept_native_callable_retains_its_scoped_program; commit=8e2b7e3024713881f716e3d3a6a995bdf7231397]
"""

from __future__ import annotations

import inspect
import typing
from typing import Any

from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Handle,
    S,
    Symbol,
    Variable,
    _atom_from_wire,
    _encode,
    _expr,
    fresh,
)
from metta._catalog import call_signatures
from metta._catalog.containers import runtime_annotation
from metta._lazy import lazy


def argument(value: Any) -> Atom:
    """Borrow Python container arguments; their grain belongs to their storage."""
    return Grounded(value) if runtime_annotation(value) is not None else _encode(value)


def lexical_space(atom: Atom) -> Any:
    """Open a carried native identity without declaring a missing home."""
    if not isinstance(atom, (Symbol, Handle, Expression)):
        msg = "call binding requires a lexical space"
        raise TypeError(msg)
    if isinstance(atom, Expression) and not lazy('metta._binding.runtime').runtime().once(
        "metta_py_decode_shared(Wire,_Home,_),ground(_Home),metta_space_operand(_Home)",
        Wire=atom.to_wire(),
    ):
        msg = f"the callable's lexical home is not a registered space: {atom}"
        raise TypeError(msg)
    return lazy('metta._faces.space').Space(atom.name if isinstance(atom, Symbol) else atom)


def evaluate(space: Any, expression: Atom, annotation: Any, *, stream: bool) -> Any:
    """Project the native answer contract through the existing result doors."""
    if stream:
        return space.eval(expression, answer="stream", on_error="abort").into(annotation, space=space)
    from metta._catalog.build import build  # noqa: PLC0415 -- build constructs callable values

    with space.answers(expression) as answers:
        return build(answers.one(), annotation, space=space)


class NativeCallable:
    """A Python application of a native callable value, with no host body."""

    def __init__(self, atom: Atom, space: Any, annotation: Any):
        self.atom, self.space = atom, space
        result = typing.get_args(annotation)
        self.result_type = result[-1] if result else Any

    def __metta__(self) -> Atom:
        return self.atom

    @property
    def __signature__(self) -> inspect.Signature:
        return self.contract()[0]

    def contract(self) -> tuple[inspect.Signature, bool]:
        # Read stored program data through the occurrence relation. A written
        # match pattern would interpret the lambda's :seg binder as a query
        # gap, although this consumer is looking up a callable value. A
        # lambda carried with its current home has the same contract as its
        # written body in that home; both keys remain native program data.
        rows = self.space._rt.must(
            "metta_py_decode_shared(Wire,_Scoped,_),"
            "findall([_Wire,_Cardinality,_Captured],("
            "(_Scoped=['|->',_Parameters,[evalc,_Body,_Home]],_Home==Space -> "
            "member(_Value,[_Scoped,['|->',_Parameters,_Body]]) ; _Value=_Scoped),"
            "(spaces:metta_space_pair(Space,['@python-callable',_Value,_Signature,_Cardinality],_,_),_Captured=0;"
            "spaces:metta_space_pair(Space,['@python-binding',_Value,_Canonical,_Captured],_,_),"
            "spaces:metta_space_pair(Space,['@python-callable',_Canonical,_Signature,_Cardinality],_,_)),"
            "metta_py_encode(_Signature,_Wire)),Contracts)",
            Space=self.space.name, Wire=self.atom.to_wire(),
        )
        found = [(_atom_from_wire(wire), cardinality, captured) for wire, cardinality, captured in rows["Contracts"]]
        if found:
            if len(found) != 1 or found[0][1] not in ("one", "stream"):
                msg = "a native callable needs one Python signature and answer-cardinality declaration"
                raise TypeError(msg)
            signature, cardinality, captured = call_signatures.build(found[0][0]), found[0][1], found[0][2]
            complete = tuple(signature.parameters.values())
            if not isinstance(captured, int) or not 0 <= captured <= len(complete):
                msg = "a native callable binding must name the number of captured parameters"
                raise TypeError(msg)
            return signature.replace(parameters=complete[captured:]), cardinality == "stream"
        if isinstance(self.atom, Symbol):
            return self.space.fn[self.atom.name].__signature__, False
        parameters = []
        for parameter in self.atom.args[0].children:
            if isinstance(parameter, Variable):
                parameters.append(inspect.Parameter(parameter.name, inspect.Parameter.POSITIONAL_OR_KEYWORD))
            elif isinstance(parameter, Expression) and parameter.head == S[":seg"] and len(parameter.args) == 1 and isinstance(parameter.args[0], Variable):
                parameters.append(inspect.Parameter(parameter.args[0].name.replace("-", "_"), inspect.Parameter.VAR_POSITIONAL))
            else:
                msg = "a patterned native lambda has no Python keyword parameter names; apply its atom in a space"
                raise TypeError(msg)
        return inspect.Signature(parameters, return_annotation=self.result_type), False

    def application(self, args: Any, kwargs: Any) -> tuple[Atom, inspect.Signature, bool]:
        """Bind call syntax without evaluating the resulting native term."""
        signature, stream = self.contract()
        bound = signature.bind(*args, **kwargs)
        # The existing native Kwargs packet belongs to call syntax. A bound
        # method's segment lambda passes it to the same signature binder as a
        # directly written method call. A plain lambda has fixed parameters.
        segmented = isinstance(self.atom, Expression) and any(
            isinstance(parameter, Expression) and parameter.head == S[":seg"]
            for parameter in self.atom.args[0].children
        )
        if segmented:
            values = [argument(value) for value in args]
            if kwargs:
                values.append(_expr(S.Kwargs, *(Expression([Symbol(name), argument(value)]) for name, value in kwargs.items())))
        else:
            bound.apply_defaults()
            # A fixed binder holds one parameter value. BoundArguments.args
            # flattens *args and excludes keyword-only and **kwargs values.
            values = [argument(value) for value in bound.arguments.values()]
        return _expr(self.atom, *values), signature, stream

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        expression, signature, stream = self.application(args, kwargs)
        result_type = self.result_type
        if result_type is Any and signature.return_annotation is not inspect.Signature.empty:
            result_type = signature.return_annotation
        if stream:
            parts = typing.get_args(result_type)
            result_type = parts[0] if parts else Any
        return evaluate(self.space, expression, result_type, stream=stream)


def _written_callable(space: Any, source: Symbol, captured: tuple[Atom, ...]) -> Atom | None:
    """Recover an evaluated lambda through its exact native source clause."""
    row = space._rt.must(
        "metta_py_decode_shared(Captures,_Captured,_),space_module(Space,_Module),"
        "findall(_Wire,(current_predicate(_Module:Name/_Arity),"
        "functor(_Head,Name,_Arity),predicate_property(_Module:_Head,interpreted),"
        "clause(_Module:_Head,_,_Ref),"
        "translated_from(_Ref,[=,[Name|_Parameters],_Body]),"
        "append(_Captured,_Remaining,_Parameters),_Written=['|->',_Remaining,_Body],"
        "(nonvar(_Body),_Body=[evalc,_,_Home] -> true ; _Home=Space),"
        "(spaces:metta_space_pair(_Home,['@python-callable',_Written,_,_],_,_);"
        "spaces:metta_space_pair(_Home,['@python-binding',_Written,_,_],_,_)),"
        "metta_py_encode(_Written,_Wire)),Written)",
        Space=space.name, Name=source.name, Captures=Expression(captured).to_wire(),
    )
    written = row["Written"]
    if len(written) > 1:
        msg = "a native callable has more than one matching source contract"
        raise TypeError(msg)
    return _atom_from_wire(written[0]) if written else None


def rebuild(atom: Atom, annotation: Any, space: Any) -> NativeCallable | None:
    """Read the lexical evaluator already carried by a lambda value."""
    if isinstance(atom, Expression) and atom.head == S.noeval and len(atom.args) == 1:
        atom = atom.args[0]
    source = atom
    captured: tuple[Atom, ...] = ()
    if isinstance(atom, Expression) and atom.head == S.partial and len(atom.args) == 2 and isinstance(atom.args[0], Symbol) and isinstance(atom.args[1], Expression):
        source, captured = atom.args[0], atom.args[1].children
    if isinstance(source, Symbol) and space is not None:
        if not space._rt.once(
            "metta_py_catalogue_member(Space,Name);metta_py_function_visible(Space,Name)",
            Space=space.name, Name=source.name,
        ):
            return None
        written = _written_callable(space, source, captured)
        if written is not None:
            return rebuild(written, annotation, space)
        signature = space.fn[source.name].__signature__
        parameters = tuple(signature.parameters.values())
        fixed = [parameter for parameter in parameters if parameter.kind is not inspect.Parameter.VAR_POSITIONAL]
        rest = next((parameter for parameter in parameters if parameter.kind is inspect.Parameter.VAR_POSITIONAL), None)
        variables = [Variable(parameter.name) for parameter in fixed[len(captured):]]
        operands = [*captured, *variables]
        if rest is None:
            body = _expr(source, *operands)
            binders = Expression(variables)
        else:
            tail: Atom = Variable(rest.name)
            binders = Expression([*variables, _expr(S[":seg"], tail)])
            for value in reversed(operands):
                tail = _expr(S["cons-atom"], _expr(S.noeval, value), tail)
            application = fresh()
            body = _expr(S.chain, _expr(S["cons-atom"], _expr(S.noeval, source), tail),
                         application, _expr(S.eval, application))
        atom = _expr(S["|->"], binders, _expr(S.evalc, body, space))
    if isinstance(atom, Expression) and atom.head == S["|->"] and len(atom.args) == 2:
        lambda_binders, lambda_body = atom.args
        if not isinstance(lambda_binders, Expression):
            return None
        if isinstance(lambda_body, Expression) and lambda_body.head == S.evalc and len(lambda_body.args) == 2:
            home = lambda_body.args[1]
            space = lexical_space(home)
        elif space is not None:
            atom = _expr(S["|->"], lambda_binders, _expr(S.evalc, lambda_body, space))
        else:
            return None
        return NativeCallable(atom, space, annotation)
    return None
