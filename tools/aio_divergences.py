"""Purpose: project async and context policy from the door contracts.

Guarantees: membership and worker exceptions come from the same rows that
  declare the synchronous surface [tested:
  test_every_async_counterpart_has_the_sync_parameters; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
"""

from __future__ import annotations

import sys
from pathlib import Path

# A component is a distribution OR a repository, so both markers are asked for:
# a tree copied without its history has no `.git`, which is how every gate here
# runs, in a worktree populated by rsync. Derived inline rather than through
# `metta._roots`, which states the same rule, because this tool runs as a SCRIPT
# and puts tools/ on sys.path rather than the seat.
sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents
     if (parent / 'pyproject.toml').exists() or (parent / '.git').exists())))
from metta.doors import Owner, Tier, core_rows

_rows = core_rows()

EXCLUDED = {
    row.python: row.async_excluded for row in _rows
    if row.owner is Owner.space and row.async_excluded is not None
}
DIVERGENT = {
    row.python: (row.async_signature.parameters, row.async_reason)
    for row in _rows if row.owner is Owner.space and row.async_signature is not None
}
PRIVATE_TARGET = {
    (row.alias or row.python): (
        row.python if Tier.sync in row.tiers else row.body.symbol.rpartition(".")[2]
    )
    for row in _rows if row.owner is Owner.space and row.body is not None
    and Tier.async_ in row.tiers and (row.alias or Tier.sync not in row.tiers)
}
MODULE_DOORS = tuple(
    (row.alias or row.python, row.python) for row in _rows
    if row.owner is Owner.space and Tier.module in row.tiers
)
