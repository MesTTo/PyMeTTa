"""Purpose: verify stable provider identity, token refusals and stream cleanup.

Guarantees: blame preserves occurrence multiplicity and orders provider tokens;
    invalid or failed streams close [tested: test_provider_token_streams_close;
    commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
Guarantees: optional mutation methods make a provider a reference receiver
    without ordinary add/remove methods [tested:
    test_token_mutation_receives_and_withdraws_a_reference; commit=WORKTREE].
"""

from contextlib import contextmanager

import pytest

from metta import MeTTa, S, V
from metta._declare import declarations as _space_declarations
from metta._errors.errors import EngineError, SpaceCapabilityError
from metta.foreign import (
    SpaceProvider,
    TokenAdder,
    TokenProvider,
    TokenRemover,
    foreign_remove_token,
)
from metta.testing import SpaceComplianceSuite


class TokenRows(SpaceProvider):
    """A stream whose close count reveals every query's cleanup."""

    def __init__(self, pairs, *, fail=False):
        """Hold stable row identities and an optional stream failure."""
        self.pairs = pairs
        self.fail = fail
        self.closed = 0

    def atoms(self):
        """Enumerate the same bag the token pairs identify."""
        return (atom for _, atom in self.pairs)

    def tokens(self, _pattern):
        """Yield provider candidates; the engine performs unification."""
        try:
            yield from self.pairs
            if self.fail:
                message = "token stream failed"
                raise ValueError(message)
        finally:
            self.closed += 1


@contextmanager
def provider_space(m, provider):
    """Keep process-wide registration scoped to one test."""
    name = f"&occurrence-provider-{id(provider)}"
    _space_declarations._register_space(m.self, provider, name)
    try:
        yield m.self._at(name)
    finally:
        _space_declarations._unregister_space(m.self, name)


def test_provider_tokens_keep_multiplicity_order_and_identity(tmp_path):
    """An equal atom with two row identities is two occurrences on both doors."""
    atom = S.row(1)
    expected = [S.t(S.a, 6), S.t(S.a, 7), S.t(S.z, 7)]
    provider = TokenRows([(expected[2], atom), (expected[0], atom),
                          (S.t(S.z, 3), S.row(2)), (expected[1], atom)])
    assert isinstance(provider, TokenProvider)
    with MeTTa() as m, provider_space(m, provider) as space, m.space() as restored:
        assert space.blame(atom) == expected
        assert provider.closed == 1
        assert space.blame(S.absent) == []
        assert provider.closed == 2
        path = tmp_path / "provider.fast"
        assert space.save(path, format="fast") == 4
        assert provider.closed == 3
        restored.load(path)
        assert restored.blame(atom) == expected
        assert len(restored) == 4


@pytest.mark.parametrize("bad", [S.t(S.actor, -1), S.t(S.actor, 1.5), S.wrong])
def test_provider_token_streams_close_after_invalid_identity(bad):
    """Refusal closes a provider suspended immediately after its yielded row."""
    provider = TokenRows([(bad, S.row(1))])
    with MeTTa() as m, provider_space(m, provider) as space:
        with pytest.raises(EngineError):
            space.blame(S.row(1))
        assert provider.closed == 1
        assert m.eval(S["+"](1, 2)) == [3]


def test_provider_token_streams_close(tmp_path):
    """A late exception and duplicate identities are failures, never short bags."""
    pair = (S.t(S.actor, 1), S.row(1))
    with MeTTa() as m:
        failed = TokenRows([pair], fail=True)
        with provider_space(m, failed) as space:
            with pytest.raises(EngineError, match="token stream failed"):
                space.blame(S.row(1))
            assert failed.closed == 1
        duplicate = TokenRows([pair, pair])
        with provider_space(m, duplicate) as space:
            with pytest.raises(EngineError, match="distinct_occurrence_tokens"):
                space.blame(S.row(1))
            assert duplicate.closed == 1
            path = tmp_path / "duplicate.fast"
            with pytest.raises(EngineError, match="distinct_occurrence_tokens"):
                space.save(path, format="fast")
            assert duplicate.closed == 2
            assert not path.exists()


def test_eager_provider_failure_is_classified():
    """Calling tokens itself can fail before an iterator is returned."""
    class EagerFailure(SpaceProvider):
        def tokens(self, _pattern):
            message = "eager token failure"
            raise ValueError(message)

    with MeTTa() as m, provider_space(m, EagerFailure()) as space:
        with pytest.raises(EngineError, match="eager token failure"):
            space.blame(S.row(1))


class TestTokenRowsComply(SpaceComplianceSuite):
    """Stable token rows satisfy the same laws as every other provider."""

    @pytest.fixture()
    def provider(self):
        """Supply two equal occurrences and one different row."""
        return TokenRows([(S.t(S.rows, 1), S.row(1)),
                          (S.t(S.rows, 2), S.row(1)),
                          (S.t(S.rows, 3), S.row(2))])


class MutableTokenRows(TokenRows):
    """An in-memory fixture implementing only the optional mutation doors."""

    def __init__(self, pairs):
        """Keep the existing identities and a separate fresh actor."""
        super().__init__(pairs)
        self.generation = 0

    def add_token(self, atom):
        """Append one occurrence with a fresh identity."""
        self.generation += 1
        token = S.t(S[f"mutable-provider-{id(self)}"], self.generation)
        self.pairs.append((token, atom))
        return token

    def remove_token(self, token):
        """Remove by identity even when several occurrences have equal atoms."""
        for index, (held, _) in enumerate(self.pairs):
            if held == token:
                del self.pairs[index]
                return True
        return False


class TestMutableTokenRowsComply(TestTokenRowsComply):
    """Both optional mutations pass the existing compliance coverage law."""

    @pytest.fixture()
    def provider(self):
        """Keep duplicate contents so value-based removal would be caught."""
        return MutableTokenRows([(S.t(S.rows, 1), S.row(1)),
                                 (S.t(S.rows, 2), S.row(1))])


def test_token_mutation_receives_and_withdraws_a_reference():
    """The engine uses exact mutations for a stored reference and its removal."""
    provider = MutableTokenRows([])
    assert isinstance(provider, TokenAdder) and isinstance(provider, TokenRemover)
    assert not provider.can_run("add") and not provider.can_run("remove")
    with MeTTa() as m, m.space() as home, provider_space(m, provider) as target:
        home.add(S["="](S.token_answer(), 42))
        target.from_(home)
        row = S["from"](home)
        assert len(target.blame(row)) == 1
        assert target.eval(S.token_answer()) == [42]
        assert target.remove(row)
        assert not target.blame(row)
        assert target.eval(S.token_answer()) == [S.token_answer()]


@pytest.mark.parametrize("result", [None, 1, "true"])
def test_exact_remove_requires_a_boolean_verdict(result):
    """A provider cannot turn an ambiguous verdict into successful removal."""
    class BadVerdict(MutableTokenRows):
        def remove_token(self, _token):
            return result

    with MeTTa() as m, provider_space(m, BadVerdict([])) as space:
        with pytest.raises(EngineError, match="remove_token must return a bool"):
            foreign_remove_token(space.name, S.t(S.rows, 1).to_wire())
        assert space.blame(V.any) == []


def test_compliance_rejects_unstable_tokens():
    """Distinct tokens that change between reads fail the identity law."""
    class UnstableRows(TokenRows):
        def tokens(self, _pattern):
            self.closed += 1
            return [(S.t(S.rows, self.closed), S.row(1))]

    provider = UnstableRows([])
    with MeTTa() as m, provider_space(m, provider) as space:
        with pytest.raises(AssertionError):
            SpaceComplianceSuite().test_tokens_identify_each_stored_occurrence_stably(
                provider, {"ran": set(), "skipped": set()}, space, [S.row(1)])


def test_tokenless_provider_refuses_blame_and_fast_save(tmp_path):
    """Content reads remain available; token reads name their missing capability."""
    class AnonymousRows(SpaceProvider):
        def atoms(self):
            return iter([S.row(1)])

    with MeTTa() as m, provider_space(m, AnonymousRows()) as space:
        assert list(space.atoms()) == [S.row(1)]
        for operation in (lambda: space.blame(S.row(1)),
                          lambda: space.save(tmp_path / "refused.fast", format="fast")):
            with pytest.raises(SpaceCapabilityError, match="native overlay") as caught:
                operation()
            assert "stable provider identities" in str(caught.value)
        assert not (tmp_path / "refused.fast").exists()
