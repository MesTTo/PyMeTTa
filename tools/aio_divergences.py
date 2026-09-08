"""Purpose: project async and context policy from the door contracts.

Guarantees: membership and worker exceptions come from the same rows that
  declare the synchronous surface [tested:
  test_every_async_counterpart_has_the_sync_parameters; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metta.doors import DOORS, Owner, Tier

EXCLUDED = {
    row.python: row.async_excluded for row in DOORS
    if row.owner is Owner.space and row.async_excluded is not None
}
DIVERGENT = {
    row.python: (row.async_signature.parameters, row.async_reason)
    for row in DOORS if row.owner is Owner.space and row.async_signature is not None
}
PRIVATE_TARGET = {
    row.python: row.body.symbol.rpartition(".")[2]
    for row in DOORS if row.owner is Owner.space and row.body is not None
    and Tier.async_ in row.tiers and Tier.sync not in row.tiers
}
MODULE_DOORS = tuple(
    (row.alias or row.python, row.python) for row in DOORS
    if row.owner is Owner.space and Tier.module in row.tiers
)
CONTEXT_DUNDERS = tuple(
    row.python for row in DOORS
    if row.owner is Owner.space and Tier.context in row.tiers and row.python.startswith("__")
)
INPLACE_DUNDERS = frozenset(row.python for row in DOORS if row.context_inplace)
