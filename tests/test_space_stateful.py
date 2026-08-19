"""Purpose: exercise space behavior across generated operation histories.
Guarantees:
  - stored atoms, length, membership, and exact queries follow a multiset
    model after every generated operation [tested TestSpaceStateMachine]
  - text and fast saves load into a fresh space with the same multiset
    [tested TestSpaceStateMachine]
  - remove subtracts ONE matching plain-fact copy, remove-atom's multiset
    law, and reports whether one was there [tested TestSpaceStateMachine]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from collections import Counter
from tempfile import TemporaryDirectory

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule  # noqa: E402

from petta import Expr, MeTTa, Var, testing, unify  # noqa: E402


def _substitute(atom, bindings):
    if isinstance(atom, Var):
        return bindings.get(atom.name, atom)
    if isinstance(atom, Expr):
        return Expr([_substitute(child, bindings) for child in atom])
    return atom


class SpaceStateMachine(RuleBasedStateMachine):
    """A real PeTTa space checked against a Counter reference model."""

    def __init__(self):
        super().__init__()
        self._owner = MeTTa()
        self.space = self._owner.new_space()
        self.model = Counter()
        self._temporary = TemporaryDirectory(prefix="petta-stateful-")

    @rule(atom=testing.expressions(max_leaves=5, ground=True))
    def add(self, atom):
        self.space.add(atom)
        self.model[atom] += 1

    @rule(atom=testing.expressions(max_leaves=5, ground=True))
    def add_duplicate(self, atom):
        self.space.add(atom, atom)
        self.model[atom] += 2

    @rule(atom=testing.expressions(max_leaves=5, ground=True))
    def remove(self, atom):
        """Multiset subtraction: one copy leaves and the answer says whether
        one did. The model used to pop the whole count, which is what the
        engine used to do; hypothesis found the disagreement on the first
        add_duplicate-then-remove history it generated."""
        expected = atom in self.model
        assert self.space.remove(atom) is expected
        self.model -= Counter({atom: 1})

    @rule()
    def clear(self):
        self.space.clear()
        self.model.clear()

    @rule(pattern=testing.expressions(max_leaves=5))
    def query_matches_the_reference_model(self, pattern):
        expected = Counter()
        for atom, copies in self.model.items():
            if unify(pattern, atom) is not None:
                expected[atom] += copies

        rows = self.space.query(pattern)
        actual = Counter(
            _substitute(pattern, dict(zip(rows.columns, row, strict=True))) for row in rows
        )
        assert actual == expected

    @rule(format=st.sampled_from(("metta", "fast")))
    def save_load_round_trip(self, format):
        path = f"{self._temporary.name}/space.{format}"
        assert self.space.save(path, format=format) == sum(self.model.values())
        with self._owner.new_space() as loaded:
            loaded.load(path)
            assert Counter(loaded.atoms()) == self.model

    @invariant()
    def storage_matches_the_reference_model(self):
        assert Counter(self.space.atoms()) == self.model
        assert len(self.space) == sum(self.model.values())
        for atom in self.model:
            assert atom in self.space

    def teardown(self):
        self.space.drop()
        self._temporary.cleanup()


TestSpaceStateMachine = SpaceStateMachine.TestCase
TestSpaceStateMachine.settings = settings(
    max_examples=25,
    stateful_step_count=20,
    deadline=None,
)
