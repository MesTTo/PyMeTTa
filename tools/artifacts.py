"""Purpose: declare generated artifacts and derive their checks and documentation.

Guarantees: graphlib orders producers before consumers; the same declaration
generates gate selection, literal commands and the contributor table [tested:
tests/checks/check_generated_artifact_group_selftest.py; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Fails when: an input, output or command is missing, output ownership overlaps,
dependencies cycle, or any generated projection drifts.
Decides: observed outputs require their explicit remeasurement command.
Ordinary --write only updates this manifest's shell and documentation regions.
Guarantees: what a generated file says about itself (`notice`) is read from the
same declared outputs the drift check reads, through `owner`, which names one
artifact per path and refuses none or two [tested:
ManifestTests.test_owner_and_notice_read_the_declared_outputs; commit=WORKTREE].
"""

from __future__ import annotations

import argparse
import fnmatch
import html
import re
import shlex
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = "@root/extensions/python/tools/"
SEAT = "extensions/python/metta/"
BEGIN = "# begin generated artifact selection"
END = "# end generated artifact selection"
LANES_BEGIN = "# begin generated artifact lanes"
LANES_END = "# end generated artifact lanes"
DOC_BEGIN = "<!-- begin generated artifact manifest -->"
DOC_END = "<!-- end generated artifact manifest -->"

Command = tuple[str, ...]


@dataclass(frozen=True)
class Output:
    """An owned file or region, optionally selected by its generated header."""

    path: str
    region: tuple[str, str] | None = None
    contains: str = ""
    remeasure: Command = ()

    def paths(self, root: Path) -> tuple[Path, ...]:
        """Resolve the declared output set without importing a generator."""
        return tuple(path for path in sorted(root.glob(self.path)) if path.is_file()
                     and (not self.contains or self.contains in path.read_text(encoding="utf-8")))

    def span(self, text: str) -> tuple[int, int]:
        """Locate exactly one owned interval, including its region delimiters."""
        if self.region is None:
            return 0, len(text)
        begin, stop = self.region
        start, end = text.find(begin), text.find(stop)
        if text.count(begin) != 1 or text.count(stop) != 1 or start >= end:
            message = f"missing or repeated output region: {self.path}: {begin}"
            raise ValueError(message)
        return start, end + len(stop)


@dataclass(frozen=True)
class Artifact:
    """One source contract, its projections, and executable discrimination."""

    name: str
    inputs: tuple[str, ...]
    emitter: Command
    outputs: tuple[Output, ...]
    check: Command
    witnesses: tuple[Command, ...]
    depends: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()


def tool(name: str, *args: str) -> Command:
    """Name a checkout tool with the gate's selected Python interpreter."""
    return ("@python", TOOLS + name + ".py", *args)


def suite(*targets: str) -> Command:
    """Use the seat runner and its interpreter, collection and cleanup policy."""
    return ("env", "CHECK_PY=@python", "sh", "@root/extensions/python/test.sh",
            *("@root/extensions/python/" + target if target.startswith("tests/") else target for target in targets))


ARTIFACTS = (
    Artifact(
        "artifact-sync", ("extensions/python/tools/artifacts.py",), tool("artifacts", "--write"),
        (Output("check.sh", (BEGIN, END)), Output("check.sh", (LANES_BEGIN, LANES_END)),
         Output("DEVELOPING.md", (DOC_BEGIN, DOC_END))),
        ("@python", "@root/tests/checks/check_generated_artifact_group.py"),
        (("@python", "@root/tests/checks/check_generated_artifact_group_selftest.py"),),
    ),
    Artifact(
        "layer-sync", (SEAT + "_layers.py",), tool("layergen", "--write"),
        (Output("pyproject.toml", ("# begin generated package layers", "# end generated package layers")),
         Output("DEVELOPING.md", ("<!-- begin generated package layers", "<!-- end generated package layers -->"))),
        tool("layergen"), (suite("tests/repository/test_layout_projections.py", "-k", "layergen"),
                           suite("tests/repository/test_lazy_loading.py"),
                           ("@python", "@root/tests/checks/check_layering_selftest.py")),
    ),
    Artifact(
        "bounds-sync", (SEAT + "_catalog/bounds.py",), tool("boundsgen", "--write"),
        (Output(SEAT + "_catalog/bounds.py", ("    # begin generated configure", "    # end generated configure")),
         Output("DEVELOPING.md", ("<!-- begin generated settings", "<!-- end generated settings -->"))),
        tool("boundsgen"), (suite("tests/repository/test_layout_projections.py", "-k", "boundsgen"),
                            suite("tests/ch01_getting_started/test_config.py"),
                            suite("tests/repository/test_artifact_projections.py", "-k", "setting_configuration")),
        requires=("engine for live setting witnesses",),
    ),
    Artifact(
        "vocab-sync", ("engine/**/*.pl", "lib/*/*.metta"), tool("vocabgen", "--write"),
        (Output(SEAT + "vocabularies.py"), Output("extensions/node/src/vocabularies.ts")),
        tool("vocabgen"), (suite("tests/repository/test_artifact_projections.py", "-k", "vocabulary"),),
        requires=("engine",),
    ),
    Artifact(
        "fn-sync", ("engine/**/*.pl", "lib/*/*.metta", SEAT + "_atoms/names.py",
                    "extensions/python/tools/phrasebook_entries.py"), tool("fngen", "--write"),
        (Output(SEAT + "_catalog/fn.py"),), tool("fngen"),
        (suite("tests/ch11_python_as_a_notation/test_mention_doors.py", "tests/repository/test_doc_emission.py"),),
        depends=("vocab-sync",), requires=("engine",),
    ),
    Artifact(
        "aio-mirror", (SEAT + "**/*.py", "extensions/python/ext/metta-*/*.py"), tool("aiogen", "--write"),
        (Output(SEAT + "_faces/space.py"), Output(SEAT + "_faces/metta.py"), Output(SEAT + "aio/_mirror.py")),
        tool("aiogen"), (suite("tests/repository/test_async_mirror.py"),),
        depends=("layer-sync", "vocab-sync"),
    ),
    Artifact(
        "init-stub", (SEAT + "__init__.pyi", SEAT + "vocabularies.py", SEAT + "_faces/*.py"),
        tool("rootgen", "--write"),
        (Output(SEAT + "__init__.py"),
         Output(SEAT + "__init__.pyi", ("# begin generated root imports", "# end generated root imports")),
         Output(SEAT + "__init__.pyi", ("# begin generated root declarations", "# end generated root declarations")),
         Output(SEAT + "__init__.pyi", ("# begin generated algebra declaration", "# end generated algebra declaration")),
         Output("extensions/python/tests/typing/algebra_surface.py")),
        tool("rootgen"), (suite("tests/repository/test_artifact_projections.py", "-k", "root or source_bindings"),),
        depends=("aio-mirror", "fn-sync"),
    ),
    Artifact(
        "door-sync", (SEAT + "**/*.py", "extensions/python/ext/metta-*/*.py"), tool("doorgen", "--write"),
        (Output(SEAT + "doors/_namespaces.py"),
         Output(SEAT + "remote/_schemas.py", ("# begin generated remote operations", "# end generated remote operations")),
         *(Output(SEAT + "_spaces/results.py", (f"    # begin generated extension declarations: {name}",
                                                 f"    # end generated extension declarations: {name}"))
           for name in ("Rows", "Answers")),
         Output(SEAT + "_spaces/execution.py", ("# begin generated evaluation keywords", "# end generated evaluation keywords")),
         Output("website/reference/python-door-contracts.md"),
         Output("llms.txt", ("<!-- begin generated door contracts -->", "<!-- end generated door contracts -->"))),
        tool("doorgen"), (suite("tests/repository/test_door_rows.py", "tests/repository/test_door_marks.py"), tool("doorgen", "--refusals")),
        depends=("init-stub", "bounds-sync"), requires=("engine for behavior and refusal witnesses",),
    ),
    Artifact(
        "ledger", (SEAT + "**/*.py",), tool("ledger", "--write"),
        (Output("website/reference/shrink-ledger.md"),), tool("ledger"),
        (suite("tests/repository/test_artifact_projections.py", "-k", "door_documents"),),
        depends=("door-sync",),
    ),
    Artifact(
        "refusal-sync", ("engine/**/*.pl", "tests/data/error-kinds.json", SEAT + "_errors/errors.py"),
        tool("refusalgen", "--write"), (Output(SEAT + "_errors/refusals.py"),), tool("refusalgen"),
        (("@python", "@root/tests/checks/check_refusal_sync_selftest.py"),), requires=("engine",),
    ),
    Artifact(
        "refusals", ("engine/**/*.pl", "tests/data/error-kinds.json"), tool("refusalsdoc", "--write"),
        (Output("website/reference/refusals.md"),), tool("refusalsdoc"),
        (suite("tests/repository/test_refusal_rows.py"),), depends=("refusal-sync",), requires=("engine",),
    ),
    Artifact(
        "face-sync", ("lib/*/*.metta", SEAT + "library/_face.py"), tool("facegen", "--write"),
        (Output("lib/*/*.metta", contains="Import:"),), tool("facegen"),
        (suite("tests/ch11_python_as_a_notation/test_face.py"),),
        requires=("the installed Python modules named by each face header; missing modules are reported",),
    ),
    Artifact(
        "libdoc", ("lib/*/*.metta", "lib/*/*.pl"), tool("libdoc", "--write"),
        (Output("website/reference/metta-libraries.md"),), tool("libdoc"),
        (suite("tests/repository/test_artifact_projections.py", "-k", "library_document"),),
        depends=("face-sync",),
    ),
    Artifact(
        "codec-doc", ("tests/codec/corpus.json",), tool("codecdoc", "--write"),
        (Output("CODEC.md"),),
        tool("codecdoc"), (suite("tests/repository/test_artifact_projections.py", "-k", "codec_document"),),
    ),
    Artifact(
        "pygments-sync", ("website/.vitepress/metta.tmLanguage.json",), tool("pygmentsgen", "--write"),
        (Output(SEAT + "_pygments.py"),), tool("pygmentsgen"),
        (suite("tests/repository/test_artifact_projections.py", "-k", "lexer"),
         ("@python", "@root/tests/checks/check_tokenisation_parity.py"),
         ("@python", "@root/tests/checks/check_tokenisation_selftest.py")),
        requires=("Node and the website tokenizer dependencies for corpus token comparison",),
    ),
    Artifact(
        "phrasebook", ("extensions/python/tools/phrasebook_entries.py", "lib/*/*.metta"),
        tool("phrasebook", "--markdown", "--gate"),
        (Output("website/reference/stdlib-phrasebook.md"),
         Output("extensions/python/tools/phrasebook_answers.json", remeasure=tool("phrasebook", "--learn", "--markdown", "--gate"))),
        tool("phrasebook", "--gate"), (suite("tests/repository/test_phrasebook.py"),),
        depends=("fn-sync", "door-sync"), requires=("engine; frozen answers are compared with a fresh execution",),
    ),
    Artifact(
        "example-origins", ("examples/**/*.metta", "extensions/python/tools/example_origins.py"),
        tool("example_origins", "--write"), (Output("examples/ORIGINS.tsv"),), tool("example_origins"),
        (suite("tests/repository/test_artifact_projections.py", "-k", "example_origins"),
         suite("tests/repository/test_executable_docs.py",
               "tests/repository/test_example_parity.py::test_example_parity_reports_a_planted_difference")),
        requires=("the external source checkout named by METTA_UPSTREAM for lineage remeasurement",),
    ),
    Artifact(
        "reference", (SEAT + "**/*.py", SEAT + "__init__.pyi", "website/reference/*.md"),
        tool("reference", "--write"),
        (Output("website/reference/metta*.md", contains="<!-- Generated by extensions/python/tools/reference.py"),
         Output("website/reference/index.md", ("<!-- begin generated reference index -->", "<!-- end generated reference index -->")),
         Output("website/.vitepress/config.ts", ("          // begin generated reference navigation", "          // end generated reference navigation"))),
        tool("reference"), (suite("tests/repository/test_reference_projections.py"),),
        depends=("init-stub", "door-sync", "ledger", "libdoc", "refusals", "phrasebook"),
        requires=("griffelib; analyzed modules are never executed",),
    ),
)


def owner(path: str, records: tuple[Artifact, ...] = ARTIFACTS, root: Path = ROOT) -> Artifact:
    """The one artifact whose outputs include this generated path.

    Resolved by the outputs' own `paths` predicate, so a header-selected
    output (`contains`) owns a file only when that header is present, exactly
    as the drift check reads it; a path that does not exist yet is matched by
    glob alone, since the emitter is about to write it. A path several REGION
    outputs of one artifact share has that one owner; two artifacts claiming
    one path is the ownership overlap `findings` already refuses, and it is
    refused here too.
    """
    target = root / path

    def owns(output: Output) -> bool:
        if target.is_file():
            return target in output.paths(root)
        return fnmatch.fnmatchcase(path, output.path)

    owners = [artifact for artifact in records if any(owns(output) for output in artifact.outputs)]
    if len(owners) != 1:
        names = ", ".join(artifact.name for artifact in owners) or "no artifact"
        message = f"{names} declares {path} as an output; exactly one must"
        raise KeyError(message)
    return owners[0]


def notice(path: str, records: tuple[Artifact, ...] = ARTIFACTS, root: Path = ROOT) -> str:
    """The sentence a generated file says about itself, read from the manifest.

    It names which tool wrote the file from which inputs and which lane
    refuses drift. Derived rather than written into each emitter's template,
    which is how the root face came to name doorgen and the door-sync lane
    while the manifest said rootgen and init-stub.
    """
    artifact = owner(path, records, root)
    words = " ".join(word.removeprefix("@root/") for word in artifact.emitter if word != "@python")
    return (
        f"GENERATED by {words} from {', '.join(artifact.inputs)}: the {artifact.name} "
        f"artifact in extensions/python/tools/artifacts.py, whose {artifact.name} lane "
        f"refuses drift."
    )


def ordered(records: tuple[Artifact, ...] = ARTIFACTS) -> tuple[Artifact, ...]:
    """Validate identities and return a deterministic graphlib dependency order."""
    by_name: dict[str, Artifact] = {}
    for artifact in records:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", artifact.name) or artifact.name in by_name:
            message = f"invalid or duplicate artifact name: {artifact.name}"
            raise ValueError(message)
        by_name[artifact.name] = artifact
    for artifact in records:
        if missing := set(artifact.depends) - by_name.keys():
            message = f"{artifact.name}: unknown artifact dependencies: {', '.join(sorted(missing))}"
            raise ValueError(message)
        if not artifact.inputs or not artifact.outputs or not artifact.check or not artifact.emitter or not artifact.witnesses:
            message = f"{artifact.name}: inputs, outputs, emitter, check and witnesses must be declared"
            raise ValueError(message)
    graph = {name: tuple(sorted(by_name[name].depends)) for name in sorted(by_name)}
    try:
        return tuple(by_name[name] for name in TopologicalSorter(graph).static_order())
    except CycleError as error:
        message = "artifact dependency cycle: " + ", ".join(error.args[1])
        raise ValueError(message) from error


def command_text(command: Command, *, shell: bool = True) -> str:
    """Quote argv while retaining only the gate's explicit interpreter/root slots."""
    words = []
    for word in command:
        if word == "@python":
            words.append('"$PY"')
        elif word == "CHECK_PY=@python":
            words.append('CHECK_PY="$PY"')
        elif word.startswith("@root/"):
            relative = word.removeprefix("@root/")
            escaped = relative.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
            words.append('"$HERE/' + escaped + '"' if shell else shlex.quote(relative))
        else:
            words.append(shlex.quote(word))
    return " ".join(words)


def region(text: str, begin: str, end: str, body: str) -> str:
    """Replace one uniquely delimited region without touching authored text."""
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
        message = f"expected one ordered generated region: {begin}"
        raise ValueError(message)
    before, rest = text.split(begin)
    _, after = rest.split(end)
    return before + begin + "\n" + body + "\n" + end + after


def selection(records: tuple[Artifact, ...]) -> str:
    """Derive aggregate and per-artifact selection from the same ordered rows."""
    names = " ".join(row.name for row in records)
    return f'''# Generated by extensions/python/tools/artifacts.py from ARTIFACTS.
GENERATED_ARTIFACT_LANES="{names}"
WANT="$*"
case " $WANT " in
    *" generated-artifacts "*) WANT="$WANT $GENERATED_ARTIFACT_LANES" ;;
esac
for metta_artifact_lane in $GENERATED_ARTIFACT_LANES; do
    case " $WANT " in
        *" $metta_artifact_lane "*|*" generated-artifacts-selftest "*)
            WANT="$WANT $metta_artifact_lane-selftest" ;;
    esac
done'''


def lanes(records: tuple[Artifact, ...]) -> str:
    """Keep executable paths literal for tests/checks/evidence_runners.py."""
    lines = ["# Generated by extensions/python/tools/artifacts.py from ARTIFACTS."]
    for row in records:
        function = "artifact_" + row.name.replace("-", "_") + "_witnesses"
        lines.extend(["", f"run GATE {row.name} {command_text(row.check)}", f"{function}() {{"])
        lines.extend(f"    bounded {command_text(command)} || return $?" for command in row.witnesses)
        lines.extend(["}", f"run GATE {row.name}-selftest {function}"])
    return "\n".join(lines)


def documentation(records: tuple[Artifact, ...]) -> str:
    """Describe authorities, commands, ownership and frozen observations once."""
    lines = [
        "Generated by `extensions/python/tools/artifacts.py` from `ARTIFACTS`.", "",
        'Run `CHECK_PY="$PY" sh check.sh generated-artifacts` to check every artifact and its mutation witnesses.', "",
        "The order below follows declared dependencies. Each individual artifact also selects its `-selftest` lane. "
        "`generated-artifacts-selftest` selects all mutation lanes. Emitters are shown for deliberate regeneration; "
        "`artifacts.py --write` only refreshes this table and the gate declarations.", "",
        "| Artifact | Inputs | Emitter | Outputs | Check and mutation witnesses | Depends on; requires |",
        "|---|---|---|---|---|---|",
    ]
    for row in records:
        outputs = [f"`{output.path}`" + (f" (region `{output.region[0]}`)" if output.region else "")
                   + (f" (header contains `{output.contains}`)" if output.contains else "")
                   + (f" (frozen; remeasure with `{command_text(output.remeasure, shell=False)}`)" if output.remeasure else "")
                   for output in row.outputs]
        cells = [f"`{row.name}`", "; ".join(f"`{path}`" for path in row.inputs),
                 f"`{command_text(row.emitter, shell=False)}`", "; ".join(outputs),
                 "; ".join(f"`{command_text(command, shell=False)}`" for command in (row.check, *row.witnesses)),
                 ", ".join(f"`{name}`" for name in row.depends) + ("; " + "; ".join(row.requires) if row.requires else "")]
        lines.append("| " + " | ".join(html.escape(cell, quote=False).replace("|", "&#124;") for cell in cells) + " |")
    return "\n".join(lines)


def projections(root: Path = ROOT, records: tuple[Artifact, ...] = ARTIFACTS) -> dict[Path, str]:
    """Derive both gate regions and the contributor guide from the graph."""
    rows = ordered(records)
    check, guide = root / "check.sh", root / "DEVELOPING.md"
    text = region(check.read_text(encoding="utf-8"), BEGIN, END, selection(rows))
    return {
        check: region(text, LANES_BEGIN, LANES_END, lanes(rows)),
        guide: region(guide.read_text(encoding="utf-8"), DOC_BEGIN, DOC_END, documentation(rows)),
    }


def findings(root: Path = ROOT, records: tuple[Artifact, ...] = ARTIFACTS) -> list[str]:
    """Validate graph, file ownership, command paths and every derived region."""
    try:
        rows = ordered(records)
        expected = projections(root, records)
    except (ValueError, OSError) as error:
        return [str(error)]
    problems = []
    ownership: dict[Path, list[tuple[int, int, str]]] = {}
    for row in rows:
        problems.extend(f"{row.name}: missing input: {pattern}" for pattern in row.inputs if not any(root.glob(pattern)))
        for command in (row.emitter, row.check, *row.witnesses, *(output.remeasure for output in row.outputs if output.remeasure)):
            problems.extend(f"{row.name}: missing command path: {word}" for word in command
                            if word.startswith("@root/") and not (root / word.removeprefix("@root/").split("::", 1)[0]).is_file())
        for output in row.outputs:
            paths = output.paths(root)
            if not paths:
                problems.append(f"{row.name}: missing output: {output.path}")
            for path in paths:
                text = path.read_text(encoding="utf-8")
                try:
                    start, end = output.span(text)
                except ValueError as error:
                    problems.append(f"{row.name}: {error}")
                    continue
                for other_start, other_end, owner in ownership.setdefault(path, []):
                    if start < other_end and other_start < end:
                        problems.append(f"overlapping artifact output: {path.relative_to(root)}: {owner}, {row.name}")
                ownership[path].append((start, end, row.name))
    for path, wanted in expected.items():
        if path.read_text(encoding="utf-8") != wanted:
            problems.append(f"artifact manifest projection drift: {path.relative_to(root)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Check the manifest, or refresh its shell and documentation projections."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        for path, wanted in projections().items():
            path.write_text(wanted, encoding="utf-8")
    problems = findings()
    for problem in problems:
        print(problem)
    if not problems:
        print(f"artifact-sync: {len(ARTIFACTS)} artifacts, dependencies, outputs and generated checks agree")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
