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
  - a clone of the upstream holding UPSTREAM_COMMIT is beside this repository
    or beside its main checkout, or is named by METTA_UPSTREAM; without any
    clone the check skips rather than failing, since a contributor's tree need
    not carry one
Guarantees:
  - the attribution is read at UPSTREAM_COMMIT out of the clone's object
    store, so METTA_UPSTREAM names a clone and never a revision: a clone's
    working tree, its later history and its untracked files never reach the
    rows, and a clone that lacks the commit is refused by the commit's name
    [tested 2026-09-25T04:49:10+10:00: test_example_origins_reads_the_pinned_commit_from_any_clone,
    test_example_origins_refuses_a_clone_without_its_commit]
  - with no clone found the lane exits 125, which the gate reports as
    skipped under MEASURED NOTHING rather than as a pass
    [tested 2026-09-25T04:58:12+10:00: test_example_origins_measures_nothing_without_a_clone]
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
from pathlib import Path, PurePosixPath

from example_parity import corpus

#: Below this, a resemblance is coincidence rather than derivation. Chosen
#: because the examples between 0.75 and 0.85 are recognisably the same
#: program with an edited body, and nothing between 0.5 and 0.75 was.
THRESHOLD = 0.75

# Derived inline rather than through `metta._roots`, because this tool runs as a
# SCRIPT: `python tools/example_origins.py` puts tools/ on sys.path and not the seat, so the
# package holding the resolver is not importable yet. Same rule as the seat's own
# bootstrap files, and the marker is the workspace's, the tree holding engine/ and lib/.
REPO = next(parent for parent in Path(__file__).resolve().parents
       if (parent / "engine").is_dir() and (parent / "lib").is_dir())
MANIFEST = REPO / "examples" / "ORIGINS.tsv"

UPSTREAM_SOURCE = "https://github.com/patham9/PeTTa"
UPSTREAM_COMMIT = "43705f5d9ff8958ffe7f0aa6777fb8477f2401f2"
UPSTREAM_DATE = "2026-07-24"
#: Where a clone is looked for when METTA_UPSTREAM names none, in order: the
#: attribution's own upstream, then the parity lane's newer one, whose history
#: holds UPSTREAM_COMMIT as well.
CLONES = ("PeTTa-base", "PeTTa-upstream")


class MissingCommitError(Exception):
    """A clone was found and none of the clones holds the commit the attribution is read at."""


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
    """The clone the attribution is read from, or None when this tree has no clone.

    METTA_UPSTREAM names a CLONE and never a revision. The rows are read at
    UPSTREAM_COMMIT out of the clone's object store, whatever its working tree
    holds, because the parity lane exports the same variable for its own,
    newer upstream: read from that clone's working tree, its later history
    and its untracked ai_fz_progs/ were credited as sources and this lane went
    red whenever the variable was set [measured 2026-09-24T23:21:26+10:00: unset or naming
    PeTTa-base the lane passed with 143 derived, naming PeTTa-upstream it
    failed on ai_fz_progs rows]. Both upstreams hold UPSTREAM_COMMIT, so
    either clone serves.

    Named, the one clone is the only candidate, since an operator who says
    where it is outranks anything inferred. Otherwise each of CLONES beside
    this tree, then beside the main checkout: a worktree's parent is not the
    checkout's parent, and every gate runs in one, so `--git-common-dir`, which
    names the MAIN .git from any tree, is where the siblings are found
    [measured 2026-09-25T04:48:15+10:00: from a linked worktree inside the main
    checkout, git rev-parse --git-common-dir answered the checkout's own .git
    while the worktree's parent was a directory inside that checkout].
    """
    named = os.environ.get("METTA_UPSTREAM")
    if named:
        candidates = [Path(named)]
    else:
        parents = [REPO.parent]
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],  # noqa: S607  -- git from PATH
            cwd=REPO, capture_output=True, text=True, check=False,
        )
        if common.returncode == 0 and common.stdout.strip():
            parents.append(Path(common.stdout.strip()).parent.parent)
        candidates = [parent / name for parent in parents for name in CLONES]
    clones = [path for path in candidates if _git(path, "rev-parse", "--git-dir").returncode == 0]
    if not clones:
        return None
    for clone in clones:
        if _git(clone, "cat-file", "-e", f"{UPSTREAM_COMMIT}^{{commit}}").returncode == 0:
            return clone
    message = (
        f"no upstream clone holds {UPSTREAM_COMMIT}, the commit the attribution is read at: "
        f"looked in {', '.join(str(clone) for clone in clones)}; fetch {UPSTREAM_SOURCE} "
        f"into one of them, or name a clone that holds it with METTA_UPSTREAM"
    )
    raise MissingCommitError(message)


def _git(root: Path, *arguments: str, **options) -> subprocess.CompletedProcess:
    """Run git on one repository, with nothing inherited from the caller's position."""
    return subprocess.run(  # noqa: S603  -- git, on a path this tool derived or was named
        ["git", "-C", str(root), *arguments],  # noqa: S607  -- git from PATH, not this box's copy of it
        capture_output=True, check=False, **options,
    )


def upstream_sources(root: Path) -> list[tuple[str, str]]:
    """Every .metta file UPSTREAM_COMMIT holds, as (path, text), in path order.

    One ls-tree names the files and one cat-file --batch reads them all, so
    the cost is two processes whatever the file count. The order is by path
    COMPONENT, which is the order the working-tree walk this replaced gave:
    an identical body credits the first path holding it, and a tie between
    near matches keeps the first, so a string order that put `a-b/x` before
    `a/b` would move rows.
    """
    listing = _git(root, "ls-tree", "-r", "-z", "--format=%(objecttype) %(objectname) %(path)",
                   UPSTREAM_COMMIT)
    if listing.returncode != 0:
        message = f"git ls-tree {UPSTREAM_COMMIT} failed in {root}: {listing.stderr.decode(errors='replace')}"
        raise MissingCommitError(message)
    files = sorted(
        ((path, name) for kind, name, path in (entry.split(" ", 2) for entry in listing.stdout.decode().split("\0") if entry)
         if kind == "blob" and path.endswith(".metta")),
        key=lambda item: PurePosixPath(item[0]).parts,
    )
    batch = _git(root, "cat-file", "--batch", input="".join(f"{name}\n" for _, name in files).encode())
    if batch.returncode != 0:
        message = f"git cat-file --batch failed in {root}: {batch.stderr.decode(errors='replace')}"
        raise MissingCommitError(message)
    sources, at, out = [], 0, batch.stdout
    for path, _ in files:
        header_end = out.index(b"\n", at)
        size = int(out[at:header_end].rsplit(b" ", 1)[1])
        start = header_end + 1
        sources.append((path, out[start:start + size].decode("utf-8", errors="replace")))
        at = start + size + 1
    return sources


def authors(root: Path, relative: str) -> str:
    """Who wrote an upstream file up to UPSTREAM_COMMIT, most commits first.

    Per file rather than per project: thirteen people wrote the upstream files
    these examples come from, and naming only the most prolific would
    miscredit the rest.
    """
    result = _git(root, "log", UPSTREAM_COMMIT, "--format=%an", "--follow", "--", relative, text=True)
    if result.returncode != 0:
        return ""
    counted: dict[str, int] = {}
    for line in result.stdout.splitlines():
        name = line.strip()
        if name and name != "unknown":
            counted[name] = counted.get(name, 0) + 1
    return "; ".join(sorted(counted, key=lambda n: (-counted[n], n)))


def program(text: str) -> str:
    """A source's program, without comments or blank lines."""
    return "\n".join(
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(";")
    )


def derived(root: Path) -> list[tuple[str, str, float, str]]:
    """Every example whose body comes from upstream, with how much survives."""
    upstream = [(path, program(text)) for path, text in upstream_sources(root)]
    identical = {}
    for path, text in upstream:
        identical.setdefault(text, path)

    rows: list[tuple[str, str, float, str]] = []
    for path in sorted((REPO / "examples").rglob("*.metta")):
        text = program(path.read_text(encoding="utf-8", errors="replace"))
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
            rows.append((ours, best, round(score, 3), authors(root, best)))
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

    try:
        root = upstream_root()
        if root is None:
            # 125 is the gate's word for a run that compared nothing, which it
            # reads as skipped rather than ok; 0 here reported this lane as
            # passing wherever no clone could be found.
            print("no upstream clone, so nothing was compared; set METTA_UPSTREAM to check the attribution")
            return 125
        rows = derived(root)
    except MissingCommitError as missing:
        print(f"example_origins: {missing}", file=sys.stderr)
        return 1
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
