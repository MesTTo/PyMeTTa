"""Purpose: the engine's CODE names no host, permanently. Every host
reaches the engine through the declared seams (seam:extension_builtin,
seam:host_import, seam:host_object, seam:form_rewriter, the grounded
type family, the error hooks), and every per-host line lives in that
host's own hosts/ bridge, so the next host cannot regress the property by
editing the engine.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re
import subprocess
from pathlib import Path

import pytest

#: `py-` is here because MeTTa spells its names with hyphens and Prolog does
#: not: without it the pattern could match `py_arg_norm` and never `'py-list'`,
#: which is the spelling a host's BUILTINS actually take. That gap hid seven of
#: them for as long as they existed (see the scan root below).
_HOST_TOKEN = re.compile(r"\bpy_|\bpy-|\bpython|\bjanus", re.IGNORECASE)


def _engine_sources():
    """Every engine source, at any depth.

    This globbed `engine/*.pl`, one level, while the engine's code lives in
    `engine/metta/`, `engine/spaces/`, `engine/translator/` and
    `engine/filereader/` as well: 18 files scanned of 40. Both halves of that
    filter were load-bearing, and together they hid a real violation for as
    long as it existed. `engine/metta/effects.pl` carried seven
    `metta_builtin_effect_override('py-atom', oracleIO)` rows -- a list inside
    the engine naming a host's builtins, which is the exact property this file
    exists to forbid -- and it survived because it sat one directory too deep
    AND spelled its names with a hyphen. Measured 2026-08-28 against the tree
    before the fix: 7 offenders with both filters corrected, 0 with either one
    left in place.
    """
    root = Path(__file__).resolve().parents[4]
    return sorted((root / "engine").rglob("*.pl"))


@pytest.mark.parametrize(
    "source", _engine_sources(), ids=lambda p: str(p.relative_to(p.parents[1]))
)
def test_no_code_in_the_engine_names_a_host(source):
    """A comment may explain a host; a code line may not name one.

    The word boundary is what keeps copy_term/2 out of the count, the
    measured inflation the first census had. The tokens are the Python
    host's whole vocabulary; a new host's vocabulary joins this scan in
    the commit that adds its bridge.
    """
    offenders = []
    for number, line in enumerate(source.read_text().splitlines(), 1):
        if line.lstrip().startswith("%"):
            continue
        if _HOST_TOKEN.search(line):
            offenders.append(f"{source.name}:{number}: {line.strip()[:80]}")
    assert not offenders, (
        "the engine's code names a host; move the line behind a seam into "
        "the host's own bridge, declaring seam:extension_builtin/2 for a "
        "builtin and its effect class:\n" + "\n".join(offenders)
    )


def test_the_python_binding_calls_only_the_published_host_surface(repo_root):
    """The host transport's engine calls are all declared host_service.

    The same walk the backends' gate uses, aimed the other way down the
    wire: prolog_walk_code over extensions/python/metta with meta-predicate inference,
    against the measured list engine/ext_points.pl declares. A shim call to an
    undeclared engine internal fails this naming the pair.
    """
    done = subprocess.run(
        ["swipl", "-q", "-g",
         "consult(static_checks), consult('../../engine/metta.pl'), "
         "a_host_binding_calls_only_published_surface",
         "-t", "halt"],
        cwd=repo_root / "tests" / "prolog",
        capture_output=True,
        text=True,
        timeout=280,
    )
    assert done.returncode == 0, done.stderr
    assert "calls only published surface" in done.stdout
