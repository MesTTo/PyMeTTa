"""Purpose: project locked Python protocol facts into runtime rows and twins.

Assumes: protocol_source validates the exact source inventory and provenance.
Guarantees: reflected partners join through C slot roles, in-place partners
join through direct AST forms and their slot role, and guarded source bodies
cannot become an unconditional syntax operation [source:
extensions/python/tools/protocol_source.py:inventory; commit=WORKTREE].
Fails when: source links are ambiguous, a policy has no source operation, or a
generated artifact differs. Generation uses local locked inputs and no engine.
Decides: generated records are immutable; MeTTa meaning choices remain in
metta/_atoms/operators.py. Differential functions are generated per source
shape and evaluated by the existing twin runner.
"""

from __future__ import annotations

import argparse
import ast
import keyword
from collections import defaultdict
from pathlib import Path
from textwrap import indent

from artifacts import notice
from protocol_source import inventory, validate_inventory

ROOT = Path(__file__).resolve().parents[3]
ROW_PATH = "extensions/python/metta/_atoms/_python_protocols.py"
TWIN_PATH = "extensions/python/tests/ch11_python_as_a_notation/_protocol_programs.py"


def _word(name: str) -> str:
    """Normalize the public keyword escape without guessing a callable name."""
    return name[:-1] if name.endswith("_") and keyword.iskeyword(name[:-1]) else name


def _identity(value):
    return tuple(value) if value is not None else None


def _source_form(row, forms):
    return forms.get(tuple(row["source_function"])) or forms.get(tuple(row["id"]))


def operator_rows(data: dict) -> list[dict]:
    """Join callable aliases, slot roles and direct syntax without name rules."""
    members = {tuple(row["id"]): row for row in data["members"]}
    callables = {tuple(row["id"]): row for row in data["callables"]}
    forms = {tuple(row["callable"]): row for row in data["forms"]}
    candidates = defaultdict(list)
    reflected = defaultdict(set)
    inplace = defaultdict(set)
    for member, row in members.items():
        for slot in row["slots"]:
            if slot["role"] == "reflected":
                reflected[(slot["family"], slot["c_member"])].add(member)
    for row in callables.values():
        member = _identity(row["member"])
        if member is None:
            continue
        candidates[member].append(row)
        form = _source_form(row, forms)
        if (form is not None and form["direct"] and form["kind"] == "AugAssign"
                and any(slot["role"] == "inplace" for slot in members[member]["slots"])):
            target = _identity(row["alias_of"]) if row["id"][1] == member[1] else tuple(row["id"])
            if target is not None and not target[1].startswith("__"):
                inplace[form["node"]].add(target)
    output = []
    for member, choices in sorted(candidates.items()):
        aliases = [row for row in choices if row["id"] == ["operator", member[1]]]
        if aliases:
            target = tuple(aliases[0]["alias_of"])
        else:
            public = {tuple(row["id"]) for row in choices if row["alias_of"] is None}
            if len(public) != 1:
                # A member used by several APIs has no unique source operation.
                # Its complete callable and slot rows remain in the inventory.
                continue
            target = public.pop()
        row = callables[target]
        form = _source_form(row, forms)
        partners = set()
        for slot in members[member]["slots"]:
            if slot["role"] == "left":
                partners.update(reflected[(slot["family"], slot["c_member"])])
        if len(partners) > 1:
            message = f"ambiguous reflected source partners for {member}: {sorted(partners)}"
            raise ValueError(message)
        augmentations = (inplace[form["node"]]
                         if form is not None and form["direct"] and form["kind"] == "BinOp" else set())
        if len(augmentations) > 1:
            message = f"ambiguous in-place source partners for {member}: {sorted(augmentations)}"
            raise ValueError(message)
        augmented = next(iter(augmentations), None)
        if form is not None and form["direct"] and form["kind"] != "Call":
            syntax = form["syntax"]
            node = form["node"] if form["kind"] != "AugAssign" else None
        else:
            syntax = f"{'.'.join(target)}({', '.join(f'x{n + 1}' for n in range(row['min_positional']))})"
            node = None
        output.append({
            "member": member, "callable": target,
            "reflected": next(iter(partners), None), "inplace": augmented,
            "selector": _word(target[1]),
            "inplace_selector": _word(augmented[1]) if augmented else None,
            "syntax": syntax, "arity": row["min_positional"], "node": node,
        })
    return output


# The generated grammar carries source evidence separately from derived views.
GRAMMAR = '''from __future__ import annotations

from types import MappingProxyType
from typing import NamedTuple


class SourceSpan(NamedTuple):
    """An interval in an immutable upstream source."""

    source: str
    start_line: int
    end_line: int


class SourceSegment(NamedTuple):
    """A checked source interval within a packed local file."""

    path: str
    start_line: int
    end_line: int
    sha256: str
    offset: int
    bytes: int


class Source(NamedTuple):
    """The complete source identity, excerpt hashes and extraction metadata."""

    id: str
    revision: str
    path: str
    url: str | None
    full_sha256: str
    segments: tuple[SourceSegment, ...]
    details: tuple[tuple[str, object], ...]


class Slot(NamedTuple):
    """One expanded CPython slot row with its dispatch role."""

    family: str
    c_member: str
    generic: str | None
    wrapper: str | None
    flags: str
    signature: str | None
    macro: str
    role: str | None
    sources: tuple[SourceSpan, ...]


class Member(NamedTuple):
    """A Python member and every source that declares it."""

    id: tuple[str, str]
    slots: tuple[Slot, ...]
    sources: tuple[SourceSpan, ...]


class Parameter(NamedTuple):
    """A source parameter with its inspect kind and literal default."""

    name: str
    kind: str
    default: str | None


class PythonCallable(NamedTuple):
    """An exact exported callable identity and its source argument contract."""

    id: tuple[str, str]
    member: tuple[str, str] | None
    source_function: tuple[str, str]
    alias_of: tuple[str, str] | None
    signature: str | None
    parameters: tuple[Parameter, ...] | None
    min_positional: int
    max_positional: int | None
    required_keyword_only: tuple[str, ...]
    accepts_keywords: bool
    sources: tuple[SourceSpan, ...]
    selector: str

    def accepts_positional(self, count: int) -> bool:
        """Recognize a positional call shape; this does not bind arguments."""
        return (not self.required_keyword_only and count >= self.min_positional
                and (self.max_positional is None or count <= self.max_positional))


class SourceForm(NamedTuple):
    """A source body with a recognized direct syntax shape when available."""

    callable: tuple[str, str]
    kind: str
    node: str | None
    parameters: tuple[str, ...]
    operands: tuple[str, ...] | None
    result: str | None
    syntax: str
    body: str
    direct: bool
    sources: tuple[SourceSpan, ...]


class PythonOperator(NamedTuple):
    """Source facts joined by callable identity, C slot role and syntax."""

    member: tuple[str, str]
    callable: tuple[str, str]
    reflected: tuple[str, str] | None
    inplace: tuple[str, str] | None
    selector: str
    inplace_selector: str | None
    syntax: str
    arity: int
    node: str | None
'''


def _construct(name: str, values) -> str:
    return f"{name}({', '.join(values)})"


def _sequence(values) -> str:
    items = tuple(values)
    return "(" + ", ".join(items) + ("," if len(items) == 1 else "") + ")"


def _spans(rows) -> str:
    return _sequence(_construct("SourceSpan", (repr(row[key]) for key in
                     ("source", "start_line", "end_line"))) for row in rows)


def _record(name, row, fields, converted=None) -> str:
    converted = converted or {}
    return _construct(name, (f"{key}=" + (converted[key](row[key]) if key in converted else repr(row[key]))
                             for key in fields))


def _tuple_literal(value) -> str:
    return repr(_identity(value))


def _frozen(value):
    if isinstance(value, dict):
        return tuple((key, _frozen(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def render_rows(data: dict, root: Path = ROOT) -> str:
    """Emit the complete immutable inventory and its source-derived indexes."""
    output = [f'"""{notice(ROW_PATH, root=root)}"""', "", GRAMMAR.rstrip(), "",
              f"SCHEMA_VERSION = {data['schema_version']!r}",
              f"SOURCE_REVISION = {data['source_revision']!r}", ""]
    families = [
        ("SOURCES", "Source", [dict(row, details=_frozen({key: value for key, value in row.items()
          if key not in {"id", "revision", "path", "url", "full_sha256", "segments"}})) for row in data["sources"]],
         ("id", "revision", "path", "url", "full_sha256", "segments", "details"),
         {"segments": lambda rows: _sequence(_record("SourceSegment", row,
          ("path", "start_line", "end_line", "sha256", "offset", "bytes")) for row in rows)}),
        ("MEMBERS", "Member", data["members"], ("id", "slots", "sources"),
         {"id": _tuple_literal, "sources": _spans, "slots": lambda rows: _sequence(_record(
             "Slot", row, ("family", "c_member", "generic", "wrapper", "flags", "signature",
                           "macro", "role", "sources"), {"sources": _spans}) for row in rows)}),
        ("CALLABLES", "PythonCallable", [dict(row, selector=_word(row["id"][1])) for row in data["callables"]],
         ("id", "member", "source_function", "alias_of", "signature", "parameters",
          "min_positional", "max_positional", "required_keyword_only", "accepts_keywords", "sources", "selector"),
         {"id": _tuple_literal, "member": _tuple_literal, "source_function": _tuple_literal, "alias_of": _tuple_literal,
          "required_keyword_only": _tuple_literal, "sources": _spans,
          "parameters": lambda rows: "None" if rows is None else _sequence(_record(
              "Parameter", row, ("name", "kind", "default")) for row in rows)}),
        ("FORMS", "SourceForm", data["forms"],
         ("callable", "kind", "node", "parameters", "operands", "result", "syntax", "body", "direct", "sources"),
         {"callable": _tuple_literal, "parameters": _tuple_literal, "operands": _tuple_literal, "sources": _spans}),
        ("OPERATORS", "PythonOperator", operator_rows(data),
         ("member", "callable", "reflected", "inplace", "selector", "inplace_selector", "syntax", "arity", "node"), {}),
    ]
    for variable, grammar, rows, fields, converted in families:
        output.extend([f"{variable} = (", *(f"    {_record(grammar, row, fields, converted)}," for row in rows), ")", ""])
    for index, rows, key in (("BY_SOURCE", "SOURCES", "id"), ("BY_MEMBER", "MEMBERS", "id"),
                             ("BY_CALLABLE", "CALLABLES", "id"), ("BY_FORM", "FORMS", "callable"),
                             ("BY_OPERATOR", "OPERATORS", "member")):
        output.append(f"{index} = MappingProxyType({{row.{key}: row for row in {rows}}})")
    output.append("REQUIRED = MappingProxyType({")
    output.extend(f"    {key!r}: {_frozen(value)!r}," for key, value in sorted(data["required"].items()))
    output.append("})")
    output.append("")
    return "\n".join(output)


def _observed_function(name: str, parameters: list[str], body: str) -> str:
    """Return exception identity and message as data for the existing twin oracle."""
    tree = ast.parse(body)
    if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        tree.body.pop(0)
    returns = [node for node in ast.walk(tree) if isinstance(node, ast.Return)]
    if len(returns) != 1 or tree.body[-1] is not returns[0]:
        message = f"differential body needs one final source return: {name}"
        raise ValueError(message)
    returned = tree.body.pop()
    tree.body.append(ast.Assign(targets=[ast.Name(id="result", ctx=ast.Store())],
                                value=returned.value or ast.Constant(None)))
    handler = ast.ExceptHandler(type=ast.Name(id="Exception", ctx=ast.Load()), name="error", body=[
        ast.parse("return ('raise', error.__class__.__name__, str(error))").body[0],
    ])
    protected = ast.Try(body=tree.body, handlers=[handler], orelse=[], finalbody=[])
    observed = ast.Module(body=[protected, ast.parse("return ('return', result)").body[0]], type_ignores=[])
    return (f"def {name}({', '.join(parameters)}):\n"
            '    """Observe the source operation or its exception as ordinary data."""\n'
            + indent(ast.unparse(ast.fix_missing_locations(observed)), "    "))


def render_programs(data: dict, root: Path = ROOT) -> str:
    """Generate exact-call and direct-syntax twins with ordinary Python bodies."""
    callables = {tuple(row["id"]): row for row in data["callables"]}
    forms = {tuple(row["callable"]): row for row in data["forms"]}
    output = [f'"""{notice(TWIN_PATH, root=root)}"""', "", "import operator", "", ""]
    cases, calls, aliases = [], [], []
    for row in operator_rows(data):
        function = callables[row["callable"]]
        form = _source_form(function, forms)
        if (row["callable"][0] != "operator" or form is None or not form["direct"]
                or form["kind"] not in {"BinOp", "AugAssign", "Compare", "UnaryOp"}):
            continue
        parameters = form["parameters"]
        if len(parameters) != function["min_positional"] or function["max_positional"] != len(parameters):
            message = f"syntax and callable operand shapes disagree for {row['callable']}"
            raise ValueError(message)
        label = "protocol_" + row["callable"][1]
        args = ", ".join(parameters)
        output.extend([_observed_function(f"{label}_syntax", parameters, form["body"]), "", "",
                       _observed_function(f"{label}_call", parameters, f"return operator.{row['callable'][1]}({args})"), "", ""])
        cases.append((row["member"], form["kind"], form["node"], f"{label}_syntax", f"{label}_call"))
    output.extend(["PROGRAMS = (", *(f"    ({member!r}, {kind!r}, {node!r}, {syntax}, {call}),"
                                   for member, kind, node, syntax, call in cases), ")", ""])
    for identity, function in sorted(callables.items()):
        if identity[0] != "operator" or identity[1].startswith("__"):
            continue
        low, high = function["min_positional"], function["max_positional"]
        binding = f"_protocol_binding_{identity[1].lower()}"
        output.extend([f"{binding} = vars(operator).get({identity[1]!r})", "", ""])
        # A bounded optional shape exercises both ends. An unbounded shape
        # exercises its minimum and a call with several supplied values.
        for count in sorted({low, low + 2 if high is None else high}):
            parameters = [f"a{index}" for index in range(count)]
            name = f"protocol_exact_{identity[1].lower()}_{count}"
            body = f"return operator.{identity[1]}({', '.join(parameters)})"
            output.extend([_observed_function(name, parameters, body), "", ""])
            calls.append((identity, count, name))
            alias_name = f"protocol_alias_{identity[1].lower()}_{count}"
            body = f"return {binding}({', '.join(parameters)})"
            output.extend([_observed_function(alias_name, parameters, body), "", ""])
            aliases.append((identity, count, alias_name))
    output.extend(["CALL_PROGRAMS = (", *(f"    ({identity!r}, {count}, {name})," for identity, count, name in calls), ")", ""])
    output.extend(["ALIAS_PROGRAMS = (", *(f"    ({identity!r}, {count}, {name})," for identity, count, name in aliases), ")", ""])
    return "\n".join(output)


def projections(root: Path = ROOT, source_root: Path | None = None) -> dict[Path, str]:
    """Read the checked local source once for every protocol artifact."""
    source_root = source_root or root / "extensions/python/tools/protocol_sources"
    data = inventory(source_root)
    validate_inventory(data, source_root)
    _validate_policy_sources(data, root)
    return {root / ROW_PATH: render_rows(data, root), root / TWIN_PATH: render_programs(data, root)}


def _validate_policy_sources(data: dict, root: Path) -> None:
    """Require every handwritten meaning choice to join an authoritative fact."""
    path = root / "extensions/python/metta/_atoms/operators.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    declaration = next((node for node in tree.body if isinstance(node, ast.AnnAssign)
                        and isinstance(node.target, ast.Name) and node.target.id == "_POLICIES"), None)
    if (declaration is None or not isinstance(declaration.value, ast.Call) or len(declaration.value.args) != 1
            or not isinstance(declaration.value.args[0], ast.Dict)):
        message = "operator policy must be one literal mapping of source members to atom meanings"
        raise ValueError(message)
    names = [ast.literal_eval(key) for key in declaration.value.args[0].keys]
    available = {row["member"] for row in operator_rows(data)}
    missing = [("object", name) for name in names if ("object", name) not in available]
    if missing or len(names) != len(set(names)):
        message = f"operator policy has missing or repeated source members: {missing}"
        raise ValueError(message)


def main(argv: list[str] | None = None) -> int:
    """Write or verify every projection from checked local source bytes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for path, wanted in projections().items():
        ast.parse(wanted)
        if path.is_file() and path.read_text(encoding="utf-8") == wanted:
            continue
        if args.write:
            path.write_text(wanted, encoding="utf-8")
        else:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        print("protocol-sync: stale projections: " + ", ".join(stale))
        return 1
    print("protocol-sync: locked source, immutable rows and differential programs agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
