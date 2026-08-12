"""Purpose: a %%metta cell magic for the ordinary Python kernel, so one
notebook holds both languages and one session holds both namespaces. The
full-notebook experience is trueagi-io/jupyter-petta-kernel; this composes
with it rather than competing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None

    %load_ext petta.ipython

    %%metta
    (= (foo) boo)
    !(foo)
"""

from __future__ import annotations

from .space import MeTTa

_METTA: MeTTa | None = None


def _current() -> MeTTa:
    global _METTA
    if _METTA is None:
        _METTA = MeTTa()
    return _METTA


def use(metta: MeTTa) -> None:
    """Point the magic at a space other than the default &self."""
    global _METTA
    _METTA = metta


def load_ipython_extension(ipython) -> None:
    """Register the %%metta cell magic; IPython calls this on %load_ext."""

    def metta(line: str, cell: str):
        """Run the cell as MeTTa source; the line names a space if given."""
        target = _current() if not line.strip() else _current().space(line.strip())
        groups = target.run(cell)
        # One printed line per directive, the way the CLI prints, and the
        # structured groups as the cell's value for the notebook to show.
        for group in groups:
            print(" ".join(str(a) for a in group))
        return groups

    ipython.register_magic_function(metta, magic_kind="cell", magic_name="metta")
