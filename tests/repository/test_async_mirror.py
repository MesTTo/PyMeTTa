"""Purpose: gate the generated async mirror, and prove the gate can fail.

Sixty-six of AsyncMeTTa's doors are nothing but one worker round trip to the
Space method of the same name. Hand-written, they drifted from it: measured
2026-08-31, fifteen carried a different signature, sixteen weakened its return
annotation, and sixty-four of sixty-six paraphrased its docstring under a
section comment saying the synchronous docstrings applied verbatim. Two were
runtime refusals, not annotations: `await am.type(atom=x)` raised TypeError
where `m.type(atom=x)` answers, and the parity test could not see any of it
because it compares parameter NAMES.

Assumes:
  - `Space` is the source of truth and the generator reads its AST, so this
    file needs no engine to check the shape
Guarantees:
  - the checked-in block equals what the generator renders [tested:
    test_the_async_mirror_is_generated_from_the_sync_surface]
  - every generated door carries Space's signature and docstring verbatim,
    except those in DIVERGENT [tested: test_every_generated_door_is_spaces_door]
  - the gate DISCRIMINATES: a hand-edited door in the block is a finding
    [tested: test_the_async_mirror_gate_catches_a_planted_edit]
  - every exclusion names a live Space method and says why [tested:
    test_every_exclusion_names_a_live_door_and_a_reason]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "extensions" / "python" / "tools"))

import aiogen  # noqa: E402
from aio_divergences import (  # noqa: E402
    DIVERGENT,
    EXCLUDED,
    MODULE_DOORS,
    PRIVATE_TARGET,
)


def _generated() -> tuple[dict[str, ast.AST], dict[str, ast.AST], list[str], list[str]]:
    space, space_lines = aiogen._class(aiogen.SPACE, "Space")
    asy, aio_lines = aiogen._class(aiogen.AIO, "AsyncMeTTa")
    first, last = aio_lines.index(aiogen.START), aio_lines.index(aiogen.END)
    doors = {
        node.name: node
        for node in asy.body
        if isinstance(node, ast.AsyncFunctionDef) and first < node.lineno <= last
    }
    sync = {
        node.name: node
        for node in space.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not any("overload" in ast.unparse(d) for d in node.decorator_list)
    }
    return doors, sync, space_lines, aio_lines


def test_the_async_mirror_is_generated_from_the_sync_surface():
    """The checked-in block is what the generator renders, byte for byte."""
    assert aiogen.main([]) == 0


def test_every_generated_door_is_spaces_door():
    """Signature and docstring come from Space verbatim, or say why not."""
    doors, sync, space_lines, aio_lines = _generated()
    assert len(doors) >= 60, f"only {len(doors)} generated doors; the block looks empty"
    for name, door in doors.items():
        target = PRIVATE_TARGET.get(name, name)
        assert target in sync, f"{name} mirrors a Space method that no longer exists"
        original = sync[target]
        assert ast.get_docstring(door) == ast.get_docstring(original), (
            f"{name}'s docstring is not Space.{target}'s"
        )
        if name in DIVERGENT:
            continue
        assert ast.unparse(door.args) == ast.unparse(original.args), (
            f"{name}'s signature differs from Space.{target}'s with no ledger row"
        )
        here = ast.unparse(door.returns) if door.returns else None
        there = ast.unparse(original.returns) if original.returns else None
        assert here == there, f"{name} returns {here}, Space.{target} returns {there}"


def test_the_async_mirror_gate_catches_a_planted_edit():
    """A lane that cannot be shown failing is evidence of nothing."""
    original = aiogen.AIO.read_text(encoding="utf-8")
    lines = original.splitlines()
    first = lines.index(aiogen.START)
    door = next(i for i in range(first, len(lines)) if lines[i].startswith("    async def "))
    planted = [*lines[:door], "    # a hand edit inside the generated block", *lines[door:]]
    try:
        aiogen.AIO.write_text("\n".join(planted) + "\n", encoding="utf-8")
        assert aiogen.main([]) == 1, "the gate did not see a hand edit in the block"
    finally:
        aiogen.AIO.write_text(original, encoding="utf-8")
    assert aiogen.main([]) == 0, "the plant was not fully unwound"


def test_every_exclusion_names_a_live_door_and_a_reason():
    """An exclusion is a decision, so it names the mechanism behind it."""
    _, sync, _, _ = _generated()
    for name, reason in EXCLUDED.items():
        assert name in sync, f"{name} is excluded but Space no longer has it"
        assert len(reason.split()) >= 6, f"{name}: too short to be a reason"
    for name, (signature, reason) in DIVERGENT.items():
        assert name in sync, f"{name} diverges but Space no longer has it"
        assert signature.startswith("self"), f"{name}: a method signature starts with self"
        assert len(reason.split()) >= 8, f"{name}: too short to be a reason"


def test_the_module_tier_is_generated_from_the_sync_surface():
    """Each module door carries Space's signature, aliased, tier note appended.

    The tier had drifted the same three ways the async mirror had: nine doors
    erased their signatures into *args/**kwargs, and trace() bounded at
    10,000 events with the parameter keyword-only where Space bounds at
    1,000,000 positional-or-keyword [measured 2026-08-31]. Generation makes
    the drift unrepresentable; this checks the generated block really is the
    generator's output door by door, on top of the byte-equality the gate
    already enforces.
    """
    space, space_lines = aiogen._class(aiogen.SPACE, "Space")
    init_lines = aiogen.INIT.read_text(encoding="utf-8").splitlines()
    first = init_lines.index(aiogen.MODULE_START)
    last = init_lines.index(aiogen.MODULE_END)
    block = ast.parse("\n".join(init_lines[first + 6 : last]))
    doors = {n.name: n for n in block.body if isinstance(n, ast.FunctionDef)}
    assert set(doors) == {name for name, _ in MODULE_DOORS}

    sync = {
        node.name: node
        for node in space.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not any("overload" in ast.unparse(d) for d in node.decorator_list)
    }
    for name, target in MODULE_DOORS:
        door, original = doors[name], sync[target]
        rendered = ", ".join(
            aiogen.spaced_default(aiogen._aliased(part))
            for part in aiogen.split_top_level(ast.unparse(original.args))
            if part != "self"
        )
        assert ast.unparse(door.args) == rendered.replace(" = ", "="), (
            f"metta.{name}'s parameters are not Space.{target}'s"
        )
        doc = ast.get_docstring(door)
        assert doc is not None and doc.endswith(aiogen.TIER_NOTE), (
            f"metta.{name} lost the tier note"
        )
        assert (ast.get_docstring(original) or "").splitlines()[0] in doc, (
            f"metta.{name}'s docstring is not Space.{target}'s"
        )

