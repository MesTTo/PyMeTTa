"""Purpose: the %%metta cell magic, exercised through IPython's own
interactive shell machinery; skipped without IPython.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

IPython = pytest.importorskip("IPython")

from petta import S  # noqa: E402


@pytest.fixture(scope="module")
def shell(metta):
    from IPython.testing.globalipapp import get_ipython

    ip = get_ipython()
    ip.run_line_magic("load_ext", "petta.ipython")
    return ip


def test_cell_magic_runs_and_returns_groups(shell, capsys):
    groups = shell.run_cell_magic("metta", "", "(= (nb-f) 7)\n!(nb-f)\n!(+ 1 2)")
    assert groups == [[7], [3]]
    printed = capsys.readouterr().out
    assert "7" in printed and "3" in printed


def test_cell_magic_targets_a_named_space(shell):
    shell.run_cell_magic("metta", "&nbspace", "(nb-fact here)")
    from petta import MeTTa, V

    assert MeTTa("&nbspace").query(S["nb-fact"](V.x))[0].x == S.here
