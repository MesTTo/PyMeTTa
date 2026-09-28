"""Purpose: hold every refusal class the package defines to a public import path.

A caller that means "a builtin refused this value" writes
`except MettaOperationError`, and needs somewhere public to import it from.
0.9.0 moved the error family into the private `metta._errors.errors`, which
left nineteen of its classes, `EngineError` and `MettaOperationError` among
them, with no public path at all, and the private module is what a downstream
integration had to import.

Assumes: every module of the package imports without a network or an
  optional library, so walking all of them sees every class they define.
Guarantees:
  - no MettaError subclass the package defines is reachable only privately
    [tested 2026-09-30T08:15:12+10:00: test_every_refusal_class_has_a_public_home]
  - the walk reports a class a private module defines and nothing re-exports,
    and one a public module holds outside its __all__, and no other
    [tested 2026-09-30T08:15:12+10:00: test_a_class_without_a_public_home_is_reported,
    test_a_published_or_underscore_class_is_not_reported]
"""

from __future__ import annotations

import importlib
import pkgutil
import types

import pytest

import metta
from metta import MeTTa, MettaError


def _package_modules() -> list[types.ModuleType]:
    """Every module of the package, private ones included, imported."""
    names = ["metta", *(info.name for info in pkgutil.walk_packages(metta.__path__, "metta."))]
    return [importlib.import_module(name) for name in names]


def _public(name: str) -> bool:
    return not any(part.startswith("_") for part in name.split(".")[1:])


def _descendants(root: type) -> set[type]:
    found: set[type] = set()
    pending = [root]
    while pending:
        for child in pending.pop().__subclasses__():
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def _homeless(modules: list[types.ModuleType]) -> list[type]:
    """Each MettaError subclass one of `modules` defines and no public one publishes.

    Defined means the class names the module as its `__module__`. Published
    means a public module's `__all__` names that very class, so a class a
    private module defines and nothing re-exports is reported, and so is one a
    public module holds without declaring it.
    """
    defined = {module.__name__ for module in modules}
    published = {
        id(getattr(module, name))
        for module in modules if _public(module.__name__)
        for name in getattr(module, "__all__", ())
    }
    return sorted(
        (cls for cls in _descendants(MettaError)
         if cls.__module__ in defined
         and not cls.__name__.startswith("_")
         and id(cls) not in published),
        key=_dotted,
    )


def _dotted(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def _planted(name: str, source: str) -> types.ModuleType:
    module = types.ModuleType(name)
    exec(source, module.__dict__)
    return module


def test_every_refusal_class_has_a_public_home() -> None:
    """No MettaError subclass the package defines is reachable only privately."""
    assert [_dotted(cls) for cls in _homeless(_package_modules())] == []


def _reported(name: str, source: str) -> list[type]:
    """The classes of a module planted under `name` from `source` that the walk reports."""
    planted = _planted(name, source)
    return [cls for cls in _homeless([*_package_modules(), planted]) if vars(planted).get(cls.__name__) is cls]


@pytest.mark.parametrize(
    ("name", "source"),
    [
        # A private module defines it and nothing re-exports it.
        ("metta._planted", "from metta import MettaError\nclass PlantedError(MettaError): pass\n"),
        # A public module holds it without naming it in __all__.
        ("metta.planted", "from metta import MettaError\nclass PlantedError(MettaError): pass\n"),
    ],
)
def test_a_class_without_a_public_home_is_reported(name: str, source: str) -> None:
    """The walk reports a planted class no public __all__ holds."""
    assert _reported(name, source)


@pytest.mark.parametrize(
    ("name", "source"),
    [
        # A public module publishes it.
        ("metta.planted", "from metta import MettaError\n__all__ = ['PlantedError']\nclass PlantedError(MettaError): pass\n"),
        # An underscore class is private by its own name.
        ("metta._planted", "from metta import MettaError\nclass _PlantedError(MettaError): pass\n"),
    ],
)
def test_a_published_or_underscore_class_is_not_reported(name: str, source: str) -> None:
    """The walk leaves a planted class alone once a public __all__ holds it or its name marks it private."""
    assert not _reported(name, source)


def test_the_error_family_imports_from_metta_errors() -> None:
    """A refusal's class and the repair and authority it carries import publicly."""
    from metta.errors import EngineError, Ground, MettaOperationError, MettaSyntaxError, Remedy

    with MeTTa() as m:
        with pytest.raises(MettaOperationError) as refused:
            m.run("!(+ $left $right)")
        assert isinstance(refused.value, EngineError)
        assert isinstance(refused.value.remedy, Remedy)
        assert isinstance(refused.value.ground, Ground)
        with pytest.raises(MettaSyntaxError):
            m.run("(")
