"""Purpose: check call-value construction without importing a native runtime.

Actual helper definitions run against inert Atom records and boundary spies.
These controls establish source delegation, validation and exact host calls;
native masks, execution, cardinality and ownership need the native tests.
"""

from __future__ import annotations

import ast
import inspect
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


class Atom:
    """An inert value used only to inspect the actual source constructors."""


@dataclass(frozen=True)
class Grounded(Atom):
    """Retain exact test values without invoking a transport codec."""

    value: Any


@dataclass(frozen=True)
class Symbol(Atom):
    """Name a node in the emitted source record."""

    name: str


class Variable(Symbol):
    """Distinguish source binders from ordinary names."""


class Expression(Atom):
    """Record constructor order without evaluating or substituting anything."""

    def __init__(self, children):
        """Store source operands without interpreting them."""
        self.children = tuple(children)

    @property
    def head(self):
        """Read the source constructor."""
        return self.children[0]

    @property
    def args(self):
        """Read its ordered operands."""
        return self.children[1:]


class _Symbols:
    def __getitem__(self, name):
        return Symbol(name)

    def __getattr__(self, name):
        return Symbol(name)


def _expr(*values):
    return Expression(values)


def _helpers(path, selected, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in selected]
    if len(body) != len(selected):
        raise AssertionError((path, selected, [node.name for node in body]))
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)


def _shape(atom):
    if isinstance(atom, Expression):
        return tuple(_shape(child) for child in atom.children)
    if isinstance(atom, Variable):
        return "$" + atom.name
    if isinstance(atom, Symbol):
        return atom.name
    return atom


class CallValueSourceTests(unittest.TestCase):
    """Discriminate exact host invocation from source construction and binding."""

    def setUp(self):
        """Load actual helpers with inert construction and host boundary spies."""
        self.events = []
        self.images = {}
        self.native = None
        self.values = types.SimpleNamespace(
            lexical_space=lambda home: home,
            argument=Grounded,
            rebuild=lambda *_args: self.native,
            apply_sources=lambda head, sources: _expr(head, *sources),
            pythonic=lambda value: value.value if isinstance(value, Grounded) else value,
        )
        self.namespace = {
            "Atom": Atom, "Expression": Expression, "Grounded": Grounded,
            "Symbol": Symbol, "Variable": Variable, "S": _Symbols(), "_expr": _expr,
            "inspect": inspect, "Any": Any, "call_values": self.values,
            "build": self.build, "argument": Grounded,
            "hold": Grounded, "runtime_annotation": lambda _value: None,
            "deferred": lambda _value: False,
            "explicit_projection": lambda value: self.images.get(id(value)),
            "host": types.SimpleNamespace(unboxed=lambda value: value),
        }
        _helpers(ROOT / "metta/_catalog/call_values.py", {"returned"}, self.namespace)
        self.values.returned = self.namespace["returned"]
        _helpers(ROOT / "metta/_declare/call_syntax.py", {
            "_argument_values", "bind_arguments", "_native_application", "bind_value",
            "apply_host_value", "value_declarations",
        }, self.namespace)

    def build(self, value, *, space):
        """Record each use of the existing reverse-projection boundary."""
        self.events.append(("build", value, space))
        return value.value if isinstance(value, Grounded) else value

    def frames(self):
        """Make distinct borrowed values in the two source frames."""
        left, right = object(), object()
        return left, right, Expression([Grounded(left)]), Expression([
            Expression([Grounded("right"), Grounded(right)]),
        ])

    def test_binding_a_host_value_does_not_call_or_inspect_it(self):
        """Binding constructs held source while the host body stays untouched."""
        def prohibited(*_args, **_kwargs):
            message = "source construction executed the host callable"
            raise AssertionError(message)

        _left, _right, positional, keywords = self.frames()
        image = self.namespace["bind_value"](Symbol("Home"), Grounded(prohibited), positional, keywords)
        self.assertEqual(image.head, Symbol("_python-apply-host-value"))
        self.assertEqual(tuple(child.head for child in image.args), (Symbol("noeval"),) * 4)
        self.assertIs(image.args[2].args[0], positional)
        self.assertIs(image.args[3].args[0], keywords)
        self.assertEqual(self.events, [])

    def test_host_call_uses_exact_object_frames_and_result(self):
        """One invocation receives exact positional and keyword objects."""
        events = self.events
        result = object()

        class Opaque:
            @property
            def __signature__(self):
                message = "host value calls may not inspect signatures"
                raise AssertionError(message)

            def __call__(self, left, *, right):
                events.append(("call", left, right))
                return result

        left, right, positional, keywords = self.frames()
        home = Symbol("Home")
        actual = self.namespace["apply_host_value"](home, Grounded(Opaque()), positional, keywords)
        self.assertIs(actual.value, result)
        # The operands cross as the twin's values and the callable is the held
        # object itself; nothing passes through build.
        self.assertEqual(self.events, [("call", left, right)])

    def test_successful_results_keep_their_existing_image_policy(self):
        """Explicit images win and ordinary results remain exact held objects."""
        returned = self.namespace["returned"]
        for value in (None, False, [], {}, object(), Symbol("Error"), Expression([])):
            with self.subTest(kind=type(value).__name__):
                self.assertIs(returned(value).value, value)
        # A raw tuple is not held by identity: it reaches hold, whose real
        # implementation spells it as the expression pythonic reads it from.
        self.namespace["hold"] = lambda value: ("held", value)
        try:
            self.assertEqual(returned((1, 2)), ("held", (1, 2)))
        finally:
            self.namespace["hold"] = Grounded
        value = object()
        image = Expression([Symbol("Declared"), Grounded(3)])
        self.images[id(value)] = image
        self.assertIs(returned(value), image)

    def test_host_generator_and_coroutine_creation_does_not_start_or_replace_them(self):
        """Creation returns the original deferred object without advancing it."""
        def generator():
            self.events.append("started generator")
            yield 1

        async def coroutine():
            self.events.append("started coroutine")
            return 2

        for source in (generator, coroutine):
            value = source()
            try:
                result = self.namespace["apply_host_value"](
                    Symbol("Home"), Grounded(lambda value=value: value), Expression([]), Expression([]))
                self.assertIs(result.value, value)
                self.assertFalse(any(isinstance(event, str) for event in self.events))
            finally:
                value.close()

    def test_host_exceptions_propagate_as_the_original_instance(self):
        """A host failure remains an exception through the source boundary."""
        failure = RuntimeError("call-value witness")

        def fails():
            raise failure

        with self.assertRaises(RuntimeError) as caught:
            self.namespace["apply_host_value"](Symbol("Home"), Grounded(fails), Expression([]), Expression([]))
        self.assertIs(caught.exception, failure)

    def test_a_one_answer_native_binding_is_observed_through_eval_one(self):
        """The binder wraps a one-answer application; a stream application stays bare."""
        application = Symbol("Application")
        shapes = []

        class Native:
            space = Symbol("NativeHome")

            def application(self, _arguments, _keywords, **_flags):
                return application, inspect.Signature(), shapes.pop()

        self.native = Native()
        shapes.append(False)
        wrapped = self.namespace["bind_value"](Symbol("Caller"), Symbol("Native"), Expression([]), Expression([]))
        self.assertEqual(_shape(wrapped), ("eval-one", ("evalc", "Application", "NativeHome")))
        shapes.append(True)
        bare = self.namespace["bind_value"](Symbol("Caller"), Symbol("Native"), Expression([]), Expression([]))
        self.assertEqual(_shape(bare), ("evalc", "Application", "NativeHome"))

    def test_native_binding_reuses_the_current_application_and_lexical_home(self):
        """The current native applicator owns source and its lexical home."""
        application, native_home = Symbol("Application"), Symbol("NativeHome")
        calls = []

        class Native:
            space = native_home

            def application(self, arguments, keywords, *, written=True):
                calls.append((arguments, keywords, written))
                return application, inspect.Signature(), True

        self.native = Native()
        _left, _right, positional, keywords = self.frames()
        result = self.namespace["bind_value"](Symbol("Caller"), Symbol("Native"), positional, keywords)
        self.assertEqual(_shape(result), ("evalc", "Application", "NativeHome"))
        self.assertIs(calls[0][0], positional.children)
        self.assertIs(calls[0][1]["right"], keywords.children[0].children[1])
        self.assertEqual(self.events, [])
        self.native = None
        with self.assertRaisesRegex(TypeError, "no native callable image"):
            self.namespace["bind_value"](Symbol("Caller"), Symbol("Absent"), positional, keywords)

    def test_keyword_validation_is_shared_with_canonical_binding(self):
        """Both consumers reject malformed frames before any body executes."""
        signature = inspect.Signature([inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD)])
        pairs = Expression([Expression([Grounded("b"), Grounded(2)]), Expression([Grounded("a"), Grounded(1)])])
        bound = self.namespace["bind_arguments"](signature, Expression([]), pairs)
        self.assertEqual(tuple(bound.arguments["options"]), ("b", "a"))
        invalid = (
            (Grounded(()), Expression([])),
            (Expression([]), Grounded({})),
            (Expression([]), Expression([Grounded(3)])),
            (Expression([]), Expression([Expression([Grounded("name")])])),
            (Expression([]), Expression([Expression([Symbol("name"), Grounded(2)])])),
            (Expression([]), Expression([Expression([Grounded(3), Grounded(2)])])),
            (Expression([]), Expression([Expression([Grounded("a"), Grounded(1)]),
                                         Expression([Grounded("a"), Grounded(2)])])),
        )
        for positional, keywords in invalid:
            with self.subTest(positional=positional, keywords=keywords), self.assertRaises(TypeError):
                self.namespace["bind_arguments"](signature, positional, keywords)
            with self.assertRaises(TypeError):
                self.namespace["bind_value"](Symbol("Home"), Grounded(object()), positional, keywords)
        self.assertEqual(self.events, [])

    def test_equation_holds_four_inputs_and_returns_the_observed_value(self):
        """The emitted equation observes one value outside any function frame and returns it without a wrapper."""
        declarations = self.namespace["value_declarations"]()
        self.assertEqual(_shape(declarations[0]), (":", "_python-call-value", ("->", *("Atom",) * 4, "%Undefined%")))
        self.assertEqual(_shape(declarations[1]), (
            "=", ("_python-call-value", "$call-home", "$call-function", "$call-positionals", "$call-keywords"),
            ("let", "$call-source",
                ("_python-bind-call-value", "$call-home", "$call-function", "$call-positionals", "$call-keywords"),
                ("evalc", "$call-source", "$call-home")),
        ))
        self.assertEqual(_shape(declarations[2]), ("internal", "_python-call-value"))


if __name__ == "__main__":
    unittest.main()
