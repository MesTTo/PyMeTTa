"""Purpose: keep every generated MeTTa face and its Python module one authority.

Each face is regenerated from its own header and the result is required to
equal the file that is checked in.

A face names the module it wraps in its header, so this tool names none: it
reads `lib/*/*.metta`, takes the files whose header carries an `Import:` line,
and regenerates those. A library with no such header is hand-written and is not
this tool's business; a library whose module is not installed here is REPORTED
as unchecked rather than passed over in silence, the same split every other
lane draws between an absent toolchain and a failing one.

The finding is the drift itself: an upgrade that moves a signature shows the
lines that moved, and the repair is `--write` plus a reading of the diff. A
version bump alone is a NOTE, not a finding, because the face's header pins the
version it was READ from and renders the same bytes until someone rewrites it.

Assumes:
  - the interpreter running this is the one whose site-packages the faces were
    read from, which is what `select-python.sh` arranges for every lane
Guarantees:
  - the checked-in face equals what the module's own signatures produce, gated
    on every run [tested: test_the_torch_face_is_generated; commit=WORKTREE]
  - a face whose module is absent is named and skipped, so a box without the
    library reports what it could not check [tested:
    test_a_face_whose_module_is_absent_is_reported_and_skipped; commit=WORKTREE]
  - a planted signature change is reported with the lines that moved [tested:
    test_a_planted_signature_change_is_reported; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import difflib
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "extensions" / "python"))

from metta._errors.errors import MettaError  # noqa: E402
from metta.library._face import Face, read, render  # noqa: E402

#: Where a shipped face lives. One directory, because a MeTTa library IS the
#: shape a face ships in; a face outside it is named on the command line.
FACES = _REPO / "lib"

#: How many diff lines one drifted face prints before the rest are counted.
DIFF_LINES = 24


def face_paths(roots: list[pathlib.Path]) -> list[pathlib.Path]:
    """Every MeTTa source under the given roots, in one order on every box."""
    found: list[pathlib.Path] = []
    for root in roots:
        found.extend(sorted(root.glob("*/*.metta")) if root.is_dir() else [root])
    return found


def _named(path: pathlib.Path) -> str:
    """How a face is spelled in a finding: its repository path, or its name.

    A face under test lives in a temporary directory rather than under the
    repository, and a report that raises while naming its subject is worse
    than useless.
    """
    try:
        return str(path.relative_to(_REPO))
    except ValueError:
        return path.name


def _drift(path: pathlib.Path, current: str, wanted: str) -> str:
    """One face's drift, as the lines that moved."""
    diff = list(
        difflib.unified_diff(
            current.splitlines(),
            wanted.splitlines(),
            fromfile=f"{_named(path)} (checked in)",
            tofile="what the module's signatures say now",
            lineterm="",
            n=1,
        )
    )
    shown = diff[:DIFF_LINES]
    if len(diff) > DIFF_LINES:
        shown.append(f"... and {len(diff) - DIFF_LINES} more diff lines")
    return "\n".join(shown)


def review(
    paths: list[pathlib.Path], *, rewrite: bool
) -> tuple[list[str], list[str]]:
    """Check every face among these paths; answer its findings and its notes."""
    findings: list[str] = []
    notes: list[str] = []
    for path in paths:
        current = path.read_text(encoding="utf-8")
        manifest = read(current)
        if manifest is None:
            continue
        try:
            face = Face(manifest)
            wanted = face.text() if not rewrite else render(
                dataclasses.replace(manifest, versions=())
            )
        except ImportError as absent:
            notes.append(
                f"{_named(path)}: {absent.name} is not installed "
                f"here, so this face was not checked against it"
            )
            continue
        except MettaError as refused:
            findings.append(f"{_named(path)}: {refused}")
            continue
        for module, pinned, live in face.drifted_versions():
            notes.append(
                f"{_named(path)}: read from {module} {pinned}, and "
                f"{live} is installed here; `--write` moves the pin"
            )
        if current == wanted:
            continue
        if rewrite:
            path.write_text(wanted, encoding="utf-8")
            print(f"rewrote {_named(path)}")
            continue
        findings.append(
            f"{_named(path)} no longer matches the signatures its "
            f"module publishes: run `python {pathlib.Path(__file__).relative_to(_REPO)} "
            f"--write` and read the diff before committing it\n{_drift(path, current, wanted)}"
        )
    return findings, notes


def main(argv: list[str]) -> int:
    """Check every shipped face, or rewrite the ones that have drifted."""
    named = [pathlib.Path(word) for word in argv if not word.startswith("-")]
    findings, notes = review(
        face_paths(named or [FACES]), rewrite="--write" in argv
    )
    for note in notes:
        print(f"note: {note}")
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
