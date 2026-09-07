"""Purpose: a %metta line magic and a %%metta cell magic for the ordinary
Python kernel, so one notebook holds both languages and one session holds both
namespaces. The full-notebook experience is trueagi-io/jupyter-petta-kernel;
this composes with it rather than competing, and `metta._pygments` is what
colours a MeTTa cell under either.
Guarded by:
  - _MagicSession._lock protects the selected space [tested
    test_ipython_magic_uses_selected_space]
Guarantees:
  - `%metta <source>` and `%%metta [space]` are one registration in IPython's
    own line_cell form, so the two cannot drift apart the way `%time` and
    `%%time` cannot [tested: test_line_magic_runs_one_line_against_the_selection;
    commit=7ba114f280ec3b132658cacb562064d0bac23f41]
  - `%metta` with nothing after it refuses with the two spellings that do
    something, rather than running the empty program [tested:
    test_the_line_magic_refuses_an_empty_line; commit=7ba114f280ec3b132658cacb562064d0bac23f41]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.

    %load_ext metta.ipython

    %metta !(+ 1 2)

    %%metta
    (= (foo) boo)
    !(foo)
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import threading

from ._api_types import _SpaceId
from ._space import Space as MeTTa


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
    """Register %metta and %%metta; IPython calls this on %load_ext."""
    # Imported here rather than at the top of the module, because `use()` is
    # importable in a plain Python process and IPython need not be installed
    # there; by the time this runs, the shell that called it is loaded.
    from IPython.core.error import UsageError  # noqa: PLC0415

    def metta(line: str, cell: str | None = None):
        """Run MeTTa source: the line for %metta, the cell for %%metta.

        One function in IPython's `line_cell` form, which is how `%time` and
        `%%time` stay one magic, so the two faces cannot drift apart. What the
        LINE means is what differs, because it is the argument line in both and
        the argument is not the same thing:

            %metta !(+ 1 2)         the line is the program
            %%metta                 the line names a space, or is empty
            %%metta &kb             for &self, and the cell is the program

        A one-line evaluation therefore has no room to name a space, and
        `use(m)` is the rung below it: it points both faces at one runtime for
        the rest of the session.

        Both print one line per directive, the way the CLI prints, and return
        the structured answer groups as the cell's value.
        """
        if cell is None:
            if not line.strip():
                msg = (
                    "%metta wants MeTTa source on the same line, as in "
                    "`%metta !(+ 1 2)`; `%%metta` runs a whole cell, and its "
                    "line names a space instead"
                )
                raise UsageError(msg)
            target, source = _current(), line
        else:
            target = (
                _current()
                if not line.strip()
                else _current()._at(_SpaceId(line.strip()))
            )
            source = cell
        groups = target.run(source)
        for group in groups:
            print(" ".join(str(a) for a in group))
        return groups

    ipython.register_magic_function(metta, magic_kind="line_cell", magic_name="metta")
