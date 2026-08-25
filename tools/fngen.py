"""Purpose: generate the closed runtime fn namespace and its typed stub.
Assumes:
  - the project interpreter can import the local metta package and start the
    provisioned engine [tested: test_the_fn_namespace_is_generated;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
Guarantees:
  - runtime names and explicit stub members come from the same fresh catalog
    snapshot and generation is deterministic [tested:
    test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - exact-only catalog spellings stay off the attribute surface instead of
    weakening static checks [tested:
    test_generated_aliases_keep_exact_only_spellings_on_the_bracket_door;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - operator word aliases are generated from the same fixed vocabulary as
    both runtime fn doors, including composite ``neg`` [tested:
    test_operator_words_precede_the_mechanical_name_map; commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - executable phrasebook rows supply inert runtime and stub documentation
    without starting the engine [tested: test_generated_fn_help_is_offline;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - runtime exact names include INTERNAL catalog rows while generated docs and
    typed members include PUBLIC rows only [tested:
    test_internal_catalog_names_stay_exact_but_leave_public_outputs;
    commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "bindings" / "python" / "metta" / "_fn.py"
STUB = ROOT / "bindings" / "python" / "metta" / "_fn.pyi"

sys.path.insert(0, str(ROOT / "bindings" / "python"))
from phrasebook_entries import (  # noqa: E402  -- sibling generator rows are the documentation authority
    ENTRIES,
)

from metta._name_mapping import (  # noqa: E402  -- derive the source root before importing it
    OPERATOR_WORDS,
    OperatorRecipe,
    generated_aliases,
)


def catalog_documentation(
    names: list[str], public_names: set[str] | None = None
) -> dict[str, str]:
    """Format the phrasebook's executable catalog rows as offline help."""
    allowed = set(names) if public_names is None else set(names) & public_names
    documented: dict[str, str] = {}
    for entry in ENTRIES:
        if entry.name not in allowed or entry.name in documented:
            continue
        signature = "\n".join(f"{entry.name}: {type_}" for type_ in entry.types)
        documented[entry.name] = f"{signature}\n\n{entry.note}"
    return documented


def catalog_snapshot() -> tuple[list[str], dict[str, str]]:
    """Read callable names and their visibility from one fresh runtime."""
    source = (
        "import json\n"
        "from metta import MeTTa, S, V\n"
        "space = MeTTa().self\n"
        "rows = space._at('&petta').match(S.visibility(V.name, V.level))\n"
        "print(json.dumps({'names': space.builtins(), 'visibility': "
        "[(str(row.name), str(row.level)) for row in rows]}))\n"
    )
    environment = os.environ | {"PYTHONPATH": str(ROOT / "bindings" / "python")}
    completed = subprocess.run(  # noqa: S603  -- fixed interpreter and source, no untrusted input
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    snapshot = json.loads(completed.stdout)
    names = snapshot.get("names") if isinstance(snapshot, dict) else None
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        msg = "the engine answered no valid function catalog"
        raise RuntimeError(msg)
    rows = snapshot.get("visibility")
    if (
        not isinstance(rows, list)
        or not all(
            isinstance(row, list)
            and len(row) == 2
            and all(isinstance(value, str) for value in row)
            for row in rows
        )
    ):
        msg = "the engine answered no valid visibility catalog"
        raise RuntimeError(msg)
    visibility = dict(rows)
    unique_names = sorted(set(names))
    if len(rows) != len(visibility) or set(unique_names) != visibility.keys():
        msg = "every callable must have exactly one catalog visibility row"
        raise RuntimeError(msg)
    if set(visibility.values()) - {"PUBLIC", "INTERNAL"}:
        msg = "callable visibility must be PUBLIC or INTERNAL"
        raise RuntimeError(msg)
    return unique_names, visibility


def catalog_names() -> list[str]:
    """Read a fresh runtime's complete function and special-form catalog."""
    names, _ = catalog_snapshot()
    return names


def runtime_text(names: list[str], documentation: dict[str, str] | None = None) -> str:
    """Render the inert runtime namespace from one catalog snapshot."""
    rendered = "\n".join(f"        {json.dumps(name)}," for name in names)
    aliases = generated_aliases(names)
    rendered_aliases = "\n".join(
        f"        ({json.dumps(alias)}, {json.dumps(target)})," for alias, target in aliases.items()
    )
    rendered_docs = "\n".join(
        f"    {json.dumps(name)}: {json.dumps(text)},"
        for name, text in sorted((documentation or {}).items())
    )
    return f'''"""Purpose: expose the generated static function-mention namespace.

GENERATED by bindings/python/tools/fngen.py from a fresh running engine's
function and special-form catalog. Edit the catalog and rerun with --write,
never edit this file directly.

Guarantees:
  - attribute access is closed over the generated catalog and exact bracket
    access never applies the Python spelling map [tested:
    test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - generated operator word attributes resolve through the shared fixed table
    [tested: test_operator_words_precede_the_mechanical_name_map;
    commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - documented catalog rows remain available to help() before an engine starts
    [tested: test_generated_fn_help_is_offline; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - INTERNAL catalog names remain exact runtime mentions but carry no generated
    documentation [tested:
    test_internal_catalog_names_stay_exact_but_leave_public_outputs;
    commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from ._atom_namespace import _Namespace
from .atoms import Symbol

_NAMES = frozenset(
    {{
{rendered}
    }}
)

_ALIASES: dict[str, str] = {{}}
_ALIASES.update(
    (
{rendered_aliases}
    )
)

_DOCUMENTATION = {{
{rendered_docs}
}}

fn = _Namespace(
    Symbol,
    allowed=_NAMES,
    aliases=_ALIASES,
    documentation=_DOCUMENTATION,
    label="target function",
)
'''


def stub_text(
    names: list[str],
    documentation: dict[str, str] | None = None,
    public_names: set[str] | None = None,
) -> str:
    """Render explicit members; no catch-all may erase typo checking.

    PEP 484 makes the colocated .pyi authoritative to type checkers, so the
    generated class lists every safe alias instead of advertising dynamic Any.
    [source: https://peps.python.org/pep-0484/#stub-files; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
    """
    aliases = generated_aliases(names if public_names is None else public_names)
    documentation = documentation or {}
    rows = []
    for alias, target in aliases.items():
        target_kind = OPERATOR_WORDS.get(alias)
        annotation = (
            "Callable[[object], Expression]"
            if isinstance(target_kind, OperatorRecipe)
            else "Symbol"
        )
        row = f"    {alias}: {annotation}"
        if alias[:1].islower() and alias != alias.lower():
            row += "  # noqa: N815"
        if target in documentation:
            row += f"\n    {json.dumps(documentation[target])}"
        rows.append(row)
    members = "\n".join(rows)
    return f"""# Purpose: declare every generated fn attribute to static type checkers.
# Guarantees:
#   - every safe runtime alias is explicit and no dynamic Any fallback exists
#     [tested: test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
#   - operator word aliases are explicit members generated from the runtime
#     catalog [tested: test_operator_words_precede_the_mechanical_name_map;
#     commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
#   - catalog-row documentation is attached to explicit members for static
#     help [tested: test_generated_fn_help_is_offline; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
#   - INTERNAL names have no static member while their exact runtime bracket
#     door remains available [tested:
#     test_internal_catalog_names_stay_exact_but_leave_public_outputs;
#     commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
# Open Obligations:
#   To Do: None
#   Hacks: None
#   Future Enhancements: None.

from collections.abc import Callable
from typing import Final

from .atoms import Expression, Symbol

class _FunctionNamespace:
{members}
    def __getitem__(self, name: str, /) -> Symbol: ...

fn: Final[_FunctionNamespace]
"""


def main(argv: list[str]) -> int:
    """Check generated outputs, or replace both together from one snapshot."""
    names, visibility = catalog_snapshot()
    public_names = {name for name in names if visibility[name] == "PUBLIC"}
    documentation = catalog_documentation(names, public_names)
    wanted = {
        RUNTIME: runtime_text(names, documentation),
        STUB: stub_text(names, documentation, public_names),
    }
    stale = [
        path
        for path, content in wanted.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    if not stale:
        return 0
    if "--write" in argv:
        for path in stale:
            path.write_text(wanted[path], encoding="utf-8")
            print(f"rewrote {path.name}")
        return 0
    print(
        "metta's fn runtime/stub no longer match the running catalog: "
        "run `python bindings/python/tools/fngen.py --write`"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
