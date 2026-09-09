"""Purpose: represent, branch, evaluate, diff, and commit immutable worlds.

Assumes:
  - a provider is reifiable only through ``foreign.Snapshotter``; ordinary
    enumeration is live and is never promoted to a snapshot.
Guarantees:
  - a plan is admitted before scratch-space creation exactly when its joined
    effect is covered by the originating world's catalog declaration;
    structural plans need no declaration [tested:
    test_an_uncovered_world_refuses_before_creating_scratch_or_running_the_operation,
    test_world_coverage_admits_the_joined_plan; commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - evaluation replays into a fresh receiver, rebases self references, fences
    State writes, emits no event, and returns a new frozen world without
    changing its parent [tested: test_world_eval_branches_without_touching_parent,
    test_world_eval_fences_state_and_emits_nothing; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - commit validates the world's origin and base inside the owning
    transaction, then removes and adds the multiset diff as ordinary writes
    whose events publish after the complete diff is visible [tested:
    test_commit_applies_the_world_diff_as_post_commit_events; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Fails when:
  - a live member has no snapshot protocol, the parent changed since reify,
    or a provider cannot participate in an atomic transaction.
"""

from __future__ import annotations

import weakref
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn

import metta.doors as _doors
from metta._atoms.factories import Atom, Undefined, _atom_from_wire, _from_wire, _to_atom
from metta._binding.runtime import defer_engine_call
from metta._errors.errors import _EFFECT_SAFETY_GROUND, MettaError
from metta._spaces.scope import _apply_limited, _limits
from metta.foreign import Transactional, WorldCommitter
from metta.spaces import _Member, _surplus
from metta.vocabularies import EffectClass

if TYPE_CHECKING:
    import metta._faces.space as _space_face
else:
    import metta._faces.space as _space_face


def _raise_world_refusal(
    origin: _space_face.Space,
    target: Any,
    rows: list[Any],
    required_raw: Any,
    coverage_raw: Any,
) -> NoReturn:
    """Raise the one grounded refusal for either admission checkpoint."""
    required = EffectClass(str(required_raw))
    coverage = EffectClass(str(coverage_raw))
    strongest = [
        str(name)
        for name, declared in rows
        if EffectClass(str(declared)) == required
    ]
    operation = strongest[0] if strongest else "<dynamic-operation>"
    operations = ", ".join(strongest) if strongest else operation
    msg = (
        f"reified-world evaluation refuses operation {operations} at effect "
        f"rank {required} because world {origin} covers only {coverage}. "
        f"Declare the handler coverage with space.covers({str(required)!r}), "
        "or route this evaluation through the mutable space instead."
    )
    raise MettaError(
        msg,
        atom=target,
        space=str(origin),
        operation=operation,
        capability=str(required),
        ground=_EFFECT_SAFETY_GROUND,
    )

def _admit_world_effect(
    plan: _space_face.Space,
    origin: _space_face.Space,
    target: Any,
    image_rows: tuple[tuple[str, str], ...],
    image_effect: EffectClass,
) -> tuple[list[list[str]], EffectClass]:
    """Refuse the joined target-and-image plan or return its stable snapshot."""
    target_wire = target if isinstance(target, str) else _to_atom(target).to_wire()
    rows, required_raw, coverage_raw = plan._rt.apply_must(
        "metta_py_world_effect_plan",
        plan._space,
        origin._space,
        target_wire,
    )
    required = EffectClass(str(required_raw)).join(image_effect)
    coverage = EffectClass(str(coverage_raw))
    combined_rows = [
        *([name, declared] for name, declared in image_rows),
        *([str(name), str(declared)] for name, declared in rows),
    ]
    if required <= coverage:
        return combined_rows, required
    _raise_world_refusal(origin, target, combined_rows, required, coverage)

_WORLD_EFFECT_ADMISSION: Callable[..., tuple[list[list[str]], EffectClass]] = (
    _admit_world_effect
)

def _abandon_world_plan(plan: str) -> None:
    """The abandonment backstop: hand the drop over, never make it, never pool.

    Reached only when a ReifiedWorld is collected without close(). It enqueues,
    because a finaliser may only enqueue
    [docs/journal/2026-09-06-finalisers-must-not-call-prolog.md], and it drops
    without pooling, because the anonymous pool is served first-in-first-out and
    a collection landing between another caller's mint and its release would
    otherwise hand the next mint a name nobody released. Measured 2026-09-07:
    an abandoned world collected inside a `with m._new_space()` block made the
    next mint answer `&pyspace_1` for a released `&pyspace_2`, which is
    test_new_spaces_drop_and_names_recycle's failure. close() below is the
    scheduled path and still recycles, the way MeTTa.close() does beside
    _release_abandoned_world
    [tested: test_a_collected_world_does_not_take_the_name_a_live_mint_released,
    test_a_closed_world_releases_its_plan_image; commit=59c3cbf1bc269dfa7194f78da34497f1757a9604].
    """
    defer_engine_call("metta_py_drop_space", plan)

@dataclass(frozen=True, slots=True, weakref_slot=True)
class ReifiedWorld:
    """One immutable multiset state with an immutable reification base."""

    _origin: _space_face.Space = field(repr=False, compare=False)
    _base: tuple[Atom, ...] = field(repr=False)
    atoms: tuple[Atom, ...]
    _plan: _space_face.Space = field(repr=False, compare=False)
    _prepare_rows: tuple[tuple[str, str], ...] = field(repr=False, compare=False)
    _prepare_effect: EffectClass = field(repr=False, compare=False)
    _finalizer: weakref.finalize = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_finalizer",
            weakref.finalize(self, _abandon_world_plan, self._plan.name),
        )

    def close(self) -> None:
        """Release this world's retained native program image.

        The full drop, Python-side cleanup and the name back in the pool,
        because this is the caller's own scheduled release. Detaching first
        makes closing twice a no-op and leaves `_finalizer.alive` answering
        False exactly as calling it did.
        """
        if self._finalizer.detach() is not None:
            with suppress(BaseException):
                self._plan.drop()

    def _require_open(self) -> None:
        if not self._finalizer.alive:
            msg = "this ReifiedWorld is closed; reify the source space again"
            raise MettaError(msg, space=str(self._origin))

    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[Atom | Undefined], ReifiedWorld]:
        """Evaluate against this value and return ``(answers, successor)``."""
        self._require_open()
        operations, effect = _WORLD_EFFECT_ADMISSION(
            self._plan,
            self._origin,
            target,
            self._prepare_rows,
            self._prepare_effect,
        )
        scratch = self._origin._new_space()
        target_wire = target if isinstance(target, str) else _to_atom(target).to_wire()
        transferred = False
        try:
            atom_wires = [atom.to_wire() for atom in self.atoms]
            inputs = [
                scratch._space,
                self._origin._space,
                atom_wires,
                target_wire,
                operations,
                str(effect),
            ]
            limits = _limits(timeout, inferences)
            if limits is None:
                result = self._origin._rt.apply_must(
                    "metta_py_world_eval", *inputs
                )
            else:
                result = _apply_limited(
                    self._origin._rt,
                    limits,
                    "metta_py_world_eval",
                    inputs,
                )
            if str(result[0]) == "refused":
                _raise_world_refusal(
                    self._origin,
                    target,
                    result[1],
                    result[2],
                    result[3],
                )
            _, answer_wires, atom_wires, image_rows_raw, image_effect_raw = result
            answers = [_from_wire(wire) for wire in answer_wires]
            atoms = tuple(_atom_from_wire(wire) for wire in atom_wires)
            image_rows = tuple(
                (str(name), str(declared))
                for name, declared in image_rows_raw
            )
            successor = ReifiedWorld(
                self._origin,
                self._base,
                atoms,
                scratch,
                image_rows,
                EffectClass(str(image_effect_raw)),
            )
            transferred = True
            return answers, successor
        finally:
            if not transferred:
                scratch.drop()

    def __len__(self) -> int:
        """A world is a frozen space-state, so it counts like one."""
        return len(self.atoms)

    def __iter__(self):
        """Iterate the frozen multiset, assembly order, like a space."""
        return iter(self.atoms)

    def __contains__(self, atom: object) -> bool:
        """Multiset membership over the frozen state, like a space."""
        return atom in self.atoms

    def diff(self, other: ReifiedWorld) -> tuple[list[Atom], list[Atom]]:
        """Return this world's and the other world's ordered multiset extras."""
        if not isinstance(other, ReifiedWorld):
            msg = f"a world diff needs another ReifiedWorld, got {type(other).__name__}"
            raise TypeError(msg)
        return (
            _surplus(list(self.atoms), list(other.atoms)),
            _surplus(list(other.atoms), list(self.atoms)),
        )

def reify_space(space: _space_face.Space) -> ReifiedWorld:
    """Capture one space through its native or explicit provider snapshot."""
    captured = _Member(space).snapshot()
    image_rows_raw, image_effect_raw, coverage_raw = space._rt.apply_must(
        "metta_py_world_image_effect_plan",
        space._space,
        space._space,
        [atom.to_wire() for atom in captured],
    )
    image_rows = tuple(
        (str(name), str(declared)) for name, declared in image_rows_raw
    )
    image_effect = EffectClass(str(image_effect_raw))
    coverage = EffectClass(str(coverage_raw))
    if image_effect > coverage:
        _raise_world_refusal(
            space,
            "<frozen world image>",
            list(image_rows),
            image_effect,
            coverage,
        )
    plan = space._new_space()
    try:
        space._rt.must(
            "metta_py_world_prepare(Space, Origin, Atoms)",
            Space=plan._space,
            Origin=space._space,
            Atoms=[atom.to_wire() for atom in captured],
        )
        return ReifiedWorld(
            space,
            captured,
            captured,
            plan,
            image_rows,
            image_effect,
        )
    except BaseException:
        plan.drop()
        raise

def commit_world(space: _space_face.Space, world: ReifiedWorld) -> None:
    """Apply a world's base-relative multiset diff in one transaction."""
    if not isinstance(world, ReifiedWorld):
        msg = f"commit expects a ReifiedWorld, got {type(world).__name__}"
        raise TypeError(msg)
    if world._origin != space:
        msg = (
            f"world belongs to {world._origin}, not {space}; commit it through "
            "the space that produced it"
        )
        raise MettaError(msg)
    removed = _surplus(list(world._base), list(world.atoms))
    added = _surplus(list(world.atoms), list(world._base))
    backing = getattr(space, "_backing", None)
    if isinstance(backing, WorldCommitter):
        if space._rt.once("metta_in_user_transaction"):
            msg = (
                "a provider-owned world commit cannot nest inside an engine "
                "transaction; commit the world as the transaction boundary"
            )
            raise MettaError(msg)
        backing.commit_world(world._base, removed, added)
        # The provider has finished its durable delta. Feed exactly those
        # ordinary changes through the same observer path native writes use.
        space._rt.must(
            "metta_py_publish_world_diff(Space, Removed, Added)",
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
        raise MettaError(msg)

    def apply_diff() -> None:
        current = _Member(space).snapshot()
        if _surplus(list(current), list(world._base)) or _surplus(list(world._base), list(current)):
            msg = (
                f"{space} changed after this world was reified; refusing a "
                "stale diff that could erase or duplicate concurrent writes"
            )
            raise MettaError(msg)
        for atom in removed:
            if not space.remove(atom):
                msg = f"world commit could not remove its base atom {atom} from {space}"
                raise MettaError(msg)
        if added:
            space.add(*added)

    space.transaction(apply_diff)

__all__ = ["ReifiedWorld"]

@_doors.door(
    kind=_doors.Kind.lifecycle,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_reify_refuses_an_effectful_captured_compilation_before_replay', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_reify_refuses_and_names_a_live_composite_member', 'extensions/python/tests/ch11_python_as_a_notation/test_arrow_products.py::test_world_coverage_uses_the_annotated_effect'),
)
def reify(space: _space_face.Space):
    """Capture this space as an immutable, independently evaluable world."""
    from metta._history.world import reify_space  # noqa: PLC0415 -- avoids the Space type cycle

    return reify_space(space)

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_a_journaled_world_commit_replays_its_ordinary_diff', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_commit_applies_the_world_diff_as_post_commit_events', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_world_commit_preserves_multiplicity_and_refuses_stale_or_wrong_origins'),
)
def commit(space: _space_face.Space, world: Any) -> None:
    """Apply one reified world's diff through this originating space."""
    from metta._history.world import commit_world  # noqa: PLC0415 -- avoids the Space type cycle

    commit_world(space, world)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch19_spaces_backed_by_anything/test_occurrence_tokens.py::test_provider_tokens_keep_multiplicity_order_and_identity', 'extensions/python/tests/ch19_spaces_backed_by_anything/test_occurrence_tokens.py::test_tokenless_provider_refuses_blame_and_fast_save'),
)
def blame(space: _space_face.Space, atom: Any) -> list[Atom]:
    """Return each matching occurrence's ``(t actor generation)`` identity.

    Results are ordered by generation then actor. Equal atoms have separate
    tokens. A provider must implement the ``tokens`` capability.
    """
    rows = space._rt.apply_must("metta_py_blame", space._space, _to_atom(atom).to_wire())
    return [_atom_from_wire(row) for row in rows]
