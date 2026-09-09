# Purpose: declare named exports and the static root surface.
# The named imports and __all__ are authoritative. tools/rootgen.py derives
# the runtime exports; door declarations and catalog carriers own the marked
# regions. The init-stub lane rejects projection drift.

import builtins as _builtins
from collections.abc import Callable as _Callable
from collections.abc import Iterable as _Iterable
from typing import Any as _Any
from typing import Protocol as _Protocol
from typing import overload as _overload

from metta._atoms.answer import Answer as Answer
from metta._atoms.answer import Bindings as Bindings
from metta._atoms.designation import SpaceLike as SpaceLike
from metta._atoms.factories import FALSE as FALSE
from metta._atoms.factories import TRUE as TRUE
from metta._atoms.factories import UNIT as UNIT
from metta._atoms.factories import Atom as Atom
from metta._atoms.factories import Expression as Expression
from metta._atoms.factories import G as G
from metta._atoms.factories import Grounded as Grounded
from metta._atoms.factories import Handle as Handle
from metta._atoms.factories import S as S
from metta._atoms.factories import Symbol as Symbol
from metta._atoms.factories import Undefined as Undefined
from metta._atoms.factories import V as V
from metta._atoms.factories import Variable as Variable
from metta._atoms.factories import and_ as and_
from metta._atoms.factories import arrow as arrow
from metta._atoms.factories import fresh as fresh
from metta._atoms.factories import ground as ground
from metta._atoms.factories import if_ as if_
from metta._atoms.factories import in_ as in_
from metta._atoms.factories import not_ as not_
from metta._atoms.factories import or_ as or_
from metta._atoms.factories import parse as parse
from metta._atoms.factories import seg as seg
from metta._atoms.factories import typed as typed
from metta._atoms.library import Library as Library
from metta._atoms.library import lib as lib
from metta._atoms.state import State as State
from metta._atoms.templates import render as render
from metta._catalog.bounds import Config as Config
from metta._catalog.bounds import config as config
from metta._catalog.fn import fn as fn
from metta._compile.islands import py as py
from metta._declare.define import Defined as Defined
from metta._declare.operations import registered as registered
from metta._declare.operations import withdraw as withdraw
from metta._declare.rules import equation as equation
from metta._declare.rules import rules as rules
from metta._errors.errors import MettaError as MettaError
from metta._errors.errors import NotReducible as NotReducible
from metta._errors.errors import Timeout as Timeout
from metta._errors.errors import is_transport_failure as is_transport_failure
from metta._faces.metta import MeTTa as MeTTa
from metta._faces.space import Space as Space
from metta._spaces.ambient import accept as accept
from metta._spaces.ambient import attach as attach
from metta._spaces.ambient import current_algebra as current_algebra
from metta._spaces.ambient import current_space as current_space
from metta._spaces.ambient import drop as drop
from metta._spaces.ambient import engine as engine
from metta._spaces.ambient import forms as forms
from metta._spaces.ambient import llms as llms
from metta._spaces.ambient import refuse as refuse
from metta._spaces.ambient import space as space
from metta._spaces.ambient import stubs as stubs
from metta._spaces.ambient import superpose as superpose
from metta._spaces.ambient import under as under
from metta._spaces.ambient import unify as unify
from metta._spaces.context import catalog as catalog
from metta._spaces.context import reflection as reflection
from metta._spaces.results import Answers as Answers
from metta._spaces.results import Rows as Rows
from metta._version import __version__ as __version__
from metta.algebra import DeclaredAlgebra as _DeclaredAlgebra
from metta.algebra import amplitude as amplitude
from metta.algebra import bag as bag
from metta.algebra import bool as bool  # noqa: A004 -- the public carrier names
from metta.algebra import budget as budget
from metta.algebra import counting as counting
from metta.algebra import prob as prob
from metta.algebra import prov as prov
from metta.algebra import ranked as ranked
from metta.algebra import set as set  # noqa: A004 -- public algebra carrier
from metta.algebra import tropical as tropical
from metta.foreign import SpaceProvider as SpaceProvider
from metta.library._lock import Drift as Drift
from metta.library._lock import Lock as Lock
from metta.manifest import boot as boot
from metta.parallel import channel as channel
from metta.parallel import every as every
from metta.parallel import move_on_after as move_on_after
from metta.parallel import par_map as par_map
from metta.parallel import race as race
from metta.parallel import scope as scope
from metta.parallel import spawn as spawn
from metta.spaces import view as view
from metta.vocabularies import SemiringOrder as _SemiringOrder

# isort: split
# begin generated root imports
import builtins as _body_builtins
import collections.abc as _body_collections_abc
import os as _body_os
import typing as _body_typing

import metta._atoms.designation as _body_metta__atoms_designation
import metta._atoms.factories as _body_metta__atoms_factories
import metta._declare.define as _body_metta__declare_define
import metta._declare.operations as _body_metta__declare_operations
import metta._observe.debug as _body_metta__observe_debug
import metta._observe.recording as _body_metta__observe_recording
import metta._observe.trace as _body_metta__observe_trace
import metta._spaces.execution as _body_metta__spaces_execution
import metta._spaces.profile as _body_metta__spaces_profile
import metta._spaces.scope as _body_metta__spaces_scope
import metta.doors as _body_metta_doors
import metta.vocabularies as _body_metta_vocabularies

# end generated root imports
# isort: split


# begin generated algebra declaration
class _AlgebraModule(_Protocol):
    bool: _DeclaredAlgebra
    bag: _DeclaredAlgebra
    counting: _DeclaredAlgebra
    set: _DeclaredAlgebra
    ranked: _DeclaredAlgebra
    tropical: _DeclaredAlgebra
    prob: _DeclaredAlgebra
    prov: _DeclaredAlgebra
    budget: _DeclaredAlgebra
    amplitude: _DeclaredAlgebra

    @_overload
    def __call__(
        self,
        *,
        plus: _Any = ...,
        times: _Any = ...,
        combine: _Any = ...,
        extend: _Any = ...,
        zero: _Any = ...,
        one: _Any = ...,
        laws: _Iterable[str] = ...,
        carrier: _Iterable[_Any] = ...,
        type: _Any = ...,
        requires: _Iterable[str] = ...,
        order: _SemiringOrder | None = ...,
    ) -> _Callable[[type], _DeclaredAlgebra]: ...

    @_overload
    def __call__(
        self,
        subject: _Any,
        *,
        plus: _Any = ...,
        times: _Any = ...,
        combine: _Any = ...,
        extend: _Any = ...,
        zero: _Any = ...,
        one: _Any = ...,
        laws: _Iterable[str] = ...,
        carrier: _Iterable[_Any] = ...,
        type: _Any = ...,
        requires: _Iterable[str] = ...,
        order: _SemiringOrder | None = ...,
    ) -> _DeclaredAlgebra: ...


algebra: _AlgebraModule
# end generated algebra declaration

__all__ = ['FALSE', 'TRUE', 'UNIT', 'Answer', 'Answers', 'Atom', 'Bindings', 'Config', 'Defined', 'Drift', 'Expression', 'G', 'Grounded', 'Handle', 'Library', 'Lock', 'MeTTa', 'MettaError', 'NotReducible', 'Rows', 'S', 'Space', 'SpaceLike', 'SpaceProvider', 'State', 'Symbol', 'Timeout', 'Undefined', 'V', 'Variable', '__version__', 'accept', 'add', 'amplitude', 'and_', 'arrow', 'attach', 'bag', 'bool', 'boot', 'budget', 'catalog', 'channel', 'config', 'counting', 'current_algebra', 'current_space', 'define', 'doc', 'drop', 'engine', 'equation', 'eval', 'every', 'fn', 'forms', 'fresh', 'ground', 'if_', 'in_', 'io', 'is_transport_failure', 'lib', 'limits', 'llms', 'match', 'move_on_after', 'not_', 'op', 'or_', 'par_map', 'parse', 'prob', 'prov', 'pure', 'py', 'race', 'ranked', 'reads', 'reflection', 'refuse', 'registered', 'remove', 'render', 'rules', 'run', 'scope', 'seg', 'set', 'solve', 'space', 'spawn', 'speculate', 'stats', 'stubs', 'superpose', 'trace', 'tropical', 'typed', 'under', 'unify', 'view', 'withdraw', 'writes']


def __getattr__(name: str) -> _Any: ...


def __dir__() -> list[str]: ...


# begin generated root declarations


@_overload
def eval(  # noqa: A001 -- the declared public spelling
    target: _body_typing.Any,
    /,
    *more: _body_typing.Any,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    under: _body_typing.Any=...,
    theory: _body_typing.Any | None=...,
    interpreter: _body_typing.Any | None=...,
    answer: _body_metta_doors.EvaluationAnswer | _builtins.str=...,
    delivery: _body_metta_vocabularies.ArgumentDelivery | _builtins.str,
    limit: _builtins.int | None=...,
    image: _body_metta_vocabularies.ImageMode | _builtins.str | None=...,
    on_error: _body_metta_vocabularies.OnError | _builtins.str=...,
    determinism: _body_metta_vocabularies.Determinism | _builtins.str=...,
    **values: _body_typing.Any,
) -> _body_typing.Any:
    ...
@_overload
def eval(  # noqa: A001 -- the declared public spelling
    target: _body_typing.Any,
    /,
    *more: _body_typing.Any,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    under: _body_typing.Any=...,
    theory: _body_typing.Any | None=...,
    interpreter: _body_typing.Any | None=...,
    answer: _body_metta_doors.EvaluationAnswer | _builtins.str,
    delivery: _body_metta_vocabularies.ArgumentDelivery | _builtins.str=...,
    limit: _builtins.int | None=...,
    image: _body_metta_vocabularies.ImageMode | _builtins.str | None=...,
    on_error: _body_metta_vocabularies.OnError | _builtins.str=...,
    determinism: _body_metta_vocabularies.Determinism | _builtins.str=...,
    **values: _body_typing.Any,
) -> _body_typing.Any:
    ...
@_overload
def eval(  # noqa: A001 -- the declared public spelling
    target: _body_typing.Any,
    /,
    *,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    under: _body_typing.Any=...,
    theory: _body_typing.Any | None=...,
    interpreter: _body_typing.Any | None=...,
    **values: _body_typing.Any,
) -> _builtins.list[_body_metta__atoms_factories.Atom | _body_metta__atoms_factories.Undefined]:
    ...
@_overload
def eval(  # noqa: A001 -- the declared public spelling
    target: _body_typing.Any,
    _second: _body_typing.Any,
    /,
    *more: _body_typing.Any,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    under: _body_typing.Any=...,
    theory: _body_typing.Any | None=...,
    interpreter: _body_typing.Any | None=...,
    **values: _body_typing.Any,
) -> _builtins.list[_builtins.list[_body_metta__atoms_factories.Atom | _body_metta__atoms_factories.Undefined]]:
    ...
def stats() -> _body_metta__spaces_profile._StatsBlock:
    ...
def match(
    *patterns: _body_typing.Any,
    where: _body_typing.Any | None=...,
    limit: _builtins.int | None=...,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    under: _body_typing.Any=...,
    into: _body_builtins.type | None=...,
    **values: _body_typing.Any,
) -> _body_typing.Any:
    ...
def solve(pattern: _body_typing.Any, subject: _body_typing.Any) -> _body_typing.Any:
    ...
def limits(
    *,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    stack: _builtins.int | None=...,
) -> _body_metta__spaces_scope.ScopedLimits:
    ...
def speculate() -> _body_metta__spaces_execution.ScopedExecution:
    ...
def run(
    source: _builtins.str | _body_metta__atoms_designation.TemplateLike,
    /,
    *,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
    **values: _body_typing.Any,
) -> _builtins.list[_builtins.list[_body_metta__atoms_factories.Atom]]:
    ...
def load(
    path: _builtins.str | _body_os.PathLike[_builtins.str],
    *,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
) -> _builtins.list[_builtins.list[_body_metta__atoms_factories.Atom]]:
    ...
def add(*atoms: _body_typing.Any) -> None:
    ...
def remove(atom: _body_typing.Any, *more: _body_typing.Any) -> _builtins.bool | _builtins.int:
    ...
@_overload
@_body_typing.dataclass_transform(eq_default=False)
def define(  # type: ignore[overload-overlap]
    fn: _body_builtins.type[_body_metta__atoms_designation._T],
    /,
    *,
    accessors: _builtins.bool=...,
    methods: _builtins.bool=...,
) -> _body_builtins.type[_body_metta__atoms_designation._T]:
    ...
@_overload
def define(
    fn: _body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R],
    /,
    *,
    name: _builtins.str | None=...,
    accessors: _builtins.bool=...,
    methods: _builtins.bool=...,
) -> Defined[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]:
    ...
@_overload
def define(
    *,
    name: _builtins.str,
) -> _body_collections_abc.Callable[[_body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]], Defined[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]]:
    ...
@_overload
def define(
    *,
    prolog: _builtins.str | _body_os.PathLike[_builtins.str],
    name: _builtins.str | None=...,
) -> _body_collections_abc.Callable[[_body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]], _body_metta__declare_define.PrologBacked[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]]:
    ...
def doc(atom: _body_typing.Any) -> _body_metta__atoms_factories.Atom:
    ...
@_overload
def op(
    fn: _body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R],
    /,
    *,
    name: _builtins.str | None=...,
    transport: _body_metta__declare_operations.Transport=...,
    effect: _body_metta_vocabularies.EffectClass | _builtins.str,
    declarations: _body_collections_abc.Iterable[_body_metta__atoms_factories.Atom]=...,
    arities: _builtins.list[_builtins.int] | None=...,
    inverse: _body_collections_abc.Callable | None=...,
) -> _body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]:
    ...
@_overload
def op(
    *,
    name: _builtins.str | None=...,
    transport: _body_metta__declare_operations.Transport=...,
    effect: _body_metta_vocabularies.EffectClass | _builtins.str,
    declarations: _body_collections_abc.Iterable[_body_metta__atoms_factories.Atom]=...,
    arities: _builtins.list[_builtins.int] | None=...,
    inverse: _body_collections_abc.Callable | None=...,
) -> _body_collections_abc.Callable[[_body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]], _body_collections_abc.Callable[_body_metta__atoms_designation._P, _body_metta__atoms_designation._R]]:
    ...
def pure(
    fn: _body_collections_abc.Callable | None=...,
    /,
    **options: _body_typing.Any,
) -> _body_typing.Any:
    ...
def reads(
    fn: _body_collections_abc.Callable | None=...,
    /,
    **options: _body_typing.Any,
) -> _body_typing.Any:
    ...
def writes(
    fn: _body_collections_abc.Callable | None=...,
    /,
    **options: _body_typing.Any,
) -> _body_typing.Any:
    ...
def io(
    fn: _body_collections_abc.Callable | None=...,
    /,
    **options: _body_typing.Any,
) -> _body_typing.Any:
    ...
def debug(
    source: _body_metta__atoms_factories.Atom | _builtins.str,
    *,
    on: _body_typing.Any=...,
    inferences: _builtins.int | None=...,
    at: _builtins.int | None=...,
) -> _body_metta__observe_debug.Debugger:
    ...
def record(
    source: _body_metta__atoms_factories.Atom | _builtins.str,
    *,
    seed: _builtins.int | None=...,
    max_events: _builtins.int | None=...,
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
) -> _body_metta__observe_recording.Recording:
    ...
def trace(
    source: _body_metta__atoms_factories.Atom | _builtins.str,
    max_events: _builtins.int | None=...,
    *,
    filter: _body_metta__atoms_factories.Symbol | _builtins.str | _body_collections_abc.Iterable[_body_metta__atoms_factories.Symbol | _builtins.str] | None=...,  # noqa: A002 -- the declared public parameter spelling
    timeout: _builtins.float | None=...,
    inferences: _builtins.int | None=...,
) -> _body_metta__observe_trace.Trace:
    ...
# end generated root declarations
