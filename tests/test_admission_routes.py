"""Purpose: verify the public Python space write rides engine pre-add admission.

Guarantees:
  - ``Space.add`` observes accept, transform, drop, and refuse from the
    existing ``declare-pre-add!`` registry [tested:
    test_public_space_add_observes_every_pre_add_verdict; commit=ce55fe46f26484be4269d06d6b99684d5edc040f]
  - relative ``S.admits`` and ``S.capacity`` values written through ``+=`` use
    the receiver installers and their admission checks compose in either order
    [tested: test_relative_capacity_declaration_installs_the_receiver_contract,
    test_relative_admits_declaration_installs_the_receiver_contract,
    test_two_declared_admission_checks_interact_over_one_store;
    commit=012413efb73b4dd27c71354c7f654862f349c03f]
"""

from __future__ import annotations

import uuid

import pytest

from metta import S, V
from metta.errors import EngineError, PettaError


def _named_pool(metta, purpose):
    """Create a test-unique pool so catalog declarations cannot be reused."""
    pool = metta._at(f"&{purpose}-{uuid.uuid4().hex[:8]}")
    pool.clear()
    return pool


def _drop_admission_pool(metta, pool):
    """Remove the pool's hook claim before dropping its named storage."""
    metta.eval(S["undeclare-pre-add!"](pool))
    pool.drop()


def test_public_space_add_observes_every_pre_add_verdict(metta):
    """Exercise all four admission verdicts through the public write door."""
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


def test_relative_capacity_declaration_installs_the_receiver_contract(metta):
    """A relative capacity declaration governs the following writes."""
    pool = _named_pool(metta, "relative-capacity")
    try:
        pool += S.capacity(1)
        assert pool.atoms() == []

        pool += S.item(1)
        assert len(pool) == 1
        with pytest.raises(EngineError, match="pool-at-capacity"):
            pool += S.item(2)
        assert pool.atoms() == [S.item(1)]
    finally:
        _drop_admission_pool(metta, pool)


def test_relative_admits_declaration_installs_the_receiver_contract(metta):
    """A relative admits declaration refuses the very next wrong write."""
    suffix = uuid.uuid4().hex[:8]
    pool = _named_pool(metta, "relative-admits")
    accepted = S[f"relative-admits-{suffix}"]
    declaration = S[":"](accepted, S.RelativeWidget)
    metta.add(declaration)
    try:
        pool += S.admits(S.RelativeWidget)
        assert pool.atoms() == []
        with pytest.raises(EngineError, match="does-not-carry"):
            pool += S.wrong(1)
        assert pool.atoms() == []
    finally:
        _drop_admission_pool(metta, pool)
        metta.remove(declaration)


def test_two_declared_admission_checks_interact_over_one_store(metta):
    """Admission precedes capacity and refusals never consume capacity."""
    suffix = uuid.uuid4().hex[:8]
    first = S[f"relative-first-{suffix}"]
    second = S[f"relative-second-{suffix}"]
    declarations = [S[":"](value, S.RelativeWidget) for value in (first, second)]
    metta.add(*declarations)
    try:
        for declaration_order in ("admits-first", "capacity-first"):
            pool = _named_pool(metta, f"relative-both-{declaration_order}")
            try:
                if declaration_order == "admits-first":
                    pool += S.admits(S.RelativeWidget)
                    pool += S.capacity(1)
                else:
                    pool += S.capacity(1)
                    pool += S.admits(S.RelativeWidget)

                assert len(pool) == 0
                catalog = metta._at("&petta")
                pool_name = S[str(pool.name)]
                assert S.admits(pool_name, S.RelativeWidget) in catalog
                assert S.capacity(pool_name, 1) in catalog
                assert len(catalog.match(S["pre-add"](pool_name, V.handler))) == 1
                with pytest.raises(EngineError, match="does-not-carry"):
                    pool += S.wrong(1)
                assert len(pool) == 0

                pool += first
                assert pool.atoms() == [first]
                with pytest.raises(EngineError, match="pool-at-capacity"):
                    pool += second
                assert pool.atoms() == [first]

                with pytest.raises(EngineError, match="does-not-carry"):
                    pool += S.wrong(2)
                assert pool.atoms() == [first]
            finally:
                _drop_admission_pool(metta, pool)
    finally:
        for declaration in declarations:
            metta.remove(declaration)


def test_relative_declarations_refuse_inside_an_active_batch(metta):
    """A declaration cannot overtake facts held by a transport batch."""
    pool = _named_pool(metta, "relative-batch")
    try:
        with pool.batch():
            pool += S.item(1)
            with pytest.raises(PettaError, match="inside its own batch"):
                pool += S.capacity(1)
        assert pool.atoms() == [S.item(1)]
    finally:
        pool.drop()
