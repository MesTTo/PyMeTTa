"""Purpose: keep symbol text validation owned by the engine grammar.
Guarantees:
  - Python keeps no delimiter regex and the shim delegates every symbol
    decision to metta_symbol_writable/1 [tested:
    test_every_delimiter_check_derives_from_one_grammar_rule;
    commit=WORKTREE]
  - Vulture runs at its 60 percent dead-definition confidence floor, with
    dynamic protocol uses named explicitly in the checked whitelist [tested:
    test_every_delimiter_check_derives_from_one_grammar_rule;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import tomllib


def test_every_delimiter_check_derives_from_one_grammar_rule(metta, repo_root):
    """The grammar answer, its host crossing, and static policy stay aligned."""
    expected = {
        "plain": True,
        "%router-symbol": True,
        "naive-name": True,
        "": False,
        "$variable": False,
        "has space": False,
        "left(parenthesis": False,
        'has"quote': False,
        "has;comment": False,
        "42": False,
        "True": False,
        "line\nfeed": False,
        "unicode\u2003space": False,
    }
    rt = metta.runtime
    actual = {
        name: rt.apply_must("petta_py_symbol_writable", name) for name in expected
    }
    assert actual == expected

    core = repo_root / "bindings" / "python" / "petta" / "_atoms_core.py"
    tree = ast.parse(core.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "re" not in imported
    assert "_BARE" not in core.read_text(encoding="utf-8")

    config = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    vulture = config["tool"]["vulture"]
    assert vulture["min_confidence"] == 60
    assert "vulture_whitelist.py" in vulture["paths"]
