"""Purpose: a %%metta cell magic for the ordinary Python kernel, so one
notebook holds both languages and one session holds both namespaces. The
full-notebook experience is trueagi-io/jupyter-petta-kernel; this composes
with it rather than competing.
Guarded by:
  - _MagicSession._lock protects the selected space [tested
    test_ipython_magic_uses_selected_space]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.

    %load_ext petta.ipython

    %%metta
    (= (foo) boo)
    !(foo)
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import threading

from ._api_types import SpaceName
from .space import MeTTa


class _MagicSession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metta: MeTTa | None = None

    def current(self) -> MeTTa:
        with self._lock:
            if self._metta is None:
                self._metta = MeTTa()
            return self._metta

    def use(self, metta: MeTTa) -> None:
        with self._lock:
            self._metta = metta


_SESSION = _MagicSession()


def _current() -> MeTTa:
    return _SESSION.current()


def use(metta: MeTTa) -> None:
    """Point the magic at a space other than the default &self."""
    _SESSION.use(metta)


def load_ipython_extension(ipython) -> None:
    """Register the %%metta cell magic; IPython calls this on %load_ext."""

    def metta(line: str, cell: str):
        """Run the cell as MeTTa source; the line names a space if given."""
        target = (
            _current()
            if not line.strip()
            else _current().space(SpaceName(line.strip()))
        )
        groups = target.run(cell)
        # One printed line per directive, the way the CLI prints, and the
        # structured groups as the cell's value for the notebook to show.
        for group in groups:
            print(" ".join(str(a) for a in group))
        return groups

    ipython.register_magic_function(metta, magic_kind="cell", magic_name="metta")
