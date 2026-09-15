"""Purpose: discriminate source joins and generated protocol projections.

Guarantees: controls check semantic identities and rejection, including
guarded bodies, alias replacement, optional arity and runtime export drift
[source: extensions/python/tools/protocolgen.py:operator_rows;
commit=WORKTREE]. These controls import no PeTTa runtime.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import inspect
import operator
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
TOOLS = ROOT / "extensions/python/tools"
sys.path.insert(0, str(TOOLS))

import protocolgen  # noqa: E402 -- the source generator is a checkout tool


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {name: module}):
        spec.loader.exec_module(module)
    return module


class ProtocolProjectionTests(unittest.TestCase):
    """Source controls remain runnable through unittest before engine loading."""

    @classmethod
    def setUpClass(cls):
        """Load the locked inventory and the checked-in generated grammar."""
        cls.data = protocolgen.inventory()
        cls.rows = _module("protocol_projection_rows", ROOT / protocolgen.ROW_PATH)
        cls.programs = _module("protocol_projection_programs", ROOT / protocolgen.TWIN_PATH)

    def test_generated_files_match_source_and_preserve_all_records(self):
        """Every source record and required identity survives generation."""
        for path, wanted in protocolgen.projections(ROOT).items():
            self.assertEqual(path.read_text(encoding="utf-8"), wanted, str(path))
        for key in ("members", "callables", "forms", "sources"):
            self.assertEqual(len(getattr(self.rows, key.upper())), len(self.data[key]), key)
        for key, required in self.data["required"].items():
            self.assertEqual(self.rows.REQUIRED[key], tuple(map(tuple, required)))
        for source in self.rows.SOURCES:
            self.assertTrue(source.full_sha256)
            self.assertTrue(source.segments)
            self.assertTrue(all(segment.bytes > 0 for segment in source.segments))
        with self.assertRaises(TypeError):
            self.rows.BY_OPERATOR["object", "__add__"] = None

    def test_alias_and_slot_joins_do_not_confuse_guarded_bodies(self):
        """Reflected and in-place links come from roles and direct source forms."""
        add = self.rows.BY_OPERATOR["object", "__add__"]
        self.assertEqual((add.callable, add.reflected, add.inplace),
                         (("operator", "add"), ("object", "__radd__"), ("operator", "iadd")))
        for name in ("concat", "iconcat"):
            form = self.rows.BY_FORM["operator", name]
            self.assertFalse(form.direct)
            self.assertEqual(form.kind, "Function")
            self.assertIn("hasattr", form.body)
        self.assertEqual(self.rows.BY_FORM["operator", "contains"].operands, ("b", "a"))
        self.assertEqual(self.rows.BY_FORM["operator", "setitem"].operands, ("c", "a", "b"))
        self.assertEqual(self.rows.BY_CALLABLE["operator", "__invert__"].alias_of,
                         ("operator", "invert"))
        self.assertIsNone(self.rows.BY_CALLABLE["operator", "invert"].alias_of)
        self.assertIsNone(self.rows.BY_CALLABLE["operator", "inv"].alias_of)
        self.assertEqual(self.rows.BY_OPERATOR["object", "__and__"].selector, "and")

    def test_ambiguous_reflected_and_inplace_links_fail(self):
        """A second source candidate must fail instead of taking the first row."""
        for member, field, value, message in (
                ("__rsub__", "c_member", "nb_add", "ambiguous reflected"),
                ("__isub__", "node", "Add", "ambiguous in-place")):
            changed = copy.deepcopy(self.data)
            if field == "c_member":
                row = next(row for row in changed["members"] if row["id"] == ["object", member])
                row["slots"][0][field] = value
            else:
                for form in changed["forms"]:
                    if form["callable"] in (["operator", "isub"], ["operator", member]):
                        form[field] = value
            with self.assertRaisesRegex(ValueError, message):
                protocolgen.operator_rows(changed)

    def test_callable_shapes_follow_inspect_and_keep_optional_and_unbounded_forms(self):
        """The generated predicate recognizes the source contract, not ABI arity."""
        for row in self.rows.CALLABLES:
            if row.id[0] != "operator" or row.id[1] not in vars(operator):
                continue
            signature = inspect.signature(vars(operator)[row.id[1]])
            boundary = row.min_positional + 3 if row.max_positional is None else row.max_positional + 1
            for count in range(boundary + 1):
                try:
                    signature.bind(*([None] * count))
                except TypeError:
                    expected = False
                else:
                    expected = True
                self.assertEqual(row.accepts_positional(count), expected, (row.id, count))
        self.assertTrue(self.rows.BY_CALLABLE["operator", "call"].accepts_positional(100))
        self.assertTrue(self.rows.BY_CALLABLE["builtins", "round"].accepts_positional(2))
        self.assertEqual(self.rows.BY_OPERATOR["object", "__round__"].arity, 1)
        self.assertEqual(self.rows.BY_CALLABLE["math", "log"].parameters, None)
        self.assertTrue(self.rows.BY_CALLABLE["math", "log"].accepts_positional(2))

    def test_runtime_bindings_intersect_exports_and_preserve_exact_identity(self):
        """A source-only future export neither imports nor acquires a selector."""
        name = "future_protocol_export"
        row = self.rows.BY_CALLABLE["operator", "call"]._replace(id=("operator", name), selector=name)
        generated = types.ModuleType("metta._atoms._python_protocols")
        generated.__dict__.update(vars(self.rows))
        generated.CALLABLES = (*self.rows.CALLABLES, row)
        # Execute only the engine-free policy and bindings with local module
        # entries, keeping a live seat's imported modules intact.
        modules = {"metta": types.ModuleType("metta"),
                   "metta._atoms": types.ModuleType("metta._atoms"),
                   "metta._atoms._python_protocols": generated}
        with patch.dict(sys.modules, modules):
            policies = _module("metta._atoms.operators", ROOT / "extensions/python/metta/_atoms/operators.py")
            with patch.dict(sys.modules, {"metta._atoms.operators": policies}):
                bindings = _module("protocol_projection_bindings", ROOT / "extensions/python/metta/_atoms/mentions.py")
        self.assertNotIn(name, bindings.OPERATOR_CALLABLES)
        for selector, value in bindings.OPERATOR_CALLABLES.items():
            self.assertIs(bindings.OPERATOR_CALLABLES[bindings.operator_callable_selector(value)], value,
                          selector)
        self.assertIs(bindings.OPERATOR_CALLABLES["inv"], operator.inv)
        self.assertIs(bindings.OPERATOR_CALLABLES["invert"], operator.invert)
        self.assertIsNone(bindings.operator_callable_selector(lambda: None))

    def test_generated_programs_cover_source_shapes_and_observe_exceptions(self):
        """Generated executable bodies preserve direct syntax and exact calls."""
        available = {row.id for row in self.rows.CALLABLES if row.id[0] == "operator"
                     and not row.id[1].startswith("__")}
        self.assertEqual({identity for identity, _, _ in self.programs.CALL_PROGRAMS}, available)
        self.assertEqual({identity for identity, _, _ in self.programs.ALIAS_PROGRAMS}, available)
        for identity, _, alias in self.programs.ALIAS_PROGRAMS:
            call = next(node for node in ast.walk(ast.parse(inspect.getsource(alias)))
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id.startswith("_protocol_binding_"))
            self.assertIs(alias.__globals__[call.func.id], vars(operator).get(identity[1]))
        functions = {function.__name__: function for _, _, function in self.programs.CALL_PROGRAMS}
        observed = functions["protocol_exact_concat_2"](1, 2)
        self.assertEqual(observed[0:2], ("raise", "TypeError"))
        self.assertIn("concat", observed[2])
        operands = (lambda *values: values, False, 0)
        self.assertEqual(functions["protocol_exact_call_3"](*operands),
                         ("return", (False, 0)))
        for _, kind, _, syntax, _ in self.programs.PROGRAMS:
            tree = ast.parse(inspect.getsource(syntax))
            self.assertTrue(any(type(node).__name__ == kind for node in ast.walk(tree)), syntax.__name__)
        with self.assertRaisesRegex(ValueError, "one final source return"):
            protocolgen._observed_function("guarded", ["a"], "if a:\n    return 1\nreturn 2")

    def test_unjoined_policy_and_stale_generated_output_fail(self):
        """Policy drift and changed output bytes fail through the public check."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / "extensions/python/metta/_atoms/operators.py"
            policy.parent.mkdir(parents=True)
            policy.write_text('_POLICIES: object = MappingProxyType({"__unclassified__": None})\n',
                              encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing or repeated source members"):
                protocolgen._validate_policy_sources(self.data, root)
            policy.write_text("unrelated = {}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "one literal mapping"):
                protocolgen._validate_policy_sources(self.data, root)
            output = root / "generated.py"
            output.write_text("value = 0\n", encoding="utf-8")
            with patch.object(protocolgen, "ROOT", root), patch.object(
                    protocolgen, "projections", return_value={output: "value = 1\n"}):
                self.assertEqual(protocolgen.main([]), 1)
                self.assertEqual(protocolgen.main(["--write"]), 0)
                self.assertEqual(output.read_text(encoding="utf-8"), "value = 1\n")
                self.assertEqual(protocolgen.main([]), 0)


if __name__ == "__main__":
    unittest.main()
