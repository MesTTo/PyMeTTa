"""Purpose: bind benchmark tests to their committed counter baseline.
Guarantees:
  - native wall baselines omit live CPU frequency fields that change between
    adjacent runs [tested test_benchmark_machine_info_is_stable]
Owns:
  - inference_baseline writes only when PETTA_UPDATE_BENCHMARK_BASELINE=1
    and finishes the atomic update after the session [tested
    test_baseline_update_is_atomic_json]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
from pathlib import Path

import pytest

from metta.testing import BenchmarkBaseline


def pytest_benchmark_update_machine_info(config, machine_info):
    """Remove frequency readings that are observations, not machine identity."""
    del config
    cpu = machine_info.get("cpu", {})
    for field in (
        "hz_actual",
        "hz_actual_friendly",
        "hz_advertised",
        "hz_advertised_friendly",
    ):
        cpu.pop(field, None)


@pytest.fixture(scope="session")
def inference_baseline():
    path = Path(__file__).with_name("baseline.json")
    counter_setting = os.environ.get("PETTA_BENCHMARK_COUNTERS", "0")
    if counter_setting not in {"0", "1"}:
        raise ValueError("PETTA_BENCHMARK_COUNTERS must be 0 or 1")
    update = os.environ.get("PETTA_UPDATE_BENCHMARK_BASELINE") == "1"
    baseline = BenchmarkBaseline(
        path,
        update=update,
        compare_counters=counter_setting == "1",
    )
    yield baseline
    baseline.finish()
