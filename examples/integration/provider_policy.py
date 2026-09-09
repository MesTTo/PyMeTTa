"""Purpose: enforce request-specific policy at a foreign space boundary.

``can_run`` describes which operations a provider implements. ``should_run``
then decides whether one concrete request is allowed, and ``refusal`` gives the
caller the provider's reason when it is not.
"""

from _common import check, done

from metta import MeTTa, S
from metta._errors.errors import MettaError
from metta.foreign import SpaceProvider


class CuratedFacts(SpaceProvider):
    """A writable provider that reserves the ``system`` namespace."""

    def __init__(self) -> None:
        """Start with an empty store."""
        self.stored = []

    def atoms(self):
        """Enumerate the admitted facts."""
        return iter(self.stored)

    def add(self, atom) -> None:
        """Store one fact after policy has admitted it."""
        self.stored.append(atom)

    def should_run(self, capability, /, **request) -> bool:
        """Reserve system-headed additions for the catalog loader."""
        return capability != "add" or request["atom"].head != S.system

    def refusal(self, capability, /, **request):
        """Explain the one request this provider declines."""
        if capability == "add" and request["atom"].head == S.system:
            return "system facts are written by the catalog loader"
        return None


with MeTTa() as context:
    provider = CuratedFacts()
    space = context.space("&curated-example", backing=provider)
    space.add(S.user(S.Ada))
    check("an admitted request reaches the provider", provider.stored, [S.user(S.Ada)])

    try:
        space.add(S.system(S.secret))
    except MettaError as refusal:
        check(
            "a declined request reports the provider's reason",
            "system facts are written by the catalog loader" in str(refusal),
        )
    else:
        msg = "the provider admitted a reserved system fact"
        raise AssertionError(msg)

    check("a declined request has no side effect", provider.stored, [S.user(S.Ada)])

done("provider_policy")
