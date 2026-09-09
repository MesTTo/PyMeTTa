"""Purpose: bind an evaluation context to its home space.

Owns resources: MeTTaBase.close releases the context's minted home and spaces.
Borrowed spaces survive. _release_abandoned_world defers an abandoned home's
drop to the engine [source: extensions/python/metta/_spaces/context.py:148,
_release_abandoned_world; commit=WORKTREE].
"""

from __future__ import annotations

import os
import sys
import weakref
from collections import abc as _abc
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self, overload

import metta._spaces.lifetime as _spaces_lifetime_module
import metta.doors as _doors
from metta._atoms.designation import _DEFAULT_SPACE, _R
from metta._atoms.factories import Atom, Expression, Symbol, Undefined
from metta._binding.runtime import Runtime, bridge, defer_engine_call, runtime
from metta._errors.errors import EngineError
from metta._lazy import lazy
from metta._lazy import package as _package
from metta._version import __version__
from metta.vocabularies import Atomicity, JournalSync

if TYPE_CHECKING:
    from metta._faces.space import Space


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import metta.library._lock

def _release_abandoned_world(home: str) -> None:
    """The finalize backstop: hand the drop over, never make it, never pool.

    Enqueued rather than called, because a finaliser may only enqueue: it runs
    at a point no caller chooses, on any thread, possibly inside a crossing
    already [docs/journal/2026-09-06-finalisers-must-not-call-prolog.md]. This
    one was the last `rt.must` left in a weakref callback, with its failure
    swallowed by `contextlib.suppress` rather than deferred.

    And it DROPS rather than releases, so an abandoned world's name is retired
    instead of returning to the anonymous pool. The pool is a queue served
    first-in-first-out (`retract(metta_py_free_space(C))` over clauses
    `assertz` appends), and a garbage collection landing between another
    caller's mint and its release inserts a name AHEAD of that caller's own,
    so the next mint answers a name nobody just released. Measured 2026-09-07:
    with an abandoned `MeTTa()` collected inside a `with m._new_space()` block,
    the next mint answered `&pyspace_1` for a released `&pyspace_2`, which is
    test_new_spaces_drop_and_names_recycle's failure exactly. Retiring the name
    costs one counter value per LEAKED context and makes the pool's order a
    function of program order alone, which is the property
    `Space.drop()`'s callers can actually reason about; the world itself is
    still released, which is all this backstop ever promised
    [tested: test_an_abandoned_context_releases_its_world,
    test_a_dropped_handle_cannot_write_into_the_name_it_released; commit=59c3cbf1bc269dfa7194f78da34497f1757a9604].
    """
    defer_engine_call("metta_py_drop_space", home)

class MeTTaBase:
    """One MeTTa evaluation context; context-relative operations use Space.

    ``MeTTa()`` is a fresh context, the way ``dict()`` is a fresh dict: it
    mints an anonymous space of its own as its home, so two contexts never
    see each other's atoms or equations, and it owns that space, releasing
    it on :meth:`close` or when a ``with`` block leaves. Passing a space
    (a ``Space``, an ``&name`` string, a ``Symbol``, or a parametric ground
    ``Expression``) makes the context a BORROWER of that space instead:
    ``MeTTa(Space())`` is the process-default context ``metta.engine()``
    answers, and closing a borrower never drops what the caller supplied,
    the way a file object built on someone else's descriptor leaves it open.
    ``&self`` is just the default home's name; within any context its own
    home plays that role.
    """

    __slots__ = ("__weakref__", "_finalizer", "_minted", "_owns_self", "_rt", "_self")

    def __init__(
        self,
        space: _root.Space | Symbol | Expression | str | None = None,
        *,
        verbose: bool | None = None,
        metta_path: str | None = None,
        _runtime: Runtime | None = None,
    ) -> None:
        self._minted: dict[str, _root.Space] = {}
        self._finalizer = None
        if isinstance(space, lazy('metta._faces.space').Space):
            # A borrowed home carries its runtime, and explicit options
            # still mean what they say: routing them through runtime()
            # applies verbose and raises on a conflicting metta_path,
            # exactly the one-engine contract that method documents. Silently
            # ignoring them was measured as accepting a conflicting engine
            # path and a dead verbose=True
            # [tested: test_a_borrowing_context_still_honors_its_options].
            if metta_path is not None or verbose is not None:
                runtime(metta_path=metta_path, verbose=verbose)
            self._rt = space.runtime
            self._self = space
            self._owns_self = False
            return
        self._rt = (
            runtime(metta_path=metta_path, verbose=verbose)
            if _runtime is None
            else _runtime
        )
        if space is None:
            home = lazy('metta._faces.space').Space(_DEFAULT_SPACE, _runtime=self._rt)
            # Minted as a WORLD: the home declares itself onto &self, so
            # spaces the program mints inside it (new-space included) read
            # its equations the way every default-world space reads &self's,
            # and close() can tear the whole world down as one unit.
            self._self = home._new_space(_equation_home=home)
            # Ownership transfer: the home's lifetime is this context's
            # close(), not any with-block entered on the space itself.
            self._self._autodrop = False
            self._owns_self = True
            # close() is the contract; the finalize backstop only covers an
            # ABANDONED context. It watches the HOME HANDLE, not this
            # context object, because the handle is what a caller keeps:
            # `MeTTa().self` leaves the context unreferenced while its home
            # is very much in use, and a backstop on the context released
            # that home into the free-name pool, where the next mint drew
            # the same name and tried to make it inherit from itself. A
            # resource may not die while a reference handed out of it lives
            # [tested: test_a_home_handle_outliving_its_context_keeps_the_world].
            self._finalizer = weakref.finalize(
                self._self, _release_abandoned_world, self._self._space
            )
        else:
            self._self = lazy('metta._faces.space').Space(space, _runtime=self._rt)
            self._owns_self = False

    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_drop_recovery.py::test_backing_close_failure_keeps_the_name_and_cleanup_retryable', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_borrowed_home_survives_close', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_context_close_leaves_a_named_space_it_only_opened'),
        state=_doors.State.any,
    )
    def close(self) -> None:
        """Release the context's own home space; closing twice is a no-op.

        A borrowed home, the process default included, is the caller's
        and survives; only a home this context minted is dropped, and the
        drop takes the whole world with it: every space minted inside the
        context, by this object or by the program's own new-space, is
        released first, since it read the home's equations and cannot
        outlive it. A space the program declared with (inherits ...) still
        refuses, naming the heir, because that relationship is the
        program's own.

        What a context OPENED by name it borrows and leaves alone, the way
        it leaves a borrowed home alone: ``m.space("&kb")`` may be a space
        that already existed, that another context is reading, or that the
        engine owns, and closing a reader is not how any of those end.
        """
        if self._owns_self:
            if self._finalizer is not None:
                self._finalizer.detach()
            # The spaces this context MINTED tear down python-side first, so
            # their subscriptions and provider state cannot follow a pooled
            # name into another life; the engine's own cascade then covers
            # the program's handle-less mints.
            for handle in list(self._minted.values()):
                if not handle.dropped:
                    handle.drop()
            self._minted.clear()
            self._self.drop()

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
    def closed(self) -> bool:
        """Whether :meth:`close` has released this context's own home."""
        return self._owns_self and self._self.dropped

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def __eq__(self, other: object) -> bool:
        """Two contexts are equal when they share a runtime and a home."""
        if not isinstance(other, lazy('metta._faces.metta').MeTTa):
            return NotImplemented
        return self._rt is other._rt and self._self == other._self

    def __hash__(self) -> int:
        return hash((id(self._rt), self._self))

    def __repr__(self) -> str:
        # The identity face beside __eq__: the home space names the context,
        # the way Space's own repr names the handle, and a closed context
        # says so instead of hiding behind the object default.
        state = ", closed" if self.closed else ""
        return f"MeTTa(self={str(self._self)!r}{state})"

    if not TYPE_CHECKING:
        # HIDDEN FROM TYPE CHECKERS ON PURPOSE. A visible __getattr__ makes
        # mypy type every unknown attribute as its return type rather than
        # reporting attr-defined, which trades a static error for a runtime
        # one, exactly backwards. Measured 2026-09-04: with it visible, both
        # `m.totally_made_up` and `x: int = m.atoms` type-checked clean.
        def __getattr__(self, name):
            """Refuse a Space door reached on the context, naming the spelling that works.

            The context forwards the evaluation doors and its home space owns
            storage and introspection. That split is real, but it is invisible
            at a call site: an installer written as `install(m)` reached for
            `m.is_function` and got Python's bare `'MeTTa' object has no
            attribute 'is_function'`, which says nothing about
            `m.self.is_function` sitting one attribute away. The roster is
            Space's own surface rather than a list kept here, so a door Space
            grows is covered the day it lands.

            This raises rather than forwards on purpose. `MeTTa` owns runtime
            context and `Space` owns storage, and silently answering for the
            home space would erase the distinction the two classes draw.
            """
            # A private or dunder name is machinery rather than a door: copy,
            # pickle and weakref all probe for names this answers about as
            # Python does, and a slot read during __init__ arrives here too.
            # Those probes also keep the two suggestion fields off, because
            # nobody reads a probe's traceback and carrying them costs the
            # round trip 296 ns against 462 ns [measured 2026-09-06: minimum
            # of nine timeit rounds of 200,000 on CPython 3.14.4 over
            # `try: o.__wrapped__` / `except AttributeError: pass`, against a
            # class whose __getattr__ raises AttributeError(name) and one
            # whose raises AttributeError(name, name=name, obj=self);
            # recorded in docs/journal/2026-09-06-a-head-knows-where-it-came-from.md].
            private = name.startswith("_")
            if not private:
                from metta.doors import (  # noqa: PLC0415 -- namespace discovery follows context initialization
                    Tier,
                    namespace,
                )

                try:
                    return namespace(self, name, Tier.context)
                except AttributeError:
                    pass
            if not private and hasattr(lazy('metta._faces.space').Space, name):
                msg = (
                    f"{type(self).__name__} has no {name!r}: it is a Space door, "
                    f"and a context is not its space. Write `m.self.{name}` to "
                    f"reach the home space, or `m.space(...)` for a named one."
                )
                raise AttributeError(msg, name=name, obj=self)
            msg = f"{type(self).__name__!r} object has no attribute {name!r}"
            if private:
                raise AttributeError(msg)
            raise AttributeError(msg, name=name, obj=self)

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
    )
    def self(self) -> _root.Space:
        """The context's home space handle, its own ``&self``."""
        return self._self

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

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.mapping,
        effect=_doors.EffectClass.readOnlyLookup,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch01_getting_started/test_backend_info.py::test_backend_info_reports_versions_and_consulted_tree',),
        refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_info_refuses_an_unreported_engine_version'),),
    )
    def info(self) -> dict[str, str | int | None]:
        """Return backend versions and the consulted MeTTa runtime tree."""
        janus_bridge = bridge()
        version_row = janus_bridge.query_once(
            "current_prolog_flag(version, SwiVersion)"
        )
        if version_row is None or not isinstance(version_row.get("SwiVersion"), int):
            msg = "janus did not report the running SWI-Prolog version"
            raise EngineError(msg)
        swi_version_num = version_row["SwiVersion"]
        identity = self._rt.must(
            "metta_actor(Actor), flag('$metta_generation', Next, Next)"
        )
        return {
            "metta": __version__,
            "janus": janus_bridge.version_str(),
            "swi_prolog": janus_bridge.version_str(swi_version_num),
            "python": (
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
            "metta_path": self._rt.metta_path,
            "actor": str(identity["Actor"]),
            "next_generation": int(identity["Next"]),
        }

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch01_getting_started/test_lock.py::test_a_drifted_engine_names_the_field_that_moved', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_drift_refusal_names_every_entry_and_its_repair', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_is_readable_toml_with_the_documented_tables'),
    )
    def lock(self) -> _root.Lock:
        """Pin the knowledge this context has loaded, as a `Lock`.

            m.load("kb/facts.metta")
            m.lock().write("metta.lock")
            python -m metta lock kb/facts.metta -o metta.lock

        One `[[library]]` row per shipped library imported, one `[[source]]`
        row per other file loaded with the space it landed in, one `[[pin]]`
        row per repository revision acquired, and an `[engine]` table naming
        this build and a digest over its own sources: what a second machine
        needs to load exactly this program. `metta.Lock.read` reads one back
        and :meth:`check` says what a tree no longer matches.

        The scope is the PROCESS, not this context. The engine's loads,
        registrations and git pins are process-wide, and a program that loads
        knowledge into `&kb` from one place and reads it from another is one
        program; a lock naming only one context's own loads would omit the
        rest of what has to be reproduced. Two contexts in one process
        therefore take the same lock.

        A lock taken while a source is still loading is refused, because it
        would record a program that is only half there.
        """
        return _root.library._lock.take(self._rt)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.sequence,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch01_getting_started/test_lock.py::test_a_drifted_engine_names_the_field_that_moved', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_round_trips_through_its_file', 'extensions/python/tests/ch01_getting_started/test_lock.py::test_a_removed_source_drifts_as_not_present'),
    )
    def check(self, lock: _root.Lock) -> list[_root.Drift]:
        """Every entry of a lock this tree no longer matches, as `Drift` rows.

            for drift in m.check(metta.Lock.read("metta.lock")):
                print(drift)

        An empty list is agreement. Nothing is loaded to answer it: each entry
        names something on disk, so the answer is what a fresh process would
        find rather than what this one happens to hold. `metta run --locked`
        is the same check with a refusal instead of a list.
        """
        return _root.library._lock.check(self._rt, lock)

    @_doors.door(
        kind=_doors.Kind.lifecycle,
        answers=_doors.AnswersAs.space,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_context_owns_and_releases_its_minted_home', 'extensions/python/tests/repository/test_door_rows.py::test_remote_storage_doors_use_the_declared_operation_protocol'),
        refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[context:space]'),),
    )
    def space(
        self,
        name: str | Symbol | Expression | _root.Space | None = None,
        backing: Any = None,
        *,
        inherits: _root.Space | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
        journal: str | os.PathLike[str] | None = None,
        schema: _abc.Mapping[str, Any] | None = None,
        sync: JournalSync = JournalSync.none,
        rename: _abc.Mapping[str, str] | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> _root.Space:
        """Create one native, provider-backed, remote, or journaled space.

        The BACKING value derives the implementation, so the common calls
        carry no options at all: with no name the engine mints an anonymous
        handle; a ``Space`` reopens that same space, which is what an engine
        answer naming one arrives as; a ``SpaceProvider`` backing is
        attached directly; an HTTP(S) URL becomes a remote provider (build
        the transport with ``metta.remote.connect`` when it needs a token,
        headers, or its own timeout, and hand THAT in as the backing); and
        ``journal=`` constructs ``PersistentFactSpace`` from ``schema=`` or
        a schema mapping supplied as the backing. ``sync`` paces the
        journal and ``rename`` performs its one-open schema migration; neither
        means anything without ``journal``, so either refuses alone.

        ``inherits``, ``restricted`` and ``grants`` choose the space MODEL and
        are independent of whether the space is named. MeTTa's own
        ``!(new-space &locked (restricted))`` names a restricted space, and
        ``metta.space(S.locked, restricted=True)`` is that call. Declaring a
        model on a name that already carries the same one is a no-op; a
        different one raises, because a space cannot have two models.

        The context OWNS what it mints and BORROWS what it opens by name:
        :meth:`close` releases the anonymous mints and leaves ``&kb``,
        ``&metta`` and every other named space exactly as it found them,
        whether or not the handle is still referenced. Inside a lifetime
        scope, that scope owns newly created spaces and their cleanup;
        ``scope.keep(value)`` transfers returned spaces on successful exit.
        """
        if sync != "none" and journal is None:
            msg = "space(sync=...) paces a journal; pass journal= as well"
            raise TypeError(msg)
        if rename is not None and journal is None:
            msg = "space(rename=...) migrates a journal; pass journal= as well"
            raise TypeError(msg)
        # VALIDATE first, so a refusal costs nothing: no space is minted
        # for a request that cannot be built
        # [tested: test_a_failed_space_construction_leaks_nothing].
        if journal is not None:
            if schema is None and isinstance(backing, _abc.Mapping):
                schema = backing
            if schema is None:
                msg = "space(journal=...) needs schema= or a schema mapping as backing"
                raise TypeError(msg)
            if backing is not None and not isinstance(backing, _abc.Mapping):
                msg = "journaled space backing is its schema mapping"
                raise TypeError(msg)
        elif isinstance(backing, str):
            #A bare URL takes the transport's own defaults; a transport that
            #needs a token, headers, an ssl context, a timeout, another
            #remote space, or batching is BUILT with metta.remote and handed
            #in as a RemoteSpace backing, so those knobs live where the
            #protocol does.
            lazy('metta.remote._transport')._refuse_this_process(
                backing, "&anonymous" if name is None else str(name)
            )
        elif callable(backing) and not isinstance(
            backing, lazy('metta.foreign').SpaceProvider
        ):
            #A bare transport callable is a PROTOCOL, not a space. Refusing
            #with the composition beats the provider checker's can_run
            #message, which would send its author down the wrong path.
            msg = (
                "a transport callable is not a space; wrap it as the space "
                "it serves: metta.remote.RemoteSpace(transport)"
            )
            raise TypeError(msg)
        if name is None:
            # The context's home plays the &self role for the context's own
            # spaces: an anonymous space minted here resolves EQUATIONS
            # through the home, by the narrow equation-home relation, so its
            # atoms stay its own and conjunctive matching keeps the direct
            # native path (a space_parent row would also union reads and
            # route joins per conjunct, both measured as defects). When the
            # home IS &self that resolution already holds, so the default
            # world needs no row at all.
            equation_home = (
                self._self
                if inherits is None
                and not restricted
                and self._self._space != _DEFAULT_SPACE
                else None
            )
            handle = self._self._new_space(
                inherits=inherits,
                restricted=restricted,
                grants=grants,
                _equation_home=equation_home,
                _created_at=_created_at,
            )
        else:
            handle = self._self._open(
                name, inherits=inherits, restricted=restricted, grants=grants
            )

        # Everything below can refuse, and a refusal must not leak what was
        # just acquired: the anonymous mint unwinds by dropping (it is
        # fresh by construction), while a NAMED open never drops on unwind,
        # because the name may be a pre-existing space whose destruction
        # would be data loss, and an auto-created empty name is the benign
        # residue. An owned provider constructed before the failure closes
        # first, so a journal cannot stay attached past its failed space
        # [tested: test_a_failed_space_construction_leaks_nothing].
        # ACQUIRE under one unwind. The anonymous mint unwinds by dropping
        # (fresh by construction); a NAMED open never drops on unwind,
        # because the name may be a pre-existing space whose destruction
        # would be data loss. An owned provider constructed before the
        # failure closes first, so a journal cannot stay attached past its
        # failed space [tested: test_a_failed_space_construction_leaks_nothing].
        minted_fresh = name is None
        owns_backing = False
        provider = backing
        try:
            if journal is not None:
                provider = lazy('metta.foreign._persistent').PersistentFactSpace(
                    journal,
                    schema,
                    sync=sync,
                    rename=rename,
                )
                owns_backing = True
            elif isinstance(backing, str):
                remote = lazy('metta.remote')
                provider = remote.RemoteSpace(remote.connect(backing))
                owns_backing = True
            if provider is not None:
                lazy('metta.foreign').register_provider(
                    self._rt, handle._space, provider
                )
                handle._backing = provider
                handle._owns_backing = owns_backing
                if journal is not None:
                    # An owned journal stages user-transaction writes and
                    # journals only the committed delta. The declaration is
                    # what makes the existing coordinator enlist that
                    # protocol; the enclosing unwind owns the failure path.
                    handle.atomicity(Atomicity.transactional)
        except BaseException:
            if owns_backing and provider is not backing:
                close = getattr(provider, "close", None)
                if callable(close):
                    close()
            if minted_fresh:
                handle.drop()
            raise
        handle._scoped = _spaces_lifetime_module.attach(handle)
        if minted_fresh and not handle._scoped:
            # ONLY the mints. A named open is a BORROW: the name may be a
            # space that already existed, one another context is reading, or
            # an engine-owned root, and close() releasing it destroyed the
            # first two and raised `No permission to release
            # metta_base_space` on the third. Recorded STRONGLY and keyed by
            # the engine name, so which spaces a close releases is decided
            # when they are minted rather than by when the collector runs,
            # and a pooled name a later mint draws replaces its own entry
            # instead of accumulating one per mint
            # [tested: test_a_context_closes_the_same_way_whether_a_base_space_handle_lives].
            self._minted[str(handle._name)] = handle
        return handle

    @property
    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.readOnlyLookup,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_fn_decodes_exactly_as_value', 'extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_fn_doors_split_the_same_way', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call'),
        is_property=True,
    )
    def fn(self) -> _declare.functions._FunctionNamespace:
        """The bound function namespace of this context's self space."""
        return self._self.fn

    @_doors.door(
        kind=_doors.Kind.provider,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_shared_class_declarations_survive_one_unregister', 'extensions/python/tests/ch11_python_as_a_notation/test_ops.py::test_unregistering_a_name_a_system_predicate_shares_does_not_throw', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_unregister_removes_the_effect_atom_with_the_op_facts'),
    )
    def unregister_op(self, name: str) -> None:
        """Release an operation installed through :meth:`op`."""
        self._self.unregister_op(name)

    @_doors.door(
        kind=_doors.Kind.scope,
        answers=_doors.AnswersAs.context,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_capture_composes_with_limits', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_eval_capture', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_capture_collects_held_engine_output'),
    )
    def capture(self) -> _spaces_execution.CapturedOutput:
        """Capture printed engine text across this context."""
        return self._self.capture()

    @_doors.door(
        kind=_doors.Kind.scope,
        answers=_doors.AnswersAs.context,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_an_atomic_scope_makes_one_python_write_one_transaction', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_atomic_run_commits_or_rolls_back_whole', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_lazy_atomic_rolls_back_after_a_late_cursor_failure'),
    )
    def atomic(self) -> _spaces_execution.ScopedExecution:
        """Scope source execution to committing transactions."""
        return self._self.atomic()

    @_doors.door(
        kind=_doors.Kind.scope,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch17_concurrency_and_the_loop/test_scopes.py::test_scope_owner_confines_keep_and_close',),
    )
    def scope(self) -> _root.parallel.Scope:
        """Own this block's children through the home space's library scope."""
        return self._self.scope()

    @overload
    def transaction(self, target: Callable[[], _R], /) -> _R: ...

    @overload
    def transaction(self, target: Atom | str, /) -> list[Atom | Undefined]: ...

    @_doors.door(
        kind=_doors.Kind.scope,
        answers=_doors.AnswersAs.value,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ladder.py::test_batch_composes_with_transaction', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_transaction_term_uses_empty_answer_rollback_law', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_saga_refuses_transaction_speculation_and_batch_boundaries'),
    )
    def transaction(self, target: Any, /) -> Any:
        """Run one callable or term in an engine transaction."""
        return self._self.transaction(target)

    @_doors.door(
        kind=_doors.Kind.provider,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_builtin_name_is_refused_and_the_builtin_still_works', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declaration_without_an_extension_still_reports_its_names', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declared_det_function_answers_normally'),
    )
    def register_prolog(self, *args: Any, **kwargs: Any) -> tuple[str, ...]:
        """Install a declared Prolog extension."""
        return self._self.register_prolog(*args, **kwargs)

    @_doors.door(
        kind=_doors.Kind.provider,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_compiled_library_registers_from_python', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_absent_compiled_library_is_refused_here', 'extensions/python/tests/ch14_seeing_your_program/test_trace.py::test_a_foreign_predicate_does_not_break_tracing'),
    )
    def register_foreign_library(self, *args: Any, **kwargs: Any) -> tuple[str, ...]:
        """Install a compiled SWI foreign library."""
        return self._self.register_foreign_library(*args, **kwargs)

    @_doors.door(
        kind=_doors.Kind.provider,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_an_explicitly_shared_library_alias_keeps_all_directories', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_unwinds_every_framework_registration'),
    )
    def register_library_path(self, directory: Any, name: str) -> None:
        """Register one named Prolog library directory."""
        self._self.register_library_path(directory, name)

    @_doors.door(
        kind=_doors.Kind.provider,
        answers=_doors.AnswersAs.tuple,
        effect=_doors.EffectClass.writesState,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_provider_only_file_registers_no_functions_and_is_accepted', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_extension_unloads_whole', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_unloaded_extension_does_not_leave_its_names_behind'),
    )
    def unregister_prolog(self, extension: str) -> tuple[str, ...]:
        """Release one declared Prolog extension."""
        return self._self.unregister_prolog(extension)

    @_doors.door(
        kind=_doors.Kind.introspection,
        answers=_doors.AnswersAs.none,
        effect=_doors.EffectClass.oracleIO,
        determinism=_doors.Determinism.det,
        tiers=(_doors.Tier.sync,),
        evidence=('extensions/python/tests/repository/test_door_rows.py::test_the_interactive_door_reaches_the_owned_runtime',),
    )
    def prolog(self) -> None:
        """Enter SWI-Prolog's interactive toplevel."""
        self._self.prolog()


if TYPE_CHECKING:
    catalog: Space
    reflection: Space


def _reflection_space() -> _root.Space:
    """Open the running context's queryable catalog on first attribute access."""
    return lazy("metta").engine().space("&metta")



__lazy_exports__ = {"catalog": _reflection_space, "reflection": _reflection_space}
__getattr__, __dir__ = _package(__name__)

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta._declare.functions
    import metta.parallel  # noqa: F401 -- child of the annotation namespace
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
if TYPE_CHECKING:
    from metta import _declare
else:
    _declare = lazy('metta._declare')
import metta._spaces.execution as _spaces_execution  # noqa: E402 -- deferred annotation bindings
