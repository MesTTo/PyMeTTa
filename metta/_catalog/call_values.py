"""Purpose: rebuild native callable values with their lexical space.

Guarantees:
  - the call consumer domain names immediate application or iteration,
    independently of the refusal vocabulary [tested:
    test_call_consumer_source.CallConsumerSourceTests; commit=b8f5c6b9a3ef41b173d6af81e1b9bb526977a908]
  - returned Python values keep explicit images, borrowed container identity
    and Atom object identity at the one-value boundary [tested: test_call_value_preserves_host_result_identity; commit=d78d867637047c164be4bc1ab63c40b46d2cff5d].
  - two-frame callable applications consume supplied positional values while
    raw native ports retain their formal-slot capture contract [tested: test_bound_application_prefixes_keep_variadic_collectors and test_raw_native_captures_still_hold_formal_slots; commit=d78d867637047c164be4bc1ab63c40b46d2cff5d].
  - compiled parameter slots hold fixed values, positional expressions and
    ordered keyword-pair expressions through one packing operation [tested:
    test_native_parameter_binding_preserves_values_and_defers_the_body;
    test_compiled_keyword_collectors_keep_atom_values;
    test_constructor_arguments_preserve_values_and_run_factories;
    commit=1796cf0f581aa767db9289b807f66238cb747065]
  - named callable values select their live Python contract independently of
    supplied argument count, retaining defaults and both variadic segments
    [tested: test_named_callable_uses_its_complete_signature,
    test_named_callable_binding_agrees_with_python,
    test_named_callable_observes_signature_replacement; commit=6d91840990d95e72b88c946b36b9c8babe7f768a]
  - exact positional ports precede overlapping variadic layouts, whose
    ambiguity requires an explicit native image [tested:
    test_an_exact_positional_port_precedes_variadic_ports,
    test_overlapping_variadic_ports_require_an_explicit_native_image;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - a Python call spells the MeTTa application: an Atom argument is syntax
    written at the call site and the arrow decides its evaluation (Atom and
    its refinements take it as written, every other position evaluates it),
    a Python object crosses as a value bound unevaluated, and a lambda image
    holds the positions its Callable annotation or signature rows declare
    Atom [tested: test_python_call_arguments_follow_the_arrow,
    test_computed_receivers_preserve_their_stored_syntax,
    test_written_symbol_arguments_follow_live_scalar_rules,
    test_native_value_binding_keeps_lambda_parameter_patterns; commit=e59104aced3902c3ca0ba5fa87fc93bc5dceb38a]
  - nonsymbol literal arguments retain direct cursor application [tested:
    test_function_calls_suspend_endless_producers; commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - quoted variables retain their value boundary when callable templates
    capture receivers [tested:
    test_class_methods_keep_full_python_signatures_and_native_bodies,
    test_class_generator_methods_return_owned_cursors; commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - native application facts receive separate data frames, retaining supplied
    arguments, captures and live program edits [tested:
    test_native_application_frames_preserve_data_and_live_programs;
    test_forwarded_application_frames_preserve_captured_arguments;
    test_native_application_mapping_lookup_preserves_distinct_binders;
    test_native_application_keywords_do_not_bind_adapter_parameters;
    test_captured_application_parameters_keep_their_keyword_binding_rule;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - native references select their current call port and preserve captures
    and explicit contracts [tested:
    test_expanded_partial_references_preserve_capture_and_parameter_names;
    test_forwarding_contracts_preserve_explicit_cardinality_and_bound_captures;
    test_native_references_observe_later_arity_changes; commit=6d91840990d95e72b88c946b36b9c8babe7f768a]
  - application evaluates the carried native value, including subsequent source
    rewrites [tested: test_native_callable_values_keep_their_lexical_program;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - segment applications execute the constructed call and preserve captured
    arguments [tested: test_evaluated_native_lambdas_apply_their_assembled_arguments;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - adding the current lexical home retains the source lambda's contract
    [tested: test_native_callable_contracts_survive_lexical_wrapping;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - contract lookup preserves distinct binders and references to authored
    heads [tested: test_contract_lookup_preserves_distinct_lambda_binders;
    test_callable_conversion_keeps_authored_heads_as_live_references;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
Owns resources:
  - the callable image contains its lexical home and captured receiver, so
    scope retention follows the ordinary native value graph [tested:
    test_a_kept_native_callable_retains_its_scoped_program; commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any, Literal, NamedTuple

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
    hold,
)
from metta._catalog import call_signatures
from metta._catalog.annotations import type_atoms_for
from metta._catalog.containers import runtime_annotation
from metta._catalog.project import explicit_projection
from metta._lazy import lazy

# The consumer chooses how a caller uses the published result contract.
# An explicit stream remains a stream when its consumer is "value".
# policy-inventory-exempt: mechanism-internal; reason=callers select application or iteration of the published result contract; evidence=extensions/python/metta/_declare/call_syntax.py:bind_call
type CallConsumer = Literal["value", "iterable"]


def argument(value: Any) -> Atom:
    """Borrow Python container arguments; their grain belongs to their storage."""
    return Grounded(value) if runtime_annotation(value) is not None else _encode(value)


def returned(value: Any) -> Atom:
    """Carry one successful Python result through its existing value image.

    A view whose image is an observation (`__metta_observes__`) is held by
    identity: observation is what term construction does to a view, and a
    returned view is not in a term yet, so `len(m.match(...))`
    in a compiled body counts it and `.one()` reads it. An author's declared
    image projects next, since a declared class instance is a face of a native
    value whatever else it is (a prototype instance is a space, and a space is
    an atom); an Atom result is then held under a data wrapper so returned
    syntax is not reduced; a container is borrowed by identity; and anything
    else is held by its exact class, which is where a generator or a coroutine
    stays unstarted: neither has an image, so the twin receives the object it
    returned.
    """
    if getattr(type(value), "__metta_observes__", False):
        return hold(value)
    projected = explicit_projection(value)
    if projected is not None:
        return projected
    if isinstance(value, Atom) or runtime_annotation(value) is not None:
        return Grounded(value)
    return hold(value)


def pythonic(value: Any) -> Any:
    """An atom as the Python value the twin computes with: grounded values
    unwrap, expressions become tuples, a symbol stays itself (the twin
    cannot hold one, and hazard tracking keeps it out of twin paths). The
    prelude's operators and the seam's host application share it, so a
    Python callable computes on the same values whichever way it is reached.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(value, Grounded):
        return value.value
    if isinstance(value, Expression):
        return tuple(pythonic(c) for c in value)
    return value


class Written(NamedTuple):
    """Syntax the caller wrote at a Python call site.

    apply_sources places it in the application as written, so the callee's
    declared parameter type decides its evaluation exactly as for the same
    application written in MeTTa: an Atom position takes it as it stands and
    every other position evaluates it. `f(S.add(1, 1))` IS `!(f (+ 1 1))`.
    """

    atom: Atom


def held_position(annotation: Any) -> bool:
    """True when a declared parameter type takes its argument as written.

    That is MeTTa's Atom and every refinement of it: `Annotated[Atom,
    MinLen(2)]` publishes `(Annotated Atom (MinLen 2))`, a predicate over the
    written atom, so the engine masks the position the way it masks Atom
    [source: engine/translator/typing.pl:non_evaluated_parameter_type/1]. An
    unannotated or Any parameter is `%Undefined%`, which evaluates.
    """
    if annotation is inspect.Parameter.empty or annotation is Any:
        return False
    return any(
        atom == S.Atom or (isinstance(atom, Expression) and atom.head == S.Annotated
                           and bool(atom.args) and atom.args[0] == S.Atom)
        for atom in type_atoms_for(annotation)
    )


def source(value: Any, *, held: bool = False, encode: Callable[[Any], Atom] = argument) -> Atom | Written:
    """One Python argument as the source it is at an engine door.

    Syntax WRITTEN at the call site is an Atom the caller built, or a Python
    literal the codec spells: a number, a string, a container (`(43,)` is
    `(43)`). It enters the application as written and the callee's arrow
    decides its evaluation. Every other Python object, a declared class
    instance, a class, a function, a space, a view, encodes to an IMAGE of
    itself, and an image is a VALUE the caller computed: it crosses under
    noeval, which apply_sources binds to a fresh variable, so the callee
    receives it unevaluated the way a compiled body passes a bound variable,
    and an instance's syntax fields survive the call. A grounded image is a
    literal either way. A position the door already knows is held (a lambda's
    Atom-typed parameter has no arrow the engine could read) takes written
    syntax as a value too.
    """
    image = value if isinstance(value, Atom) else encode(value)
    if held or (not isinstance(value, Atom) and runtime_annotation(value) is None and not isinstance(image, Grounded)):
        return _expr(S.noeval, image)
    return Written(image)


def _literal(atom: Atom) -> bool:
    # The wire decoder makes these tags nonsymbol literals, which eager
    # argument translation already passes through. A variable can still be
    # instantiated in a callable template, so it keeps its binding. Boolean
    # and space tags decode to atoms and can have scalar rules.
    return not isinstance(atom, Expression) and atom.to_wire()[0] in ("n", "g", "o", "h")


def pack(parts: Sequence[Atom | Written], *, keys: Sequence[Atom] | None = None,
         head: Atom | None = None) -> Atom:
    """A data frame of argument sources, `(noeval (v1 v2 ...))`.

    A frame is data by construction, so a value's atom sits in it as it is.
    Written syntax and computations are evaluated first, in order, and their
    results bound into the frame: `(let $e (+ 1 1) (noeval ($e)))`. The result
    is itself a computation when anything had to run and a value otherwise,
    and apply_sources binds either correctly. `keys` pairs each element with
    its key, `head` prefixes the frame.
    """
    elements: list[Atom] = []
    bindings: list[tuple[Variable, Atom]] = []
    for part in parts:
        if isinstance(part, Expression) and part.head == S.noeval and len(part.args) == 1:
            element = part.args[0]
        else:
            computation = part.atom if isinstance(part, Written) else part
            if _literal(computation):
                element = computation
            else:
                element = fresh()
                bindings.append((element, computation))
        elements.append(element)
    if keys is not None:
        elements = [Expression([key, element]) for key, element in zip(keys, elements, strict=True)]
    frame: Atom = _expr(S.noeval, Expression(elements if head is None else [head, *elements]))
    for variable, computation in reversed(bindings):
        frame = _expr(S.let, variable, computation, frame)
    return frame


def argument_sources(signature: inspect.Signature, supplied: Mapping[str, Any],
                     defaults: Mapping[str, Atom], *, written: bool) -> tuple[Atom | Written, ...]:
    """Pack canonical parameters, retaining the caller's default source policy.

    `written` says the supplied objects come from a Python call site, where an
    Atom is syntax the caller wrote and a parameter's annotation says whether
    its position is held. A frame of completed values is not written: every
    atom in it crosses as a value.
    """
    def one(value: Any, parameter: inspect.Parameter) -> Atom | Written:
        if written:
            return source(value, held=held_position(parameter.annotation))
        return _expr(S.noeval, argument(value))

    result: list[Atom | Written] = []
    for name, parameter in signature.parameters.items():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            result.append(pack([one(part, parameter) for part in supplied.get(name, ())]))
        elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
            entries = supplied.get(name, {})
            result.append(pack([one(part, parameter) for part in entries.values()],
                               keys=[Grounded(key) for key in entries]))
        elif name in supplied:
            result.append(one(supplied[name], parameter))
        else:
            result.append(defaults[name])
    return tuple(result)


def apply_sources(head: Atom, sources: Sequence[Atom | Written]) -> Atom:
    """Apply a head to its argument sources.

    Written syntax is placed as it stands, so the head's declared parameter
    type decides whether it is evaluated. A `(noeval v)` source is a value: a
    nonsymbol literal is passed directly, anything else is bound unevaluated
    to a fresh variable. Every other source is a computation, bound to a fresh
    variable after it runs, the administrative binding of an A-normal form,
    which is what lets a default factory run before an Atom-typed entry that
    would otherwise take the factory call as syntax.
    """
    if isinstance(head, Expression) and head.head == S["|->"] and len(head.args) == 2:
        binders, body = head.args
        if isinstance(body, Expression) and body.head == S.evalc and len(body.args) == 2:
            # evalc compiles its supplied term in the target home. Rebind the
            # matched values there so substitution cannot turn them into code.
            # The original parameter pattern and home expression stay in place.
            replacements = {Variable(name): fresh() for name in _variables(binders)}
            if replacements:
                held = body.args[0].subs(replacements)
                for parameter, replacement in reversed(tuple(replacements.items())):
                    held = _expr(S.let, replacement, _expr(S.noeval, parameter), held)
                head = _expr(S["|->"], binders, _expr(S.evalc, held, body.args[1]))
    operands: list[Atom] = []
    bindings: list[tuple[Variable, Atom]] = []
    for item in sources:
        if isinstance(item, Written):
            operands.append(item.atom)
            continue
        value = (item.args[0] if isinstance(item, Expression)
                 and item.head == S.noeval and len(item.args) == 1 else item)
        if _literal(value):
            operands.append(value)
        else:
            parameter = fresh()
            operands.append(parameter)
            bindings.append((parameter, item))
    body = _expr(head, *operands)
    for parameter, item in reversed(bindings):
        body = _expr(S.let, parameter, item, body)
    return body


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


def _uncaptured(signature: inspect.Signature, captured: int, keywords: Collection[str]) -> inspect.Signature:
    parameters = tuple(signature.parameters.values())
    if not isinstance(captured, int) or not 0 <= captured <= len(parameters):
        msg = "a native callable binding must name the number of captured parameters"
        raise TypeError(msg)
    for parameter in parameters[:captured]:
        if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and parameter.name in keywords:
            msg = f"multiple values for argument {parameter.name!r}"
            raise TypeError(msg)
    return signature.replace(parameters=parameters[captured:])


def _positional_signature(signature: inspect.Signature, captured: int,
                          keywords: Collection[str], refusal: type[Exception]) -> inspect.Signature:
    """Project supplied positional values through the canonical parameter kinds."""
    if not isinstance(captured, int) or captured < 0:
        msg = "a native callable binding must name the number of captured arguments"
        raise TypeError(msg)
    remaining, consumed = captured, 0
    # A bound *args collector survives receiver injection. The same rule
    # projects an arbitrary positional prefix; keyword-only slots never take
    # its values. The caller owns whether observation means inspect or call.
    # https://github.com/python/cpython/blob/23116f998f6789d8c2fbe5ed5b8146854c8c2a4f/Lib/inspect.py#L1877
    for parameter in signature.parameters.values():
        if not remaining:
            break
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            remaining = 0
            break
        if parameter.kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            break
        consumed += 1
        remaining -= 1
    if remaining:
        msg = "invalid method signature" if refusal is ValueError else "too many positional arguments"
        raise refusal(msg)
    return _uncaptured(signature, consumed, keywords)


class NativeCallable:
    """A Python application of a native callable value, with no host body."""

    def __init__(self, atom: Atom, space: Any, annotation: Any):
        self.atom, self.space = atom, space
        result = typing.get_args(annotation)
        self.result_type = result[-1] if result else Any
        # `Callable[[Atom, int], R]` is the arrow a lambda image has nowhere
        # else: its positional types say which positions take their argument
        # as written when the signature rows leave a parameter unannotated.
        self.parameter_types: list[Any] | None = list(result[0]) if result and isinstance(result[0], list) else None

    def __metta__(self) -> Atom:
        return self.atom

    @property
    def __signature__(self) -> inspect.Signature:
        return self.contract()[0]

    def contract(self) -> tuple[inspect.Signature, bool]:
        _, signature, stream, _application = self._layout()
        return signature, stream

    def _declared_contract(self, keywords: Collection[str] = (), *,
                           refusal: type[Exception] = ValueError) -> tuple[inspect.Signature, bool, Atom | None] | None:
        # Read stored program data through the occurrence relation. A written
        # match pattern would interpret the lambda's :seg binder as a query
        # gap, although this consumer is looking up a callable value. A
        # lambda carried with its current home has the same contract as its
        # written body in that home; both keys remain native program data.
        rows = self.space._rt.must(
            "metta_py_decode_shared(Wire,_Scoped,_),"
            "findall([_Wire,_Cardinality,_Captured,_ApplicationsWire],("
            "(_Scoped=['|->',_Parameters,[evalc,_Body,_Home]],_Home==Space -> "
            "member(_Value,[_Scoped,['|->',_Parameters,_Body]]) ; _Value=_Scoped),"
            "(_Contracts=Space ; Space\\=='&metta',_Contracts='&metta'),"
            "(spaces:metta_space_pair(_Contracts,['@python-callable',_Pattern,_Signature,_Cardinality],_,_),"
            "subsumes_term(_Pattern,_Value),_Pattern=_Value,_Captured=0;"
            "spaces:metta_space_pair(_Contracts,['@python-binding',_Pattern,_Canonical,_Captured],_,_),"
            "subsumes_term(_Pattern,_Value),_Pattern=_Value,"
            "spaces:metta_space_pair(_Contracts,['@python-callable',_Canonical,_Signature,_Cardinality],_,_)),"
            "findall(_Application,("
            "spaces:metta_space_pair(_Contracts,['@python-application',_ApplicationPattern,_Application],_,_),"
            "subsumes_term(_ApplicationPattern,_Value),_ApplicationPattern=_Value),_Applications),"
            "metta_py_encode(_Applications,_ApplicationsWire),metta_py_encode(_Signature,_Wire)),Contracts)",
            Space=self.space.name, Wire=self.atom.to_wire(),
        )
        found = rows["Contracts"]
        if found:
            if len(found) != 1 or found[0][1] not in ("one", "stream"):
                msg = "a native callable needs one Python signature and answer-cardinality declaration"
                raise TypeError(msg)
            signature = call_signatures.build(_atom_from_wire(found[0][0]))
            cardinality, captured = found[0][1:3]
            applications = _atom_from_wire(found[0][3]).children
            if len(applications) > 1:
                msg = "a native callable needs at most one native application declaration"
                raise TypeError(msg)
            application = next(iter(applications), None)
            remaining = (_positional_signature(signature, captured, keywords, refusal)
                         if application is not None else _uncaptured(signature, captured, keywords))
            return remaining, cardinality == "stream", application
        return None

    def _layout(self, arity: int | None = None, keyword_names: Collection[str] = ()) -> tuple[Atom, inspect.Signature, bool, Atom | None]:
        if (declared := self._declared_contract(keyword_names, refusal=ValueError if arity is None else TypeError)) is not None:
            return self.atom, *declared
        if (layout := self._reference_layout(arity, keyword_names)) is not None:
            return layout
        if isinstance(self.atom, Symbol):
            return self.atom, self.space.fn[self.atom.name].__signature__, False, None
        parameters = []
        for parameter in self.atom.args[0].children:
            if isinstance(parameter, Variable):
                parameters.append(inspect.Parameter(parameter.name, inspect.Parameter.POSITIONAL_OR_KEYWORD))
            elif isinstance(parameter, Expression) and parameter.head == S[":seg"] and len(parameter.args) == 1 and isinstance(parameter.args[0], Variable):
                parameters.append(inspect.Parameter(parameter.args[0].name.replace("-", "_"), inspect.Parameter.VAR_POSITIONAL))
            else:
                msg = "a patterned native lambda has no Python keyword parameter names; apply its atom in a space"
                raise TypeError(msg)
        return self.atom, inspect.Signature(parameters, return_annotation=self.result_type), False, None

    def _reference_layout(self, arity: int | None, keywords: Collection[str]) -> tuple[Atom, inspect.Signature, bool, Atom | None] | None:
        """Select a live native port by its argument grammar, not slot count."""
        reference = _forwarded(self.atom, 0 if arity is None else arity)
        if reference is None:
            return None
        source, captures = reference
        layouts: list[tuple[Atom, inspect.Signature, bool, Atom | None]] = []
        exact = None if arity is None else arity + len(captures)
        refusal = ValueError if arity is None else TypeError
        if exact is not None and (layout := self._port_layout(source, captures, exact, keywords, refusal)) is not None:
            layouts.append(layout)
            # Native fixed-arity dispatch is the specific case. Preserve its
            # direct lookup and single binding pass, including binding errors.
            if all(parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ) for parameter in layout[1].parameters.values()):
                return layout
        for native_arity in self.space.arities(source.name):
            count = native_arity - 1
            if (count != exact
                    and (layout := self._port_layout(source, captures, count, keywords, refusal)) is not None):
                layouts.append(layout)
        # A unique declaration needs no speculative binding pass. This also
        # preserves effects from keyword keys and the declaration's diagnostics.
        if len(layouts) == 1:
            return layouts[0]
        if not layouts or arity is None:
            return None
        accepted = []
        for layout in layouts:
            try:
                layout[1].bind(*([None] * (arity - len(keywords))), **dict.fromkeys(keywords))
            except TypeError:
                continue
            accepted.append(layout)
        if len(accepted) > 1:
            msg = f"{source.name}: more than one native call port accepts these arguments; carry the intended native lambda image"
            raise TypeError(msg)
        if accepted:
            return accepted[0]
        msg = f"{source.name}: no declared native call port accepts these arguments"
        raise TypeError(msg)

    def _port_layout(self, source: Symbol, captures: tuple[Atom, ...], count: int,
                     keywords: Collection[str], refusal: type[Exception]) -> tuple[Atom, inspect.Signature, bool, Atom | None] | None:
        canonical = _application_image(source, (), count, self.space)
        declared = NativeCallable(canonical, self.space, Any)._declared_contract(keywords, refusal=refusal)
        if declared is None:
            return None
        signature, stream, applicator = declared
        if applicator is None and count < len(captures):
            return None
        remaining = (_positional_signature(signature, len(captures), keywords, refusal)
                     if applicator is not None else _uncaptured(signature, len(captures), keywords))
        if applicator is not None and captures:
            positional, named, complete = fresh(), fresh(), fresh()
            supplied: Atom = positional
            for capture in reversed(captures):
                supplied = _expr(S["cons-atom"], _expr(S.noeval, capture), supplied)
            applicator = _expr(S["|->"], Expression([positional, named]),
                               _expr(S.let, complete, supplied, _expr(applicator, complete, named)))
        image = (self.atom if applicator is not None
                 else _application_image(source, captures, count - len(captures), self.space))
        return image, remaining, stream, applicator

    def _sources(self, signature: inspect.Signature, args: Any, kwargs: Any, *,
                 written: bool) -> tuple[list[Atom | Written], dict[str, Atom | Written]]:
        """Each supplied argument as its source, held where its parameter takes syntax as written.

        A positional argument meets the positional parameters in order and the
        variadic collector after them; a keyword argument meets its named
        parameter or the keyword collector. An unannotated position falls back
        to the Callable annotation's positional types. A frame's atoms
        (`written=False`) are values whatever their parameter says.
        """
        parameters = list(signature.parameters.values())
        positional_parameters = [parameter for parameter in parameters if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )]
        variadic = next((parameter for parameter in parameters if parameter.kind is inspect.Parameter.VAR_POSITIONAL), None)
        collector = next((parameter for parameter in parameters if parameter.kind is inspect.Parameter.VAR_KEYWORD), None)

        def held(parameter: inspect.Parameter | None, index: int | None) -> bool:
            annotation = inspect.Parameter.empty if parameter is None else parameter.annotation
            if (annotation is inspect.Parameter.empty and index is not None
                    and self.parameter_types is not None and index < len(self.parameter_types)):
                annotation = self.parameter_types[index]
            return held_position(annotation)

        def one(value: Any, parameter: inspect.Parameter | None, index: int | None) -> Atom | Written:
            return source(value, held=held(parameter, index)) if written else _expr(S.noeval, argument(value))

        positional = [
            one(value, positional_parameters[index] if index < len(positional_parameters) else variadic, index)
            for index, value in enumerate(args)
        ]
        named = {}
        for name, value in kwargs.items():
            parameter = signature.parameters.get(name)
            # A keyword reaches a parameter only where Python would bind it
            # there; a positional-only namesake and a collector send it on to
            # the keyword collector.
            if parameter is None or parameter.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY,
            ):
                parameter = collector
            named[name] = one(value, parameter, None)
        return positional, named

    def application(self, args: Any, kwargs: Any, *, written: bool = True) -> tuple[Atom, inspect.Signature, bool]:
        """Bind call syntax without evaluating the resulting native term.

        `written` marks a Python call site, where each argument crosses as the
        source it is (`source`): written syntax follows the parameter's
        declared type, a Python object is a value. A frame of completed values
        handed on by a compiled body is not written: every atom in it is a
        value.
        """
        image, signature, stream, applicator = self._layout(len(args) + len(kwargs), kwargs)
        bound = signature.bind(*args, **kwargs)
        positional, named = self._sources(signature, args, kwargs, written=written)
        if applicator is not None:
            # Bind the frames before application. A frame is data, including
            # when the applicator is an untyped lambda rather than an
            # Expression-typed native function, so written syntax bound for an
            # evaluated position runs before it enters the frame.
            expression = apply_sources(applicator, (
                pack(positional),
                pack(list(named.values()), keys=[Grounded(name) for name in named]),
            ))
            return expression, signature, stream
        # A segment binder receives the native application's arguments. A
        # fixed binder receives one value per reflected Python parameter.
        segmented = isinstance(image, Expression) and any(
            isinstance(parameter, Expression) and parameter.head == S[":seg"]
            for parameter in image.args[0].children
        )
        values: list[Atom | Written]
        if segmented:
            values = list(positional)
            if kwargs:
                values.append(pack(list(named.values()), keys=[Symbol(name) for name in named], head=S.Kwargs))
        else:
            supplied = set(bound.arguments)
            bound.apply_defaults()
            # A fixed binder holds one parameter value: a supplied argument as
            # its source, a collector's whole Python tuple or dict, and a
            # signature default as the value it is. Python's own binding says
            # which parameter each argument reached.
            remaining = iter(positional)
            values = []
            for name, parameter in signature.parameters.items():
                if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    values.append(_expr(S.noeval, argument(bound.arguments[name])))
                elif name in supplied:
                    values.append(named[name] if name in named and parameter.kind is not inspect.Parameter.POSITIONAL_ONLY
                                  else next(remaining))
                else:
                    values.append(_expr(S.noeval, argument(bound.arguments[name])))
        return apply_sources(image, tuple(values)), signature, stream

    def __call__(self, /, *args: Any, **kwargs: Any) -> Any:
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
    # Equal cardinality proves every binder is a distinct variable.
    bound_names = {value.name for value in binders if isinstance(value, Variable)}
    if len(bound_names) != len(binders):
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
        if not isinstance(result, Variable) or result.name in bound_names or evaluated != _expr(S.eval, result):
            return None
        bound_names.add(result.name)
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
    if set(_variables(Expression(captures))) & bound_names:
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
