"""Purpose: pin the behavioral laws taught by the Python-first guide.

Assumes:
  - bare Python threads share the home engine and serialize individual engine
    calls, while callers own synchronization across several calls.
Guarantees:
  - a walrus-bound nondeterministic call uses call-time choice, so both uses
    in one pair share one answer [tested:
    test_walrus_call_time_choice_shares_one_nondeterministic_value;
    commit=WORKTREE]
  - State.value augmented assignment is a non-atomic read-modify-write, and a
    caller lock makes the compound update atomic [tested:
    test_state_increment_requires_a_lock_around_read_modify_write;
    commit=WORKTREE]
  - grouped MettaResultError reprs carry their Error atoms without fabricated
    Python stack text [tested:
    test_grouped_metta_errors_render_atoms_without_python_stacks;
    commit=WORKTREE]
  - record attribute docstrings are recovered from source for @doc while the
    runtime field descriptor has no __doc__ [tested:
    test_attribute_docstrings_are_source_only_not_field_runtime_docs;
    commit=WORKTREE]
  - the guide keeps every documentation-law explainer and boundary sentence
    in its owning page [tested: test_guides_keep_documentation_law_explainers;
    commit=WORKTREE]
"""

import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Barrier, Lock

import pytest

from metta import Expression, MeTTa, S, State, V
from metta.errors import MettaResultError

_REPOSITORY = Path(__file__).resolve().parents[3]


def _guide(name: str) -> str:
    text = (_REPOSITORY / "website" / "guide" / name).read_text(encoding="utf-8")
    return " ".join(text.split())


class _RendezvousState(State[int]):
    """A State whose two test reads meet before either augmented write."""

    __slots__ = ("_read_barrier",)

    def __init__(self, value: int, *, space, read_barrier: Barrier) -> None:
        super().__init__(value, space=space)
        self._read_barrier = read_barrier

    @property
    def value(self) -> int:
        """Read through the real State door, then expose the legal race."""
        assert State.value.fget is not None
        current = State.value.fget(self)
        self._read_barrier.wait()
        return current

    @value.setter
    def value(self, replacement: int) -> None:
        """Write through the real State door after both reads completed."""
        assert State.value.fset is not None
        State.value.fset(self, replacement)


def test_walrus_call_time_choice_shares_one_nondeterministic_value() -> None:
    """One nondeterministic call is chosen once for both pair positions."""
    with MeTTa().space() as target:

        @target.define
        def docs_law_coin():
            yield 0
            yield 1

        @target.define
        def docs_law_doubled_pair():
            return ((choice := docs_law_coin()), choice)

        answers = target.eval(S.docs_law_doubled_pair())
        expected = [Expression((0, 0)), Expression((1, 1))]
        assert Counter(answers) == Counter(expected)
        assert all(answer[0] == answer[1] for answer in answers)


def test_state_increment_requires_a_lock_around_read_modify_write() -> None:
    """Engine serialization covers each property access, not the += pair."""
    with MeTTa().space() as target:
        racy = _RendezvousState(0, space=target, read_barrier=Barrier(2, timeout=30))

        def increment_racy() -> None:
            racy.value += 1

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(increment_racy) for _ in range(2)]
            for future in futures:
                future.result()

        assert State.value.fget is not None
        assert State.value.fget(racy) == 1

        protected = State[int](0, space=target)
        update_lock = Lock()

        def increment_under_lock() -> None:
            with update_lock:
                protected.value += 1

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(increment_under_lock) for _ in range(2)]
            for future in futures:
                future.result()

        assert protected.value == 2


def test_grouped_metta_errors_render_atoms_without_python_stacks() -> None:
    """The group displays the error values it carries, not invented traces."""
    with MeTTa().space() as target:
        target.add(
            '(docs-law-log first (Error (job 1) "boom"))',
            '(docs-law-log second (Error (job 2) "bust"))',
        )
        with pytest.raises(ExceptionGroup) as failure:
            target.match(S.docs_law_log(V.id, V.error)).raise_for_errors()

        group = failure.value
        assert all(isinstance(error, MettaResultError) for error in group.exceptions)
        assert all(str(error.atom) in repr(error) for error in group.exceptions)
        rendered = "".join(traceback.format_exception(group))
        assert all(str(error.atom) in rendered for error in group.exceptions)
        assert all(error.__traceback__ is None for error in group.exceptions)

        tree = traceback.TracebackException.from_exception(group)
        assert tree.exceptions is not None
        assert all(not error.stack for error in tree.exceptions)


def test_attribute_docstrings_are_source_only_not_field_runtime_docs() -> None:
    """PeTTa parses the source prose; CPython does not attach it to a field."""
    with MeTTa().space() as target:

        @target.define
        @dataclass(slots=True)
        class DocsLawOrder:
            total: int
            """The total carried by this order."""

        documentation = [
            str(atom)
            for atom in target.atoms()
            if str(atom).startswith("(@doc DocsLawOrder ")
        ]
        assert len(documentation) == 1
        assert "The total carried by this order." in documentation[0]
        assert DocsLawOrder.total.__doc__ is None


def test_guides_keep_documentation_law_explainers() -> None:
    """The prose that closes each audited row remains explicit and findable."""
    atoms = _guide("atoms-terms.md")
    assert "## S and V are name factories" in atoms
    assert "including the 3.12 floor" in atoms
    assert "`Space.run` accepts a `str`, not a `Template`" in atoms

    locations = _guide("where-code-runs.md")
    assert "## Staged term construction" in locations
    assert "## Live evaluation" in locations
    assert "## Compiled Python bodies" in locations

    concepts = _guide("concepts.md")
    assert "strongly encapsulates the nondeterminism evaluated below its own" in concepts
    assert "not choices that already formed its arguments" in concepts

    definitions = _guide("define.md")
    assert "one bound nondeterministic value is chosen once and shared" in definitions
    assert "`g = gen()` binds one generator object" in definitions

    threads = _guide("threads.md")
    assert "`cell.value += 1` is still a read followed by a separate write" in threads
    assert "Pickling an atom only makes a process argument transportable by value" in threads

    errors = _guide("run-query.md")
    assert "does not fabricate a stack for any error atom" in errors

    records = _guide("python-functions.md")
    assert "Python 3.13 adds the general spelling `copy.replace" in records
    assert "`Order.total.__doc__ is None`" in records

    floor = _guide("getting-started.md")
    assert "PeTTa supports Python 3.12 and newer" in floor
    assert "Python 3.14 adds t-string syntax" in floor
