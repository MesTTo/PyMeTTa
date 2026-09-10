"""Purpose: identify native spaces and manage each handle's lifetime.

Owns resources: SpaceHandle.drop releases owned backing state and subscriptions.
Failed cleanup retains its state for retry before an anonymous name is pooled
[source: extensions/python/metta/_spaces/handle.py:544; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import hashlib
import os
from collections import abc as _abc
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Self, cast

import metta._spaces.intents as _spaces_intents_module
import metta._spaces.lifetime as _spaces_lifetime_module
import metta._spaces.scope as _spaces_scope_module
import metta.doors as _doors
from metta._atoms.designation import _DEFAULT_SPACE, _SpaceId
from metta._atoms.factories import Atom, Expression, Grounded, Handle, Symbol, Variable, _to_atom
from metta._atoms.templates import HOLE_PREFIX as _HOLE_PREFIX
from metta._binding.runtime import Runtime, bridge, runtime, started
from metta._errors.errors import MettaError
from metta._lazy import lazy
from metta.vocabularies import SpaceCapability


def _creation_site() -> tuple[str, int]:
    """Return the first caller frame outside the metta package."""
    import inspect  # noqa: PLC0415  -- anonymous construction alone pays

    frame = inspect.currentframe()
    try:
        frame = None if frame is None else frame.f_back
        package_name = (__package__ or __name__).split('.', 1)[0]
        package_prefix = f"{package_name}."
        while frame is not None:
            module = str(frame.f_globals.get("__name__", ""))
            if module != package_name and not module.startswith(package_prefix):
                filename = frame.f_code.co_filename
                if not filename.startswith("<"):
                    filename = str(Path(filename).resolve())
                return filename, frame.f_lineno
            frame = frame.f_back
    finally:
        del frame
    return "<unknown>", 0

def current_space(default: str = _DEFAULT_SPACE) -> _SpaceId:
    """The space whose module the ENGINE is evaluating in right now.

    Callable from inside a registered operation, where it answers the space
    of the program that called it: janus re-enters the engine cleanly, so
    an operation can behave per-space without the space being an argument.
    Outside any evaluation it answers the default.
    """
    selected = _spaces_scope_module._ACTIVE_SPACE.get()
    if selected is not None:
        return selected
    if not started():
        return _SpaceId(default)
    row = bridge().query_once("current_metta_space(S)")
    return _SpaceId(str(row["S"])) if row else _SpaceId(default)

def _require_name(name: Any, called: str) -> None:
    """Refuse a non-string name here, where the caller can still be named.

    The engine reports one as `atom_string/2: Type error`, which names a
    Prolog builtin and the tagged null `@none` instead of the argument.
    """
    if not isinstance(name, str):
        msg = f"{called} takes a name as a string, got {name!r}"
        raise TypeError(msg)

def _substituted(target: Any, using: dict[str, Any]) -> Atom:
    """Apply a bindings mapping to a target in the host, as the engine does.

    ``metta_host_substitute/3`` replaces an ATOM whose name is a binding key,
    recursively [source: engine/filereader.pl:579-584]. Any caller that has to
    hold the substituted term rather than hand the pairs to the engine needs
    exactly that, so it is written once.
    """
    atom = _to_atom(target)
    return atom.map(
        lambda item: (
            _to_atom(using[item.name])
            if isinstance(item, Symbol) and item.name in using
            else item
        )
    )

class _SpaceModel(NamedTuple):
    """Which engine declaration a space request needs, and its one argument.

    The mint and the declaration used to be one predicate per model, which is
    why a NAME and a model were exclusive: there was nowhere to put the name.
    Splitting them leaves exactly this to decide, once, for both paths --
    anonymous space() mints a name and declares, named space() declares on the
    name it was given -- and the model crosses as the atom the engine
    already dispatches on rather than as part of a predicate name.
    """

    model: str
    argument: Any

def _space_model(
    inherits: _root.Space | None,
    *,
    restricted: bool,
    grants: tuple[str, ...],
    equation_home: _root.Space | None,
) -> _SpaceModel | None:
    """The declaration a request needs, or None for a plain space."""
    if restricted:
        return _SpaceModel("restricted", list(grants))
    if equation_home is not None:
        return _SpaceModel("scoped", equation_home._space)
    if inherits is not None:
        return _SpaceModel("inherits", inherits._space)
    return None

def _checked_new_space_request(
    inherits: _root.Space | None,
    *,
    restricted: bool,
    grants: _abc.Iterable[str],
) -> tuple[str, ...]:
    """Refuse a malformed anonymous ``space()`` request at one boundary.

    Validation lives at this public boundary so the engine-side declaration
    transaction only ever sees a live parent, a boolean restriction, and
    known string capability grants.
    """
    if inherits is not None and not isinstance(inherits, lazy('metta._faces.space').Space):
        msg = f"space(inherits=...) takes a live Space handle, got {inherits!r}"
        raise TypeError(msg)
    if inherits is not None and inherits._dropped:
        msg = "space(inherits=...) takes a live Space handle"
        raise MettaError(msg)
    if not isinstance(restricted, bool):
        msg = "space(restricted=...) takes a bool"
        raise TypeError(msg)
    if isinstance(grants, str):
        msg = "space(grants=...) takes an iterable of capability names"
        raise TypeError(msg)
    try:
        requested_grants = tuple(grants)
    except TypeError as exc:
        msg = "space(grants=...) takes an iterable of capability names"
        raise TypeError(msg) from exc
    if any(not isinstance(capability, str) for capability in requested_grants):
        msg = "every space grant must be a string"
        raise TypeError(msg)
    unknown = set(requested_grants) - set(SpaceCapability)
    if unknown:
        msg = f"unknown space capabilities: {sorted(unknown)!r}"
        raise ValueError(msg)
    if requested_grants and not restricted:
        msg = "space grants require restricted=True"
        raise ValueError(msg)
    if inherits is not None and restricted:
        msg = "a space cannot be both inherited and restricted"
        raise ValueError(msg)
    return requested_grants

def _source_identity(source: str | None, path: Any) -> str:
    """What the engine will record this registration's source as.

    The pre-load check needs it, because "a name another Prolog source owns"
    has to distinguish another source from THIS one re-registering. Both
    routes know it before the load: a file is its path, and inline source is
    the module name it loads under, which is what the engine reads back off
    the clauses afterwards.
    """
    if path is not None:
        return os.fspath(path)
    return _inline_module_name(str(source))

def _inline_module_name(source: str) -> str:
    """The name SWI loads inline Prolog source under.

    SWI removes every clause loaded under a name when that name is loaded
    again, so this name decides which library's clauses a later registration
    erases. It was `id(source)`, an address CPython hands to the next object
    of the same size the moment the string is freed, and a library generating
    Prolog therefore lost every predicate but the last: the reuse struck on
    the SECOND registration, not after four hundred, and the failure surfaced
    later as `findall_loop/4: Unknown procedure`.

    A content hash fixes every axis at once. It is deterministic, so two
    different sources cannot collide; it is idempotent, so registering the
    same source twice reloads it rather than accumulating clauses; and it
    means something in a stack trace.

    persistent.py hashes the journal PATH and appends a counter, because two
    providers on one journal need distinct modules. Here the requirement is
    the opposite, that the same source reuse one name, so the two do not
    share a helper.
    """
    digest = hashlib.blake2s(source.encode("utf-8"), digest_size=8).hexdigest()
    return f"metta_inline_{digest}"

class _HashableSpaceTerm(list[Any]):
    """A Janus list carrier that can also key Python's per-space registries."""

    def __hash__(self) -> int:  # type: ignore[override]  # Janus requires a list carrier while per-space registries require a stable hash
        def frozen(value: Any) -> Any:
            if isinstance(value, list):
                return tuple(frozen(item) for item in value)
            return value

        return hash(frozen(self))

class SpaceHandle(Handle):
    """A space bound to the engine: the way in from Python.

    MeTTa keeps one engine per process; every context shares it. The
    process-default home is &self, the space the CLI itself uses, so source
    pasted from a .metta file behaves identically through ``metta.engine()``.
    ``MeTTa()`` itself is a fresh context over its own anonymous home, so two
    contexts never share stored state; ``Space()`` is still the process
    home, and ``metta.engine()`` the context that borrows it.

    A named space isolates both its atoms and its EQUATIONS, and the rule for
    equations has a third part this docstring used to get wrong by calling
    them process-wide. They are per-space, with a dynamic fallback to &self
    and local shadowing [measured 2026-08-17]:

        equation defined in     &self       s1          s2
        ------------------      ---------   ---------   ---------
        s1                      unreduced   answers     unreduced
        &self                   answers     answers     answers
        both                    &self's     s1's        &self's

    So a helper put in &self is reachable from every space, one put in a named
    space is private to it, and a name defined in both resolves to the local
    one where it exists. Registrations are the thing that really is
    process-wide, which the anonymous ``space()`` factory says.

        from metta import MeTTa, S, V

        m = MeTTa().self
        m.run("(= (foo) boo) !(foo)")     # [[Symbol('boo')]]
        m.add(S.Parent(S.Tom, S.Bob))
        m.match(S.Parent(V.x, S.Bob))
    """
    __slots__ = ('__weakref__', '_autodrop', '_backing', '_context_tokens', '_created_at', '_drop_engine_done', '_dropped', '_ephemeral', '_name', '_name_atom', '_owns_backing', '_rt', '_scoped')
    _expression_listing_snapshot = True

    def __setattr__(self, name: str, value: Any, /) -> None:
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str, /) -> None:
        object.__delattr__(self, name)

    def __init__(
        self,
        name: str | Symbol | Expression | _root.Space = _DEFAULT_SPACE,
        *,
        verbose: bool | None = None,
        metta_path: str | None = None,
        _runtime: Runtime | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> None:
        super().__init__()
        self._rt = _runtime or runtime(metta_path=metta_path, verbose=verbose)
        self._name_atom: Symbol | Expression | None = None
        if isinstance(name, SpaceHandle):
            # Opening a space is idempotent, so this constructor accepts a handle
            # it previously returned. A dropped handle still refuses because
            # _space reads the name. It matters now that an engine answer
            # naming a space arrives AS a Space:
            # `metta.space(json_decode(...).one())`
            # used to hand a Symbol here and would otherwise have started
            # raising the moment the codec began classifying that atom
            # correctly.
            self._name_atom = name._name_atom
            engine_name: str | _HashableSpaceTerm = name._space
        elif isinstance(name, Symbol):
            self._name_atom = name
            engine_name = (
                name.name if name.name.startswith("&") else f"&{name.name}"
            )
        elif isinstance(name, Expression):
            if name.vars:
                msg = (
                    f"a parametric space name must be ground; {name!s} leaves "
                    f"free variable(s) {[str(v) for v in name.vars]} open"
                )
                raise ValueError(msg)
            if not name.children:
                msg = "a parametric space name is a nonempty ground expression"
                raise ValueError(msg)
            self._name_atom = name
            engine_name = _HashableSpaceTerm(
                self._rt.apply_must("metta_py_open_atom_space", name.to_wire())
            )
        else:
            engine_name = name
        if not isinstance(engine_name, (str, list)):
            msg = (
                f"a space name is a string, Symbol, or ground Expression; "
                f"got {engine_name!r}"
            )
            raise TypeError(
                msg
            )
        # A STRING names the space exactly, which is the bracket door's rule
        # everywhere else on this surface: `S["add"]` is the symbol `add` while
        # `S.add` is the operator word. The Symbol door above still supplies
        # the `&` for a name written as one, so `space(S.kb)` is `&kb`; a
        # string is what says "this exact name". It has to be, because the
        # engine registers a space under any symbol a program writes through
        # (`(= (space) my_space_name)`) and `space_names()` LISTS that name --
        # a listing door whose names the opening door refuses is one seat
        # disagreeing with the engine, and the Node seat opens them.
        #
        # Two spellings are still refused, and they are the two the old
        # message named as real. A `$` name reads back as a VARIABLE, so an
        # atom carrying it would stop being the same term it crossed as; and
        # the empty name is no name at all.
        if isinstance(engine_name, str) and engine_name.startswith("$"):
            msg = (
                f"a space name cannot start with $; got {engine_name!r}. A $ "
                f"name reads back as a variable, so a term mentioning this "
                f"space would not be the term it crossed as. Any other symbol "
                f"is a space name, prefixed or not: space('&kb') and "
                f"space('my_space_name') both name themselves."
            )
            raise ValueError(
                msg
            )
        if isinstance(engine_name, str) and not engine_name:
            msg = (
                "a space name is a nonempty symbol; got ''. Use space() with "
                "no argument for an anonymous space."
            )
            raise ValueError(
                msg
            )
        # The public parameter takes a plain str so a literal is writable;
        # the NewType is constructed once here and threads through inside.
        self._name = cast(_SpaceId, engine_name)
        self._dropped = False
        self._drop_engine_done = False
        self._ephemeral = False
        self._autodrop = False
        self._backing: Any = None
        self._owns_backing = False
        self._created_at = _created_at
        self._context_tokens: list[Any] = []
        self._scoped = _spaces_lifetime_module.attach(self)

    @property
    def _space(self) -> _SpaceId:
        """The space name, refused once this handle has been dropped.

        Every engine call reads the name through here, so a dropped handle
        cannot reach the engine at all. That matters because drop() returns
        an anonymous name to the pool: without this, a later ``space()``
        hands the same name to a new handle and writes through the dead one
        land in the new space, silently.
        """
        if self._dropped:
            msg = (
                f"{self._name} was dropped; this handle is dead. Its name may "
                f"already belong to another space, so writes through it would "
                f"land there. Take a new handle from space()."
            )
            raise MettaError(
                msg
            )
        if self._drop_engine_done:
            msg = f"{self._name} finished engine teardown; call drop() again to finish cleanup"
            raise MettaError(msg)
        scope_context = _spaces_lifetime_module
        if not self._scoped and scope_context.current() is not None:
            self._scoped = scope_context.attach(self)
        if self._scoped:
            with _spaces_lifetime_module.suspend():
                self._rt.must("lib_thread:scope_space_live(Name)", Name=self._name)
        return self._name

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.live,
        is_property=True,
    )
    def name(self) -> _SpaceId:
        """The live engine name represented by this handle."""
        return self._space

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.space,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.any,
        is_property=True,
        async_excluded="the space a receiver's doors work in, which for a space IS the receiver: mirroring it would give the async tier a property whose answer is the SYNCHRONOUS space, which is the one thing the async surface exists not to hand out. AsyncMeTTa answers its own home through the context tier, and an async space is already itself",
    )
    def self(self) -> Self:
        """The space this receiver's doors work in, which for a space is itself.

        MeTTa's own `&self` is the space a form is evaluated in, and a form
        stored in a space is evaluated in THAT space, so a space's `&self` is
        the space. `MeTTa.self` answers the same question for a context, whose
        answer is its home space, which is what makes `m.self` one attribute
        read at every door that takes either [source:
        extensions/python/metta/_atoms/designation.py:97, SpaceLike; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
        """
        return self

    def _at(self, name: str) -> _root.Space:
        """Return another handle in this runtime for internal composition."""
        return lazy('metta._faces.space').Space(name, _runtime=self._rt)

    def _open(
        self,
        name: Any,
        *,
        inherits: _root.Space | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
    ) -> _root.Space:
        """Open a NAMED space, declaring its model on the name given.

        A name and a model are independent: the engine's declarations validate
        with metta_require_space_name/2 and take any space name, while the
        anonymous path calls this method after minting a fresh name. Both the
        synchronous space() and the async one come through here, so the two
        cannot drift on which models a named space accepts.
        """
        model = _space_model(
            inherits,
            restricted=restricted,
            grants=_checked_new_space_request(
                inherits, restricted=restricted, grants=grants
            ),
            equation_home=None,
        )
        handle = lazy('metta._faces.space').Space(name, _runtime=self._rt)
        if model is not None:
            # On the handle's own normalized name, so space(S.locked) and
            # space("&locked") declare the same space the same way.
            self._rt.must(
                "metta_py_declare_space(Model, Space, Argument)",
                Model=model.model,
                Space=handle._space,
                Argument=model.argument,
            )
        return handle

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.readOnlyLookup,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync, _doors.Tier.async_),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_space_names_lists_the_registered_spaces',),
        binding=_doors.Binding('metta_py_space_names', _doors.Wire.goal),
    )
    def space_names(self) -> list[str]:
        """Every space name this engine registers, sorted: '&self' and
        '&metta' from boot, every native space something created or wrote to,
        and every foreign space currently bound. (new-space) and (spawn ...)
        create, so their answers are here at once; naming a space never
        registers it, so Space('&kb') is not here until a write, and a bind!
        token's target appears once something is stored under it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        row = self._rt.once("metta_py_space_names(Names)")
        return [str(name) for name in row["Names"]]

    def _new_space(
        self,
        *,
        inherits: _root.Space | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
        _equation_home: _root.Space | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> _root.Space:
        """An anonymous space with a name nothing else is using.

        Works as a context manager: leaving the block drops the space, so a
        churn of short-lived spaces reuses names instead of growing the
        engine's module table. A lifetime scope retains revoked names so an
        escaped alias cannot address a later allocation.

            with m._new_space() as scratch:
                scratch.add(...)

        What it isolates is STORED STATE: atoms and equations. Registrations
        are process-wide, so a register_prolog, an op, or a define made on an
        anonymous space is visible from every other one. Reach for this to
        isolate the data a test writes, not the names it registers; to isolate
        a name, unregister it.
        """
        requested_grants = _checked_new_space_request(
            inherits, restricted=restricted, grants=grants
        )
        model = _space_model(
            inherits, restricted=restricted, grants=requested_grants,
            equation_home=_equation_home,
        )
        if model is None:
            row = self._rt.must("metta_py_new_space(Name)")
        else:
            row = self._rt.must(
                "metta_py_new_modelled_space(Model, Argument, Name)",
                Model=model.model,
                Argument=model.argument,
            )
        fresh = lazy('metta._faces.space').Space(
            str(row["Name"]),
            _runtime=self._rt,
            _created_at=_creation_site() if _created_at is None else _created_at,
        )
        fresh._ephemeral = not fresh._scoped
        fresh._autodrop = True
        return fresh

    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync, _doors.Tier.async_),
        evidence=('extensions/python/ext/metta-arrays/tests/test_arrays.py::test_dropping_the_space_retires_its_installation_row', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_drop_retires_algebra_before_redeclaration', 'extensions/python/tests/ch04_spaces_and_matching/test_drop_recovery.py::test_backing_close_failure_keeps_the_name_and_cleanup_retryable'),
        state=_doors.State.any,
        binding=_doors.Binding('metta_py_drop_space', _doors.Wire.goal),
    )
    def drop(self) -> None:
        """Clear this space and release its owned resources.

        Dropping retires every space-owned catalog declaration, including
        algebra rows and their Python mirrors.
        Dropping unregisters a Python provider and closes only backing state
        owned by this handle. A foreign provider with a clear/drop lifecycle,
        such as MORK, releases its provider state.
        A named space's public name is not an anonymous allocation and never
        enters the anonymous pool. The engine-owned &self and &metta roots
        refuse before any Python-side state changes; drop the caller's own
        context or a named space instead.
        Anonymous names outside a lifetime scope return to the pool. Scoped
        names remain revoked, including after ownership transfers to a caller.
        Subscriptions on the space cancel with it: a pooled name reused later
        must not deliver to the old life's watchers. The handle itself dies
        here, and dropping twice is a no-op, as closing twice is.

        Engine teardown must succeed before Python cleanup is discarded.
        If later cleanup fails, call drop() again to finish it. The handle
        refuses other operations in that state and retains its anonymous name
        until cleanup succeeds; retrying does not repeat engine teardown.
        """
        if self._dropped:
            return
        self._scoped = _spaces_lifetime_module.attach(self)
        if self._scoped:
            with _spaces_lifetime_module.suspend():
                if not self._rt.once("lib_thread:scope_cleanup"):
                    self._rt.must("lib_thread:scope_drop_space(Name)", Name=self._name)
                    return
                if self._rt.once("lib_thread:scope_engine_released(Name)", Name=self._name):
                    self._drop_engine_done = True
        name = self._name
        subscriptions = lazy('metta.subscribe')
        foreign = lazy('metta.foreign')
        integrate = lazy('metta.integrate')
        if not self._drop_engine_done:
            self._rt.must("metta_py_space_releasable(Space)", Space=name)
            # Detach the engine's provider route while keeping Python ownership.
            # Drop must not clear an external journal or borrowed provider.
            provider = foreign._provider(name) if foreign.has_provider(name) else None
            try:
                if provider is not None:
                    self._rt.must("metta_py_unregister_foreign(Space)", Space=name)
                # Separate queries let SWI reclaim clauses erased by the clear.
                self._rt.must("metta_py_clear_for_release(Space)", Space=name)
                self._rt.must("metta_py_drop_space(Space)", Space=name)
            except BaseException as teardown_error:
                if provider is not None:
                    try:
                        foreign.register_provider(self._rt, name, provider)
                    except BaseException as restore_error:  # noqa: BLE001 -- preserve both teardown failures
                        msg = "space teardown and provider restoration failed"
                        raise BaseExceptionGroup(
                            msg,
                            [teardown_error, restore_error],
                        ) from None
                raise
            self._drop_engine_done = True

        # A failed cleanup is retryable, but may not release the name for reuse
        # or repeat engine teardown. The bookkeeping handle carries only the
        # name/runtime needed to retire satellites; it creates no engine state.
        cleanup = lazy('metta._faces.space').Space(name, _runtime=self._rt)
        cleanup._scoped = False
        for subscription in subscriptions._subscriptions_for(name):
            subscription.cancel()
        if foreign.has_provider(name):
            foreign.unregister_provider(self._rt, name)
        if self._owns_backing:
            close = getattr(self._backing, "close", None)
            if callable(close):
                close()
            self._owns_backing = False
        _spaces_intents_module.clear(cleanup)
        lazy('metta._declare.functions')._invalidate_builtins_cache(self._rt)
        lazy('metta._declare.definitions').release_definitions(cleanup)
        integrate._forget_space(name)
        lazy('metta._declare.operations')._forget_space(name)
        lazy('metta.algebra')._forget_space(cleanup)
        if self._ephemeral:
            self._rt.must(
                "atom_string(_Name, Space), metta_py_pool_space(_Name)", Space=name
            )
        self._dropped = True
        self._scoped = _spaces_lifetime_module.attach(self)
        if self._scoped:
            with _spaces_lifetime_module.suspend():
                self._rt.must("lib_thread:scope_forget_space(Name)", Name=name)

    @property
    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.boolean,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.any,
        is_property=True,
    )
    def dropped(self) -> bool:
        """Whether :meth:`drop` has released this handle's space."""
        if self._dropped:
            return True
        self._scoped = _spaces_lifetime_module.attach(self)
        if self._scoped:
            with _spaces_lifetime_module.suspend():
                return bool(self._rt.once("lib_thread:scope_space_dead(Name)", Name=self._name))
        return False

    def __enter__(self) -> Self:
        self._context_tokens.append(_spaces_scope_module._ACTIVE_SPACE.set(self._space))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _spaces_scope_module._ACTIVE_SPACE.reset(self._context_tokens.pop())
        # _autodrop, not _ephemeral: an anonymous name is always pooled at
        # drop (_ephemeral), but only a scratch space whose lifetime IS the
        # with-block dies on exit. A context home minted by MeTTa() is
        # ephemeral yet owned by its context, which drops it at close().
        if self._autodrop and not self._context_tokens:
            self.drop()

    def __repr__(self) -> str:
        state = ", dropped" if self._dropped else ""
        shown = self._name_atom if self._name_atom is not None else self._name
        created = (
            ""
            if self._created_at is None
            else f", created_at={f'{self._created_at[0]}:{self._created_at[1]}'!r}"
        )
        return f"Space({shown!r}{state}{created})"

    def __str__(self) -> str:
        return str(self._name_atom if self._name_atom is not None else self._name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Symbol):
            return self._name_atom == other or self._name == other.name
        if isinstance(other, Expression):
            return self._name_atom == other
        return (
            isinstance(other, lazy('metta._faces.space').Space)
            and self._rt is other._rt
            and self._name == other._name
        )

    def __hash__(self) -> int:
        # The engine has one atom for this reference and the legacy Symbol
        # spelling, so equal Python operands must share its symbol hash.
        if self._name_atom is not None:
            return hash(self._name_atom)
        return hash(("sym", self._name))

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.live,
        async_excluded="Space's Atom/Handle operand protocol, not an engine call",
    )
    def to_wire(self) -> list:
        """Encode the live engine reference as a portable space operand."""
        if isinstance(self._name_atom, Expression):
            return self._name_atom.to_wire()
        return ["p", str(self._space)]

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.text,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.any,
        is_property=True,
        async_excluded="Space's Atom/Handle operand protocol, not an engine call",
    )
    def metatype(self) -> str:
        """Read Space.metatype."""
        return "Grounded"

    def __reduce__(self):
        return lazy('metta._faces.space').Space, (
            self._name_atom if self._name_atom is not None else str(self._space),
        )

    def __deepcopy__(self, _memo: dict[int, Any]) -> _root.Space:
        msg = (
            "a space handle owns live engine state and cannot be deep-copied; "
            "use space.copy() to clone its stored atoms"
        )
        raise TypeError(msg)

    @_doors.door(
        kind=_doors.Kind.scope,
        answers=_doors.AnswersAs.context,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync, _doors.Tier.async_),
        evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_atoms.py::test_bind_reaches_a_variable_hole_through_an_atom_key', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_bind_carries_identity_into_a_term', 'extensions/python/tests/ch04_spaces_and_matching/test_variadic_doors.py::test_eval_batches_with_one_bind_scope'),
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:bind]'), _doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_bind_refuses_the_reserved_template_namespace')),
    )
    def bind(
        self,
        values: _abc.Mapping[str, Any] | None = None,
        /,
        **named: Any,
    ) -> _spaces_scope_module._BoundValues:
        """Scope named host values for :meth:`run` without a call flag."""
        bindings = {} if values is None else dict(values)
        if any(
            not isinstance(name, str | Atom) for name in bindings
        ):
            msg = (
                "a bound host value is named by a string, meaning the SYMBOL "
                "of that name, or by an atom, meaning that atom itself"
            )
            raise TypeError(msg)
        overlap = bindings.keys() & named.keys()
        if overlap:
            msg = f"host values were bound twice: {sorted(overlap)!r}"
            raise TypeError(msg)
        bindings.update(named)
        reserved = sorted(
            name
            for name in bindings
            if isinstance(name, str) and name.startswith(_HOLE_PREFIX)
        )
        if reserved:
            msg = (
                f"{_HOLE_PREFIX!r} names the symbols a template hole is spliced "
                f"as, so {reserved!r} cannot be bound: a hole and a binding "
                f"would be indistinguishable. Bind another name."
            )
            raise ValueError(msg)
        return _spaces_scope_module._BoundValues(bindings)

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.any,
        is_property=True,
    )
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface."""
        return self._rt

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
        state=_doors.State.any,
        is_property=True,
    )
    def metta(self) -> _root.MeTTa:
        """The owning evaluation context, so a handle can reach every
        context-level method: ``m.metta.space(S.kb)`` creates a sibling space
        in THIS handle's own context rather than the process default, which
        is the creation method the twins' known-issue asked for. The context
        BORROWS this handle's space as its home, so answering it mints
        nothing, and two answers compare equal because they share the
        runtime and the home.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return lazy('metta._faces.metta').MeTTa(self)

    if not TYPE_CHECKING:
        def __getattr__(self, name):
            """Resolve an installed package's namespace on first access."""
            if name.startswith("_"):
                raise AttributeError(name)
            from metta.doors import namespace  # noqa: PLC0415  -- the current registrant rows

            return namespace(self, name)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def alpha(self, other: Any) -> Expression:
        """The alpha-equality TERM, (=alpha self other); alpha_eq answers now.

        The nearest-relative spelling of the head whose `=` marker Python
        cannot carry, exactly as eq() spells ==; compiled bodies write the
        same test as a bare alpha(x, y) call, and fn["=alpha"] stays the
        exact form.
        """
        return super().alpha(other)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.boolean,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def alpha_eq(self, other: Atom) -> bool:
        """Whether two atoms differ only by consistent variable renaming."""
        return super().alpha_eq(other)

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
        is_property=True,
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:args]'),),
    )
    def args(self) -> tuple[Atom, ...]:
        """Read Space.args."""
        return super().args

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
        is_property=True,
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:children]'),),
    )
    def children(self) -> tuple[Atom, ...]:
        """Read Space.children."""
        return super().children

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def eq(self, other: Any) -> Expression:
        """The equality TERM, (== self other); == itself compares atoms."""
        return super().eq(other)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def ge(self, other: Any) -> Expression:
        """The greater-or-equal TERM, (>= self other)."""
        return super().ge(other)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def gt(self, other: Any) -> Expression:
        """The strictly-greater TERM, (> self other)."""
        return super().gt(other)

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
        is_property=True,
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:head]'),),
    )
    def head(self) -> Atom | None:
        """Read Space.head."""
        return super().head

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def le(self, other: Any) -> Expression:
        """The less-or-equal TERM, (<= self other)."""
        return super().le(other)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def lt(self, other: Any) -> Expression:
        """The strictly-less TERM, (< self other)."""
        return super().lt(other)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def map(self, transform: Callable[[Atom], Atom]) -> Atom:
        """Transform every node, children before parents, without recursion."""
        return super().map(transform)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def ne(self, other: Any) -> Expression:
        """Read Space.ne."""
        return super().ne(other)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.atom,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def subs(self, bindings: Mapping[Atom, Any] | Any) -> Atom:
        """Replace each atom the bindings name, everywhere it occurs.

            pattern = S.job(V.who, V.rank)
            pattern.subs(pattern.unify(S.job(S.ada, 9)))   # (job ada 9)
            S.hired(V.who).subs(space.match(pattern)[0])   # (hired ada)
            S.greet(S.name).subs({S.name: "ada"})          # (greet "ada")

        The KEY says what is being replaced, so a variable hole and a
        placeholder symbol are different substitutions rather than one
        ambiguous string. ``unify`` produces variable keys; a ``bind()`` scope
        at the evaluation methods accepts either.

        An answer ``Row`` is accepted directly, because its columns ARE the
        query's variable names. It is the library's other producer of
        bindings, and it could not be fed back either.

        Sugar over :meth:`map`, which stays available as the lower-level method:
        this is ``atom.map(lambda item: bindings.get(item, item))`` with the
        keys and values encoded. Nothing consumed a substitution before this,
        so both producers answered in a currency the library did not accept,
        and two tests had written the recursive walk by hand.
        """
        return super().subs(bindings)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
    )
    def unify(self, other: Atom, *more: Atom) -> Mapping[Atom, Atom] | None:
        """Unify with the others, returning bindings or ``None``.

        Variadic means SIMULTANEOUS: every operand must agree under ONE
        substitution, folded through one shared binding store, so several
        rule heads unify at once the way two always did. The keys are the
        VARIABLES themselves, which is the currency :meth:`subs` accepts,
        so ``template.subs(pattern.unify(fact))`` is the round trip. They
        were plain names once, and a name cannot say whether it means a
        variable or a symbol in a language that has both.
        """
        return super().unify(other, *more)

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
        is_property=True,
    )
    def vars(self) -> tuple[Variable, ...]:
        """The variables in first-appearance order; none means ground.

        The variables THEMSELVES, not their names, so what this answers is
        what :meth:`subs` and :meth:`unify` accept and a round trip composes:
        ``template.subs(dict(zip(pattern.vars, values)))``. Names were what it
        answered once, and a name cannot say whether it means a variable or a
        symbol on a surface that has both. ``not atom.vars`` still reads
        "ground", because an empty tuple is still empty.
        """
        return super().vars

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.pureStructural,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_inherited_atom_doors_remain_declared',),
        state=_doors.State.any,
        inherited=True,
        is_property=True,
    )
    def value(self) -> Any:
        """The inherited payload slot remains unset: a Space is a Handle, and reading value raises AttributeError."""
        return super().value

    @value.setter
    def value(self, value: Any) -> None:
        Grounded.__dict__['value'].__set__(self, value)  # pylint: disable=unnecessary-dunder-call # delegate to the base slot without re-entering this setter

    @value.deleter
    def value(self) -> None:
        Grounded.__dict__['value'].__delete__(self)  # pylint: disable=unnecessary-dunder-call # delegate to the base slot without re-entering this deleter

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
