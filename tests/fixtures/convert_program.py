"""Purpose: exercise Python-to-MeTTa CLI conversion with real declarations.

Guarantees:
  - importing this module declares one typed function, one rule, one typed
    record, and one fact through both the root and conventional bound-space
    surfaces [tested:
    test_convert_imports_a_python_program_and_round_trips_its_source;
    commit=42502e9d4a7fedd419856d5e6a1c291fc18ba644]
"""

from dataclasses import dataclass

import metta
from metta import MeTTa, S, equation

print("convert fixture imported")


@metta.define
def converted_double(value: int) -> int:
    """Double one integer."""
    return value * 2


m = MeTTa().space()


@m.rules
def converted_laws(value):
    """Keep one value unchanged."""
    yield equation(S.converted_identity(value)).to(value)


@m.define
@dataclass(frozen=True)
class ConvertedPair:
    """Two numeric fields whose accessors become equations."""

    left: int
    right: int


m += S.converted_fact(S.ready)
