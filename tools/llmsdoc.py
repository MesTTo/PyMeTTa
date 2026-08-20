"""Purpose: check every checkable claim in llms.txt against the live engine and
the real file tree, so the file an LLM reads first cannot quietly rot.

It was written because llms.txt HAD rotted: six commits after it was last
touched it still named `m.fresh_space()` and `m.value()`, both renamed, and
documented `petta.matching` and `petta.measure`, both deleted, which is the
worst possible failure for a file whose whole purpose is to be believed
without being verified.

Assumes:
  - petta imports here, unlike bindings/python/tools/reference.py, which reads the AST
    so it can run without janus. Builtin names come from the running engine
    and there is no static inventory exposed to this checker
    [assumed: the supported builtin inventory is runtime-defined; commit=dcfc20be4933c19140ccb5759291401d13058301]
  - a backticked token containing a slash and ending in a known extension is
    a path claim, and nothing else in the file is shaped that way
    [source: bindings/python/tools/llmsdoc.py:PATH_LIKE and check; commit=dcfc20be4933c19140ccb5759291401d13058301]
Guarantees:
  - every petta name, MeTTa method, path, count, special form, derived form,
    builtin and library named in llms.txt exists, and the two modules it says
    are gone really are gone
    [tested: GATE_ONLY=1 sh check.sh llms; commit=dcfc20be4933c19140ccb5759291401d13058301]
  - all failures are reported at once, not just the first
    [source: bindings/python/tools/llmsdoc.py:check and main; commit=dcfc20be4933c19140ccb5759291401d13058301]
Fails when:
  - a claim is prose rather than a name, a count or a path. Those stay the
    reader's job; this checks what a machine can check
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib
import inspect
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "llms.txt"

BACKTICK = re.compile(r"`([^`\n]+)`")
PATH_LIKE = re.compile(r"^[\w./*-]+\.(?:md|py|pl|metta|sh|ipynb|toml|txt|json)$")
METHOD = re.compile(r"\bm\.([a-z_]\w*)")
PETTA_ATTR = re.compile(r"\bpetta\.([a-z_]\w*)(?:\.([a-z_]\w*))?")
SECTION = re.compile(r"^## (.+)$", re.MULTILINE)


def sections(text: str) -> dict[str, str]:
    """The file split by its own `##` headings."""
    marks = list(SECTION.finditer(text))
    out = {}
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[mark.group(1)] = text[mark.end() : end]
    return out


def paragraph(text: str, opening: str) -> str:
    """The one paragraph whose opening matches `opening`, as a regex.

    A regex rather than a literal prefix because these paragraphs open with
    a COUNT, and the count is already checked, separately and exactly, by
    counts(). Written as a literal, the locator was a second copy of the
    number: registering one more builtin made this raise "no longer has a
    paragraph opening '209 builtins are registered'", which names a missing
    paragraph rather than a stale count and points at the wrong file.
    """
    for block in text.split("\n\n"):
        if re.match(opening, block.lstrip()):
            return block
    raise AssertionError(f"llms.txt no longer has a paragraph opening {opening!r}")


def fenced(text: str) -> list[str]:
    """Every fenced code block's body."""
    return re.findall(r"^```\w*\n(.*?)^```", text, re.MULTILINE | re.DOTALL)


def engine_vocabulary() -> tuple[set[str], set[str], set[str]]:
    """Builtins from the running engine; the two translated sets from source.

    The special forms are the heads of translate_special_dl/5, read the way
    engine/translator.pl says to read them: from the clauses themselves, so a
    form added there is covered the day it is added. The derived forms are the
    names engine/prelude.metta registers with add-translator-rule!, read the same
    way, which is where a form goes when it leaves the compiler.
    """
    sys.path.insert(0, str(ROOT / "bindings" / "python"))
    from petta import MeTTa

    builtins = set(MeTTa().builtins())
    special = set()
    for source in sorted((ROOT / "engine").glob("*.pl")):
        body = source.read_text()
        special |= {
            head.strip("'")
            for head in re.findall(r"^translate_special_dl\(\s*('?[^,']+'?)", body, re.MULTILINE)
        }
    derived = set(
        re.findall(
            r"^!\(add-translator-rule!\s+([^\s)]+)\)",
            (ROOT / "engine" / "prelude.metta").read_text(),
            re.MULTILINE,
        )
    )
    return builtins, special, derived


def counts() -> list[tuple[str, int]]:
    """Each dated count in llms.txt, with what the tree says it is now."""
    src_lines = sum(
        len(p.read_text().splitlines()) for p in sorted((ROOT / "engine").glob("*.pl"))
    )
    main = (ROOT / "bindings" / "python" / "petta" / "__main__.py").read_text()
    # The example count comes from the runners' own definition rather than a
    # glob. A bare examples/**/*.metta answers 242, which counts 24 symlink
    # aliases for files already in the list and 12 fixtures that are inputs
    # rather than programs, so the gate endorsed a number no runner uses
    # [measured 2026-08-18: 242 paths, 218 regular files, 206 discovered,
    # 200 run]. examples/README.md and this file disagreed with each other
    # and with the runner, each by a different amount.
    sys.path.insert(0, str(ROOT / "bindings" / "python" / "tools"))
    from example_parity import corpus

    return [
        (r"(\d+) executable programs", len(corpus())),
        (r"(\d+) pages reproducing source", len(list(ROOT.glob("website/reference/petta-*.md")))),
        (r"(\d+) plunit suites", len(list(ROOT.glob("tests/prolog/*.plt")))),
        (r"(\d+) files, blackbox", len(list(ROOT.glob("bindings/python/tests/*.py")))),
        (r"(\d+) pages of prose", len(list(ROOT.glob("website/guide/*.md")))),
        (r"(\d+) numbered lessons", len(list(ROOT.glob("website/tutorials/[0-9]*.md")))),
        (r"(\d+) runnable Python programs", len(list(ROOT.glob("bindings/python/examples/*/*.py")))),
        (r"([\d,]+) lines: `engine/metta.pl`", src_lines),
        (r"(\d+) MeTTa libraries loaded", len(list(ROOT.glob("lib/lib_*.metta")))),
        (r"(\d+) libraries load with", len(list(ROOT.glob("lib/lib_*.metta")))),
        (r"(\d+) builtins are registered", -1),
        (r"has (six|five|seven) subcommands", main.count("commands.add_parser(")),
    ]


WORDS = {"five": 5, "six": 6, "seven": 7}


def _absent_artefact_diagnosis(stated: int, actual: int, root: pathlib.Path = ROOT) -> str | None:
    """The missing-build-product reading of a builtin-count mismatch.

    Each backend under backends/ loads only where its artefact exists and
    declares what it would register as metta_backend_builtin/1 facts in its
    implementation file. When the stated count exceeds the live one by
    exactly the declarations of backends whose artefacts are absent here,
    the mismatch is this checkout's configuration, not documentation drift,
    and the answer is to name the artefact rather than fail the claim.
    """
    absent: list[tuple[str, list[str]]] = []
    fact = re.compile(r"^metta_backend_builtin\('?([^')]+)'?\)\.", re.MULTILINE)
    # Per-integration discovery: any fact-bearing implementation under a
    # backend's folder, its artefact the crate build beside it, so a new
    # backend is a new folder and this diagnosis needs no edit.
    for backend in sorted(root.glob("backends/*/**/*.pl")):
        names = fact.findall(backend.read_text())
        if not names:
            continue
        release = backend.parent / "target" / "release"
        if release.is_dir() and any(release.glob("*.so")):
            continue
        artefact = release / f"lib{backend.parent.name}.so"
        absent.append((str(artefact.relative_to(root)), names))
    missing = sum(len(names) for _, names in absent)
    if missing and stated == actual + missing:
        parts = "; ".join(
            f"{artefact} would register {', '.join(names)}"
            for artefact, names in absent
        )
        return (
            f"the builtin count reads {actual} here where llms.txt says "
            f"{stated}, and the whole difference is this checkout's missing "
            f"build product, not doc drift: {parts}. Build it (sh build.sh "
            f"in the backend's directory) or symlink the main checkout's "
            f"target/ into this worktree."
        )
    return None


def check() -> list[str]:
    """Every failed claim, in reading order."""
    text = DOC.read_text()
    parts = sections(text)
    bad: list[str] = []

    sys.path.insert(0, str(ROOT / "bindings" / "python"))
    import petta
    from petta import MeTTa

    for name in sorted(set(METHOD.findall(text))):
        if name.endswith("_"):        # m.declare_*, a family rather than a method
            continue
        if not hasattr(MeTTa, name):
            bad.append(f"MeTTa has no method m.{name}")

    gone = {"matching", "measure"}
    groups = {petta.integrate.ENTRY_POINT_GROUP, petta.integrate.SPACES_GROUP, petta.integrate.LIBRARIES_GROUP}
    for module, member in sorted(set(PETTA_ATTR.findall(text))):
        if module in gone or f"petta.{module}" in groups and not member:
            continue
        found = getattr(petta, module, None)
        if found is None:
            try:
                found = importlib.import_module(f"petta.{module}")
            except ImportError:
                bad.append(f"petta has no attribute or submodule petta.{module}")
                continue
        if member and not hasattr(found, member):
            bad.append(f"petta.{module} has no attribute {member}")
    # A deleted module may be NAMED, but only in the sentence saying it is gone.
    # Skipping the name everywhere is how "there is no petta.matching" would
    # have covered for a later paragraph using it as though it were live.
    denial = paragraph(parts["The MeTTa language surface"], r"\d+ libraries load with")
    for module in sorted(gone):
        if (ROOT / "bindings" / "python" / "petta" / f"{module}.py").exists():
            bad.append(f"llms.txt says petta.{module} is gone, but the module is back")
        elif text.count(f"petta.{module}") != denial.count(f"petta.{module}"):
            bad.append(f"petta.{module} is deleted but llms.txt names it outside the sentence saying so")

    for token in sorted({t for t in BACKTICK.findall(text) if "/" in t and PATH_LIKE.match(t)}):
        if not list(ROOT.glob(token)):
            bad.append(f"path claim resolves to nothing: {token}")

    builtins, special, derived = engine_vocabulary()
    language = parts["The MeTTa language surface"]
    for form in fenced(language)[0].split():
        if form not in special:
            bad.append(f"{form} is listed as a special form but is not a translate_special_dl head")
    written_in_metta = paragraph(language, r"\w+ more are written in MeTTa")
    for name in BACKTICK.findall(written_in_metta):
        if name not in derived:
            bad.append(f"{name} is listed as a derived form but engine/prelude.metta registers no rule for it")
    registered = paragraph(language, r"\d+ builtins are registered")
    for name in BACKTICK.findall(registered):
        if name.startswith("m.") or name.endswith(")") or "*" in name or name == "#":
            continue
        if name not in builtins:
            bad.append(f"{name} is listed as a builtin but the engine does not register it")
    for name in BACKTICK.findall(paragraph(language, r"\d+ libraries load with")):
        if name.startswith("lib_") and not (ROOT / "lib" / f"{name}.metta").exists():
            bad.append(f"library claim resolves to nothing: lib/{name}.metta")

    for pattern, actual in counts():
        builtins_claim = actual == -1
        if builtins_claim:
            actual = len(builtins)
        found = re.search(pattern, text)
        if not found:
            bad.append(f"llms.txt no longer states the count matching /{pattern}/")
            continue
        stated = found.group(1)
        value = WORDS.get(stated, None) or int(stated.replace(",", ""))
        if value != actual:
            # The builtin count is the one claim that carries a CONFIGURATION:
            # a backend registers builtins only where its artefact is built,
            # so a worktree without the build product reads falsely red. The
            # backends declare those registrations as metta_backend_builtin/1
            # facts, so a mismatch that the absent artefact fully explains is
            # diagnosed by name instead of reported as doc drift
            # [tested:
            # test_the_llms_builtin_claim_holds_in_a_bare_configuration].
            diagnosis = _absent_artefact_diagnosis(value, actual) if builtins_claim else None
            if diagnosis:
                # The claim HOLDS under the stated configuration: the doc
                # counts the full build and this checkout verifiably lacks
                # exactly the named artefact's registrations, so the lane
                # compares like with like and passes with the note.
                print(diagnosis)
            else:
                bad.append(f"llms.txt says {stated} where the tree has {actual} (/{pattern}/)")

    declared = re.search(r"`match`, `enumerate`(.*?)refuses loudly", text, re.DOTALL)
    if declared is None:
        bad.append("llms.txt no longer lists the provider capabilities")
    else:
        listed = ("match", "enumerate", *BACKTICK.findall(declared.group(1)))
        if listed != petta.foreign.CAPABILITIES:
            bad.append(f"capabilities differ: llms.txt {listed}, engine {petta.foreign.CAPABILITIES}")

    services = re.search(r"whole permitted inward surface\n\((.*?)\), and", text, re.DOTALL)
    if services is None:
        bad.append("llms.txt no longer lists the ext_points service seams")
    else:
        listed = set(BACKTICK.findall(services.group(1)))
        real = set(
            re.findall(
                r"^ext_point_kind\(([\w/]+), service\)", (ROOT / "engine" / "ext_points.pl").read_text(), re.MULTILINE
            )
        )
        if listed != real:
            bad.append(f"service seams differ: llms.txt missing {sorted(real - listed)}, extra {sorted(listed - real)}")

    # Read from the frozenset rather than a second copy of it here: a hand-kept
    # list is the same rot this whole lane exists to catch.
    lazy = paragraph(parts["Apps, from source"], r"\w+ submodules")
    listed = {name for name in BACKTICK.findall(lazy) if name != "import petta"}
    real = set(petta._LAZY_MODULES) | set(petta._LAZY_ATTRIBUTES)
    if listed != real - {"Boot"}:
        bad.append(f"lazy submodules differ: missing {sorted(real - {'Boot'} - listed)}, extra {sorted(listed - real)}")
    if not inspect.getsource(petta).count("def __getattr__"):
        bad.append("petta no longer lazy-loads submodules, so llms.txt's lazy list is wrong")

    return bad


def main() -> int:
    """Report every failed claim; nonzero when any failed."""
    bad = check()
    for line in bad:
        print(f"llms.txt: {line}")
    if bad:
        print(f"{len(bad)} claim(s) in llms.txt no longer hold")
        return 1
    print("llms.txt: every checkable claim holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
