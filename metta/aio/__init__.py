"""Purpose: expose worker-owned asynchronous operations and result views.

Decides: DEFAULT_CLOSE_TIMEOUT gives worker shutdown ten seconds unless the
caller supplies another bound [tested: test_policy_constants_are_final;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Owns resources: connect transfers its started worker to the returned AsyncMeTTa;
cancelled startup closes the worker [tested:
test_aio_cancelled_connect_leaves_no_live_worker; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import metta.aio as _aio
from metta._atoms.designation import _DEFAULT_SPACE
from metta._atoms.factories import Expression, Symbol
from metta._lazy import lazy as _lazy
from metta._lazy import package as _package

if TYPE_CHECKING:
    import metta as _root
    from metta.aio._mirror import AsyncMeTTa as AsyncMeTTa
    from metta.aio._views import AsyncSaga as AsyncSaga
    from metta.aio._views import AsyncWorld as AsyncWorld

else:
    _root = _lazy("metta")

DEFAULT_CLOSE_TIMEOUT: Final[float] = 10.0

__all__ = ["AsyncMeTTa", "connect"]
__getattr__, __dir__ = _package(__name__)

async def connect(
    space: str | Symbol | Expression | _root.Space = _DEFAULT_SPACE,
    *,
    metta: _root.Space | None = None,
) -> _aio.AsyncMeTTa:
    """An AsyncMeTTa with its engine thread already running, aiosqlite's
    own naming for the entry point.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return await _aio.AsyncMeTTa(space, metta=metta).start()
