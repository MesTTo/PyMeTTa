"""Purpose: bind compiled parameter slots from editable native call records.

Guarantees:
  - native binding holds values, separates both variadic segments and leaves
    body evaluation to its caller [tested:
    test_native_parameter_binding_preserves_values_and_defers_the_body;
    commit=1796cf0f581aa767db9289b807f66238cb747065]
  - retained binding expressions read live signatures and canonical bodies
    [tested: test_native_parameter_binding_observes_graph_rewrites;
    commit=1796cf0f581aa767db9289b807f66238cb747065]
"""

import inspect

import pytest

from metta import Expression, G, MeTTa, S, Space, V
from metta._catalog import call_signatures, call_values
from metta._declare import call_syntax


def _program(home, default=2):
    """Publish native source independently of a Python function body."""
    signature = inspect.Signature([
        inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter("offset", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default),
        inspect.Parameter("extra", inspect.Parameter.VAR_POSITIONAL),
        inspect.Parameter("scale", inspect.Parameter.KEYWORD_ONLY, default=3),
        inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),
    ])
    parameters = Expression([V.value, V.offset, V.extra, V.scale, V.options])
    head = S["packed-parameters"](*parameters.children)
    image = S["|->"](parameters, S.evalc(head, home))
    contract = S["@python-callable"](image, call_signatures.project(signature, call_values.argument), S.one)
    equation = S["="](head, S.let(V.bound_options, S["dict-space"](V.options), S.progn(
        S["add-atom"](home, S.entered()),
        S.noeval(S.received(V.value, V.offset, V.extra, V.scale, V.bound_options)),
    )))
    home.run('!(import! &self (library lib_dict))')
    home.add(equation, contract, S[":"](S["packed-parameters"], S["->"](S.Atom, S.Atom, S.Expression, S.Atom, S.Expression, S["%Undefined%"])))
    call_syntax.link(home, ("_python-bind-parameters",))
    return image, contract, equation


def _binding(home, image, positional, keywords):
    body = S["_python-bind-parameters"](V.binding_home, V.binding_image, V.binding_positionals, V.binding_keywords)
    values = (
        (V.binding_home, home), (V.binding_image, image),
        (V.binding_positionals, Expression(positional)),
        (V.binding_keywords, Expression([Expression([G(key), value]) for key, value in keywords.items()])),
    )
    for variable, value in reversed(values):
        body = S.let(variable, S.noeval(value), body)
    return body


@pytest.mark.parametrize("value", (None, False, 0, "", S.scalar, S["+"](1, 2), V.held))
@pytest.mark.parametrize("supplied", (False, True))
def test_native_parameter_binding_preserves_values_and_defers_the_body(value, supplied):
    """Executable-looking data stays in its slot, even in either collector."""
    with MeTTa() as context:
        home = context.self
        image, _, _ = _program(home, default=value)
        home.add(S["="](S.scalar, 97))
        positional = (value, value, value) if supplied else (0,)
        keywords = {"scale": value, "value": value} if supplied else {}
        (application,) = home.eval(_binding(home, image, positional, keywords))
        assert S.entered() not in home.atoms()
        (result,) = home.eval(application)
        expected = Expression([value if supplied else 0, value, Expression([value] if supplied else []), value if supplied else 3])
        assert Expression(result.args[:4]).alpha_eq(expected)
        pairs = Expression(Space(result.args[4]).atoms())
        assert pairs.alpha_eq(Expression([Expression(["value", value])] if supplied else []))
        assert S.entered() in home.atoms()


def test_native_parameter_binding_observes_graph_rewrites():
    """The same native binder term reads a new default and then a new body."""
    with MeTTa() as context:
        home = context.self
        image, contract, equation = _program(home)
        binding = _binding(home, image, (1,), {})
        (first,) = home.eval(binding)
        assert home.eval(first)[0].args[1] == 2
        signature = call_signatures.build(contract.args[1])
        parameters = tuple(signature.parameters.values())
        signature = signature.replace(parameters=[parameters[0], parameters[1].replace(default=13), *parameters[2:]])
        home.remove(contract)
        home.add(S["@python-callable"](image, call_signatures.project(signature, G), S.one))
        (second,) = home.eval(binding)
        assert home.eval(second)[0].args[1] == 13
        home.remove(equation)
        home.add(S["="](equation.args[0], S.noeval(S.rewritten(V.value, V.offset))))
        assert home.eval(second) == [S.rewritten(1, 13)]
