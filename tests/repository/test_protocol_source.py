"""Exercise locked source extraction without importing the Python seat.

Purpose: guard exact inventory coverage, source contracts and parser rejection.
Assumes: the adjacent protocol_source.py and protocol_sources inputs are present.
Guarantees: missing continuations, slot roles, aliases, arities and required
    identities fail independently of row counts; source bytes are checked first.
[source: extensions/python/tools/protocol_source.py:validate_inventory; commit=WORKTREE]
"""
from __future__ import annotations

import copy
import importlib
import importlib.util
import inspect
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools"
SPEC = importlib.util.spec_from_file_location("protocol_source", TOOLS / "protocol_source.py")
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)


class ProtocolSourceTests(unittest.TestCase):
    """Check source parsing, exact completeness and pinned live contracts."""

    @classmethod
    def setUpClass(cls):
        """Read the source inventory once for independent mutation controls."""
        cls.data = SOURCE.inventory()
        cls.sources = SOURCE.Sources()
        cls.members = {tuple(row["id"]): row for row in cls.data["members"]}
        cls.callables = {tuple(row["id"]): row for row in cls.data["callables"]}
        cls.forms = {tuple(row["callable"]): row for row in cls.data["forms"]}

    def reject(self, mutate, message):
        """Require an altered inventory to name its changed source fact."""
        data = copy.deepcopy(self.data)
        mutate(data)
        with self.assertRaisesRegex(ValueError, message):
            SOURCE.validate_inventory(data)

    def test_round_trip_and_source_scope(self):
        """Preserve exact source membership and the required reference scope."""
        SOURCE.validate_inventory(json.loads(json.dumps(self.data)))
        self.assertEqual(sum(len(row["slots"]) for row in self.data["members"]), 94)
        required = set(map(tuple, self.data["required"]["reference"]))
        self.assertIn(("object", "__le__"), required)
        self.assertNotIn(("type", "__qualname__"), required)
        self.assertIn(("type", "__qualname__"), self.members)
        self.assertIn(["type", "__qualname__"], self.data["required"]["journal_members"])
        self.assertIn(["typing", "runtime_checkable"], self.data["required"]["journal_apis"])

    def test_directive_continuation_and_nested_table_parser(self):
        """Read continued signatures and directives nested in list tables."""
        text = ".. method:: object.__lt__(self, other)\n            object.__le__(self, other)\n\n   * - .. attribute:: type.__qualname__\n"
        self.assertEqual(list(SOURCE._directives(text)), [(("object", "__lt__"), 1), (("object", "__le__"), 2), (("type", "__qualname__"), 4)])
        altered = text.replace("            object.__le__(self, other)\n", "")
        self.assertNotEqual(list(SOURCE._directives(text)), list(SOURCE._directives(altered)))

    def test_reference_loss_and_same_count_substitution_fail(self):
        """Reject missing identities even when a replacement preserves counts."""
        def remove(data):
            data["required"]["reference"].remove(["object", "__le__"])
        self.reject(remove, "required.reference")
        def replace(data):
            rows = data["required"]["reference"]
            rows[rows.index(["object", "__le__"])] = ["object", "__not_a_protocol__"]
        self.reject(replace, "required.reference")

    def test_reflected_role_alias_and_arity_mutations_fail(self):
        """Reject altered dispatch roles, source aliases and callable bounds."""
        def role(data):
            row = next(m for m in data["members"] if m["id"] == ["object", "__radd__"])
            row["slots"][0]["role"] = "left"
        self.reject(role, "role")
        def alias(data):
            row = next(c for c in data["callables"] if c["id"] == ["operator", "__add__"])
            row["alias_of"] = ["operator", "sub"]
        self.reject(alias, "alias_of")
        def arity(data):
            row = next(c for c in data["callables"] if c["id"] == ["math", "log"])
            row["max_positional"] = 1
        self.reject(arity, "max_positional")

    def test_unclassified_requirement_fails(self):
        """Require every added journal API or hook to have source membership."""
        self.reject(lambda data: data["required"]["journal_members"].append(["object", "__unclassified__"]), "journal_members")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sources"
            shutil.copytree(self.sources.root, root)
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["required_apis"].append(["typing", "unclassified_api"])
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "unclassified required APIs"):
                SOURCE.inventory(root)

    def test_locked_bytes_and_complete_packs_fail_closed(self):
        """Reject changed excerpts and trailing bytes outside manifest spans."""
        for suffix in (b"changed", b"\n"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "sources"
                shutil.copytree(self.sources.root, root)
                path = root / self.sources.records["cpython.operator"]["segments"][0]["path"]
                if suffix == b"changed":
                    raw = path.read_bytes().replace(b"__add__ = add", b"__add__ = sub")
                    path.write_bytes(raw)
                else:
                    path.write_bytes(path.read_bytes() + suffix)
                with self.assertRaisesRegex(ValueError, "source hash mismatch|unaccounted packed bytes"):
                    SOURCE.inventory(root)

    def test_unknown_macro_and_alias_cycle_fail(self):
        """Reject unsupported macro applications and recursive source aliases."""
        self.assertEqual(SOURCE._expand(["EMPTY", "(", ")"], SOURCE._macros("#define EMPTY() {}\n")), ["{", "}"])
        with self.assertRaisesRegex(ValueError, "recursive C macro"):
            SOURCE._expand(["A"], {"A": (None, ["B"]), "B": (None, ["A"])})
        with self.assertRaisesRegex(ValueError, "C macro arity changed"):
            SOURCE._expand(["A", "(", "x", ",", "y", ")"], {"A": (["one"], ["one"])})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sources"
            shutil.copytree(self.sources.root, root)
            manifest = json.loads((root / "manifest.json").read_text())
            record = next(r for r in manifest["sources"] if r["id"] == "cpython.operator")
            segment = record["segments"][0]
            path = root / segment["path"]
            raw = path.read_bytes().replace(b"invert = inv", b"invert = invert")
            path.write_bytes(raw)
            segment["sha256"], segment["bytes"] = SOURCE._digest(raw), len(raw)
            record["full_sha256"], record["full_bytes"] = SOURCE._digest(raw), len(raw)
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "cyclic Python alias"):
                SOURCE.inventory(root)

    def test_unclassified_source_slot_shape_fails(self):
        """Require every parsed slot macro and numeric role to be classified."""
        sources = SOURCE.Sources()
        key = sources.manifest["slots"]
        original = sources.texts[key]
        sources.texts[key] = original.replace("wrap_binaryfunc_r", "wrap_binaryfunc_unclassified")
        with self.assertRaisesRegex(ValueError, "unclassified numeric slot roles"):
            SOURCE._slot_rows(sources)
        sources.texts[key] = original.replace("BINSLOT(__add__", "UNKNOWNSLOT(__add__")
        with self.assertRaisesRegex(ValueError, "unrecognized slot row"):
            SOURCE._slot_rows(sources)

    def test_callable_and_syntax_arities_remain_distinct(self):
        """Keep complete call contracts separate from syntax operand shapes."""
        self.assertEqual(self.callables["builtins", "round"]["min_positional"], 1)
        self.assertEqual(self.callables["builtins", "round"]["max_positional"], 2)
        self.assertEqual(self.callables["operator", "pow"]["max_positional"], 2)
        self.assertEqual(self.callables["builtins", "pow"]["max_positional"], 3)
        self.assertIsNone(self.callables["operator", "call"]["max_positional"])
        log = self.callables["math", "log"]
        self.assertIsNone(log["signature"])
        self.assertIsNone(log["parameters"])
        self.assertEqual((log["min_positional"], log["max_positional"], log["accepts_keywords"]), (1, 2, False))
        self.assertEqual(self.forms["operator", "contains"]["operands"], ["b", "a"])
        self.assertEqual(self.forms["operator", "setitem"]["operands"], ["c", "a", "b"])
        self.assertEqual(self.forms["operator", "iadd"]["result"], "target")
        for name in ("concat", "iconcat", "call"):
            self.assertFalse(self.forms["operator", name]["direct"])
            self.assertEqual(self.forms["operator", name]["kind"], "Function")
        self.assertIn("hasattr", self.forms["operator", "concat"]["body"])
        self.assertIn("hasattr", self.forms["operator", "iconcat"]["body"])

    def test_refresh_rejects_revision_and_existing_destination(self):
        """Refuse a different source pin or an already published destination."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "revision differs"):
                SOURCE.refresh(Path(directory), "not-the-pin", Path(directory) / "new")
            with self.assertRaisesRegex(ValueError, "already exists"):
                SOURCE.refresh(Path(directory), self.data["source_revision"], Path(directory))

    def test_refresh_checks_full_source_before_publishing(self):
        """Reject a corrupt upstream file before creating the destination."""
        revision = self.data["source_revision"]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "new"
            first = next(r for r in self.data["sources"] if r["revision"] == revision)
            source_file = Path(directory) / first["path"]
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_bytes(b"incorrect full source\n")
            with self.assertRaisesRegex(ValueError, "full source hash mismatch"):
                SOURCE.refresh(Path(directory), revision, destination)
            self.assertFalse(destination.exists())

    @unittest.skipUnless(sys.version_info[:3] == (3, 14, 4), "live oracle requires the locked CPython 3.14.4")
    def test_active_stdlib_signatures_and_alias_identities(self):
        """Compare available signatures and exact aliases with pinned CPython."""
        for row in self.data["callables"]:
            module, name = row["id"]
            with self.subTest(module=module, name=name):
                value = getattr(importlib.import_module(module), name)
                if row["alias_of"]:
                    owner, alias = row["alias_of"]
                    self.assertIs(value, getattr(importlib.import_module(owner), alias))
                try:
                    signature = inspect.signature(value)
                except (TypeError, ValueError):
                    self.assertTrue(row["signature"] is None or "<unrepresentable>" in row["signature"],
                                    f"unexplained unavailable live signature: {module}.{name}")
                    continue
                parameters = list(signature.parameters.values())
                positional = [p for p in parameters if p.kind in {p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD}]
                minimum = sum(p.default is p.empty for p in positional)
                maximum = None if any(p.kind is p.VAR_POSITIONAL for p in parameters) else len(positional)
                self.assertEqual((row["min_positional"], row["max_positional"]), (minimum, maximum))
                if row["parameters"] is not None:
                    self.assertEqual([(p["name"], p["kind"]) for p in row["parameters"]], [(p.name, p.kind.name) for p in parameters])
        operator = importlib.import_module("operator")
        self.assertIsNot(operator.inv, operator.invert)
        self.assertIsNone(self.callables["operator", "invert"]["alias_of"])
        self.assertEqual(self.callables["operator", "__invert__"]["alias_of"], ["operator", "invert"])

    def test_direct_source_forms_match_operator_calls(self):
        """Compare source syntax with the corresponding stdlib operation."""
        operator = importlib.import_module("operator")
        class Matrix(int):
            def __matmul__(self, other):
                return int(self) * other

            def __imatmul__(self, other):
                return int(self) * other + 1

        for row in self.data["forms"]:
            if not row["direct"]:
                continue
            name = row["callable"][1]
            if not hasattr(operator, name):
                continue
            with self.subTest(name=name):
                values = {"a": 6, "b": 2, "c": 99}
                if row["node"] == "MatMult":
                    values["a"] = Matrix(6)
                if row["kind"] in {"Subscript", "Assign", "Delete"} or row["node"] == "In":
                    values.update(a=[10, 20, 30], b=1)
                expected_values = copy.deepcopy(values)
                arguments = [expected_values[p] for p in row["parameters"]]
                try:
                    value = getattr(operator, name)(*arguments)
                    if row["result"] == "target":
                        expected_values[row["parameters"][0]] = value
                    expected = ("value", value, expected_values)
                except Exception as error:
                    expected = ("error", type(error))
                scope = {**values, "_abs": abs}
                try:
                    if row["result"] == "value":
                        value = eval(row["syntax"], scope)
                    else:
                        exec(row["syntax"], scope)
                        value = scope[row["parameters"][0]] if row["result"] == "target" else None
                    actual = ("value", value, {key: scope[key] for key in values})
                except Exception as error:
                    actual = ("error", type(error))
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
