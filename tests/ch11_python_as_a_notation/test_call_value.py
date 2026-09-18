"""Purpose: observe one immediate value from native and exact host callables.

Owns resources: each context retires its linked operations and local equations;
  deferred host witnesses are explicitly closed even if an assertion fails.
"""

import inspect

import pytest

from metta import Atom, Expression, G, Grounded, MeTTa, S, V, Variable
from metta._catalog import call_signatures, call_values
from metta._declare import call_syntax
from metta._errors.errors import EngineError


def _call(home, function, *arguments, **keywords):
    return S["_python-call-value"](S[home.name], function, Expression(arguments), Expression([
        Expression([G(name), value]) for name, value in keywords.items()
    ]))


def _native(home, body, *, stream=False):
    image = S["|->"](Expression([]), S.evalc(S["call-value-target"](), home))
    equation = S["="](S["call-value-target"](), body)
    home.add(equation)
    home.add(S["@python-callable"](image, call_signatures.project(inspect.Signature(), G), S.stream if stream else S.one))
    return image, equation


@pytest.mark.parametrize("value", (None, False, [], {}, set(), NotImplemented, object(), S["+"](1, 2), S.Error(S.held, S.data)))
def test_call_value_preserves_host_result_identity(value):
    """None is one success and Atom or iterator objects do not become syntax."""
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        result = home.eval(_call(home, G(lambda: value)))
        assert len(result) == 1
        # The eval door hands a held Python object back as the Grounded atom
        # that holds it, the same object, never a spelling of it.
        assert isinstance(result[0], Grounded)
        assert result[0].value is value


def test_call_value_spells_a_returned_tuple_as_its_expression():
    """A tuple is what pythonic hands a callable for an expression, so it returns as one."""
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        assert home.eval(_call(home, G(lambda: (1, 2)))) == [Expression([1, 2])]
        assert home.eval(_call(home, G(lambda: ()))) == [Expression([])]


def test_call_value_uses_exact_opaque_callable_frames():
    """The selected host call needs no signature and preserves both argument frames."""
    positional, keyword = object(), object()
    calls = []

    class Opaque:
        @property
        def __signature__(self):
            message = "the call boundary inspected host signature metadata"
            raise AssertionError(message)

        def __call__(self, value, *, other):
            calls.append((value, other))
            return value is positional and other is keyword

    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        assert home.eval(_call(home, G(Opaque()), G(positional), other=G(keyword))) == [True]
        assert calls == [(positional, keyword)]


def test_call_value_does_not_start_or_replace_deferred_host_results():
    """A returned generator or coroutine is one original unstarted object."""
    events = []

    def generator():
        events.append("generator")
        yield NotImplemented

    async def coroutine():
        events.append("coroutine")
        return 3

    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        for source in (generator, coroutine):
            value = source()
            try:
                result = home.eval(_call(home, G(lambda value=value: value)))
                assert len(result) == 1 and isinstance(result[0], Grounded)
                assert result[0].value is value
                assert events == []
            finally:
                value.close()


@pytest.mark.parametrize("value", (G(None), G(value=False), Expression([]), V.held, S["+"](1, 2), S.Error(S.held, S.data)))
def test_call_value_holds_native_results(value):
    """The result stays under a data wrapper, including an Error head and redex."""
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        image, _equation = _native(home, S.noeval(value))
        wrapped = S.function(S.let(V.result, _call(home, image), S["return"](S.observed(V.result))))
        answers = home.eval(wrapped)
        if isinstance(value, Variable):
            # A variable crosses the engine under a fresh name; its shape is the claim.
            assert len(answers) == 1 and answers[0].head == S.observed
            assert isinstance(answers[0].args[0], Variable)
        else:
            assert answers == [S.observed(value)]


@pytest.mark.parametrize("values", ((), (G(1), G(2))))
def test_call_value_refuses_zero_and_multiple_answers(values):
    """A published one-result declaration cannot conceal an edited source's count."""
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        image, _equation = _native(home, S.superpose(Expression(values)))
        with pytest.raises(EngineError, match="cardinality"):
            home.eval(_call(home, image), on_error="abort")


def test_call_value_exceptions_propagate_and_never_become_decline():
    """An operational failure is distinct from a successful Error-shaped Atom."""
    def fails():
        message = "call-value raised witness"
        raise ValueError(message)

    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        with pytest.raises(EngineError, match="call-value raised witness"):
            home.eval(_call(home, G(fails)), on_error="abort")


def test_call_value_declines_only_for_the_actual_notimplemented_singleton():
    """An identical spelling and an equality overload do not impersonate the singleton."""
    class Equal:
        def __eq__(self, _other):
            message = "singleton identity must not invoke Python equality"
            raise AssertionError(message)

    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        for value, expected in ((NotImplemented, True), (Equal(), False), (S.NotImplemented, False)):
            expression = S.let(V.result, _call(home, G(lambda value=value: value)),
                               S["=="](S.noeval(V.result), G(NotImplemented)))
            assert home.eval(expression) == [expected]
        image, _equation = _native(home, S.noeval(S.NotImplemented))
        expression = S.let(V.result, _call(home, image), S["=="](S.noeval(V.result), G(NotImplemented)))
        assert home.eval(expression) == [False]


def test_call_value_reads_live_application_and_signature_rows():
    """Existing callable values observe edits without reconstructing the caller."""
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value", "_python-bind-parameters"))
        image = S["|->"](Expression([V.value]), S.evalc(S.noeval(V.value), home))
        signature = inspect.Signature([inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY, default=2)])
        contract = S["@python-callable"](image, call_signatures.project(signature, G), S.one)
        home.add(contract)
        application = S["|->"](Expression([V.positional, V.keywords]),
            S.let(V.source, S["_python-bind-parameters"](home, image, V.positional, V.keywords), S.eval(V.source)))
        relation = S["@python-application"](image, application)
        home.add(relation)
        source = _call(home, image)
        assert home.eval(source) == [2]
        replacement = signature.replace(parameters=[signature.parameters["value"].replace(default=7)])
        home.remove(contract)
        home.add(S["@python-callable"](image, call_signatures.project(replacement, G), S.one))
        assert home.eval(source) == [7]
        home.remove(relation)
        home.add(S["@python-application"](image, S["|->"](Expression([V.positional, V.keywords]), G(11))))
        assert home.eval(source) == [11]


def test_call_value_uses_the_callable_home_and_linking_does_not_stack_equations():
    """Cross-space use retains the callable's program and one shared interpreter."""
    with MeTTa() as context:
        first = context.self
        with first._new_space() as second:
            call_syntax.link(first, ("_python-call-value",))
            call_syntax.link(second, ("_python-call-value",))
            call_syntax.link(first, ("_python-call-value",))
            image, _equation = _native(first, G(3))
            _native(second, G(9))
            assert second.eval(_call(second, image)) == [3]
            def value_equations(space):
                # Stored rows come back with fresh variable names, so the
                # head is the claim: one native value equation per space.
                return sum(
                    1 for row in space.atoms()
                    if isinstance(row, Expression) and row.head == S["="]
                    and isinstance(row.args[0], Expression)
                    and row.args[0].head == S["_python-call-value"]
                )
            # The catalog space is policy, not a program: an equation stored
            # there reduces from no space, so each linked space owns one copy
            # and a repeated link counts as the same declaration.
            assert value_equations(first) == 1
            assert value_equations(second) == 1
            assert value_equations(call_values.lexical_space(S["&metta"])) == 0
        assert first.eval(_call(first, image)) == [3]


def test_call_value_does_not_replace_the_explicit_stream_consumer():
    """An explicitly published stream collapses only through the iterable consumer.

    Under the value seam it stays a stream, one answer per element, neither
    collapsed nor refused: the binder leaves a stream application bare and
    wraps every other native application in eval-one, which is the
    CallConsumer contract compiled value calls rely on.
    """
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        image, _equation = _native(home, S.superpose(Expression([G(1), G(2)])), stream=True)
        application = call_syntax.bind_call(home, image, Expression([]), G({}), G("iterable"))
        assert home.eval(application) == [Expression([1, 2])]
        assert home.eval(_call(home, image), on_error="abort") == [G(1), G(2)]


def test_call_value_keeps_explicit_host_images():
    """A declared result projection remains the value selected by its author."""
    class Declared:
        def __metta__(self) -> Atom:
            return S.Declared(S.payload)

    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        assert home.eval(_call(home, G(Declared))) == [S.Declared(S.payload)]


def test_call_value_holds_a_returned_answer_view():
    """A returned view crosses by identity; observation waits for a term, so the twin counts it."""
    with MeTTa() as context:
        home = context.self
        call_syntax.link(home, ("_python-call-value",))
        home.add(S.row(1), S.row(2))
        rows = S.match(S[home.name], S.row(V.x), V.x)
        view = home.answers(rows)
        result = home.eval(_call(home, G(lambda: view)))
        assert len(result) == 1 and isinstance(result[0], Grounded)
        assert result[0].value is view
        assert len(view) == 2
        with pytest.raises(EngineError, match="exactly one answer"):
            S.observed(view)
