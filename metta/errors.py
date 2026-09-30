"""Purpose: the error family's one public home.

Every class a refusal can be an instance of, the non-reduction signal an
operation raises to decline, the repair and the authority each refusal
carries, and the two doors code raises refusals through:

    from metta.errors import MettaOperationError

    try:
        m.run("!(+ $left $right)")
    except MettaOperationError as refused:
        refused.operation, refused.remedy.title

The classes are defined in `metta._errors.errors`, beside the generated
refusal table they are checked against, and this module is their public face,
as `metta.convert` is `CastError`'s. The root keeps `MettaError`,
`NotReducible`, `Timeout` and `is_transport_failure` as its headline names and
no other member of the family.

Guarantees:
  - every MettaError subclass the package defines without a leading
    underscore is named by some public module's `__all__`, and every one
    `metta._errors.errors` defines beyond the root's by this one
    [tested 2026-09-29T06:04:25+10:00: test_every_refusal_class_has_a_public_home]
  - the root names no member of the family beyond those four
    [tested 2026-09-29T02:40:49+10:00: test_m7_narrow_core_surface]
  - a refusal's class, its Remedy and its Ground import from here
    [tested 2026-09-29T02:40:49+10:00: test_the_error_family_imports_from_metta_errors]
"""

from metta._errors.errors import (
    AssertionFailure,
    CompileError,
    EngineError,
    Ground,
    InferenceLimitError,
    IntegrityError,
    Interrupted,
    LockDrift,
    MettaError,
    MettaOperationError,
    MettaResultError,
    MettaSyntaxError,
    NotReducible,
    PartialWriteError,
    PlatformCapabilityError,
    RegistrationError,
    Remedy,
    ResourceLimitError,
    RestraintError,
    SourceNotFound,
    SpaceCapabilityError,
    StackLimitError,
    SubscriberError,
    TimeLimitError,
    Timeout,
    TransportFailure,
    is_transport_failure,
    refuse,
    refusing,
)

__all__ = [
    "AssertionFailure",
    "CompileError",
    "EngineError",
    "Ground",
    "InferenceLimitError",
    "IntegrityError",
    "Interrupted",
    "LockDrift",
    "MettaError",
    "MettaOperationError",
    "MettaResultError",
    "MettaSyntaxError",
    "NotReducible",
    "PartialWriteError",
    "PlatformCapabilityError",
    "RegistrationError",
    "Remedy",
    "ResourceLimitError",
    "RestraintError",
    "SourceNotFound",
    "SpaceCapabilityError",
    "StackLimitError",
    "SubscriberError",
    "TimeLimitError",
    "Timeout",
    "TransportFailure",
    "is_transport_failure",
    "refuse",
    "refusing",
]
