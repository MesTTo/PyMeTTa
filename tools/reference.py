"""Purpose: derive public API pages and navigation from the Python source graph.

Griffe supplies static aliases, stub merging and C3 inheritance. No analyzed
module is imported. The directory supplies public modules; existing Source
lines preserve reference URLs through moves.

Guarantees: source edits, inherited methods, callable modules and a new public
module change the generated pages and navigation [tested:
test_reference_discovers_exports_inheritance_and_new_modules; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Fails when: a declared public export or its source cannot be resolved. The
reference refuses rather than publishing an incomplete API.
"""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import pkgutil
import re
import sys

import griffe

ROOT = pathlib.Path(__file__).resolve().parents[3]
PAGES = ROOT / "website" / "reference"
SOURCE = re.compile(r"^Source: `([^`]+)`\.$", re.MULTILINE)
PREAMBLE = "The entries below reproduce the source signatures and docstrings."
LINE_LENGTH = 100


# The file-local contract header is written for whoever edits the file next: it
# names invariants, the tests that hold them, and the commit each was measured
# on. A reader looking up `Space.match` wants none of that, and publishing it
# served the machine instead of the person.
CONTRACT_LABELS = (
    "Assumes:",
    "Guarantees:",
    "Fails when:",
    "Owns resources:",
    "Guarded by:",
    "Decides:",
    "Open Obligations:",
)
EVIDENCE_TAG = re.compile(
    r"[ \t]*\[(?:tested|measured|source|assumed)\b[^\]]*\]", re.DOTALL
)


def public_prose(text: str) -> str:
    """Return the reader-facing part of a docstring."""
    text = EVIDENCE_TAG.sub("", text)
    kept: list[str] = []
    in_contract = False
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(label) for label in CONTRACT_LABELS):
            in_contract = True
            continue
        if in_contract:
            # A contract section runs until the next unindented prose line.
            if not stripped or line.startswith((" ", "\t")):
                continue
            in_contract = False
        if stripped.startswith("Purpose:"):
            stripped = stripped[len("Purpose:") :].strip()
            published_line = stripped[:1].upper() + stripped[1:] if stripped else ""
        else:
            published_line = line
        kept.append(published_line.rstrip())
    while kept and not kept[-1]:
        kept.pop()
    return "\n".join(kept).strip()


def quote(text: str) -> str:
    """A docstring as a markdown blockquote, keeping its own line breaks."""
    lines = []
    in_indented_code = False
    previous_blank = False
    for raw_line in public_prose(text).strip().splitlines():
        line = raw_line.rstrip()
        indented = line.startswith("    ")
        is_code = indented and (previous_blank or in_indented_code)
        lines.append(escape_tags(line, preserve_indented_code=is_code))
        in_indented_code = is_code
        previous_blank = not line
    return "\n".join(f"> {line}".rstrip() for line in lines)


CODE_SPAN = re.compile(r"(`+[^`]*`+)")


def escape_tags(line: str, *, preserve_indented_code: bool = True) -> str:
    """`<` in PROSE, so a docstring is not read as HTML.

    CommonMark parses `<obj>` as a raw HTML tag and the browser renders an
    unknown element as nothing, so "the space as (wrapped name <obj>)" lost
    the word it was about. Verified by rendering rather than by reading the
    spec: markdown-it leaves it as raw `<obj>` in the output.

    Only prose needs it, and only `<`. A bare `&` renders literally and `>`
    cannot open a tag; markdown-it escapes both code spans and indented code
    blocks by itself, so escaping those too would display the escape.
    """
    if preserve_indented_code and line.startswith("    "):
        return line
    return "".join(
        part if index % 2 else part.replace("<", "&lt;")
        for index, part in enumerate(CODE_SPAN.split(line))
    )


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """One def line, wrapped one argument per line when it does not fit.

    ast.unparse writes a signature on one line however long it is, so a
    thirteen-parameter method came out at 300 columns. The wrap and the spaced
    default are what the project's own formatter would have written, which is
    what the pages this replaces carried.
    """
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    parts = [spaced_default(part) for part in split_top_level(ast.unparse(node.args))]
    flat = f"{prefix} {node.name}({', '.join(parts)}){returns}:"
    if len(flat) <= LINE_LENGTH:
        return flat
    body = "".join(f"    {part},\n" for part in parts)
    return f"{prefix} {node.name}(\n{body}){returns}:"


def split_top_level(arguments: str) -> list[str]:
    """Top-level commas only: a default of dict[str, Any] holds its own."""
    depth, start, parts = 0, 0, []
    for index, character in enumerate(arguments):
        if character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
        elif character == "," and depth == 0:
            parts.append(arguments[start:index].strip())
            start = index + 1
    tail = arguments[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def spaced_default(part: str) -> str:
    """`x: int=1` as `x: int = 1`.

    PEP 8 spaces the default of an ANNOTATED parameter and not of a bare one,
    and ast.unparse spaces neither.
    """
    depth = 0
    annotated = False
    for index, character in enumerate(part):
        if character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
        elif depth == 0 and character == ":":
            annotated = True
        elif depth == 0 and character == "=":
            return f"{part[:index]} = {part[index + 1:]}" if annotated else part
    return part


def class_line(node: ast.ClassDef) -> str:
    """The `class Name(bases):` line a reader sees, bases and keywords included."""
    bases = [ast.unparse(base) for base in node.bases]
    bases += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords if kw.arg]
    return f"class {node.name}({', '.join(bases)}):" if bases else f"class {node.name}:"


def entry(heading: str, code: str, doc: str | None) -> str:
    """One reference entry: its heading, its signature block and its docstring."""
    body = quote(doc) if doc else "No docstring is defined."
    return f"{heading}\n\n```python\n{code}\n```\n\n{body}\n"


class SourceModules(griffe.Extension):
    """Retain source module identities when a stub types a callable module."""

    def __init__(self) -> None:
        """Start a source-module inventory for one load."""
        self.modules: dict[str, griffe.Module] = {}

    def on_module_instance(self, *, mod: griffe.Module, **_kwargs: object) -> None:
        """Keep the source object before the stub merge changes its parent slot."""
        if isinstance(mod.filepath, pathlib.Path) and mod.filepath.suffix == ".py":
            self.modules[mod.path] = mod


class SourceGraph:
    """One fresh, engine-free API graph for a complete generation."""

    def __init__(self, root: pathlib.Path = ROOT) -> None:
        """Load source and declarations without executing analyzed modules."""
        self.root = root
        seat = root / "extensions/python"
        capture = SourceModules()
        self.loader = griffe.GriffeLoader(
            search_paths=[seat, *sorted((seat / "ext").glob("metta-*"))],
            extensions=griffe.Extensions(capture),
            allow_inspection=False,
        )
        self.loader.load("metta", try_relative_path=False)
        for page in sorted((root / "website/reference").glob("metta*.md")):
            match = SOURCE.search(page.read_text(encoding="utf-8"))
            if match and "/ext/" in match[1]:
                self.loader.load(pathlib.Path(match[1]).stem, try_relative_path=False)
        # A callable module may be annotated as a Protocol in __init__.pyi.
        # Restore the loader's source modules before resolving their exports.
        # Griffe's hook and object model are documented in release 2.3.0:
        # https://github.com/mkdocstrings/griffe/releases/tag/2.3.0
        for name, module in sorted(capture.modules.items(), key=lambda item: item[0].count(".")):
            self.loader.modules_collection.set_member(name, module)
        self.loader.resolve_aliases(implicit=True, external=False)
        self.modules = capture.modules
        self.by_file = {module.filepath.resolve(): module for module in self.modules.values()}
        self.nodes: dict[pathlib.Path, dict[int, ast.AST]] = {}

    def target(self, module_path: str, title: str) -> griffe.Object:
        """Resolve a public class title or the module named by the page source."""
        module = self.by_file[(self.root / module_path).resolve()]
        try:
            target = self.loader.modules_collection.get_member(title)
        except KeyError:
            return module
        if target.is_alias:
            target = target.final_target
        return target if target.is_class else module

    def node(self, obj: griffe.Object) -> ast.AST:
        """Find the exact source definition retained by Griffe's line span."""
        path = obj.filepath
        if path not in self.nodes:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            self.nodes[path] = {
                line: node for node in ast.walk(tree)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                for line in (node.lineno, *(decorator.lineno for decorator in node.decorator_list))
            }
        return self.nodes[path][obj.lineno]


def public_members(module: griffe.Module) -> list[tuple[str, griffe.Object]]:
    """Follow explicit exports, or source definitions when no export list exists."""
    names = module.exports if module.exports is not None else [
        name for name, member in module.members.items()
        if not name.startswith("_") and not member.is_alias
    ]
    found = []
    for name in names:
        member = module.members[name]
        if member.is_alias:
            member = member.final_target
        if member.is_function or member.is_class:
            found.append((name, member))
    return found


class PublicNames(ast.NodeTransformer):
    """Render import aliases using the names their documented types expose."""

    def __init__(self, module: griffe.Module, graph: SourceGraph) -> None:
        """Read the module imports and root export names."""
        self.bindings = {name: member.target_path for name, member in module.members.items() if member.is_alias}
        self.exports = {}
        core = graph.modules["metta"]
        for name in core.exports or ():
            member = core.members[name]
            if member.is_alias:
                self.exports[member.target_path] = name
                self.exports[member.final_target.path] = name

    def spelling(self, name: str) -> ast.expr | None:
        """Replace an imported binding, leaving local names and values intact."""
        first, separator, rest = name.partition(".")
        if first not in self.bindings:
            return None
        canonical = self.bindings[first] + (separator + rest if separator else "")
        if canonical in self.exports:
            public = self.exports[canonical]
        elif canonical.startswith(("builtins.", "typing.", "collections.abc.")):
            public = canonical.rsplit(".", 1)[-1]
        elif canonical.startswith("metta."):
            public = canonical.removeprefix("metta.")
            if public.startswith("_"):
                public = canonical.rsplit(".", 1)[-1]
        else:
            public = canonical
        return ast.parse(public, mode="eval").body

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        """Resolve a complete imported attribute before visiting its prefix."""
        return self.spelling(ast.unparse(node)) or self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        """Resolve a named type alias."""
        return self.spelling(node.id) or node


def declaration_node(graph: SourceGraph, obj: griffe.Object, name: str) -> ast.AST:
    """Format a detached signature without changing the loader's source graph."""
    node = copy.copy(graph.node(obj))
    node.name = name
    node.body = [ast.Pass()]
    node.decorator_list = []
    return PublicNames(obj.module, graph).visit(copy.deepcopy(node))


def object_entries(graph: SourceGraph, name: str, obj: griffe.Object) -> list[str]:
    """Publish an exported identity and the methods its class actually inherits."""
    node = declaration_node(graph, obj, name)
    doc = obj.docstring.value if obj.docstring else None
    if obj.is_function:
        return [entry(f"## `{name}`", signature(node), doc)]
    out = [entry(f"## `{name}`", class_line(node), doc)]
    for method, inherited in obj.all_members.items():
        if method.startswith("_") and not (method.startswith("__") and method.endswith("__")):
            continue
        member = inherited.final_target if inherited.is_alias else inherited
        if not (member.is_function or "property" in member.labels):
            continue
        sub = declaration_node(graph, member, method)
        out.append(entry(f"### `{name}.{method}`", signature(sub),
                         member.docstring.value if member.docstring else None))
    return out


def page_for(module_path: str, title: str, *, graph: SourceGraph | None = None) -> str:
    """Render one public module or class, including aliases and inherited APIs."""
    graph = graph or SourceGraph(ROOT)
    obj = graph.target(module_path, title)
    source = obj.filepath.relative_to(graph.root).as_posix()
    head = [f"# `{title}`", "", f"Source: `{source}`.", "",
            "<!-- Generated by extensions/python/tools/reference.py from the named source and its imports; lane=reference. -->", ""]
    if obj.docstring:
        head += [quote(obj.docstring.value), ""]
    head += [PREAMBLE, "", ""]
    members = [(obj.name, obj)] if obj.is_class else public_members(obj)
    body = [text for name, member in members for text in object_entries(graph, name, member)]
    return ("\n".join(head) + "\n".join(body)).rstrip() + "\n"


def sources(*, graph: SourceGraph | None = None) -> list[tuple[pathlib.Path, str, str]]:
    """Keep existing URLs and discover new public modules from the directory."""
    graph = graph or SourceGraph(ROOT)
    pages = graph.root / "website/reference"
    found = []
    covered = set()
    for page in sorted(pages.glob("metta*.md")):
        if page.name == "metta-libraries.md":
            continue
        text = page.read_text(encoding="utf-8")
        match = SOURCE.search(text)
        if match is None:
            message = f"{page.name} carries no Source line"
            raise ValueError(message)
        title = text.splitlines()[0].strip("# `")
        obj = graph.target(match[1], title)
        source = obj.filepath.relative_to(graph.root).as_posix()
        covered.add(obj.path)
        found.append((page, source, title))
    core = graph.root / "extensions/python/metta"
    names = ["metta", *("metta." + info.name for info in pkgutil.iter_modules([str(core)])
                        if not info.name.startswith("_"))]
    for name in names:
        if name in covered:
            continue
        obj = graph.modules[name]
        page = pages / (name.replace(".", "-") + ".md")
        if any(old == page for old, _, _ in found):
            message = f"reference URL collision: {page.name}"
            raise ValueError(message)
        found.append((page, obj.filepath.relative_to(graph.root).as_posix(), name))
    return sorted(found)


def page_titles(projections: dict[pathlib.Path, str], root: pathlib.Path = ROOT) -> dict[pathlib.Path, str]:
    """Read all reference pages, including independently generated catalogs."""
    pages = {page: page.read_text(encoding="utf-8") for page in (root / "website/reference").glob("*.md")}
    pages.update(projections)
    return {
        path: match[1].replace("`", "")
        for path, text in sorted(pages.items())
        if path.name != "index.md" and (match := re.search(r"^# (.+)$", text, re.MULTILINE))
        and not re.match(r"---\n.*?navigation: false\n", text, re.DOTALL)
    }


def navigation(titles: dict[pathlib.Path, str]) -> str:
    """Generate VitePress's reference items from the page directory."""
    rows = ['          { text: "Module index", link: "/reference/" },']
    rows.extend("          { text: " + json.dumps(title) + ', link: "/reference/' + page.stem + '" },'
                for page, title in titles.items())
    return "\n".join(rows)


def region(text: str, begin: str, end: str, body: str) -> str:
    """Replace one ordered region, retaining the page's authored surroundings."""
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
        message = f"reference requires one ordered generated region: {begin}"
        raise ValueError(message)
    before, rest = text.split(begin)
    _, after = rest.split(end)
    return before + begin + "\n" + body + "\n" + end + after


def projections(root: pathlib.Path = ROOT) -> dict[pathlib.Path, str]:
    """Generate the API pages, directory index and literal sidebar links together."""
    graph = SourceGraph(root)
    out = {page: page_for(source, title, graph=graph) for page, source, title in sources(graph=graph)}
    titles = page_titles(out, root)
    index = root / "website/reference/index.md"
    begin, end = "<!-- begin generated reference index -->", "<!-- end generated reference index -->"
    current = index.read_text(encoding="utf-8") if index.exists() else begin + "\n" + end + "\n"
    table = (
        "# API reference\n\n"
        "<!-- Generated by extensions/python/tools/reference.py from the public module and reference page directories; lane=reference. -->\n\n"
        "Each Python page reproduces public source signatures and docstrings, including exported aliases and inherited methods.\n\n"
        "| Reference |\n|---|\n" + "".join(f"| [{title}](./{page.stem}) |\n" for page, title in titles.items())
    )
    out[index] = region(current, begin, end, table.rstrip())
    config = root / "website/.vitepress/config.ts"
    start = "          // begin generated reference navigation"
    end = "          // end generated reference navigation"
    text = config.read_text(encoding="utf-8")
    out[config] = region(text, start, end, navigation(titles))
    return out


def main(argv: list[str], *, root: pathlib.Path = ROOT) -> int:
    """Check every generated projection, or rewrite it with --write."""
    write = "--write" in argv
    stale = []
    for path, wanted in projections(root).items():
        if path.is_file() and path.read_text(encoding="utf-8") == wanted:
            continue
        stale.append(path.relative_to(root).as_posix())
        if write:
            path.write_text(wanted, encoding="utf-8")
    if stale:
        print(f"reference: {len(stale)} {'rewritten' if write else 'stale'} projections: " + ", ".join(stale))
    return int(bool(stale) and not write)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
