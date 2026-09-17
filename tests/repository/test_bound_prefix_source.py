"""Purpose: compare native positional-prefix projection with CPython signatures.

The isolated helper module is extracted from the actual consumer source;
these tests import no native package or bridge and execute no native body.
"""

from __future__ import annotations

import ast
import functools
import inspect
import itertools
import types
import unittest
from collections.abc import Collection
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "metta/_catalog/call_values.py"


def _source_projection():
    """Load the actual two projection helpers without importing the package."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in {"_uncaptured", "_positional_signature"}]
    namespace = {"inspect": inspect, "Collection": Collection}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


PROJECTION = _source_projection()


def _signatures():
    """Exercise the product of positional, variadic and keyword parameter kinds."""
    parameter = inspect.Parameter
    for only, ordinary, variadic, named, keywords in itertools.product(range(3), range(3), (False, True), range(3), (False, True)):
        positional = only + ordinary
        for defaults in range(positional + 1):
            parameters = [parameter(f"p{index}", parameter.POSITIONAL_ONLY if index < only else parameter.POSITIONAL_OR_KEYWORD,
                                    default=index if index >= positional - defaults else parameter.empty)
                          for index in range(positional)]
            if variadic:
                parameters.append(parameter("items", parameter.VAR_POSITIONAL))
            parameters.extend(parameter(f"k{index}", parameter.KEYWORD_ONLY, default=index or parameter.empty)
                              for index in range(named))
            if keywords:
                parameters.append(parameter("options", parameter.VAR_KEYWORD))
            yield inspect.Signature(parameters, return_annotation=int)


def _described(signature):
    """Give inspect its ordinary explicit signature metadata."""
    def function(*args, **kwargs):
        return args, kwargs

    function.__signature__ = signature
    return function


class BoundPrefixSourceTests(unittest.TestCase):
    """Observe CPython's public projection and canonical call-binding domains."""

    def test_every_positional_prefix_matches_partial_signature(self):
        """The same canonical signature accepts exactly the same prefix lengths."""
        project = PROJECTION["_positional_signature"]
        for signature in _signatures():
            function = _described(signature)
            for captured in range(7):
                with self.subTest(signature=str(signature), captured=captured):
                    partial = functools.partial(function, *range(captured))
                    try:
                        expected = inspect.signature(partial)
                    except ValueError:
                        with self.assertRaises(ValueError):
                            project(signature, captured, (), ValueError)
                    else:
                        self.assertEqual(project(signature, captured, (), ValueError), expected)

    def test_descriptor_projection_matches_method_type(self):
        """Receiver injection keeps *args and refuses impossible public signatures."""
        project = PROJECTION["_positional_signature"]
        for signature in _signatures():
            function = types.MethodType(_described(signature), object())
            with self.subTest(signature=str(signature)):
                try:
                    expected = inspect.signature(function)
                except ValueError as error:
                    with self.assertRaises(ValueError) as refused:
                        project(signature, 1, (), ValueError)
                    self.assertEqual(str(refused.exception), str(error))
                else:
                    self.assertEqual(project(signature, 1, (), ValueError), expected)

    def test_call_binding_matches_the_canonical_supplied_prefix(self):
        """No signature projection changes the legal call domain or keyword rule."""
        project = PROJECTION["_positional_signature"]
        calls = (((), {}), ((9,), {}), ((9, 10, 11), {}),
                 ((), {"p0": 4}), ((), {"k0": 5}), ((), {"extra": 6}),
                 ((9,), {"p0": 4, "k0": 5, "extra": 6}))
        for signature in _signatures():
            for captured in (0, 1, 2, 5):
                for arguments, keywords in calls:
                    with self.subTest(signature=str(signature), captured=captured, arguments=arguments, keywords=keywords):
                        try:
                            signature.bind(*range(captured), *arguments, **keywords)
                        except TypeError:
                            with self.assertRaises(TypeError):
                                remaining = project(signature, captured, keywords, TypeError)
                                remaining.bind(*arguments, **keywords)
                        else:
                            remaining = project(signature, captured, keywords, TypeError)
                            remaining.bind(*arguments, **keywords)

    def test_variadic_prefix_work_is_independent_of_the_number_of_values(self):
        """An arbitrary prefix count does not allocate one object per capture."""
        signature = inspect.Signature([inspect.Parameter("items", inspect.Parameter.VAR_POSITIONAL)])
        self.assertEqual(PROJECTION["_positional_signature"](signature, 10**100, (), ValueError), signature)

    def test_formal_slot_capture_remains_distinct(self):
        """A native captured collector is one complete stored formal value."""
        signature = inspect.Signature([
            inspect.Parameter("items", inspect.Parameter.VAR_POSITIONAL),
            inspect.Parameter("flag", inspect.Parameter.KEYWORD_ONLY, default=3),
        ])
        formal = PROJECTION["_uncaptured"](signature, 1, ())
        positional = PROJECTION["_positional_signature"](signature, 1, (), ValueError)
        self.assertEqual(tuple(formal.parameters), ("flag",))
        self.assertEqual(positional, signature)

    def test_invalid_metadata_is_not_an_inspection_refusal(self):
        """Malformed counts keep TypeError at both observation boundaries."""
        signature = inspect.Signature()
        for count in (-1, 0.5, "1", None):
            for refusal in (ValueError, TypeError):
                with self.subTest(count=count, refusal=refusal), self.assertRaises(TypeError):
                    PROJECTION["_positional_signature"](signature, count, (), refusal)


if __name__ == "__main__":
    unittest.main()
