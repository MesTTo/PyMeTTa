"""Purpose: derive each library's licence row, `(= (package license) "E")` in its pkg.metta, from lib/.reuse/dep5.

A library's licence is the MeTTa Library Pack's own, the License field of the
map's header, for its own code, AND the licence of every paragraph of the map
naming one of its files: a file under its directory, or a file its lib.metta
imports by path, which is how the libraries reach the code they adapt under
_support/. That is the user's ruling of 2026-09-27 18:20, a licence per
library. The row sits in the manifest, which any implementation reads without
evaluating it, and get-property answers it like version
[tested 2026-09-27T22:23:18+10:00: packages:every_shipped_library_answers_its_licence_row].

Assumes:
  - the map is DEP-5 in SPDX identifiers, read by
    tools/host-notices/notices.py's own parser, the last paragraph whose Files
    names a file deciding it, as DEP-5 specifies
  - the library tree is a git work tree, whose tracked files are what the pack
    ships
  - a lib.metta imports a file by path as (import! &self (library "P")),
    resolved under the library tree, or as (import! &self "P"), resolved
    beside it, and the engine's own reader reads the forms
Guarantees:
  - every manifest's generated region holds one row, the sorted AND of the
    licences above; without --write, each manifest that differs, and one with
    no region, is a finding and the exit is 1
    [tested 2026-09-27T22:19:24+10:00: tests/checks/check_librarylicences_selftest.py]
  - a tracked file under a vendor/ directory that no paragraph names, as a
    file it covers or as a licence text, is a finding, so vendored code the map
    does not state cannot reach a row unstated; the pack's own notes there,
    VENDOR.md, README.md and SHA256SUMS, have their own paragraph
    [tested 2026-09-27T22:19:24+10:00: tests/checks/check_librarylicences_selftest.py]
Fails when: a library carries third-party code outside vendor/ that no
  paragraph names; its row then states the pack's licence for it, as the map
  does for every file no paragraph names.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / 'engine').is_dir() and (parent / 'lib').is_dir())
sys.path.insert(0, str(ROOT / "extensions" / "python"))
sys.path.insert(0, str(ROOT / "tools" / "host-notices"))

import notices  # noqa: E402 -- the one DEP-5 reader the hosts' notices use
from artifacts import notice, region  # noqa: E402 -- checkout generator

from metta._atoms.factories import Expression, Grounded, Symbol, parse  # noqa: E402
from metta._binding.positions import positioned_forms  # noqa: E402

BEGIN = "; begin generated licence"
END = "; end generated licence"
MANIFEST = "pkg.metta"
SOURCE = "lib.metta"
MAP = ".reuse/dep5"


def tracked(lib: Path) -> list[str]:
    """Every file the library tree's git index holds, relative to it."""
    listed = subprocess.run(  # noqa: S603 -- fixed git argv on the library tree this tool was named
        ["git", "-C", str(lib), "ls-files", "-z", "--", "."],  # noqa: S607  -- PATH git, as every lane runs it
        capture_output=True, text=True, check=True).stdout
    return sorted(name for name in listed.split("\0") if name)


def imported(lib: Path, library: str) -> list[str]:
    """The files LIBRARY's lib.metta imports by path, relative to the tree, outside its own directory."""
    source = lib / library / SOURCE
    if not source.is_file():
        return []
    out = []
    for form in positioned_forms(source.read_text(encoding="utf-8")):
        atom = parse(form.text)
        if not (isinstance(atom, Expression) and len(atom.children) == 3
                and atom.children[0] == Symbol("import!")):
            continue
        target = atom.children[2]
        if isinstance(target, Grounded) and isinstance(target.value, str):
            path = (lib / library / target.value).resolve()
        elif (isinstance(target, Expression) and len(target.children) == 2
              and target.children[0] == Symbol("library")
              and isinstance(target.children[1], Grounded) and isinstance(target.children[1].value, str)):
            path = (lib / target.children[1].value).resolve()
        else:
            continue
        if path.is_file() and path.is_relative_to(lib.resolve()) and not path.is_relative_to((lib / library).resolve()):
            out.append(path.relative_to(lib.resolve()).as_posix())
    return out


def terms(expression: str) -> list[str]:
    """The operands of an SPDX expression's top-level AND, a parenthesised group kept whole."""
    out, depth, start = [], 0, 0
    words = expression.split()
    for index, word in enumerate(words):
        depth += word.count("(") - word.count(")")
        if depth == 0 and word == "AND":
            out.append(" ".join(words[start:index]))
            start = index + 1
    out.append(" ".join(words[start:]))
    return [term for term in out if term]


def licence(tree: notices.Tree, own: str, files: list[str]) -> str:
    """The sorted AND of OWN and the licence of every paragraph naming one of FILES."""
    found = {own}
    for name in files:
        paragraph = tree.resolve(name)
        if paragraph is not None:
            found.update(terms(paragraph.synopsis))
    return " AND ".join(sorted(found))


def unstated(tree: notices.Tree, files: list[str]) -> list[str]:
    """Each tracked vendor/ file no paragraph names as a file it covers or as a licence text."""
    texts = {name for paragraph in tree.paragraphs for name in paragraph.fields.get("License-File", "").split()}
    return [f"{name}: under a vendor/ directory and named by no paragraph of {MAP}, so no row can state its licence"
            for name in files
            if "vendor" in Path(name).parts[:-1] and tree.resolve(name) is None and name not in texts]


def main(argv: list[str] | None = None) -> int:
    """Check every manifest's licence row, or rewrite each under --write."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--lib", type=Path, default=ROOT / "lib", help="the library tree, a git work tree")
    args = parser.parse_args(argv)
    lib = args.lib
    try:
        tree = notices.Tree("lib", lib.resolve())
        tree.add_map(lib / MAP, notices.read_pins([]))
    except notices.Refusal as refused:
        print(f"library-licences: {refused}")
        return 1
    own = tree.header.get("License", "").split("\n", 1)[0].strip()
    if not own:
        print(f"library-licences: {MAP}'s header states no License, the pack's own for its own code")
        return 1
    files = tracked(lib)
    problems = unstated(tree, files)
    stamp = "; " + notice(f"lib/lib_x/{MANIFEST}", content=BEGIN)
    written = 0
    for manifest in sorted(lib.glob(f"*/{MANIFEST}")):
        library = manifest.parent.name
        own_files = [name for name in files if Path(name).parts[0] == library]
        row = f'(= (package license) "{licence(tree, own, own_files + imported(lib, library))}")'
        text = manifest.read_text(encoding="utf-8")
        body = f"{stamp}\n{row}"
        wanted = (region(text, BEGIN, END, body) if BEGIN in text
                  else text.rstrip("\n") + f"\n\n{BEGIN}\n{body}\n{END}\n")
        if wanted == text:
            continue
        if args.write:
            manifest.write_text(wanted, encoding="utf-8")
            written += 1
        else:
            problems.append(f"{library}/{MANIFEST}: its licence row is not {row}; "
                            f"run python extensions/python/tools/librarylicences.py --write")
    for problem in problems:
        print(f"library-licences: {problem}")
    print(f"library-licences: {len(list(lib.glob(f'*/{MANIFEST}')))} manifests, {written} rewritten, "
          f"{len(problems)} finding(s)")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
