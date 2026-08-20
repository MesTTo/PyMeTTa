"""Purpose: generate CODEC.md's tables from tests/codec/corpus.json, so the
grammar document and the conformance kit have ONE authority between them.

The row this answers asks for one authority for spec and kit and suggests
generating the document from R19's `.mettail` `::=` annotations. Measured
2026-08-20 and it loses, for reasons recorded in CODEC.md's own header; the
corpus wins instead, because it is the thing the kit actually runs. So the
prose is written by hand and every table of cases, tags and profiles is
generated from the corpus, and this gate is what stops the two drifting.

Assumes:
  - CODEC.md carries `<!-- generated: NAME -->` / `<!-- end generated -->`
    fences around each table [tested test_the_grammar_document_is_generated]
Guarantees:
  - the checked-in document equals what this produces, gated on every run
    [tested test_the_grammar_document_is_generated]
  - a fence naming a table this does not build, or a table this builds with
    no fence, is an error rather than a silently empty section
    [tested test_an_unknown_fence_is_refused]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tests" / "codec" / "corpus.json"
DOCUMENT = ROOT / "CODEC.md"
FENCE = re.compile(
    r"(<!-- generated: (?P<name>[a-z-]+) -->\n)(?P<body>.*?)(<!-- end generated -->)",
    re.DOTALL,
)


def _cell(value: object) -> str:
    """One JSON value as a markdown table cell."""
    text = json.dumps(value, ensure_ascii=False)
    return "`" + text.replace("|", "\\|") + "`"


def _prose(text: str) -> str:
    return text.replace("|", "\\|")


def tags_table(corpus: dict) -> list[str]:
    rows = ["| tag | class | payload | what it is |", "|---|---|---|---|"]
    for tag, entry in corpus["tags"].items():
        rows.append(
            f"| `{tag}` | {entry['class']} | {_prose(entry['payload'])} "
            f"| {_prose(entry['means'])} |"
        )
    return rows


def profiles_table(corpus: dict) -> list[str]:
    rows = ["| profile | tags | frames | what speaks it |", "|---|---|---|---|"]
    for name, entry in corpus["profiles"].items():
        tags = " ".join(f"`{tag}`" for tag in entry["tags"])
        frames = " ".join(f"`{frame}`" for frame in entry.get("frames", ())) or "none"
        rows.append(f"| {name} | {tags} | {frames} | {_prose(entry['note'])} |")
    return rows


def _written(case: dict) -> str:
    written = case.get("written")
    if written is None:
        return ""
    if isinstance(written, str):
        return _cell(written)
    return " / ".join(f"{printer} {_cell(text)}" for printer, text in written.items())


def cases_table(corpus: dict) -> list[str]:
    rows = ["| case | text | wire | written |", "|---|---|---|---|"]
    for case in corpus["cases"]:
        wire = _cell(case["wire"]) if "wire" in case else "built, see the corpus"
        text = _cell(case["text"]) if "text" in case else ""
        rows.append(f"| `{case['id']}` | {text} | {wire} | {_written(case)} |")
    return rows


def refusals_table(corpus: dict) -> list[str]:
    rows = ["| case | operation | wire | why it is refused |", "|---|---|---|---|"]
    for case in corpus["refusals"]:
        licensed = case.get("unless")
        operation = f"`{case['refuse']}`" + (f", unless `{licensed}`" if licensed else "")
        rows.append(
            f"| `{case['id']}` | {operation} | {_cell(case['wire'])} "
            f"| {_prose(case['because'])} |"
        )
    return rows


def frames_table(corpus: dict) -> list[str]:
    rows = ["| case | frame | wire | parts |", "|---|---|---|---|"]
    for case in corpus["frames"]:
        parts = ", ".join(f"{name} {_cell(value)}" for name, value in case["parts"].items())
        rows.append(f"| `{case['id']}` | `{case['frame']}` | {_cell(case['wire'])} | {parts} |")
    return rows


def transcripts_table(corpus: dict) -> list[str]:
    rows = ["| case | program | answer groups |", "|---|---|---|"]
    for case in corpus["transcripts"]:
        program = _cell(case["program"])
        rows.append(f"| `{case['id']}` | {program} | {_cell(case['groups'])} |")
    return rows


TABLES = {
    "tags": tags_table,
    "profiles": profiles_table,
    "cases": cases_table,
    "refusals": refusals_table,
    "frames": frames_table,
    "transcripts": transcripts_table,
}


def document(current: str, corpus: dict) -> str:
    """The document with every fenced table rebuilt from the corpus."""
    fenced = {match.group("name") for match in FENCE.finditer(current)}
    unknown = fenced - set(TABLES)
    if unknown:
        raise SystemExit(
            f"CODEC.md fences {sorted(unknown)}, which codecdoc.py does not build"
        )
    unfenced = set(TABLES) - fenced
    if unfenced:
        raise SystemExit(
            f"codecdoc.py builds {sorted(unfenced)} and CODEC.md has no fence for "
            f"it, so the table would be missing rather than stale"
        )

    def replace(match: re.Match) -> str:
        rows = TABLES[match.group("name")](corpus)
        return match.group(1) + "\n".join(rows) + "\n" + match.group(4)

    return FENCE.sub(replace, current)


def main(argv: list[str]) -> int:
    if not DOCUMENT.exists():
        print(f"{DOCUMENT.name} is missing; the corpus has no document to keep in step")
        return 1
    current = DOCUMENT.read_text(encoding="utf-8")
    wanted = document(current, json.loads(CORPUS.read_text(encoding="utf-8")))
    if current == wanted:
        return 0
    if "--write" in argv:
        DOCUMENT.write_text(wanted, encoding="utf-8")
        print(f"rewrote {DOCUMENT.name}")
        return 0
    print(
        f"{DOCUMENT.name}'s tables no longer match tests/codec/corpus.json: "
        f"run `python bindings/python/tools/codecdoc.py --write`"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
