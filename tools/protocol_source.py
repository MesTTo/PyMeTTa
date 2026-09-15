#!/usr/bin/env python3
"""Read the locked CPython protocol facts without importing the Python seat.

Purpose: derive source members, callable contracts and syntax projections once.
Assumes: protocol_sources/manifest.json identifies exact retained source bytes.
Guarantees: inventory() is deterministic and offline; validate_inventory() rejects
    any difference from those inputs, including extra or missing required rows.
Fails when: a hash, retained source grammar, alias or required identity drifts.
Owns resources: refresh() stages a complete checked directory before publishing
    it to a previously absent destination; normal reads retain no resources.
Decides: source inventory describes facts, never native implementation status.
[source: extensions/python/tools/protocol_sources/manifest.json; commit=WORKTREE]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import keyword
import re
import tempfile
from pathlib import Path

_IDENT = re.compile(r"[A-Za-z_]\w*\Z")
_DUNDER = re.compile(r"__\w+__\Z")
_CTOKEN = re.compile(
    r'/\*.*?\*/|//[^\n]*|\s+|"(?:\\.|[^"\\])*"|'
    r"'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|\d+|##|.", re.DOTALL)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        msg = f"unsafe source path: {relative}"
        raise ValueError(msg)
    return root / path


class Sources:
    """Verify packed exact excerpts and restore their original line positions."""

    def __init__(self, root: Path | None = None):
        """Read the manifest and verify every retained byte before parsing."""
        self.root = Path(root) if root is not None else Path(__file__).with_name("protocol_sources")
        self.manifest = json.loads((self.root / "manifest.json").read_text())
        if self.manifest["schema_version"] != 1:
            msg = "unsupported protocol source manifest version"
            raise ValueError(msg)
        self.records = {}
        self.texts = {}
        for record in self.manifest["sources"]:
            key = record["id"]
            if key in self.records:
                msg = f"duplicate source id: {key}"
                raise ValueError(msg)
            self.records[key] = record
            chunks = []
            next_line = 1
            offsets = {}
            payloads = {}
            for span in record["segments"]:
                path = _safe_path(self.root, span["path"])
                if path not in payloads:
                    payloads[path] = path.read_bytes()
                payload = payloads[path]
                offset = span["offset"]
                if offset != offsets.get(path, 0):
                    msg = f"noncontiguous packed source: {key}"
                    raise ValueError(msg)
                raw = payload[offset:offset + span["bytes"]]
                if len(raw) != span["bytes"] or _digest(raw) != span["sha256"]:
                    msg = f"source hash mismatch: {key}:{span['start_line']}"
                    raise ValueError(msg)
                start, end = span["start_line"], span["end_line"]
                if start < next_line or len(raw.splitlines()) != end - start + 1:
                    msg = f"invalid source interval: {key}:{start}-{end}"
                    raise ValueError(msg)
                chunks.extend(("\n" * (start - next_line), raw.decode("utf-8")))
                next_line = end + 1
                offsets[path] = offset + len(raw)
            for path, end in offsets.items():
                if end != path.stat().st_size:
                    msg = f"unaccounted packed bytes: {key}"
                    raise ValueError(msg)
            if len(record["segments"]) == 1:
                span = record["segments"][0]
                if (span["start_line"] == 1 and span["bytes"] == record["full_bytes"]
                        and span["sha256"] != record["full_sha256"]):
                    msg = f"full source hash mismatch: {key}"
                    raise ValueError(msg)
            self.texts[key] = "".join(chunks)

    def span(self, source: str, start: int, end: int | None = None) -> dict:
        """Return original line provenance contained in one retained segment."""
        end = start if end is None else end
        if not any(s["start_line"] <= start <= end <= s["end_line"]
                   for s in self.records[source]["segments"]):
            msg = f"source span leaves retained input: {source}:{start}-{end}"
            raise ValueError(msg)
        return {"source": source, "start_line": start, "end_line": end}

    def offset_span(self, source: str, start: int, end: int) -> dict:
        """Convert restored text offsets into checked original source lines."""
        text = self.texts[source]
        return self.span(source, text.count("\n", 0, start) + 1,
                         text.count("\n", 0, max(start, end - 1)) + 1)


def _tokens(text: str) -> list[str]:
    return [m.group() for m in _CTOKEN.finditer(text)
            if not m.group().isspace() and not m.group().startswith(("/*", "//"))]


def _groups(tokens: list[str], opener: str, closer: str) -> tuple[list[str], int]:
    if not tokens or tokens[0] != opener:
        msg = f"expected {opener} in C source"
        raise ValueError(msg)
    depth = 0
    for index, token in enumerate(tokens):
        if token == opener:
            depth += 1
        elif token == closer:
            depth -= 1
            if depth == 0:
                return tokens[1:index], index + 1
    msg = f"unterminated {opener} in C source"
    raise ValueError(msg)


def _split(tokens: list[str]) -> list[list[str]]:
    parts, current, stack = [], [], []
    closers = {"(": ")", "[": "]", "{": "}"}
    for lexeme in tokens:
        if lexeme == "," and not stack:
            parts.append(current)
            current = []
            continue
        if lexeme in closers:
            stack.append(closers[lexeme])
        elif lexeme in closers.values() and (not stack or stack.pop() != lexeme):
            msg = "unbalanced C initializer"
            raise ValueError(msg)
        current.append(lexeme)
    if stack:
        msg = "unbalanced C initializer"
        raise ValueError(msg)
    if current:
        parts.append(current)
    return parts


def _macros(text: str) -> dict[str, tuple[list[str] | None, list[str]]]:
    result = {}
    pattern = re.compile(r"^#define[ \t]+(\w+)(\([^)]*\))?(.*)$")
    lines = iter(text.splitlines())
    for physical_line in lines:
        line = physical_line
        while line.endswith("\\"):
            try:
                line = line[:-1] + " " + next(lines)
            except StopIteration as error:
                msg = "unterminated retained C macro"
                raise ValueError(msg) from error
        match = pattern.match(line)
        if match is None:
            continue
        name, arguments, body = match.groups()
        if name in result:
            msg = f"duplicate retained C macro: {name}"
            raise ValueError(msg)
        params = None if arguments is None else [p.strip() for p in arguments[1:-1].split(",") if p.strip()]
        result[name] = (params, _tokens(body))
    return result


def _expand(tokens: list[str], macros: dict, active: tuple[str, ...] = ()) -> list[str]:
    result = []
    index = 0
    while index < len(tokens):
        name = tokens[index]
        if name not in macros:
            result.append(name)
            index += 1
            continue
        if name in active:
            msg = f"recursive C macro: {' -> '.join((*active, name))}"
            raise ValueError(msg)
        params, body = macros[name]
        index += 1
        replacements = {}
        if params is not None:
            if index == len(tokens) or tokens[index] != "(":
                result.append(name)
                continue
            raw, size = _groups(tokens[index:], "(", ")")
            index += size
            args = _split(raw)
            if len(params) != len(args):
                msg = f"C macro arity changed: {name}"
                raise ValueError(msg)
            replacements = dict(zip(params, args, strict=True))
        substituted = []
        cursor = 0
        while cursor < len(body):
            lexeme = body[cursor]
            if lexeme == "#":
                cursor += 1
                parameter = body[cursor]
                if parameter not in replacements:
                    msg = f"unknown stringized parameter: {name}.{parameter}"
                    raise ValueError(msg)
                substituted.append(json.dumps(" ".join(replacements[parameter])))
            else:
                substituted.extend(replacements.get(lexeme, [lexeme]))
            cursor += 1
        pasted = []
        cursor = 0
        while cursor < len(substituted):
            if substituted[cursor] == "##":
                if not pasted or cursor + 1 == len(substituted):
                    msg = f"invalid token paste: {name}"
                    raise ValueError(msg)
                pasted[-1] += substituted[cursor + 1]
                cursor += 2
            else:
                pasted.append(substituted[cursor])
                cursor += 1
        result.extend(_expand(pasted, macros, (*active, name)))
    return result


def _calls(text: str, names: set[str]):
    if not names:
        return
    pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(names)) + r")\s*\(")
    for match in pattern.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        if text[line_start:match.start()].lstrip().startswith("#"):
            continue
        pos = match.end() - 1
        depth = 0
        for token in _CTOKEN.finditer(text, pos):
            value = token.group()
            if value == "(":
                depth += 1
            elif value == ")":
                depth -= 1
                if depth == 0:
                    raw = text[pos + 1:token.start()]
                    yield match.group(1), _split(_tokens(raw)), match.start(), token.end()
                    break
        else:
            msg = f"unterminated C call: {match.group(1)}"
            raise ValueError(msg)


def _strings(tokens: list[str]) -> str:
    if not tokens or any(not token.startswith('"') for token in tokens):
        msg = "expected adjacent C string literals"
        raise ValueError(msg)
    return "".join(ast.literal_eval(token) for token in tokens)


def _table(text: str, name: str) -> tuple[list[str], int, int]:
    match = re.search(r"\b" + re.escape(name) + r"\s*\[\s*\]\s*=\s*\{", text)
    if match is None:
        msg = f"missing C table: {name}"
        raise ValueError(msg)
    depth = 0
    for token in _CTOKEN.finditer(text, match.end() - 1):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return _tokens(text[match.end():token.start()]), match.start(), token.end()
    msg = f"unterminated C table: {name}"
    raise ValueError(msg)


def _parameters(arguments: ast.arguments) -> dict:
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults = [None] * (len(positional) - len(arguments.defaults)) + list(arguments.defaults)
    rows = []
    for index, (argument, default) in enumerate(zip(positional, defaults, strict=True)):
        rows.append({"name": argument.arg,
                     "kind": "POSITIONAL_ONLY" if index < len(arguments.posonlyargs) else "POSITIONAL_OR_KEYWORD",
                     "default": None if default is None else ast.unparse(default)})
    if arguments.vararg:
        rows.append({"name": arguments.vararg.arg, "kind": "VAR_POSITIONAL", "default": None})
    for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True):
        rows.append({"name": argument.arg, "kind": "KEYWORD_ONLY",
                     "default": None if default is None else ast.unparse(default)})
    if arguments.kwarg:
        rows.append({"name": arguments.kwarg.arg, "kind": "VAR_KEYWORD", "default": None})
    for row in rows:
        if row["default"] == "_UNREPRESENTABLE_DEFAULT":
            row["default"] = "<unrepresentable>"
    return {"parameters": rows,
            "min_positional": len(positional) - len(arguments.defaults),
            "max_positional": None if arguments.vararg else len(positional),
            "required_keyword_only": [r["name"] for r in rows if r["kind"] == "KEYWORD_ONLY" and r["default"] is None],
            "accepts_keywords": any(r["kind"] in {"POSITIONAL_OR_KEYWORD", "KEYWORD_ONLY", "VAR_KEYWORD"} for r in rows)}


def _signature(signature: str) -> dict:
    # Clinic's hidden receiver is metadata, not a caller-supplied argument.
    signature = re.sub(r"\$\w+,?\s*", "", signature)
    signature = re.sub(r"^\(\s*/\s*,?\s*", "(", signature)
    parsed = signature.replace("<unrepresentable>", "_UNREPRESENTABLE_DEFAULT")
    try:
        function = ast.parse(f"def f{parsed}: pass").body[0]
    except SyntaxError as error:
        msg = f"unsupported published signature: {signature}"
        raise ValueError(msg) from error
    return {"signature": signature, **_parameters(function.args)}


def _slot_rows(sources: Sources) -> list[tuple[str, dict]]:
    source = sources.manifest["slots"]
    text = sources.texts[source]
    macros = _macros(text)
    table, start, end = _table(text, "slotdefs")
    entries = _split(table)
    invocations = {}
    for macro, args, call_start, call_end in _calls(text[start:end], set(macros)):
        if len(args) > 1 and len(args[0]) == len(args[1]) == 1:
            key = (macro, args[0][0], args[1][0])
            if key in invocations:
                msg = f"nonunique source slot invocation: {key}"
                raise ValueError(msg)
            invocations[key] = (start + call_start, start + call_end)
    result = []
    for entry in entries:
        if entry == ["{", "NULL", "}"]:
            continue
        if not entry or entry[0] not in macros:
            msg = f"unrecognized slot row: {''.join(entry)}"
            raise ValueError(msg)
        expanded = _expand(entry, macros)
        inner, consumed = _groups(expanded, "{", "}")
        if consumed != len(expanded):
            msg = "trailing tokens after slot row"
            raise ValueError(msg)
        fields = _split(inner)
        if len(fields) not in {6, 7}:
            msg = "slot initializer fields changed"
            raise ValueError(msg)
        name = _strings(fields[0])
        c_member = re.search(r"\b((?:tp|nb|sq|mp|bf|am)_\w+)\)", "".join(fields[1]))
        if c_member is None:
            msg = f"unrecognized slot member: {name}"
            raise ValueError(msg)
        generic = re.fullmatch(r"\(void\*\)\((.*)\)", "".join(fields[2]))
        if generic is None:
            msg = f"unrecognized generic slot cast: {name}"
            raise ValueError(msg)
        if fields[4][:2] != ["PyDoc_STR", "("] or fields[4][-1] != ")":
            msg = f"unrecognized slot documentation: {name}"
            raise ValueError(msg)
        doc = _strings(fields[4][2:-1])
        signature = doc.split("\n", 1)[0] if "\n--\n" in doc else None
        member = c_member.group(1)
        wrapper = "".join(fields[3])
        role = "inplace" if "_inplace_" in member else None
        if member.startswith("nb_") and role is None:
            if wrapper in {"wrap_binaryfunc_r", "wrap_ternaryfunc_r"}:
                role = "reflected"
            elif wrapper in {"wrap_binaryfunc_l", "wrap_ternaryfunc"}:
                role = "left"
        # Find the original invocation, retaining its exact source interval.
        call_start, call_end = invocations[(entry[0], name, member)]
        result.append((name, {"family": member.split("_", 1)[0], "c_member": member,
                             "macro": entry[0], "generic": generic.group(1), "wrapper": wrapper,
                             "flags": "".join(fields[5]) if len(fields) == 7 else "0",
                             "signature": signature, "role": role,
                             "sources": [sources.offset_span(source, call_start, call_end)]}))
    numeric = {}
    for _, row in result:
        if row["family"] == "nb":
            numeric.setdefault(row["c_member"], []).append(row["role"])
    for c_member, roles in numeric.items():
        if len(roles) > 1 and set(roles) != {"left", "reflected"}:
            msg = f"unclassified numeric slot roles: {c_member}"
            raise ValueError(msg)
    return result


def _directives(text: str):
    pattern = re.compile(r"^\s*(?:\*\s*-\s*)?\.\.\s+(?:method|classmethod|attribute|data)::\s*(.+)$")
    member = re.compile(r"([\w.]+)\.(__\w+__)(?:\(.*\))?$")
    pending = False
    for number, line in enumerate(text.splitlines(), 1):
        directive = pattern.match(line)
        if directive:
            value = directive.group(1).strip()
            pending = True
        elif pending and line[:1].isspace() and member.fullmatch(line.strip()):
            value = line.strip()
        else:
            pending = False
            continue
        found = member.fullmatch(value)
        if found:
            yield (found.group(1), found.group(2)), number


def _c_facts(sources: Sources, record: dict) -> tuple[dict, dict]:
    source, module = record["id"], record["module"]
    text = sources.texts[source]
    inputs = [source, *record.get("headers", [])]
    macros, docs, doc_spans = {}, {}, {}
    for key in inputs:
        fragment = sources.texts[key]
        for name, definition in _macros(fragment).items():
            if name in macros and macros[name] != definition:
                msg = f"conflicting C macro: {name}"
                raise ValueError(msg)
            macros[name] = definition
        for _, args, start, end in _calls(fragment, {"PyDoc_STRVAR"}):
            if len(args) == 2 and len(args[0]) == 1 and _IDENT.fullmatch(args[0][0]) and all(t.startswith('"') for t in args[1]):
                docs[args[0][0]] = _strings(args[1])
                doc_spans[args[0][0]] = sources.offset_span(key, start, end)
    # math's FUNCn declarations contain the same published signatures as Clinic.
    for name, args, start, end in _calls(text, {n for n in macros if re.fullmatch(r"FUNC\d[A-Z]*", n)}):
        expanded = _expand([name, "(", *[t for i, arg in enumerate(args) for t in (([","] if i else []) + arg)], ")"], macros)
        expanded_text = " ".join(expanded)
        for _, fields, _, _ in _calls(expanded_text, {"PyDoc_STRVAR"}):
            if len(fields) != 2 or len(fields[0]) != 1:
                msg = f"unrecognized generated C documentation: {name}"
                raise ValueError(msg)
            docs[fields[0][0]] = _strings(fields[1])
            doc_spans[fields[0][0]] = sources.offset_span(source, start, end)
    table, table_start, table_end = _table(text, record["table"])
    expanded = _expand(table, macros)
    members, callables = {}, {}
    for fields in _split(expanded):
        if not fields:
            continue
        if fields[0] != "{":
            msg = f"unexpanded module method: {''.join(fields)}"
            raise ValueError(msg)
        inside, consumed = _groups(fields, "{", "}")
        if consumed != len(fields):
            msg = f"module method fields changed: {module}"
            raise ValueError(msg)
        values = _split(inside)
        if values[0] in (["NULL"], ["0"]):
            continue
        name = _strings(values[0])
        if name.startswith("_"):
            continue
        if len(values) != 4 or len(values[3]) != 1:
            msg = f"module method layout changed: {module}.{name}"
            raise ValueError(msg)
        doc_name = values[3][0]
        doc = docs.get(doc_name, "")
        spans = [sources.offset_span(source, table_start, table_end)]
        if doc_name in doc_spans:
            spans.append(doc_spans[doc_name])
        members[name] = spans
        flags = "".join(values[2])
        if "\n--\n" in doc:
            first = " ".join(doc.split("\n--\n", 1)[0].splitlines())
            if not first.startswith(name + "("):
                msg = f"published signature name changed: {module}.{name}"
                raise ValueError(msg)
            contract = _signature(first[len(name):])
        else:
            checks = list(re.finditer(r'_PyArg_CheckPositional\(\s*"' + re.escape(name) + r'"\s*,\s*\w+\s*,\s*(\d+)\s*,\s*(\d+|PY_SSIZE_T_MAX)\s*\)', text))
            if not checks:
                continue
            bounds = {(int(m.group(1)), None if m.group(2) == "PY_SSIZE_T_MAX" else int(m.group(2))) for m in checks}
            if len(bounds) != 1 or "METH_KEYWORDS" in flags:
                msg = f"ambiguous positional C contract: {module}.{name}"
                raise ValueError(msg)
            minimum, maximum = bounds.pop()
            contract = {"signature": None, "parameters": None, "min_positional": minimum,
                        "max_positional": maximum, "required_keyword_only": [], "accepts_keywords": False}
            spans.extend(sources.offset_span(source, m.start(), m.end()) for m in checks)
        c_name = re.findall(r"\b[A-Za-z_]\w*\b", "".join(values[1]))[-1]
        hooks = set()
        for function in (c_name, c_name + "_impl"):
            match = re.search(r"^" + re.escape(function) + r"\([^;{}]*\)\s*(?:/\*.*?\*/\s*)?\{", text, re.MULTILINE | re.DOTALL)
            if match:
                depth = 1
                for token in _CTOKEN.finditer(text, match.end()):
                    if token.group() == "{":
                        depth += 1
                    elif token.group() == "}":
                        depth -= 1
                        if depth == 0:
                            body = text[match.end():token.start()]
                            hooks.update(re.findall(r"_Py_ID\((__\w+__)\)", body))
                            spans.append(sources.offset_span(source, match.start(), token.end()))
                            break
                else:
                    msg = f"unterminated retained C function: {function}"
                    raise ValueError(msg)
        if len(hooks) > 1:
            msg = f"multiple special-method hooks require a call schema: {module}.{name}"
            raise ValueError(msg)
        callables[name] = {"id": [module, name], "member": ["object", next(iter(hooks))] if hooks else None,
                           "source_function": [module, name], "alias_of": None, **contract, "sources": spans}
    return members, callables


def _python_bindings(tree: ast.Module) -> dict[str, ast.AST]:
    bindings = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bindings[node.target.id] = node
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    bindings[alias.asname or alias.name] = node
    return bindings


def _form(module: str, name: str, function: ast.FunctionDef, span: dict) -> dict:
    statements = function.body
    if statements and isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
        statements = statements[1:]
    parameters = [r["name"] for r in _parameters(function.args)["parameters"]]
    row = {"callable": [module, name], "kind": "Function", "node": None,
           "parameters": parameters, "operands": None, "result": None,
           "syntax": f"{module}.{name}({', '.join(parameters)})",
           "body": "\n".join(ast.unparse(s) for s in function.body), "direct": False,
           "sources": [span]}
    if function.args.vararg or function.args.kwarg:
        supplied = [*parameters[:len(function.args.posonlyargs) + len(function.args.args)]]
        if function.args.vararg:
            supplied.append("*" + function.args.vararg.arg)
        supplied.extend(f"{a.arg}={a.arg}" for a in function.args.kwonlyargs)
        if function.args.kwarg:
            supplied.append("**" + function.args.kwarg.arg)
        row["syntax"] = f"{module}.{name}({', '.join(supplied)})"
    expression = None
    kind, result = None, None
    if len(statements) == 1:
        statement = statements[0]
        if isinstance(statement, ast.Return):
            expression, result = statement.value, "value"
        elif isinstance(statement, (ast.Assign, ast.Delete)):
            expression, kind, result = statement, type(statement).__name__, "none"
    elif len(statements) == 2 and isinstance(statements[0], ast.AugAssign) and isinstance(statements[1], ast.Return):
        if ast.dump(statements[0].target, include_attributes=False).replace("Store()", "Load()") == ast.dump(statements[1].value, include_attributes=False):
            expression, kind, result = statements[0], "AugAssign", "target"
    if expression is None:
        return row
    operands = None
    node = None
    if isinstance(expression, ast.BinOp):
        operands, node = [expression.left, expression.right], type(expression.op).__name__
    elif isinstance(expression, ast.UnaryOp):
        operands, node = [expression.operand], type(expression.op).__name__
    elif isinstance(expression, ast.Compare) and len(expression.ops) == 1:
        operands, node = [expression.left, expression.comparators[0]], type(expression.ops[0]).__name__
    elif isinstance(expression, ast.AugAssign):
        operands, node = [expression.target, expression.value], type(expression.op).__name__
    elif isinstance(expression, ast.Subscript):
        operands = [expression.value, expression.slice]
    elif isinstance(expression, ast.Assign) and len(expression.targets) == 1 and isinstance(expression.targets[0], ast.Subscript):
        target = expression.targets[0]
        operands = [expression.value, target.value, target.slice]
    elif isinstance(expression, ast.Delete) and len(expression.targets) == 1 and isinstance(expression.targets[0], ast.Subscript):
        target = expression.targets[0]
        operands = [target.value, target.slice]
    elif isinstance(expression, ast.Call) and not expression.keywords and not any(isinstance(a, ast.Starred) for a in expression.args):
        receiver = [expression.func.value] if isinstance(expression.func, ast.Attribute) else []
        operands = [*receiver, *expression.args]
    if operands is None:
        return row
    row.update(kind=kind or type(expression).__name__, node=node, operands=[ast.unparse(o) for o in operands],
               result=result, syntax=ast.unparse(expression), direct=True)
    return row


def _journal_requirements(sources: Sources, members: dict, callables: dict) -> dict:
    source = sources.manifest["journal"]
    text = sources.texts[source]
    required_members = set()
    by_name = {}
    for owner, name in members:
        by_name.setdefault(name, set()).add(owner)
    for name in set(re.findall(r"\b__\w+__\b", text)):
        owners = by_name.get(name, set())
        if "object" in owners:
            owner = "object"
        elif "type" in owners:
            owner = "type"
        elif len(owners) == 1:
            owner = next(iter(owners))
        else:
            msg = f"unclassified journal hook: {name}"
            raise ValueError(msg)
        required_members.add((owner, name))
    modules = set(sources.manifest["journal_api_modules"])
    api_ids = {key for key in members if key[0] in modules and not key[1].startswith("_") and not keyword.iskeyword(key[1])}
    apis = set()
    for code in re.findall(r"`([^`]+)`", text):
        reference = re.match(r"^@?([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?:\(|$)", code)
        if reference is None:
            continue
        token = reference.group(1)
        if "." in token:
            identity = tuple(token.rsplit(".", 1))
            if identity in api_ids:
                apis.add(identity)
        else:
            matches = {key for key in api_ids if key[1] == token}
            if len(matches) > 1:
                msg = f"ambiguous journal API reference: {token}"
                raise ValueError(msg)
            apis.update(matches)
    # The final work-order line names declaration decorators in ordinary prose.
    for line in text.splitlines():
        if re.match(r"4\. The decorator rows", line):
            words = set(re.findall(r"[A-Za-z_]\w*", line))
            apis.update(key for key in api_ids if key[1] in words)
    apis.update(map(tuple, sources.manifest.get("required_apis", [])))
    missing = apis - members.keys()
    if missing:
        msg = f"unclassified required APIs: {sorted(missing)}"
        raise ValueError(msg)
    parameters = {(module, name, p["name"]) for module, name in apis
                  for p in callables.get((module, name), {}).get("parameters") or []}
    return {"journal_members": [list(k) for k in sorted(required_members)],
            "journal_apis": [list(k) for k in sorted(apis)],
            "journal_parameters": [list(k) for k in sorted(parameters)]}


def _python_members(sources: Sources, record: dict, tree: ast.Module,
                    bindings: dict) -> tuple[set[str], list]:
    source, module = record["id"], record["module"]
    exports = (set(ast.literal_eval(bindings["__all__"].value)) if "__all__" in bindings
               else {name for name in bindings if not name.startswith("_")})
    rows = []
    for name in sorted(exports):
        declaration = bindings.get(name)
        if declaration is None:
            # Guarded imports and lazy exports retain source identity without
            # inventing a callable contract for their runtime implementation.
            candidates = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                          and any((a.asname or a.name) == name for a in n.names)]
            if not candidates and "__getattr__" in bindings:
                candidates = [bindings["__getattr__"]]
                export = bindings["__all__"]
                rows.append(((module, name), [sources.span(source, export.lineno, export.end_lineno)]))
            if not candidates:
                msg = f"unresolved public source member: {module}.{name}"
                raise ValueError(msg)
            declaration = candidates[0]
        rows.append(((module, name), [sources.span(source, declaration.lineno, declaration.end_lineno)]))
    if module == "dataclasses":
        # Generated class hooks have no definition on the dataclasses module.
        constants = {name: node.value for name, node in bindings.items()
                     if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)}
        for node in ast.walk(tree):
            value = None
            if isinstance(node, ast.Call) and node.args:
                if isinstance(node.func, ast.Attribute) and node.func.attr == "add_fn":
                    value = node.args[0]
                elif isinstance(node.func, ast.Name) and node.func.id == "_set_new_attribute" and len(node.args) > 1:
                    value = node.args[1]
                elif isinstance(node.func, ast.Name) and node.func.id == "hasattr" and len(node.args) == 2:
                    value = node.args[1]
                    if isinstance(value, ast.Name):
                        value = constants.get(value.id)
            if isinstance(value, ast.Constant) and isinstance(value.value, str) and _DUNDER.fullmatch(value.value):
                rows.append((("object", value.value), [sources.span(source, node.lineno, node.end_lineno)]))
    return exports, rows


def _python_calls(sources: Sources, record: dict, tree: ast.Module,
                  exports: set[str], c_calls: dict) -> dict:
    source, module = record["id"], record["module"]
    active = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in exports and not node.decorator_list:
            active[node.name] = {"id": [module, node.name], "member": None,
                                 "source_function": [module, node.name], "alias_of": None,
                                 "signature": "(" + ast.unparse(node.args) + ")", **_parameters(node.args),
                                 "sources": [sources.span(source, node.lineno, node.end_lineno)]}
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
            for target in node.targets:
                if isinstance(target, ast.Name) and node.value.id in active:
                    active[target.id] = dict(active[node.value.id], id=[module, target.id], alias_of=[module, node.value.id])
                    active[target.id]["sources"] = [*active[node.value.id]["sources"], sources.span(source, node.lineno, node.end_lineno)]
        if isinstance(node, (ast.Try, ast.ImportFrom)):
            imports = [node] if isinstance(node, ast.ImportFrom) else [n for n in node.body if isinstance(n, ast.ImportFrom)]
            for imported in imports:
                if imported.module != record.get("accelerator"):
                    continue
                selected = c_calls if any(a.name == "*" for a in imported.names) else {a.asname or a.name: c_calls[a.name] for a in imported.names if a.name in c_calls}
                for name, row in selected.items():
                    active[name] = dict(row, sources=[*row["sources"], sources.span(source, imported.lineno, imported.end_lineno)])
    return active


def _fallback_function(name: str, module: str, functions: dict, aliases: dict) -> ast.FunctionDef:
    seen = set()
    while True:
        if name in seen:
            msg = f"cyclic Python alias: {module}.{name}"
            raise ValueError(msg)
        if name in functions:
            return functions[name]
        if name not in aliases:
            msg = f"unresolved Python alias: {module}.{name}"
            raise ValueError(msg)
        seen.add(name)
        name = aliases[name]


def inventory(source_root: Path | None = None) -> dict:
    """Derive source facts. No returned row asserts a native implementation."""
    sources = Sources(source_root)
    members, callables, forms = {}, {}, []

    def member(identity, spans):
        key = tuple(identity)
        row = members.setdefault(key, {"id": list(key), "slots": [], "sources": []})
        for span in spans:
            if span not in row["sources"]:
                row["sources"].append(span)
        return row

    for name, slot in _slot_rows(sources):
        member(("object", name), slot["sources"])["slots"].append(slot)
    reference = sources.manifest["reference"]
    required_reference = set()
    for identity, line in _directives(sources.texts[reference["source"]]):
        member(identity, [sources.span(reference["source"], line)])
        if reference["start_line"] <= line <= reference["end_line"]:
            required_reference.add(identity)
    c_by_module = {}
    for record in sources.records.values():
        if record["kind"] == "c_module":
            c_members, c_calls = _c_facts(sources, record)
            c_by_module[record["module"]] = c_calls
            for name, spans in c_members.items():
                member((record["module"], name), spans)
            callables.update((tuple(row["id"]), row) for row in c_calls.values())
        elif record["kind"] == "c_metadata":
            for match in re.finditer(r'(?:SETBUILTIN\(\s*|\{\s*)"(\w+)"', sources.texts[record["id"]]):
                member((record["owner"], match.group(1)), [sources.offset_span(record["id"], match.start(), match.end())])

    for record in sources.records.values():
        if record["kind"] != "python":
            continue
        source, module = record["id"], record["module"]
        tree = ast.parse(sources.texts[source], filename=record["path"])
        bindings = _python_bindings(tree)
        exports, rows = _python_members(sources, record, tree, bindings)
        for identity, spans in rows:
            member(identity, spans)
        active = _python_calls(sources, record, tree, exports, c_by_module.get(module, {}))
        for name, row in active.items():
            if name not in exports and not _DUNDER.fullmatch(name):
                continue
            callables[(module, name)] = row
            member((module, name), row["sources"])
        if module == "operator":
            python_functions = {name: node for name, node in bindings.items() if isinstance(node, ast.FunctionDef)}
            fallback_aliases = {name: node.value.id for name, node in bindings.items()
                                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)}
            method_links = {}
            for name, row in active.items():
                key = ("object", name)
                if _DUNDER.fullmatch(name) and key in members:
                    target = tuple(row["source_function"])
                    if target in method_links and method_links[target] != key:
                        msg = f"conflicting operator member aliases: {target}"
                        raise ValueError(msg)
                    method_links[target] = key
            for name, row in active.items():
                if (module, name) not in callables:
                    continue
                target = tuple(row["source_function"])
                row["member"] = list(method_links[target]) if target in method_links else None
                function = _fallback_function(name, module, python_functions, fallback_aliases)
                forms.append(_form(module, name, function, sources.span(source, function.lineno, function.end_lineno)))

    asdl = sources.texts[sources.manifest["asdl"]]
    declared_nodes = set()
    for match in re.finditer(r"^\s*(?:operator|unaryop|cmpop|boolop)\s*=([^=]*?)(?=\n\s*\w+\s*=|\Z)", asdl, re.MULTILINE | re.DOTALL):
        declared_nodes.update(re.findall(r"\b[A-Z]\w*\b", match.group(1)))
    for form in forms:
        if form["node"] is not None and form["node"] not in declared_nodes:
            msg = f"AST node absent from pinned ASDL: {form['node']}"
            raise ValueError(msg)
    for row in callables.values():
        if row["member"] is not None and tuple(row["member"]) not in members:
            msg = f"callable links unknown member: {row['id']}"
            raise ValueError(msg)
    required = {"reference": [list(key) for key in sorted(required_reference)],
                **_journal_requirements(sources, members, callables)}
    return {"schema_version": 1, "source_revision": sources.manifest["source_revision"],
            "sources": sources.manifest["sources"], "members": [members[key] for key in sorted(members)],
            "callables": [callables[key] for key in sorted(callables)],
            "forms": sorted(forms, key=lambda row: row["callable"]), "required": required}


def _difference(expected, actual, path="inventory") -> str | None:
    if type(expected) is not type(actual):
        return f"{path}: expected {type(expected).__name__}, got {type(actual).__name__}"
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return f"{path}: missing={sorted(expected.keys() - actual.keys())}, extra={sorted(actual.keys() - expected.keys())}"
        for key, value in expected.items():
            if difference := _difference(value, actual[key], f"{path}.{key}"):
                return difference
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: expected {len(expected)} rows, got {len(actual)}"
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            if difference := _difference(left, right, f"{path}[{index}]"):
                return difference
    elif expected != actual:
        return f"{path}: expected {expected!r}, got {actual!r}"
    return None


def validate_inventory(data: dict, source_root: Path | None = None) -> None:
    """Compare every field and exact required set with independently read inputs."""
    if difference := _difference(inventory(source_root), data):
        raise ValueError(difference)


def refresh(checkout: Path, revision: str, destination: Path,
            source_root: Path | None = None) -> dict:
    """Reconstruct the snapshot from checked full files in a source checkout.

    Local journal inputs remain locked to their own recorded repository revision.
    A pin upgrade is an explicit manifest change, followed by source review.
    File hashes establish the input identity; checkout working-tree state, Git
    metadata and a network connection are not part of this operation.
    """
    sources = Sources(source_root)
    if revision != sources.manifest["source_revision"]:
        msg = "refresh revision differs from locked CPython revision"
        raise ValueError(msg)
    destination = Path(destination)
    if destination.exists():
        msg = f"refresh destination already exists: {destination}"
        raise ValueError(msg)
    payloads = {}
    full_files = {}
    for record in sources.records.values():
        if record["revision"] == revision:
            path = _safe_path(Path(checkout), record["path"])
            if path not in full_files:
                full_files[path] = path.read_bytes()
            raw = full_files[path]
            if _digest(raw) != record["full_sha256"]:
                msg = f"full source hash mismatch: {record['id']}"
                raise ValueError(msg)
            lines = raw.splitlines(keepends=True)
            for span in record["segments"]:
                part = b"".join(lines[span["start_line"] - 1:span["end_line"]])
                if len(part) != span["bytes"] or _digest(part) != span["sha256"]:
                    msg = f"refreshed excerpt hash mismatch: {record['id']}"
                    raise ValueError(msg)
                payloads.setdefault(span["path"], bytearray()).extend(part)
        else:
            for span in record["segments"]:
                payloads[span["path"]] = (sources.root / span["path"]).read_bytes()
    with tempfile.TemporaryDirectory(prefix="protocol-refresh-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "sources"
        stage.mkdir()
        for relative, payload in payloads.items():
            path = _safe_path(stage, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        (stage / "manifest.json").write_bytes((sources.root / "manifest.json").read_bytes())
        result = inventory(stage)
        validate_inventory(result, sources.root)
        stage.rename(destination)
    return result


def main() -> int:
    """Emit, check or explicitly refresh the locked source inventory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inventory")
    check = commands.add_parser("check")
    check.add_argument("inventory", type=Path)
    update = commands.add_parser("refresh")
    update.add_argument("--checkout", type=Path, required=True)
    update.add_argument("--revision", required=True)
    update.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "inventory":
        print(json.dumps(inventory(args.sources), indent=2, sort_keys=True))
    elif args.command == "check":
        validate_inventory(json.loads(args.inventory.read_text()), args.sources)
    else:
        data = refresh(args.checkout, args.revision, args.destination, args.sources)
        print(json.dumps({"source_revision": data["source_revision"], "diff": [], "destination": str(args.destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
