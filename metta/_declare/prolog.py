"""Purpose: register Prolog sources, shared libraries and library search paths.

Owns resources: registrations belong to their engine extension identity;
unregister_prolog releases that extension's registrations and clauses
[source: extensions/python/metta/_declare/prolog.py:377; commit=WORKTREE].
"""

from __future__ import annotations

import os
from collections import abc as _abc
from pathlib import Path
from typing import TYPE_CHECKING, Any

import metta._declare.functions as _declare_functions_module
import metta.doors as _doors
from metta._errors.errors import refuse
from metta._lazy import lazy
from metta._spaces.handle import _inline_module_name, _require_name, _source_identity
from metta.vocabularies import RefusalKind


@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.tuple,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_builtin_name_is_refused_and_the_builtin_still_works', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declaration_without_an_extension_still_reports_its_names', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_declared_det_function_answers_normally'),
    binding=_doors.Binding('import_prolog_functions', _doors.Wire.goal),
    refuses=(_doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:register-prolog]'),),
)
def register_prolog(
    space: _root.Space,
    source: str | None = None,
    *,
    path: str | os.PathLike[str] | None = None,
    names: _abc.Sequence[str] | _abc.Mapping[str, str] = (),
) -> tuple[str, ...]:
    """Register Prolog predicates as MeTTa functions, at native speed.

    This is the extension point for a library that wants to run fast.
    op() is the one most people find first, and every call it
    serves crosses the janus boundary: 25.16 inferences and 2.34us per
    call, against 7.16 inferences and 0.13us for the same operation
    written in Prolog [measured 2026-08-15, 3000 calls in one harness].

    Read the microseconds, not the inferences. The crossing counts as ONE
    inference and costs real time, so inferences say a Python operation is
    3.1x a Prolog one while wall clock says 18x. That is a fine price for
    reaching NumPy or an LLM and a bad one for arithmetic in a loop.

    A registered predicate keeps its nondeterminism: one that offers three
    solutions gives the MeTTa function three answers.

    A predicate follows the compiled calling convention, inputs first and
    one output last:

        m.register_prolog(
            "'vec-dot'(A, B, Out) :- ... .",
            names=["vec-dot"],
        )
        m.eval("(vec-dot (1 2) (3 4))")[0]

    or, for a library shipping a file beside its Python:

        m.register_prolog(path=Path(__file__).parent / "fast.pl",
                          names=["vec-dot", "vec-norm"])

    Every name is registered explicitly rather than discovered, because
    registering a name whose predicate is absent records no arity and then
    compiles every call to it into a partial application instead of
    failing, which is a silent wrong answer rather than an error. This
    raises instead: a name with no predicate behind it is refused before
    it can do that.

    The refusals are the engine's, through check_prolog_function_names/3
    and import_prolog_functions/2, so this and the MeTTa spelling enforce
    one rule rather than two copies of it. Three names are refused: one
    with no predicate behind it, a builtin, and a special form.

    Nothing is registered unless every name can be, so a typo in the list
    changes nothing. The consulted SOURCE does stay loaded on failure,
    which is deliberate rather than overlooked: loading it again is the
    retry, and it is idempotent, since the source is identified by a hash
    of its own content.

    **This is a method on a space and it registers PROCESS-WIDE.** So do
    op and define. Only equations are space-scoped, so an anonymous
    space() isolates one of the three things you can register and
    shares the other two. That is deliberate rather than overlooked: a
    Prolog predicate lives in `user`, every space has to be able to call
    it, and a library loaded inside a named space would define itself
    where the registration could not see it. The method sits on the space
    because that is where the rest of the surface is, not because the
    registration is scoped to it.

    The name is owned by one tier. A second registration of the same name
    from another tier is refused, in both directions, naming the owner, so
    two libraries cannot silently take the same name from each other.

    A parameter a MeTTa caller should reach unevaluated needs a type
    declaration, which this call does not take yet:

        m.register_prolog("'shape-of'(A, Out) :- Out = [shape, A].",
                          names=["shape-of"])
        m.run("(: shape-of (-> Atom Atom))")
        m.eval("(shape-of (+ 1 2))")[0] # (shape (+ 1 2)), not (shape 3)

    Declare it BEFORE anything calls the function. A call site compiled
    while the declaration is absent keeps evaluating the argument even
    after it lands.
    """
    if (source is None) == (path is None):
        msg = "register_prolog takes exactly one of source or path"
        raise ValueError(
            msg
        )
    if isinstance(names, _abc.Mapping):
        registered = _register_renamed(space, path, names)
        _declare_functions_module._invalidate_builtins_cache(space._rt)
        return registered
    for name in names:
        _require_name(name, "register_prolog")
    wanted = [str(name) for name in names]

    # Before the source loads, not after. Consulting a file that defines a
    # builtin's name has already replaced the engine's static predicate by
    # the time a per-name refusal could fire, so refusing afterwards left
    # (+ 1 2) answering the library's answer while this call reported the
    # registration as refused.
    if wanted:
        space._rt.must(
            "check_prolog_function_names(Names, Source, _)",
            Names=wanted,
            Source=_source_identity(source, path),
        )

    declares = "exports" if wanted else _require_a_declaration(space, source, path)

    origin = _load_prolog_source(space, source, path)

    # A source carrying its own :- metta_export/1 has already registered
    # by now, through the load, so a caller who declared in the file
    # passes no names at all.
    if not wanted:
        # An extension that exports nothing registers nothing, and that is
        # the shape of a provider: it contributes implementation clauses.
        if declares == "extension":
            _declare_functions_module._invalidate_builtins_cache(space._rt)
            return ()
        registered = _declared_exports(space, origin)
        _declare_functions_module._invalidate_builtins_cache(space._rt)
        return registered

    # One goal, so the engine validates every name before it registers any:
    # a typo in the third name used to leave the first two registered and
    # callable, with the list of what had taken dying inside the exception.
    # The rule lives there rather than here, so this and the MeTTa spelling
    # cannot drift apart.
    space._rt.must("import_prolog_functions(Names, _)", Names=wanted)
    _declare_functions_module._invalidate_builtins_cache(space._rt)
    return tuple(wanted)

def _require_a_declaration(space: _root.Space, source: str | None, path: Any) -> str:
    """What this source declares, read BEFORE it loads.

    It used to be consulted first and checked after, so a provider file
    with no declaration raised and installed the provider anyway: catching
    the error made everything work, which is the one outcome that teaches
    an author to ignore an error.

    All three routes are named, because pointing only at `metta_export` is
    a dead end for a provider author, who has no functions to export.
    """
    goal, inputs = (
        ("metta_py_source_declares(Source, Declares)", {"Source": os.fspath(path)})
        if path is not None
        else ("metta_py_string_declares(Text, Declares)", {"Text": str(source)})
    )
    declares = str(space._rt.must(goal, **inputs)["Declares"])
    if declares == "nothing":
        msg = (
            "register_prolog needs one of three things: the names to "
            'register, a :- metta_export("...") declaration for a '
            "source that defines functions, or a "
            ":- metta_extension(name, []) declaration for one that "
            "contributes clauses to an extension point and exports "
            "nothing, such as a space provider. Discovering the names would "
            "silently register whatever else the source defines"
        )
        raise ValueError(
            msg
        )
    return declares

def _register_renamed(
    space: _root.Space, path: Any, renames: _abc.Mapping[Any, Any]
) -> tuple[str, ...]:
    """Import a Prolog module's exports under names of your choosing.

    The one collision a name refusal cannot fix is two libraries that both
    export `norm/2`: neither is wrong and neither can be asked to change.
    SWI has resolved it for thirty years with a renaming import list, and
    this is that, so the second library arrives as `libb-norm` and neither
    is rebound. Without it SWI refuses the second import, prints "No
    permission to import ... (already imported from ...)" and continues,
    leaving the newcomer silently bound to the incumbent's code.

    The arity comes from the module's own export list, so a rename names
    only the two names, and a name the module does not export is refused
    with the list of what it does export.
    """
    if path is None:
        msg = (
            "renaming imports a Prolog MODULE, which SWI's import list "
            "names as a file, so it needs path= rather than source="
        )
        raise ValueError(
            msg
        )
    pairs = []
    for exported, metta_name in renames.items():
        _require_name(exported, "register_prolog")
        _require_name(metta_name, "register_prolog")
        pairs.append([str(exported), str(metta_name)])
    wanted = [pair[1] for pair in pairs]
    # Before the load, for the reason the unrenamed path documents.
    space._rt.must(
        "check_prolog_function_names(Names, Source, _)",
        Names=wanted,
        Source=os.fspath(path),
    )
    space._rt.must(
        "use_module_global(File, Renames)",
        File=os.fspath(path),
        Renames=pairs,
    )
    space._rt.must("import_prolog_functions(Names, _)", Names=wanted)
    return tuple(wanted)

def _load_prolog_source(space: _root.Space, source: str | None, path: Any) -> str:
    """Load the source and answer the name the engine knows it by."""
    if path is not None:
        source_path = os.fspath(path)
        if not Path(source_path).is_file():
            msg = f"no Prolog source at {source_path!r}"
            raise refuse(RefusalKind.source, msg, source=source_path)
        space._rt.consult(source_path)
        return source_path
    # The name the load runs under, not a constant. A declaration inside
    # the source records itself under prolog_load_context/2's answer, which
    # for a stream load is this module name, so asking under any other name
    # found nothing and a source declaring its own exports inline was told
    # it had declared none.
    module = _inline_module_name(str(source))
    space._rt.consult(module, data=str(source))
    return module

def _declared_exports(space: _root.Space, origin: str) -> tuple[str, ...]:
    row = space._rt.must("metta_py_declared_exports(Source, Names)", Source=origin)
    declared = tuple(str(name) for name in row.get("Names", []))
    if not declared:
        msg = (
            "register_prolog needs the names to register, or a "
            ':- metta_export("...") declaration in the source. '
            "Discovering them would silently register whatever else "
            "the source defines"
        )
        raise ValueError(
            msg
        )
    return declared

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.tuple,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_compiled_library_registers_from_python', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_absent_compiled_library_is_refused_here', 'extensions/python/tests/ch14_seeing_your_program/test_trace.py::test_a_foreign_predicate_does_not_break_tracing'),
    refuses=(_doors.Refusal(_doors.RefusalKind.source, 'extensions/python/tests/repository/test_door_refusals.py::test_foreign_library_refuses_a_missing_source'),),
)
def register_foreign_library(
    space: _root.Space,
    path: str | os.PathLike[str],
    *,
    entry: str | None = None,
    names: _abc.Sequence[str] = (),
) -> tuple[str, ...]:
    """Load a compiled `.so` and register its predicates as MeTTa functions.

    The C tier is the cheapest one on this page's cost table, one
    inference per call, and reaching it used to mean hand-writing two
    Prolog directives into `register_prolog`:

        m.register_foreign_library(Path(__file__).parent / "cbump.so",
                                   entry="install_cbump", names=["c-bump"])

    `entry` is the C initialiser, `install_cbump` in
    `install_t install_cbump(void)`; leave it out for a library whose
    entry is plain `install`.

    The path is resolved to an ABSOLUTE one here, which is the trap this
    exists to close: `use_foreign_library/2` accepts a path relative to
    the working directory, resolves it, and SWI deprecates that and warns
    on every load, so a library that shipped one worked from the repo root
    and warned or failed anywhere else. A file that is not there is
    refused here rather than inside the engine's loader.

    Everything after the load is `register_prolog`, so the same refusals
    apply: a name with no predicate behind it, a builtin, a special form,
    and a name another tier owns.
    """
    # resolve() rather than abspath(), which is the ruff-suggested spelling
    # and the better one here: the path is embedded in the use_foreign_library
    # goal below, so following a symlink to the real object is what the
    # loader wanted anyway.
    resolved = str(Path(os.fspath(path)).resolve())
    if not Path(resolved).is_file():
        msg = f"no compiled library at {resolved!r}"
        raise refuse(RefusalKind.source, msg, source=resolved)
    load = (
        f"use_foreign_library('{resolved}')"
        if entry is None
        else f"use_foreign_library('{resolved}', {entry})"
    )
    return space.register_prolog(
        f":- use_module(library(shlib)).\n:- {load}.\n", names=names
    )

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_an_explicitly_shared_library_alias_keeps_all_directories', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_unwinds_every_framework_registration'),
    binding=_doors.Binding('register_metta_library_path', _doors.Wire.goal),
)
def register_library_path(space: _root.Space, directory: Any, name: str) -> None:
    """Point MeTTa at a directory of files your package ships.

        # in your package's __init__
        m.register_library_path(Path(__file__).parent / "prolog", "example_package")

    Subject first, as every register_* call: the directory being
    registered, then the library name it serves.

    `(library example_package fast.pl)` then resolves, from MeTTa and from
    `register_prolog(path=...)`. Without it a pip-installed library is
    under neither `<engine>/../lib` nor a git checkout, so it has to pass
    absolute paths and compute them from `__file__` by hand.

    This is SWI's own `file_search_path/2`, so an alias registered here is
    one every SWI tool already understands, and aliases compose: the
    second argument of one may be another alias. Registering the same
    directory twice is a no-op; a directory that is not there is refused
    here rather than at the first import that needs it.
    """
    _require_name(name, "register_library_path")
    space._rt.must(
        "register_metta_library_path(Alias, Directory, _)",
        Alias=str(name),
        Directory=os.fspath(directory),
    )

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.tuple,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_a_provider_only_file_registers_no_functions_and_is_accepted', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_extension_unloads_whole', 'extensions/python/tests/ch20_extending_the_engine/test_register_prolog.py::test_an_unloaded_extension_does_not_leave_its_names_behind'),
    binding=_doors.Binding('metta_py_unregister_extension', _doors.Wire.goal),
)
def unregister_prolog(space: _root.Space, extension: str) -> tuple[str, ...]:
    """Release everything one extension registered, and its clauses.

    The unit is the extension, not the name. `register_prolog` used to
    load a bunch of loose predicates: the engine recorded that each name
    was a function and nothing at all about the library it came from, so
    there was no uninstall to write and a partly-failed registration left
    debris nobody could enumerate.

        :- metta_extension(pettorch, [version('0.3.1')]).
        :- metta_export("(: vec-dot (-> Number Number Number))").

        m.register_prolog(path="fast.pl")     # names come from the file
        m.unregister_prolog("pettorch")       # everything it installed

    PostgreSQL's rule, and its reason: an individual member cannot be
    dropped on its own, only the whole extension, which is what stops one
    registry keeping a claim on a name another route already replaced.
    The clauses go too, through SWI's own `unload_file/1`, so a name is
    not left callable through a predicate nothing records.

    Answers the names it released. Raises when no extension of that name
    is loaded, rather than reporting success for a no-op.
    """
    _require_name(extension, "unregister_prolog")
    released = space._rt.must(
        "metta_py_extension_members(Name, Names)", Name=str(extension)
    )
    names = tuple(str(name) for name in released.get("Names", []))
    space._rt.must("metta_py_unregister_extension(Name)", Name=str(extension))
    _declare_functions_module._invalidate_builtins_cache(space._rt)
    return names

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync,),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_the_interactive_door_reaches_the_owned_runtime',),
    binding=_doors.Binding('janus.prolog', _doors.Wire.goal),
    async_excluded='an interactive Prolog toplevel belongs to a terminal thread',
)
def prolog(space: _root.Space) -> None:
    """Drop into the engine's own interactive Prolog toplevel, the
    deepest debugging lever there is: listing/1 shows compiled
    equations, trace/0 steps through them, and quitting the toplevel
    returns here with the session intact. janus's own janus.prolog(),
    surfaced where the debugging happens.

    This is the only Prolog-facing surface here besides register_prolog,
    and that is a decision rather than a gap. There is no public
    "call any Prolog goal" method: the supported way to reach your own
    Prolog from Python is to register it and call it as a MeTTa function,
    which keeps one set of conversion rules, one error taxonomy and one
    lock. A raw goal is janus's job and janus is importable directly.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    space._rt._janus.prolog()

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
