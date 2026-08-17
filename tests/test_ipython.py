"""Purpose: the %%metta cell magic, exercised through IPython's own
interactive shell machinery; skipped without IPython.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import MeTTa, S, V
from petta.ipython import use

globalipapp = pytest.importorskip("IPython.testing.globalipapp")


@pytest.fixture(scope="module")
def shell(metta):
    ip = globalipapp.get_ipython()
    ip.run_line_magic("load_ext", "petta.ipython")
    return ip


def test_cell_magic_runs_and_returns_groups(shell, capsys):
    groups = shell.run_cell_magic("metta", "", "(= (nb-f) 7)\n!(nb-f)\n!(+ 1 2)")
    assert groups == [[7], [3]]
    printed = capsys.readouterr().out
    assert "7" in printed and "3" in printed


def test_cell_magic_targets_a_named_space(shell):
    shell.run_cell_magic("metta", "&nbspace", "(nb-fact here)")
    assert MeTTa("&nbspace").query(S["nb-fact"](V.x))[0].x == S.here


def test_ipython_magic_uses_selected_space(shell, metta):
    with metta.new_space() as selected:
        use(selected)
        try:
            shell.run_cell_magic("metta", "", "(selected-fact here)")
            assert selected.query(S["selected-fact"](V.x))[0].x == S.here
        finally:
            use(metta)
