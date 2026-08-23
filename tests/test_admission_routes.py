"""Purpose: verify the public Python space write rides engine pre-add admission.

Guarantees:
  - ``Space.add`` observes accept, transform, drop, and refuse from the
    existing ``declare-pre-add!`` registry [tested:
    test_public_space_add_observes_every_pre_add_verdict; commit=WORKTREE]
"""

from __future__ import annotations

import uuid

import pytest

from petta import S
from petta.errors import EngineError


def test_public_space_add_observes_every_pre_add_verdict(metta):
    suffix = uuid.uuid4().hex[:8]
    guard = f"route-guard-{suffix}"
    pool = metta._new_space()
    try:
        metta.run(
            f"(= ({guard} (plain $x)) (accept))\n"
            f"(= ({guard} (raw $x)) (accept (cooked $x)))\n"
            f"(= ({guard} (dup $x)) (drop))\n"
            f"(= ({guard} (secret $x)) (refuse \"route refused\"))"
        )
        metta.run(f"!(declare-pre-add! {pool.name} {guard})")

        pool.add(S.plain(1))
        pool.add(S.raw(2))
        pool.add(S.dup(3))
        with pytest.raises(EngineError, match="route refused"):
            pool.add(S.secret(4))

        assert pool.atoms() == [S.plain(1), S.cooked(2)]
    finally:
        metta.run(f"!(undeclare-pre-add! {pool.name})")
        pool.drop()
