"""Purpose: the Python surface's shrink ledger, the question KERNEL.md asks of
the engine asked of the library. KERNEL.md classes 58 translator heads as
primitive or derived and requires every derived form still fused into the
compiler to say why, measured. This does the same for `Space`'s public methods:
it classes each one, and requires every method that is macro-expressible ON THE
PUBLIC SURFACE to carry a reason for existing.

The classification is DERIVED FROM THE CODE, not maintained by hand. A method
that starts reaching another public method becomes derived here on its next run
and fails the gate until its row says what it buys.

Assumes:
  - a method whose body calls another public method of the same class is
    macro-expressible by that method, which is Felleisen's test for a form that
    is not primitive: it can be rewritten locally, without restructuring
  - the four other classes are structural rather than shrinkable. A method that
    speaks to the engine is primitive here; one that reaches a private helper
    shares an implementation, which is the OUTCOME a shrink wants rather than
    a target for one; one that delegates to a satellite module is the facade
    layer; a property carries no body to classify.
Guarantees:
  - every derived method has exactly one row, and every row names a live method,
    so the ledger cannot drift from the class [tested:
    test_the_shrink_ledger_covers_every_derived_door]
  - a row says what the method BUYS, because a derived method with no answer is
    the shrink target and the ledger exists to name those
    [tested: test_every_ledger_row_states_what_its_door_buys]
Fails when: read as a count. The number of derived methods is not a score; a
  named face of one mechanism is derived and should stay, and the ledger says
  so in its own row.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import ast
import inspect
import sys
import textwrap
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "extensions" / "python"))

from ledger_entries import DERIVED  # noqa: E402

PAGE = REPO / "website" / "reference" / "shrink-ledger.md"


def _source(function: object) -> ast.Module | None:
    try:
        return ast.parse(textwrap.dedent(inspect.getsource(function)))
    except (OSError, TypeError, SyntaxError):
        return None


def classify(cls: type) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Every public method, its class, and what its body reaches."""
    public = {name for name in dir(cls) if not name.startswith("_")}
    out: dict[str, tuple[str, tuple[str, ...]]] = {}
    for name in sorted(public):
        attribute = inspect.getattr_static(cls, name)
        function = getattr(attribute, "__func__", attribute)
        if not callable(function):
            out[name] = ("property", ())
            continue
        tree = _source(function)
        if tree is None:
            out[name] = ("property", ())
            continue
        doors, helpers, engine, satellites = set(), False, False, set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = ast.unparse(node.func)
            if target.startswith("self._rt"):
                engine = True
            attribute_of_self = (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
            )
            if attribute_of_self:
                if node.func.attr in public and node.func.attr != name:
                    doors.add(node.func.attr)
                elif node.func.attr.startswith("_"):
                    helpers = True
            if target.startswith("_satellite"):
                satellites.add(target)
        if doors:
            out[name] = ("derived", tuple(sorted(doors)))
        elif engine:
            out[name] = ("primitive", ())
        elif helpers:
            out[name] = ("shared", ())
        else:
            out[name] = ("facade", tuple(sorted(satellites)))
    return out


def findings(rows: dict[str, tuple[str, tuple[str, ...]]]) -> list[str]:
    """Everything wrong with the ledger, named."""
    derived = {name for name, (kind, _) in rows.items() if kind == "derived"}
    out = []
    for name in sorted(derived - set(DERIVED)):
        expressed = ", ".join(rows[name][1])
        out.append(
            f"{name}: reaches {expressed} and so is macro-expressible by it, "
            f"and the ledger has no row saying what it buys. Add one to "
            f"tools/ledger_entries.py, or shrink the method."
        )
    out.extend(
        f"{name}: has a ledger row but no longer reaches another public "
        f"method. Remove the row."
        for name in sorted(set(DERIVED) - derived)
    )
    out.extend(
        f"{name}: its row is empty, so it says nothing."
        for name in sorted(derived & set(DERIVED))
        if not DERIVED[name].strip()
    )
    return out


def page(rows: dict[str, tuple[str, tuple[str, ...]]]) -> str:
    """The ledger, rendered."""
    counts = dict.fromkeys(
        ("primitive", "derived", "shared", "facade", "property"), 0
    )
    for kind, _ in rows.values():
        counts[kind] += 1
    lines = [
        "# The Python surface's shrink ledger",
        "",
        "`KERNEL.md` asks which translator heads are primitive and which are",
        "derived, and requires every derived form still fused into the compiler",
        "to say why. This page asks the same of the library, and is generated by",
        "`extensions/python/tools/ledger.py` from the code rather than",
        "maintained by hand.",
        "",
        f"`Space` publishes **{len(rows)}** methods.",
        "",
        "| class | count | what it means |",
        "|---|---|---|",
        f"| primitive | {counts['primitive']} | speaks to the engine; nothing on this surface expresses it |",
        f"| derived | {counts['derived']} | its body reaches another PUBLIC method, so it is macro-expressible by one |",
        f"| shared | {counts['shared']} | reaches a private helper: an implementation already collapsed, which is a shrink's outcome rather than its target |",
        f"| facade | {counts['facade']} | delegates to a satellite module; the layering, not a duplication |",
        f"| property | {counts['property']} | no body to class |",
        "",
        "## The derived methods, and what each buys",
        "",
        "A derived method is not a defect. A named form of one mechanism is",
        "derived and should stay, because collapsing it would put the mechanism's",
        "argument back at the call site. What the ledger refuses is a derived",
        "method with no answer.",
        "",
        "| method | expressible by | what it buys |",
        "|---|---|---|",
    ]
    for name, (kind, reaches) in sorted(rows.items()):
        if kind != "derived":
            continue
        lines.append(f"| `{name}` | `{'`, `'.join(reaches)}` | {DERIVED.get(name, '')} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """Check the ledger, or rewrite its page."""
    parser = argparse.ArgumentParser(description="the Python surface's shrink ledger")
    parser.add_argument("--write", action="store_true", help="rewrite the page")
    arguments = parser.parse_args(argv)

    # Deferred so the tool imports without an engine.
    from metta._space import Space  # noqa: PLC0415  -- see above

    rows = classify(Space)
    problems = findings(rows)
    rendered = page(rows)
    if arguments.write:
        PAGE.write_text(rendered, encoding="utf-8")
        print(f"rewrote {PAGE.relative_to(REPO)}")
    elif PAGE.is_file() and PAGE.read_text(encoding="utf-8") != rendered:
        problems.append(
            "the page no longer matches the code; run "
            "`python extensions/python/tools/ledger.py --write`"
        )
    for problem in problems:
        print(f"  {problem}")
    print(f"{len(problems)} finding(s) over {len(rows)} methods")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
