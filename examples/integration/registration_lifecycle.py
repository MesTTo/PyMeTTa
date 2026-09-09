"""Purpose: discover integrations without loading them and undo global hooks.

Entry-point discovery is read-only. Protocol type, representation, and
reflection hooks are process-wide, so an integration that installs them also
owns their exact unregister calls.
Owns resources: the three registrations are removed in ``finally`` and the
MeTTa context closes its engine.
"""

from _common import check, done

from metta import MeTTa, S, V, ground, integrate
from metta._errors.errors import MettaError


class ExtensionTarget:
    """One object claimed by each integration hook in this example."""


target = ExtensionTarget()


def claims_target(value) -> bool:
    """Claim only this example's host type."""
    return isinstance(value, ExtensionTarget)


def format_target(_value) -> str:
    """Give the claimed object a stable MeTTa representation."""
    return "<extension target>"


def reflect_target(space, name, _value) -> int:
    """Lower one claimed object to one ordinary fact."""
    return integrate.facts(space, [S.reflected(S[name])])


with MeTTa() as context:
    space = context.self
    check("entry-point discovery is an unloaded mapping", isinstance(integrate.entry_points(), dict))

    integrate.register_object_type(claims_target, "ExtensionTargetProtocol")
    integrate.register_repr(claims_target, format_target)
    integrate.register_reflector(claims_target, reflect_target)
    try:
        check("the protocol type is active", space.cast(target, "ExtensionTargetProtocol") is target)
        check("the protocol representation is active", str(ground(target)), "<extension target>")
        check("the reflector writes its facts", integrate.reflect(space, "registered", target), 1)
        check("the reflected fact is queryable", space.match(S.reflected(V.name))[0].name, S.registered)
    finally:
        integrate.unregister_reflector(claims_target, reflect_target)
        integrate.unregister_repr(claims_target, format_target)
        integrate.unregister_object_type(claims_target, "ExtensionTargetProtocol")

    try:
        integrate.reflect(space, "removed", target)
    except MettaError as refusal:
        check("unregister_reflector removes the global hook", "no reflector claims" in str(refusal))
    else:
        msg = "the removed reflector still claimed its object"
        raise AssertionError(msg)

done("registration_lifecycle")
