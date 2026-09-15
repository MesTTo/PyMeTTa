"""Purpose: check the shared call-consumer domain without starting a runtime.

The actual validator prefix runs with inert values. Its source boundary and
the compiler annotations retain the same two consumption forms. These tests
do not claim native evaluation or argument-transport coverage.
"""

from __future__ import annotations

import ast
import types
import unittest
from pathlib import Path
from typing import Any, Literal, get_args

ROOT = Path(__file__).resolve().parents[2]


def _tree(relative: str) -> ast.Module:
    return ast.parse((ROOT / relative).read_text(encoding="utf-8"))


def _domain():
    tree = _tree("metta/_catalog/call_values.py")
    alias, = (node for node in tree.body if isinstance(node, ast.TypeAlias) and node.name.id == "CallConsumer")
    namespace = {"Literal": Literal}
    exec(compile(ast.Module(body=[alias], type_ignores=[]), "<call-consumer>", "exec"), namespace)
    return namespace["CallConsumer"]


class _Grounded:
    def __init__(self, value):
        self.value = value


def _validator(alias):
    tree = _tree("metta/_declare/call_syntax.py")
    function, = (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "bind_call")
    # Keep the argument checks, stopping before native or host application.
    prefix = []
    for statement in function.body:
        if isinstance(statement, ast.Assign):
            break
        prefix.append(statement)
    prefix.append(ast.Return(value=ast.Constant(value=True)))
    function.body = prefix
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, function], type_ignores=[]))
    namespace = {"Grounded": _Grounded, "Expression": tuple, "get_args": get_args,
                 "call_values": types.SimpleNamespace(CallConsumer=alias)}
    exec(compile(module, "<call-consumer-validator>", "exec"), namespace)
    return namespace["bind_call"]


class CallConsumerSourceTests(unittest.TestCase):
    """Check admitted words, compiler contracts and source-derived validation."""

    def test_consumers_describe_application_and_iteration(self):
        """Use a result-consumption domain independent of refusal kinds."""
        self.assertEqual(get_args(_domain().__value__), ("value", "iterable"))

    def test_compiler_signatures_share_the_domain(self):
        """Both call builders retain the same default and the shared type."""
        tree = _tree("metta/_compile/call_syntax.py")
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        for name in ("bound_application", "application"):
            with self.subTest(name=name):
                function = functions[name]
                parameter, = (argument for argument in function.args.kwonlyargs if argument.arg == "consumer")
                self.assertEqual(ast.unparse(parameter.annotation), "CallConsumer")
                index = function.args.kwonlyargs.index(parameter)
                self.assertEqual(ast.literal_eval(function.args.kw_defaults[index]), "value")

    def test_validator_accepts_exactly_the_consumption_words(self):
        """Preserve supported strings and reject unrelated refusal values."""
        validate = _validator(_domain())
        for word in get_args(_domain().__value__):
            with self.subTest(word=word):
                self.assertTrue(validate(None, None, (), _Grounded({}), _Grounded(word)))
        for value in ("type", "syntax", "stream", "", None, False, (), "value "):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "value or iterable consumer"):
                validate(None, None, (), _Grounded({}), _Grounded(value))
        with self.assertRaisesRegex(TypeError, "value or iterable consumer"):
            validate(None, None, (), _Grounded({}), "value")

    def test_validator_follows_the_alias_instead_of_a_second_list(self):
        """A changed source domain changes acceptance without editing a validator."""
        namespace: dict[str, Any] = {"Literal": Literal}
        exec("type ProbeConsumer = Literal['probe']", namespace)
        validate = _validator(namespace["ProbeConsumer"])
        self.assertTrue(validate(None, None, (), _Grounded({}), _Grounded("probe")))
        with self.assertRaisesRegex(TypeError, "value or iterable consumer"):
            validate(None, None, (), _Grounded({}), _Grounded("value"))


if __name__ == "__main__":
    unittest.main()
