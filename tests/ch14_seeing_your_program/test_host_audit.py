"""Purpose: the three doors that run host code raise ``metta.host`` audit events.

`py-atom` evaluates a Python expression, `load` reads a file that can carry
`!` directives and an import graph, and the compile door turns a Python
function into equations whose host islands run later. Each raises its event
BEFORE the effect, which is what lets a hook refuse, and each names the door
and what it was handed.

Assumes:
  - `sys.addaudithook` cannot be undone, so every scenario shares one hook
    installed for the module and reads its buffer [source: CPython
    Doc/library/sys.rst, addaudithook: "cannot be removed"]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import sys

import pytest

#: Every `metta.host` event this process has raised since the hook went in.
_SEEN: list[tuple[str, str]] = []


def _record(event: str, arguments: tuple) -> None:
    if event == "metta.host":
        _SEEN.append((str(arguments[0]), str(arguments[1])))


sys.addaudithook(_record)


@pytest.fixture()
def m(metta):
    """An isolated space, so a load here is a door this test opened."""
    with metta._new_space() as space:
        yield space


@pytest.fixture()
def seen():
    """The events raised inside one scenario, in order."""
    mark = len(_SEEN)
    yield _SEEN
    del _SEEN[mark:]


def _doors(seen, mark):
    return [door for door, _ in seen[mark:]]


def test_the_py_atom_expression_door_raises_its_event(m, seen):
    """The payload is the source, not the code object `exec` would carry."""
    mark = len(seen)
    assert m.run('!(py-atom "1 + 1")')[0][0] == 2
    assert ("py-atom", "1 + 1") in seen[mark:]


def test_the_load_door_raises_its_event(m, seen, tmp_path):
    """A file is named by its path, the way `open`'s own event names one."""
    path = tmp_path / "audited.metta"
    path.write_text("(= (audited $x) $x)\n", encoding="utf-8")
    mark = len(seen)
    m.load(str(path))
    assert ("load", str(path)) in seen[mark:]


def test_the_compile_door_raises_its_event(m, seen):
    """The payload names the function, which is what identifies it in a log."""
    mark = len(seen)

    @m.define
    def audited_twice(x: int) -> int:
        return x * 2

    doors = _doors(seen, mark)
    assert "compile" in doors
    payloads = [payload for door, payload in seen[mark:] if door == "compile"]
    assert any(p.endswith(".audited_twice") for p in payloads), payloads


def test_a_hook_can_refuse_a_door_by_raising(m, seen, tmp_path):
    """PEP 578's point: the event precedes the effect.

    A hook that raises stops the operation, which is only true if the event
    is raised before the file is read. The refusal is the hook's own
    exception, unchanged.
    """

    class RefusedError(Exception):
        pass

    def refuse(event, arguments):
        if event == "metta.host" and arguments[0] == "load":
            if str(arguments[1]).endswith("refused.metta"):
                raise RefusedError(str(arguments[1]))

    sys.addaudithook(refuse)
    path = tmp_path / "refused.metta"
    path.write_text("(= (never-loaded $x) $x)\n", encoding="utf-8")

    mark = len(seen)
    with pytest.raises(RefusedError):
        m.load(str(path))
    assert ("load", str(path)) in seen[mark:], "the event preceded the read"
    assert not m.is_function_here("never-loaded"), "nothing was loaded from it"
