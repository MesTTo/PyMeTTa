"""Purpose: distinguish nested rollback from an outer-only provider transaction.

Owns resources: fixture contexts release each registered or native store.
"""

from collections import Counter

import pytest

from metta import MeTTa
from metta.testing import SpaceComplianceSuite

from .test_compliance_suite import ROWS, NativeInheritedSpace
from .test_foreign import ListSpace


class _OuterTransactionOnly(ListSpace):
    def __init__(self):
        super().__init__(ROWS)
        self.saved = None
        self.events = []

    def can_run(self, capability, /, **request):
        return capability == "savepoint" or super().can_run(capability, **request)

    def begin(self):
        self.saved = list(self.stored)
        self.events.append("begin")

    def commit(self):
        self.saved = None
        self.events.append("commit")

    def rollback(self):
        self.stored = self.saved
        self.saved = None
        self.events.append("rollback")


def test_savepoint_compliance_rejects_an_outer_transaction_only_provider():
    """Claiming the word cannot substitute for restoring a nested savepoint."""
    provider = _OuterTransactionOnly()
    record = {"ran": set(), "skipped": set()}
    with MeTTa() as context, context.space(backing=provider) as space:
        with pytest.raises(AssertionError, match="retained provider writes"):
            SpaceComplianceSuite().test_a_nested_transaction_restores_its_provider_savepoint(
                provider, record, space, list(provider.atoms()),
            )
        assert Counter(provider.atoms()) == Counter(ROWS)
        assert provider.events == ["begin", "rollback"]
        assert "savepoint" in record["ran"]


def test_savepoint_compliance_accepts_native_nested_rollback(monkeypatch):
    """The same law passes against the native engine's nested transaction."""
    provider = NativeInheritedSpace()
    original = provider.can_run
    monkeypatch.setattr(
        provider, "can_run",
        lambda capability, **request: capability == "savepoint" or original(capability, **request),
    )
    record = {"ran": set(), "skipped": set()}
    try:
        SpaceComplianceSuite().test_a_nested_transaction_restores_its_provider_savepoint(
            provider, record, provider.child, list(provider.atoms()),
        )
        assert Counter(provider.atoms()) == Counter(ROWS)
        assert "savepoint" in record["ran"]
    finally:
        provider.close()
