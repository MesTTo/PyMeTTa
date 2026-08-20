"""Purpose: the %%metta cell magic, exercised through IPython's own
interactive shell machinery; skipped without IPython.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from petta import MeTTa, S, V
from petta.ipython import use

globalipapp = pytest.importorskip("IPython.testing.globalipapp")


@pytest.fixture(scope="module")
def shell(metta):  # noqa: ARG001, D103  -- the test reflects this callable signature, so every declared parameter must remain visible; pytest discovers or injects this callable; its descriptive name states the contract
    ip = globalipapp.get_ipython()
    ip.run_line_magic("load_ext", "petta.ipython")
    return ip


def test_cell_magic_runs_and_returns_groups(shell, capsys):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    groups = shell.run_cell_magic("metta", "", "(= (nb-f) 7)\n!(nb-f)\n!(+ 1 2)")
    assert groups == [[7], [3]]
    printed = capsys.readouterr().out
    assert "7" in printed and "3" in printed


def test_cell_magic_targets_a_named_space(shell):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    shell.run_cell_magic("metta", "&nbspace", "(nb-fact here)")
    assert MeTTa("&nbspace").query(S["nb-fact"](V.x))[0].x == S.here


def test_ipython_magic_uses_selected_space(shell, metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta.new_space() as selected:
        use(selected)
        try:
            shell.run_cell_magic("metta", "", "(selected-fact here)")
            assert selected.query(S["selected-fact"](V.x))[0].x == S.here
        finally:
            use(metta)
