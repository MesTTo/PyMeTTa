"""Purpose: derive MeTTa imports, types and documentation from Prolog exports.

Guarantees: missing metadata and edited generated regions fail the check;
handwritten equations survive regeneration and source initializers never run
[tested: tests/checks/check_prologface_selftest.py; commit=7dcfe83fcf74742a1e944db240aa918596c8d4b0].
Owns resources: the bounded source reader exits before output is changed;
temporary output files are removed after replacement or failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests/checks"))

from artifacts import notice, region  # noqa: E402 -- checkout generator
from bounded_spawn import bounded  # noqa: E402 -- repository process policy

BEGIN = "; begin generated Prolog face"
END = "; end generated Prolog face"
SOURCE_ROOTS = ((ROOT / "lib", "*/*.pl"), (ROOT / "tests/data/prologface", "*.pl"))


def source_records(paths: list[Path]) -> list[dict[str, Any]]:
    """Read source through SWI's cross-referencer, never through consult."""
    result = subprocess.run(  # noqa: S603 -- fixed reader; paths are argv, never shell text
        bounded(["swipl", "--on-error=status", "-q", "-f", "none", "-s",
                 str(Path(__file__).with_name("prologface_source.pl")), "--",
                 *(str(path.resolve()) for path in paths)]),
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        message = f"Prolog source reader exited {result.returncode}: {result.stderr.strip()}"
        raise ValueError(message)
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        message = f"Prolog source reader returned invalid metadata: {result.stdout!r}"
        raise ValueError(message) from error
    if not isinstance(records, list) or len(records) != len(paths):
        message = "Prolog source reader did not return one record per source"
        raise ValueError(message)
    return records


def metta_type(written: str) -> str:
    """Map PlDoc's native scalar types to the language's existing types."""
    aliases = {
        "any": "%Undefined%", "term": "%Undefined%",
        "integer": "Number", "int": "Number", "nonneg": "Number",
        "number": "Number", "float": "Number", "rational": "Number",
        "string": "String", "atom": "Symbol", "boolean": "Bool", "bool": "Bool",
        "list": "Expression",
    }
    if written in aliases:
        return aliases[written]
    if written.startswith("list(") and written.endswith(")"):
        return "Expression"
    unquoted = written[1:-1] if written.startswith("'") and written.endswith("'") else written
    if re.fullmatch(r"[A-Z][A-Za-z0-9_-]*|%Undefined%", unquoted):
        return unquoted
    message = f"unsupported PlDoc type {written}; declare an existing MeTTa type or any"
    raise ValueError(message)


def interface(record: dict[str, Any], source: Path) -> list[tuple[str, tuple[str, ...], str, tuple[str, ...]]]:
    """Validate a native interface and keep every distinct typed arity."""
    if record["module"] != source.stem:
        message = f"{source}: module must be named {source.stem}, got {record['module']!r}"
        raise ValueError(message)
    rows = []
    for exported in record["exports"]:
        if exported["private"]:
            continue
        name, arity = exported["name"], exported["arity"]
        label = f"{source}:{name}/{arity}"
        if not re.fullmatch(r'[^\s();"\']+', name):
            message = f"{label}: name cannot be written as a MeTTa head"
            raise ValueError(message)
        if not exported["doc"]:
            message = f"{label}: add a PlDoc description and typed mode"
            raise ValueError(message)
        modes = [mode for mode in exported["modes"] if mode["args"]
                 and mode["args"][-1]["mode"] in ("-", "--", "?")
                 and all(arg["mode"] not in ("-", "--") for arg in mode["args"][:-1])]
        if not modes:
            message = f"{label}: declare a forward mode with inputs followed by one output"
            raise ValueError(message)
        for mode in modes:
            args = mode["args"]
            if any(not arg["explicit"] or not arg["name"] for arg in args):
                message = f"{label}: every PlDoc argument needs a name and explicit type"
                raise ValueError(message)
            types = tuple(metta_type(arg["type"]) for arg in args)
            labels = tuple(arg["name"] for arg in args)
            rows.append((name, types, exported["doc"], labels))
    return sorted(set(rows))


def generated_body(rows: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]], source: Path,
                   generated_notice: str) -> str:
    """Render the direct registration and the metadata that describes it."""
    names = sorted({name for name, _, _, _ in rows})
    native_path = json.dumps(os.path.relpath(source.resolve(), ROOT / "lib"))
    lines = [f"; {generated_notice}", "!(import! &self (library lib_import))",
             f"!(import_prolog_functions_from_file (library {native_path})",
             "  (" + " ".join(names) + "))", ""]
    by_name: dict[str, list[tuple[str, tuple[str, ...], str, tuple[str, ...]]]] = {}
    for row in rows:
        by_name.setdefault(row[0], []).append(row)
    for name, variants in by_name.items():
        for _, types, _, _ in variants:
            lines.append(f"(: {name} (-> {' '.join(types)}))")
        doc = "\n\n".join(dict.fromkeys(row[2] for row in variants))
        labels = max((row[3] for row in variants), key=len)
        params = " ".join(f"(@param {json.dumps(label)})" for label in labels[:-1])
        lines.extend((f"(@doc {name}", f"  (@desc {json.dumps(doc, ensure_ascii=False)})",
                      f"  (@params ({params}))", f"  (@return {json.dumps(labels[-1])}))"))
        lines.append("")
    return "\n".join(lines).rstrip()


def project(current: str, body: str) -> str:
    """Replace one complete region or append the first region to authored text."""
    if BEGIN in current or END in current:
        return region(current, BEGIN, END, body)
    prefix = current.rstrip("\n") + "\n\n" if current else ""
    return prefix + BEGIN + "\n" + body + "\n" + END + "\n"


def write_projection(path: Path, current: str, wanted: str) -> None:
    """Replace beside the target only if its authored source is still current."""
    if (path.read_text(encoding="utf-8") if path.exists() else "") != current:
        message = f"{path} changed during generation; read the edit and regenerate"
        raise ValueError(message)
    scratch = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".prologface-", delete=False) as stream:
            scratch = Path(stream.name)
            stream.write(wanted)
        if path.exists():
            scratch.chmod(stat.S_IMODE(path.stat().st_mode))
        scratch.replace(path)
    finally:
        if scratch is not None:
            scratch.unlink(missing_ok=True)


def review(paths: list[Path] | None = None, *, rewrite: bool = False) -> tuple[list[str], int, int]:
    """Check selected interfaces or discover described sources and existing faces."""
    explicit = paths is not None
    if paths is None:
        paths = sorted({path for root, pattern in SOURCE_ROOTS for path in root.glob(pattern)})
        for root, pattern in SOURCE_ROOTS:
            paths.extend(path.with_suffix(".pl") for path in root.glob(pattern.replace(".pl", ".metta"))
                         if BEGIN in path.read_text(encoding="utf-8") and path.with_suffix(".pl") not in paths)
    paths = [path.resolve() for path in paths]
    records = source_records(paths)
    problems, pending = [], []
    skipped = 0
    for source, record in zip(paths, records, strict=True):
        target = source.with_suffix(".metta")
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if not explicit and not record["described"] and BEGIN not in current:
            skipped += 1
            continue
        try:
            rows = interface(record, source)
            relative = str(target.relative_to(ROOT))
            body = generated_body(rows, source, notice(relative, content=BEGIN))
            wanted = project(current, body)
        except (ValueError, KeyError) as error:
            problems.append(str(error))
            continue
        pending.append((target, current, wanted))
    if problems:
        return problems, len(pending), skipped
    for target, current, wanted in pending:
        if current != wanted:
            if rewrite:
                write_projection(target, current, wanted)
            else:
                problems.append(f"{target.relative_to(ROOT)}: generated face drift; run prologface.py --write")
    return problems, len(pending), skipped


def main() -> int:
    """Check every described library, or regenerate its derived region."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("sources", nargs="*", type=Path)
    args = parser.parse_args()
    try:
        problems, checked, skipped = review(args.sources or None, rewrite=args.write)
    except (OSError, ValueError) as error:
        print(f"prolog-face: {error}", file=sys.stderr)
        return 1
    for problem in problems:
        print(problem)
    print(f"prolog-face: {checked} described sources, {skipped} sources without export modes, {len(problems)} findings")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
