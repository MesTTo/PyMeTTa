"""Purpose: generate website/reference/petta-*.md from the modules they
document, so the page's own promise, "The entries below reproduce the source
signatures and docstrings", is true by construction rather than by hand.

Assumes:
  - every reference page names its module in a `Source: \\`path\\`.` line
    [tested test_every_reference_page_names_its_source]
  - petta.atoms and friends parse as ordinary Python, since this reads the AST
    and never imports: a page can be regenerated without a working janus
    [assumed 2026-08-16]
Guarantees:
  - the checked-in pages equal what this produces, gated on every run
    [tested test_the_reference_pages_are_up_to_date]
  - only public module-level classes and functions, and public methods of
    those classes, are documented, which is the set the pages already carried
    [source: bindings/python/tools/reference.py:entries, the three
    `startswith("_")` refusals at module level, class level and method level;
    commit=WORKTREE]
Fails when:
  - a page documents a module with runtime-generated members; those are
    invisible to the AST and would silently go missing
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PAGES = ROOT / "website" / "reference"
SOURCE = re.compile(r"^Source: `([^`]+)`\.$", re.MULTILINE)
PREAMBLE = "The entries below reproduce the source signatures and docstrings."
LINE_LENGTH = 100


def quote(text: str) -> str:
    """A docstring as a markdown blockquote, keeping its own line breaks."""
    lines = [escape_tags(line.rstrip()) for line in text.strip().splitlines()]
    return "\n".join(f"> {line}".rstrip() for line in lines)


CODE_SPAN = re.compile(r"(`+[^`]*`+)")


def escape_tags(line: str) -> str:
    """`<` in PROSE, so a docstring is not read as HTML.

    CommonMark parses `<obj>` as a raw HTML tag and the browser renders an
    unknown element as nothing, so "the space as (wrapped name <obj>)" lost
    the word it was about. Verified by rendering rather than by reading the
    spec: markdown-it leaves it as raw `<obj>` in the output.

    Only prose needs it, and only `<`. A bare `&` renders literally and `>`
    cannot open a tag; markdown-it escapes both code spans and indented code
    blocks by itself, so escaping those too would display the escape.
    """
    if line.startswith("    "):
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
    """`x: int=1` as `x: int = 1`. PEP 8 spaces the default of an ANNOTATED
    parameter and not of a bare one, and ast.unparse spaces neither."""
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


def is_overload(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """@overload declares a type, not a definition. Emitting all of them gave
    MeTTa.run four identical entries in the reference; the implementation is
    the one a reader is looking for."""
    return any(
        (isinstance(d, ast.Name) and d.id == "overload")
        or (isinstance(d, ast.Attribute) and d.attr == "overload")
        for d in node.decorator_list
    )


def class_line(node: ast.ClassDef) -> str:
    bases = [ast.unparse(base) for base in node.bases]
    bases += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords if kw.arg]
    return f"class {node.name}({', '.join(bases)}):" if bases else f"class {node.name}:"


def entry(heading: str, code: str, doc: str | None) -> str:
    body = quote(doc) if doc else "No docstring is defined."
    return f"{heading}\n\n```python\n{code}\n```\n\n{body}\n"


def entries(tree: ast.Module) -> list[str]:
    """Public module-level definitions, in source order, methods under their
    class. A leading underscore is private and a page never carried one."""
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            out.append(
                entry(f"## `{node.name}`", class_line(node), ast.get_docstring(node))
            )
            for sub in node.body:
                if (
                    isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not sub.name.startswith("_")
                    and not is_overload(sub)
                ):
                    out.append(
                        entry(
                            f"### `{node.name}.{sub.name}`",
                            signature(sub),
                            ast.get_docstring(sub),
                        )
                    )
        elif (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
            and not is_overload(node)
        ):
            out.append(entry(f"## `{node.name}`", signature(node), ast.get_docstring(node)))
    return out


def page_for(module_path: str, title: str) -> str:
    tree = ast.parse((ROOT / module_path).read_text(encoding="utf-8"))
    doc = ast.get_docstring(tree)
    head = [f"# `{title}`", "", f"Source: `{module_path}`.", ""]
    if doc:
        head += [quote(doc), ""]
    head += [PREAMBLE, "", ""]
    return "\n".join(head) + "\n".join(entries(tree))


def sources() -> list[tuple[pathlib.Path, str, str]]:
    """Every reference page, with the module it names and the title it uses."""
    found = []
    for page in sorted(PAGES.glob("petta-*.md")):
        text = page.read_text(encoding="utf-8")
        match = SOURCE.search(text)
        title = text.splitlines()[0].strip("# `")
        if match is None:
            raise SystemExit(
                f"{page.name} carries no `Source:` line, so nothing can say "
                f"which module it documents"
            )
        found.append((page, match.group(1), title))
    return found


def main(argv: list[str]) -> int:
    write = "--write" in argv
    stale = []
    for page, module_path, title in sources():
        wanted = page_for(module_path, title)
        if page.read_text(encoding="utf-8") == wanted:
            continue
        stale.append(page.name)
        if write:
            page.write_text(wanted, encoding="utf-8")
    if not stale:
        return 0
    if write:
        print(f"rewrote {len(stale)}: {', '.join(stale)}")
        return 0
    print(
        f"{len(stale)} reference page(s) no longer match their source: "
        f"{', '.join(stale)}\n"
        f"run `python bindings/python/tools/reference.py --write` to regenerate"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
