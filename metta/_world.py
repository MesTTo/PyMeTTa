"""Purpose: represent, branch, evaluate, diff, and commit immutable worlds.

Assumes:
  - a provider is reifiable only through ``foreign.Snapshotter``; ordinary
    enumeration is live and is never promoted to a snapshot.
Guarantees:
  - evaluation replays into a fresh receiver, rebases self references, fences
    State writes, emits no event, and returns a new frozen world without
    changing its parent [tested: test_world_eval_branches_without_touching_parent,
    test_world_eval_fences_state_and_emits_nothing; commit=WORKTREE]
  - commit validates the world's origin and base inside the owning
    transaction, then removes and adds the multiset diff as ordinary writes
    whose events publish after the complete diff is visible [tested:
    test_commit_applies_the_world_diff_as_post_commit_events; commit=WORKTREE]
Fails when:
  - a live member has no snapshot protocol, the parent changed since reify,
    or a provider cannot participate in an atomic transaction.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._space_objects import _apply_limited, _limits
from .atoms import Atom, Undefined, _atom_from_wire, _from_wire, _to_atom
from .errors import PettaError
from .foreign import Transactional, WorldCommitter
from .spaces import _Member, _surplus

if TYPE_CHECKING:
    from ._space import Space


def _permit_world_effect(_space: Space, _target: Any) -> None:
    """Permissive admission until the sibling EffectClass lane wires policy."""


# Integration seam for the sibling effect-rank implementation. World.eval
# calls this predicate exactly once before creating or mutating scratch state.
_WORLD_EFFECT_ADMISSION: Callable[[Space, Any], None] = _permit_world_effect


@dataclass(frozen=True, slots=True)
class ReifiedWorld:
    """One immutable multiset state with an immutable reification base."""

    _origin: Space = field(repr=False, compare=False)
    _base: tuple[Atom, ...] = field(repr=False)
    atoms: tuple[Atom, ...]

    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[Atom | Undefined], ReifiedWorld]:
        """Evaluate against this value and return ``(answers, successor)``."""
        _WORLD_EFFECT_ADMISSION(self._origin, target)
        scratch = self._origin._new_space()
        target_wire = target if isinstance(target, str) else _to_atom(target).to_wire()
        inputs = [
            scratch._space,
            self._origin._space,
            [atom.to_wire() for atom in self.atoms],
            target_wire,
        ]
        try:
            limits = _limits(timeout, inferences)
            if limits is None:
                answer_wires, atom_wires = self._origin._rt.apply_must(
                    "petta_py_world_eval", *inputs
                )
            else:
                answer_wires, atom_wires = _apply_limited(
                    self._origin._rt,
                    limits,
                    "petta_py_world_eval",
                    inputs,
                )
        finally:
            # petta_py_world_eval clears while its discard frame is open. The
            # drop therefore only retires the now-empty anonymous name.
            scratch.drop()

        answers = [_from_wire(wire) for wire in answer_wires]
        atoms = tuple(_atom_from_wire(wire) for wire in atom_wires)
        return answers, ReifiedWorld(self._origin, self._base, atoms)

    def diff(self, other: ReifiedWorld) -> tuple[list[Atom], list[Atom]]:
        """Return this world's and the other world's ordered multiset extras."""
        if not isinstance(other, ReifiedWorld):
            msg = f"a world diff needs another ReifiedWorld, got {type(other).__name__}"
            raise TypeError(msg)
        return (
            _surplus(list(self.atoms), list(other.atoms)),
            _surplus(list(other.atoms), list(self.atoms)),
        )


def reify_space(space: Space) -> ReifiedWorld:
    """Capture one space through its native or explicit provider snapshot."""
    captured = _Member(space).snapshot()
    return ReifiedWorld(space, captured, captured)


def commit_world(space: Space, world: ReifiedWorld) -> None:
    """Apply a world's base-relative multiset diff in one transaction."""
    if not isinstance(world, ReifiedWorld):
        msg = f"commit expects a ReifiedWorld, got {type(world).__name__}"
        raise TypeError(msg)
    if world._origin != space:
        msg = (
            f"world belongs to {world._origin}, not {space}; commit it through "
            "the space that produced it"
        )
        raise PettaError(msg)
    removed = _surplus(list(world._base), list(world.atoms))
    added = _surplus(list(world.atoms), list(world._base))
    backing = getattr(space, "_backing", None)
    if isinstance(backing, WorldCommitter):
        if space._rt.once("petta_in_user_transaction"):
            msg = (
                "a provider-owned world commit cannot nest inside an engine "
                "transaction; commit the world as the transaction boundary"
            )
            raise PettaError(msg)
        backing.commit_world(world._base, removed, added)
        # The provider has finished its durable delta. Feed exactly those
        # ordinary changes through the same observer seam native writes use.
        space._rt.must(
            "petta_py_publish_world_diff(Space, Removed, Added)",
            Space=space._space,
            Removed=[atom.to_wire() for atom in removed],
            Added=[atom.to_wire() for atom in added],
        )
        return
    if backing is not None and not isinstance(backing, Transactional):
        msg = (
            f"{space} is backed by {type(backing).__name__}, which can snapshot "
            "but cannot commit a world atomically because it implements no "
            "WorldCommitter or Transactional protocol"
        )
        raise PettaError(msg)

    def apply_diff() -> None:
        current = _Member(space).snapshot()
        if _surplus(list(current), list(world._base)) or _surplus(list(world._base), list(current)):
            msg = (
                f"{space} changed after this world was reified; refusing a "
                "stale diff that could erase or duplicate concurrent writes"
            )
            raise PettaError(msg)
        for atom in removed:
            if not space.remove(atom):
                msg = f"world commit could not remove its base atom {atom} from {space}"
                raise PettaError(msg)
        if added:
            space.add(*added)

    space.transaction(apply_diff)


__all__ = ["ReifiedWorld"]
