"""Purpose: keep FutureSpace waiting linear in waits plus answer count.

Guarantees:
  - quiet waits do not trigger whole-space reads, and every answer occurrence
    still arrives in order [tested:
    test_future_iteration_does_not_resnapshot_per_quiet_wait;
    commit=1877bec75a9a22265c9222f0c0c538c8f65a983f]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from benchmarks.future_iteration_snapshots import rows


def test_future_iteration_does_not_resnapshot_per_quiet_wait():
    """Increasing quiet waits leaves full-read work bounded by answer count."""
    short, long = rows((4, 16), atoms=128)

    assert short.atoms == long.atoms == 129
    assert long.snapshots <= short.snapshots + 1
    assert long.transported <= short.transported + long.atoms
