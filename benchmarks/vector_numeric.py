"""Purpose: measure public Vector traversal after checking numerical goldens.

Guarantees: every timed dot result equals the full expected scalar; finite
cancellation and intermediate overflow/underflow controls retain their values
[tested: PYTHONPATH=extensions/python python -m benchmarks.vector_numeric;
commit=615e8a68dce996a0c05b3ddddc71b80bc598442d].
Owns resources: the benchmark context releases its engine on every outcome.
Decides: report minimum-of-three inferences and process CPU seconds, not a gate
allowance; dimension traversal is linear and arithmetic also depends on bit size
[source: lib/lib_vector/lib_vector.pl:dot_value/3; commit=615e8a68dce996a0c05b3ddddc71b80bc598442d].
"""

import time

from metta import MeTTa, lib


def main():
    """Check exact goldens, then print costs at geometrically growing dimensions."""
    with MeTTa() as engine:
        engine += lib.vector  # noqa: PLW2901 -- the import returns the same context owner
        goldens = [
            ((2.0**54, 1.0, -(2.0**54)), (1, 1, 1), 1.0),
            ((1 + 2.0**-27, 1.0), (1 - 2.0**-27, -1.0), -(2.0**-54)),
            ((2.0**1000, 2.0**1000), (2.0**1000, -(2.0**1000)), 0.0),
            ((2.0**-1074, 2.0**-1074), (0.5, 0.5), 2.0**-1074),
        ]
        for left, right, expected in goldens:
            actual = engine.fn.dot(left, right).one()
            assert actual == expected, (left, right, actual, expected)
        print(f"accuracy_controls={len(goldens)}")
        print("dimension,inferences,cpu_seconds")
        for size in (32, 128, 512, 2048, 8192, 32768):
            vector = (1.0,) * size
            costs = []
            for _ in range(3):
                with engine.stats() as measured:
                    start = time.process_time()
                    answer = engine.fn.dot(vector, vector).one()
                    cpu = time.process_time() - start
                assert answer == float(size), (size, answer)
                costs.append((measured.inferences, cpu))
            print(f"{size},{min(count for count, _ in costs)},"
                  f"{min(cpu for _, cpu in costs):.9f}", flush=True)


if __name__ == "__main__":
    main()
