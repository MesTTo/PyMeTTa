"""Purpose: keep examples/ORIGINS.tsv true.

ORIGINS.tsv is the attribution for the example programs that derive from
another author's work.

An attribution nobody recomputes is a claim that rots: examples get added,
edited and reorganised, and a hand-kept list quietly stops describing the
directory. This derives the list instead, by comparing each example's body
against the upstream checkout, so the citation is a measurement.

Comparison ignores comments and blank lines, because reorganising the
examples added a header to many of them without touching the program. A body
that survives whole scores 1.0; anything at or above THRESHOLD is recorded as
derived, with its score, so a reader can see how much is the original author's.

Assumes:
  - the upstream checkout is beside this repository, or named by
    METTA_UPSTREAM; without it the check skips rather than failing, since a
    contributor's tree need not carry it
Guarantees:
  - --write rewrites examples/ORIGINS.tsv, and a plain run answers nonzero when
    the committed file no longer describes the tree
    [tested: test_the_manifest_still_describes_the_tree]
  - every recorded pair names a file that exists on both sides, with the
    authors who wrote it upstream
    [tested: test_every_derived_example_names_its_source_and_its_authors]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

from example_parity import corpus

#: Below this, a resemblance is coincidence rather than derivation. Chosen
#: because the examples between 0.75 and 0.85 are recognisably the same
#: program with an edited body, and nothing between 0.5 and 0.75 was.
THRESHOLD = 0.75

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "examples" / "ORIGINS.tsv"

UPSTREAM_SOURCE = "https://github.com/patham9/PeTTa"
UPSTREAM_COMMIT = "43705f5d9ff8958ffe7f0aa6777fb8477f2401f2"
UPSTREAM_DATE = "2026-07-24"


def readme_counts(text: str, *, derived_count: int, total: int,
                  credited: int, runnable: int) -> str:
    """Refresh the README's corpus and lineage counts from the same census.

    Missing prose anchors refuse rather than replacing unrelated text
    [tested: tests/checks/check_library_records_selftest.py; commit=9b22993447a5ddba93643895e3025661ba9f693e].
    """
    claims = (
        (r"The merged corpus contains \d+ examples", f"The merged corpus contains {runnable} examples"),
        (r"\d+ of the \d+ programs here derive", f"{derived_count} of the {total} programs here derive"),
        (r"(?:Thirteen|\d+) people wrote them", f"{credited} people wrote them"),
        (r"The other\s+\d+ examples were written", f"The other\n{total - derived_count} examples were written"),
    )
    for pattern, replacement in claims:
        text, found = re.subn(pattern, replacement, text)
        if found != 1:
            message = f"README count anchor missing or repeated: {pattern}"
            raise ValueError(message)
    return text


def upstream_root() -> Path | None:
    """The upstream checkout, or None when this tree does not carry one."""
    named = os.environ.get("METTA_UPSTREAM")
    candidates = [Path(named)] if named else []
    candidates.append(REPO.parent / "PeTTa-base")
    return next((p for p in candidates if (p / "examples").is_dir()), None)


def authors(root: Path, relative: str) -> str:
    """Who wrote an upstream file, most commits first.

    Per file rather than per project: thirteen people wrote the upstream files
    these examples come from, and naming only the most prolific would
    miscredit the rest.
    """
    result = subprocess.run(  # noqa: S603  -- git, on a path this tool derived
        ["git", "log", "--format=%an", "--follow", "--", relative],  # noqa: S607  -- git from PATH, not this box's copy of it
        cwd=root, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return ""
    counted: dict[str, int] = {}
    for line in result.stdout.splitlines():
        name = line.strip()
        if name and name != "unknown":
            counted[name] = counted.get(name, 0) + 1
    return "; ".join(sorted(counted, key=lambda n: (-counted[n], n)))


def body(path: Path) -> str:
    """The program, without comments or blank lines."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return "\n".join(
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(";")
    )


def derived(root: Path) -> list[tuple[str, str, float, str]]:
    """Every example whose body comes from upstream, with how much survives."""
    upstream = [(p, body(p)) for p in sorted(root.rglob("*.metta"))]
    identical = {}
    for path, text in upstream:
        identical.setdefault(text, str(path.relative_to(root)))

    rows: list[tuple[str, str, float, str]] = []
    for path in sorted((REPO / "examples").rglob("*.metta")):
        text = body(path)
        if not text:
            continue
        ours = str(path.relative_to(REPO))
        if text in identical:
            rows.append((ours, identical[text], 1.0, authors(root, identical[text])))
            continue
        best, score = None, 0.0
        for candidate, upstream_text in upstream:
            matcher = difflib.SequenceMatcher(None, text, upstream_text)
            # quick_ratio is an upper bound, so a low one cannot become a hit.
            if matcher.quick_ratio() <= THRESHOLD - 0.15:
                continue
            ratio = matcher.ratio()
            if ratio > score:
                best, score = candidate, ratio
        if best is not None and score >= THRESHOLD:
            relative = str(best.relative_to(root))
            rows.append((ours, relative, round(score, 3), authors(root, relative)))
    return rows


def render(rows: list[tuple[str, str, float, str]], total: int) -> str:
    """The manifest, header and all."""
    credited = sorted({name for *_, names in rows for name in names.split("; ") if name})
    header = f"""# Origins of the MeTTa examples.
#
# License: MIT
# Source: {UPSTREAM_SOURCE}
# Commit: {UPSTREAM_COMMIT}
# Date: {UPSTREAM_DATE}
#
# The {len(rows)} example programs listed below derive from that project's MeTTa
# sources. The search covers every .metta file it ships, not only its examples
# directory, because crediting too widely is the safe direction for an
# attribution. They were reorganised into the reading order this directory uses,
# and some were edited. Each row names the file it came from, how much of the
# upstream body survives with comments ignored (1.0 being unchanged), and who
# wrote it there, most commits first.
#
# Credited across those files, {len(credited)} authors:
# {", ".join(credited)}.
#
# The other {total - len(rows)} examples in this directory were written here.
#
# Regenerate with: python extensions/python/tools/example_origins.py --write
#
# ours\tupstream\tbody-retained\tupstream-authors
"""
    return header + "".join(f"{a}\t{b}\t{c}\t{d}\n" for a, b, c, d in rows)


def main(argv: list[str] | None = None) -> int:
    """Write or check the manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite the manifest")
    arguments = parser.parse_args(argv)

    root = upstream_root()
    if root is None:
        print("no upstream checkout; set METTA_UPSTREAM to check the attribution")
        return 0

    rows = derived(root)
    total = len(list((REPO / "examples").rglob("*.metta")))
    rendered = render(rows, total)
    readme = REPO / "examples/README.md"
    current_readme = readme.read_text(encoding="utf-8")
    credited = {name for *_, names in rows for name in names.split("; ") if name}
    try:
        wanted_readme = readme_counts(current_readme, derived_count=len(rows), total=total,
                                      credited=len(credited), runnable=len(corpus(REPO)))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if arguments.write:
        MANIFEST.write_text(rendered)
        readme.write_text(wanted_readme, encoding="utf-8")
        print(f"{MANIFEST.relative_to(REPO)}: {len(rows)} derived, {total - len(rows)} original")
        return 0
    if not MANIFEST.exists():
        print(f"{MANIFEST.relative_to(REPO)} is missing; run with --write")
        return 1
    committed = MANIFEST.read_text()
    if committed != rendered:
        print(f"{MANIFEST.relative_to(REPO)} no longer describes examples/; run with --write")
        #Print WHICH rows moved. The recomputation reads a sibling working tree
        #for the upstream side, so a disagreement can come from this repository
        #or from that checkout walking on, and the two are different defects
        #wearing the same sentence. Once, during a gate, this lane failed and
        #then passed on every rerun with examples/ holding an unchanged set of
        #254 .metta files; with only the sentence above there was nothing to
        #attribute it to.
        difference = list(
            difflib.unified_diff(
                committed.splitlines(), rendered.splitlines(),
                fromfile="committed", tofile="recomputed", lineterm="", n=0,
            )
        )
        for line in difference[:20]:
            print(line)
        if len(difference) > 20:
            print(f"... {len(difference) - 20} more line(s)")
        return 1
    if current_readme != wanted_readme:
        print("examples/README.md corpus or origin counts drifted; run with --write")
        return 1
    print(f"{MANIFEST.relative_to(REPO)}: {len(rows)} derived, {total - len(rows)} original")
    return 0


if __name__ == "__main__":
    sys.exit(main())
