"""Purpose: rebuild native callable values with their lexical space.

Guarantees:
  - native references select their current call port and preserve captures
    and explicit contracts [tested:
    test_expanded_partial_references_preserve_capture_and_parameter_names;
    test_forwarding_contracts_preserve_explicit_cardinality_and_bound_captures;
    test_native_references_observe_later_arity_changes; commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - application evaluates the carried native value, including subsequent source
    rewrites [tested: test_native_callable_values_keep_their_lexical_program;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - segment applications execute the constructed call and preserve captured
    arguments [tested: test_evaluated_native_lambdas_apply_their_assembled_arguments;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - adding the current lexical home retains the source lambda's contract
    [tested: test_native_callable_contracts_survive_lexical_wrapping;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - contract lookup preserves distinct binders and references to authored
    heads [tested: test_contract_lookup_preserves_distinct_lambda_binders;
    test_callable_conversion_keeps_authored_heads_as_live_references;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
Owns resources:
  - the callable image contains its lexical home and captured receiver, so
    scope retention follows the ordinary native value graph [tested:
    test_a_kept_native_callable_retains_its_scoped_program; commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
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
    _variables,
    fresh,
)
from metta._catalog import call_signatures
from metta._catalog.containers import runtime_annotation
from metta._lazy import lazy


def argument(value: Any) -> Atom:
    """Borrow Python container arguments; their grain belongs to their storage."""
    return Grounded(value) if runtime_annotation(value) is not None else _encode(value)


def is_parametric_space(atom: Expression) -> bool:
    """Ask the native operand relation without declaring an expression name."""
    return bool(lazy('metta._binding.runtime').runtime().once(
        "metta_py_decode_shared(Wire,_Home,_),ground(_Home),metta_space_operand(_Home)",
        Wire=atom.to_wire(),
    ))


def lexical_space(atom: Atom) -> Any:
    """Open a carried native identity without declaring a missing home."""
    if not isinstance(atom, (Symbol, Handle, Expression)):
        msg = "call binding requires a lexical space"
        raise TypeError(msg)
    if isinstance(atom, Expression) and not is_parametric_space(atom):
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
        _, signature, stream = self._layout()
        return signature, stream

    def _declared_contract(self) -> tuple[inspect.Signature, bool] | None:
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
            "(_Contracts=Space ; Space\\=='&metta',_Contracts='&metta'),"
            "(spaces:metta_space_pair(_Contracts,['@python-callable',_Pattern,_Signature,_Cardinality],_,_),"
            "subsumes_term(_Pattern,_Value),_Pattern=_Value,_Captured=0;"
            "spaces:metta_space_pair(_Contracts,['@python-binding',_Pattern,_Canonical,_Captured],_,_),"
            "subsumes_term(_Pattern,_Value),_Pattern=_Value,"
            "spaces:metta_space_pair(_Contracts,['@python-callable',_Canonical,_Signature,_Cardinality],_,_)),"
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
        return None

    def _layout(self, arity: int | None = None) -> tuple[Atom, inspect.Signature, bool]:
        if (declared := self._declared_contract()) is not None:
            return self.atom, *declared
        if arity is not None and (reference := _forwarded(self.atom, arity)) is not None:
            source, captures = reference
            canonical = _application_image(source, (), arity + len(captures), self.space)
            if (declared := NativeCallable(canonical, self.space, Any)._declared_contract()) is not None:
                signature, stream = declared
                remaining = tuple(signature.parameters.values())[len(captures):]
                return _application_image(source, captures, arity, self.space), signature.replace(parameters=remaining), stream
        if isinstance(self.atom, Symbol):
            return self.atom, self.space.fn[self.atom.name].__signature__, False
        parameters = []
        for parameter in self.atom.args[0].children:
            if isinstance(parameter, Variable):
                parameters.append(inspect.Parameter(parameter.name, inspect.Parameter.POSITIONAL_OR_KEYWORD))
            elif isinstance(parameter, Expression) and parameter.head == S[":seg"] and len(parameter.args) == 1 and isinstance(parameter.args[0], Variable):
                parameters.append(inspect.Parameter(parameter.args[0].name.replace("-", "_"), inspect.Parameter.VAR_POSITIONAL))
            else:
                msg = "a patterned native lambda has no Python keyword parameter names; apply its atom in a space"
                raise TypeError(msg)
        return self.atom, inspect.Signature(parameters, return_annotation=self.result_type), False

    def application(self, args: Any, kwargs: Any) -> tuple[Atom, inspect.Signature, bool]:
        """Bind call syntax without evaluating the resulting native term."""
        image, signature, stream = self._layout(len(args) + len(kwargs))
        bound = signature.bind(*args, **kwargs)
        # The existing native Kwargs packet belongs to call syntax. A bound
        # method's segment lambda passes it to the same signature binder as a
        # directly written method call. A plain lambda has fixed parameters.
        segmented = isinstance(image, Expression) and any(
            isinstance(parameter, Expression) and parameter.head == S[":seg"]
            for parameter in image.args[0].children
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
        return _expr(image, *values), signature, stream

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
    # An occurrence token identifies authored code. Its head must remain a
    # live reference; only the anonymous clause can recover a lambda body.
    row = space._rt.must(
        "metta_py_decode_shared(Captures,_Captured,_),space_module(Space,_Module),"
        "findall(_Wire,(current_predicate(_Module:Name/_Arity),"
        "functor(_Head,Name,_Arity),predicate_property(_Module:_Head,interpreted),"
        "clause(_Module:_Head,_,_Ref),"
        "\\+filereader:'$metta_equation_token'(_,Name,_Ref,_),"
        "translated_from(_Ref,[=,[Name|_Parameters],_Body]),"
        "append(_Captured,_Remaining,_Parameters),_Written=['|->',_Remaining,_Body],"
        "metta_py_encode(_Written,_Wire)),Written)",
        Space=space.name, Name=source.name, Captures=Expression(captured).to_wire(),
    )
    written = row["Written"]
    if len(written) > 1:
        msg = "a native callable has more than one anonymous source clause"
        raise TypeError(msg)
    return _atom_from_wire(written[0]) if written else None


def _application_image(source: Symbol, captures: tuple[Atom, ...], arity: int, space: Any) -> Atom:
    parameters = Expression([fresh() for _ in range(arity)])
    body = _expr(S.evalc, _expr(source, *captures, *parameters.children), space)
    return _expr(S["|->"], parameters, body)


def _forwarded(atom: Atom, arity: int) -> tuple[Symbol, tuple[Atom, ...]] | None:
    """Read a forwarding value, retaining its arity and capture conditions."""
    if not isinstance(atom, Expression) or atom.head != S["|->"] or len(atom.args) != 2:
        return None
    parameters, body = atom.args
    if not isinstance(parameters, Expression):
        return None
    fixed, rest = parameters.children, None
    if fixed and isinstance(fixed[-1], Expression) and fixed[-1].head == S[":seg"] and len(fixed[-1].args) == 1:
        fixed, rest = fixed[:-1], fixed[-1].args[0]
    binders = (*fixed, *((rest,) if rest is not None else ()))
    if arity < len(fixed) or (rest is None and arity != len(fixed)):
        return None
    if not all(isinstance(value, Variable) for value in binders) or len(set(binders)) != len(binders):
        return None
    if isinstance(body, Expression) and body.head == S.evalc and len(body.args) == 2:
        body = body.args[0]
    if not isinstance(body, Expression):
        return None
    if rest is None:
        source, operands = body.head, body.args
    else:
        if body.head != S.chain or len(body.args) != 3:
            return None
        assembled, result, evaluated = body.args
        if not isinstance(result, Variable) or result in binders or evaluated != _expr(S.eval, result):
            return None
        binders = (*binders, result)
        prefix = []
        while isinstance(assembled, Expression) and assembled.head == S["cons-atom"] and len(assembled.args) == 2:
            item, assembled = assembled.args
            if not isinstance(item, Expression) or item.head != S.noeval or len(item.args) != 1:
                return None
            prefix.append(item.args[0])
        if assembled != rest or not prefix:
            return None
        source, operands = prefix[0], tuple(prefix[1:])
    if not isinstance(source, Symbol):
        return None
    if len(operands) < len(fixed) or (fixed and operands[-len(fixed):] != fixed):
        return None
    captures = operands[:-len(fixed)] if fixed else operands
    # Eta contraction is valid only when the removed binders are absent
    # from the retained expression. GHC 9.12.2, Core/Opt/Arity.hs:tryEtaReduce
    # applies the same free-variable condition; the journal pins that source.
    if set(_variables(Expression(captures))) & {value.name for value in binders}:
        return None
    return source, captures


def rebuild(atom: Atom, annotation: Any, space: Any, *, arity: int | None = None) -> NativeCallable | None:
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
        if arity is not None:
            return NativeCallable(_application_image(source, captured, arity, space), space, annotation)
        # A named value forwards every native arity, including later edits.
        # One presently visible arrow cannot describe a family of ports.
        tail: Atom = fresh()
        binders = Expression([_expr(S[":seg"], tail)])
        for value in reversed(captured):
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
