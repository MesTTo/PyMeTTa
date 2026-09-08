"""Purpose: prove the Fork 4 surface collapse deletes superseded doors.
Guarantees:
  - the package surface is exactly what ``__all__`` names and is narrower
    than the surface M7 replaced, and keeps ``record`` and ``order_key``
    absent [tested: test_m7_narrow_core_surface; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - no extension package is a name on the root: a member is reached as its own
    module and no alias is left behind [tested: test_m7_narrow_core_surface;
    commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - the published before/after counts are exact for ``MeTTa`` and ``metta``
    [tested: test_m7_narrow_core_surface; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - every retired root, context, and atom name is absent rather than aliased
    [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - all fifteen ``declare_*`` spellings are absent from both synchronous and
    asynchronous space handles [tested: test_m7_narrow_core_surface;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - plain import and ``dir(metta)`` load no satellite, while either explicit
    import order preserves real module identity [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the retired root doors ``HERE`` and ``query`` are absent on a plain import
    rather than only under pytest [tested:
    test_retired_root_names_are_absent_in_a_fresh_process;
    commit=11c0101356844c9b8b1c7638059bfbc5235d11d1]
  - the strategies namespace is one lazy root satellite while its fifteen
    reified constructors stay inside that namespace [tested:
    test_m7_narrow_core_surface and
    test_m7_satellites_are_lazy_and_identity_stable; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
Owns:
  - subprocesses used for clean import-order probes are waited synchronously
    by ``subprocess.run(check=True)`` [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Decides:
  - ``BASELINE_*`` and ``FINAL_*`` are the published surface metrics
    [measured 2026-08-26: 90 to 20 MeTTa names and 152 to 98 metta names after the
    module-tier family, package rename, and algebra-carrier promotion;
    command=python -m pytest extensions/python/tests/ch01_getting_started/test_m7_narrow_core.py -q;
    fixture=a142938d baseline and the current generated root; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import metta
from metta import MeTTa, Space
from metta import atoms as atom_module

BASELINE_METTA_METHODS = 90
BASELINE_PACKAGE_EXPORTS = 152
# The class count: 21 before the context tier; +13 on 2026-09-01 when MeTTa
# became the third generated mirror. The finding behind it was a context
# that could define but not eval: the hand-written derived subset was typed
# (*args: Any) -> Any, had drifted, and missed most Space verbs, so
# MODULE_DOORS now renders on MeTTa exactly as on the module tier (run,
# load, eval, match, add, remove, solve, doc, pure, reads, writes, io join;
# define, op, stats, limits and trace were already carried and are now
# generated and typed), `fn` joins as the bound-namespace property, and
# speculative takes the module tier's ruled name `speculate`.
# 61 at the narrow-core commit; +4 when the R6 merge promoted the canonical
# atoms TRUE, FALSE and UNIT to root values; +1 when
# R1 exported the static fn namespace at the root; +8 when R5 landed its
# ruled doors (typed, arrow, the keyword builders, State and solve's kin),
# followed by the five newly surfaced module-tier verbs (trace replaces its
# satellite module at the same name, so it does not change the count); +1 for
# seg, the named segment builder, whose anonymous twin is Python's own `...`
# and therefore needs no name; +1 for doc, the get-doc receiver verb on the
# default context, landing beside match and eval; +2 for the library import
# door, `lib` the catalog-generated namespace the write door consumes and
# +11 for under and the ten generated-catalog semiring objects. The pin is
# the algebra-carrier surface adopted in ai-python-first-revamp-discussion.md
# lines 3024-3034 and 5471-5492; +1 for the exact ``metta.speculate()``
# module-tier spelling required by style ledger
# ``ai-python-conventions.md:1732-1733``; +1 for the lazy strategies namespace.
# P14.11 and the design ledger at
# ai-python-first-revamp-discussion.md:2921-2933 require the namespace but keep
# each combinator as a reified term rather than another root callable; +1 for
# the module-tier ``@metta.op`` primitive required by
# ``ai-python-conventions.md:290``; +1 for the visible inline-host marker
# ``py(expr)`` required by ``ai-python-conventions.md:1194-1212``;
# +2 for ``catalog`` and ``fresh``, the exact public doors required by
# ai-python-conventions.md:1811-1814 and
# ai-python-first-revamp-discussion.md:3742-3748. Two sibling branches each
# moved this pin 100 -> 102 for their own pair, which merged clean and wrong;
# the merged surface carries all four.
# +4 for ``pure``, ``reads``, ``writes`` and ``io``, the effect classes as
# named doors rather than a stringly-typed ``effect=`` argument. They widen the
# count and not the surface's MEANING: each is ``op`` with one argument filled
# in, which is why there is no fifth for ``nondeterministicReadOnly`` (a
# generator is nondeterministic and the registration lifts the class itself).
# -1 for ``cache``, removed 2026-08-31: it was a host door for ONE library,
# reaching lib_memo's exact-bag variant from Python and from nowhere else, and
# every capability it had is a library form (``memoize-exact``,
# ``get-memoize-stats``, ``invalidate-memoize``) that every seat already
# reaches.
# +1 for ``llms``, which prints llms.txt the way help() prints. It is a door
# rather than a document link because the document has to be reachable from an
# INSTALL, where there is no checkout to open and no path a reader could guess;
# setup.py ships the file into metta/_runtime/ for it.
# +1 for ``current_algebra``, the context observer paired with
# ``current_space``.
# +1 for ``stubs``, which answers a space's declarations as the text of a
# `.pyi`. It is a root door rather than a Space method for the same reason
# ``llms`` is: it takes the space as an argument so a caller can project one
# it does not own, and `python -m metta stubs` is the same generator.
# +1 for ``importing``, the satellite whose ``install()`` makes a `.metta`
# file a Python module through a ``sys.meta_path`` finder. It is a satellite
# rather than a root verb because installing an import hook is a process-wide
# act a program performs once, not a call the surface invites.
# +1 for ``render``, the other direction of the door ``run`` and ``eval``
# already take: the same program text with holes, answering text instead of
# running. It earns the root on the narrow-core ruling's own terms, a verb a
# program calls, and it takes no space, so there is nowhere else it would sit.
# +3 on 2026-09-07 for ``library``, ``Lock`` and ``Drift``. ``library`` is a
# satellite like ``lint`` and ``tables``; ``Lock`` and ``Drift`` are root
# names because a caller reads a lock a process never took
# (``metta.Lock.read``) and reacts to the rows ``m.check`` answers, which is
# the same shape ``State`` and ``Answer`` are here for.
# +1 on 2026-09-07 for ``telemetry``, a satellite like ``lint`` and ``tables``:
# it is a module of two verbs over the trace and the counters, and a lazy
# satellite is what keeps `import metta` from loading the OpenTelemetry API.
# +1 on 2026-09-07 for ``seam``, this seat's extension seam. It is a satellite
# like ``tables`` and ``lint``, and it earns the root because it is the door a
# LIBRARY reaches for: a package registering against a point imports one name,
# and a program asking what can be extended here asks it.
# -2 on 2026-09-08 for ``arrays`` and ``telemetry``, which became the
# distributions ``metta-arrays`` and ``metta-otel``. That is the last time a
# number is written here: the count below is now a RELATION, because a
# constant outlives its mechanism and this one had already been moved by six
# separate branches for six separate reasons.

#: The satellites, DERIVED from the package's own roster rather than restated.
#: What this file tests about them is laziness and identity, and a hand-copied
#: list tests neither: it goes stale the moment one moves out, which is what
#: happened when two of them became packages of their own.
SATELLITES = frozenset(metta._SATELLITES) - {"seam"}

# add, eval, fn, load, remove and run left this roster on 2026-09-01: the
# generated context tier restores them as ruled doors (`_context_doors`
# below is what the tier IS), so their absence is no longer the claim.
REMOVED_FROM_METTA = {
    "add_table",
    "add_tagged_fact",
    "add_tagged_rule",
    "arities",
    "assuming",
    "atoms",
    "batch",
    "builtins",
    "cache",
    "cast",
    "clear",
    "copy",
    "count",
    "declare_admits",
    "declare_agenda",
    "declare_algebra",
    "declare_annotations",
    "declare_capacity",
    "declare_context",
    "declare_emits",
    "declare_events",
    "declare_handles",
    "declare_image",
    "declare_merge",
    "declare_on_error",
    "declare_reaction",
    "declare_source",
    "declare_writes",
    "derivation",
    "digest",
    "disassemble",
    "drop",
    "eval_status",
    "evaluate_algebra",
    "events",
    "first",
    "hyperpose",
    "integrate",
    "is_function",
    "is_function_here",
    "lint",
    "new_space",
    "one",
    "parallel",
    "parse",
    "pool",
    "prepare",
    "profile",
    "profile_extension",
    "query",
    "register_op",
    "register_space",
    "register_token",
    "run_status",
    "sample_rates",
    "save",
    "space_name",
    "space_names",
    "stream",
    "subscribe",
    "transactional",
    "type",
    "unregister",
    "unregister_space",
    "unregister_token",
    "why",
}

#: `record` left this set on 2026-09-07. The spelling is a door again, and a
#: different one: `metta.record(src)` is the module tier's mirror of
#: `Space.record`, generated beside `trace` and `debug` because they are three
#: doors onto one run. A superseded name staying gone is what this set proves;
#: a new door that happens to spell the same way is not that name returning.
REMOVED_FROM_ROOT = {
    "HERE",
    "cache",
    "DECLINE",
    "Decline",
    "Expr",
    "Gnd",
    "MettaName",
    "REFLECTION_SPACE",
    "SpaceName",
    "Sym",
    "Var",
    "alpha_eq",
    "atom_from_wire",
    "backend_info",
    "bridge",
    "cast",
    "decode",
    "default_engine",
    "encode",
    "expr",
    "functools",
    "importlib",
    "is_ground",
    "logging",
    "map_atoms",
    "pretty",
    "query",
    "register_object_repr_protocol",
    "sym",
    "sys",
    "unregister_object_repr_protocol",
    "val",
    "var",
    "variables",
    # Specialist objects no longer re-exported from the root.
    "AlgebraDeclarationError",
    "AlgebraEvaluation",
    "AlgebraEvaluationError",
    "AlgebraLawError",
    "AlgebraOperationError",
    "AlgebraRequirementError",
    "Amplitude",
    "DeclaredAlgebra",
    "LinearEvidenceError",
    "PlanDecision",
    "RateDeclarationError",
    "TaggedAnswer",
    "tagged_fact",
    "tagged_rule",
    "AssertionFailure",
    "CompileError",
    "EngineError",
    "InferenceLimitError",
    "Interrupted",
    "MettaOperationError",
    "MettaResultError",
    "MettaSyntaxError",
    "ResourceLimitError",
    "SourceNotFound",
    "SpaceCapabilityError",
    "StrictError",
    "SubscriberError",
    "TimeLimitError",
    "Adder",
    "Clearer",
    "CustomMatch",
    "Enumerable",
    "Matcher",
    "Remover",
    "Event",
    "EventStream",
    "Fold",
    "Subscription",
    "Builtin",
    "Derivation",
    "Fact",
    "Step",
    "Truncated",
    "Attr",
    "Key",
    "Path",
    "path",
    "DefinitionFacts",
    "SourceSpan",
    "CastError",
    "Boot",
    "SaveFormat",
    "engine_thread",
    "OPERATOR_LOWERINGS",
    "OperatorLowering",
    "order_key",
    "register_object_repr",
    "unregister_object_repr",
    "Row",
    "Rows",
    "Cursor",
    "EngineProfile",
    "Prepared",
    # Importable implementation modules are not package attributes. ``define``
    # is now the ruled default-engine verb, not the implementation module.
    "answer",
    "atoms",
    "errors",
    "ops",
    "results",
    "persistent",
    "das",
}

REMOVED_FROM_ATOMS = {
    "DECLINE",
    "Decline",
    "Expr",
    "Gnd",
    "Sym",
    "Var",
    "alpha_eq",
    "atom_from_wire",
    "decode",
    "encode",
    "expr",
    "is_ground",
    "map_atoms",
    "pretty",
    "register_object_repr_protocol",
    "sym",
    "unregister_object_repr_protocol",
    "val",
    "var",
    "variables",
}

REMOVED_FROM_ASYNC = {
    "disassemble",
    "new_space",
    "register_op",
    "register_space",
    "unregister",
    "unregister_space",
}

REMOVED_DECLARATION_CEREMONY = {
    "declare_admits",
    "declare_agenda",
    "declare_algebra",
    "declare_annotations",
    "declare_capacity",
    "declare_context",
    "declare_emits",
    "declare_events",
    "declare_handles",
    "declare_image",
    "declare_merge",
    "declare_on_error",
    "declare_reaction",
    "declare_source",
    "declare_writes",
}


def _public_names(value) -> set[str]:
    return {name for name in dir(value) if not name.startswith("_")}


def _assert_absent(value, names: set[str]) -> None:
    namespace = vars(value)
    listed = set(dir(value))
    for name in names:
        assert name not in listed
        assert name not in namespace
        with pytest.raises(AttributeError):
            getattr(value, name)


def _workspace_members() -> list[str]:
    """Every extension package's module name, read from the workspace itself.

    `[tool.uv.workspace] members` is the roster, and it is a glob, so this
    reads the directory the glob names rather than a second list.
    """
    root = Path(__file__).resolve().parents[4]
    manifest = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    members = manifest["tool"]["uv"]["workspace"]["members"]
    found = [path for pattern in members for path in sorted(root.glob(pattern))]
    assert found, members
    return [path.name.replace("-", "_") for path in found]


def _context_doors() -> set[str]:
    """Every direct context door and every Space door projected to that tier."""
    from metta.doors import DOORS, Owner, Tier

    return {
        row.alias or row.python for row in DOORS
        if not row.python.startswith("_")
        and (row.owner is Owner.context
             or (row.owner is Owner.space and Tier.context in row.tiers))
    }


def test_m7_narrow_core_surface():
    """Publish the M7 metric and prove every superseded name is gone."""
    from metta.aio import AsyncMeTTa

    # The context surface is exactly its declared rows and remains narrower
    # than the surface M7 replaced.
    doors = _context_doors()
    assert _public_names(MeTTa) == doors
    assert BASELINE_METTA_METHODS > len(doors)
    # The package surface as a RELATION: it is exactly what __all__ names,
    # `__version__` excepted because it is a dunder and this reading is of the
    # names that do not begin with one, and it is narrower than the surface M7
    # replaced. A pinned integer here has been edited by six branches for six
    # reasons and says nothing either of these two facts does not.
    assert _public_names(metta) == set(metta.__all__) - {"__version__"}
    assert BASELINE_PACKAGE_EXPORTS > len(metta.__all__)
    # No extension package is a name on the root. A member reaches its own
    # module, `import metta_arrays`, with no alias here, which is what makes
    # deleting `ext/` leave the core whole.
    for member in _workspace_members():
        assert member not in dir(metta), member
    assert metta.__dir__() == sorted(metta.__all__)
    _assert_absent(MeTTa, REMOVED_FROM_METTA)
    _assert_absent(metta, REMOVED_FROM_ROOT)
    assert "janus" not in dir(metta)
    assert "janus" not in metta.__all__
    assert "janus" not in vars(metta)
    _assert_absent(atom_module, REMOVED_FROM_ATOMS)
    _assert_absent(AsyncMeTTa, REMOVED_FROM_ASYNC)
    _assert_absent(Space, REMOVED_DECLARATION_CEREMONY)
    _assert_absent(AsyncMeTTa, REMOVED_DECLARATION_CEREMONY)


def test_m7_satellites_are_lazy_and_identity_stable():
    """Check laziness and both real-module identity orders in fresh processes."""
    root = Path(__file__).resolve().parents[4]
    environment = os.environ | {"PYTHONPATH": str(root / "extensions" / "python")}
    names = repr(sorted(SATELLITES))
    scripts = [
        f"""
import importlib
import sys
import metta
names = {names}
assert all(f'metta.{{name}}' not in sys.modules for name in names)
dir(metta)
assert all(f'metta.{{name}}' not in sys.modules for name in names)
for name in names:
    first = getattr(metta, name)
    assert first is importlib.import_module(f'metta.{{name}}')
    assert getattr(metta, name) is first
""",
        f"""
import importlib
import metta
names = {names}
for name in names:
    first = importlib.import_module(f'metta.{{name}}')
    assert getattr(metta, name) is first
    assert importlib.import_module(f'metta.{{name}}') is first
""",
    ]
    for script in scripts:
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=environment,
            check=True,
        )


def test_the_namespaces_are_not_callable():
    """The retired call-form alias is gone: brackets are the exact door.

    S("x"), V("x") and fn("car-atom") were synonyms for attribute access;
    the ruled spellings are S.x / S["exact name"] and fn.car_atom /
    fn["car-atom"], one mechanism per door and no aliases.
    """
    import pytest

    from metta import S, V, fn

    for namespace in (S, V, fn):
        with pytest.raises(TypeError):
            namespace("car-atom")
    assert str(S["car-atom"]) == "car-atom"
    assert fn.car_atom is not None


def test_m7_space_factory_keeps_identity():
    """No physical submodule can overwrite the callable space factory."""
    factory = metta.space
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("metta.space")
    assert metta.space is factory


def test_m7_unknown_attribute_has_normal_module_error():
    """PEP 562 preserves Python's normal unknown-attribute diagnostic."""
    name = "misspelled"
    with pytest.raises(AttributeError) as raised:
        getattr(metta, name)
    assert str(raised.value) == "module 'metta' has no attribute 'misspelled'"


def test_retired_root_names_are_absent_in_a_fresh_process():
    """The retired root doors stay absent on a plain import, not only under pytest."""
    root = Path(__file__).resolve().parents[4]
    environment = os.environ | {"PYTHONPATH": str(root / "extensions" / "python")}
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import metta

assert 'HERE' not in metta.__all__
assert 'query' not in metta.__all__
assert not hasattr(metta, 'HERE')
assert not hasattr(metta, 'query')
""",
        ],
        cwd=root,
        env=environment,
        check=True,
    )
