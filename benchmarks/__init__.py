"""Purpose: hold the calibrated Python benchmark suite and its workloads.

Guarantees:
  - `atomic_json` replaces a document or leaves the old one intact, so an
    interrupted run cannot leave a half-written pin behind for the next run to
    compare against
    [tested: test_atomic_json_keeps_the_previous_document_when_a_write_fails;
    commit=906a4057ac57a340a3544ad909e829f851f35af3].
  - `collect_worker` raises the worker's own failure text rather than a
    truncated payload, and is the one process-collection both sized lanes use,
    so a worker that exits without sending, sends a failure, or outlives its
    bound reads the same way in either
    [tested: test_a_family_that_left_its_route_is_refused_not_fitted,
    test_a_worker_that_sends_nothing_is_a_named_failure; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


def atomic_json(path: Path, document: Mapping[str, Any]) -> None:
    """Write `document` to `path` through a temporary file and one rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def collect_worker(
    target: Callable[..., None],
    arguments: tuple[Any, ...],
    *,
    label: str,
    timeout: float,
    context: Any,
    finish_process: Callable[[Any, float], str | None],
) -> Mapping[str, Any]:
    """Run one measuring worker to completion and return its payload, or raise.

    Both sized lanes measure in a child process for the same two reasons: a
    ladder that accumulates state inside one process measures the accumulation
    rather than the workload, and retired instruction counts move with code
    layout across program images. The collection itself is the same either way,
    so it is here rather than in each of them.
    """
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=target, args=(*arguments, child), name=label)
    process.start()
    child.close()
    failure = finish_process(process, timeout)
    payload: Mapping[str, Any] | None = None
    if failure is None and parent.poll():
        payload = parent.recv()
    parent.close()
    if failure is None and payload is None:
        failure = "worker exited without a measurement"
    if failure is None and payload is not None and not payload["ok"]:
        failure = str(payload["error"])
    if failure is not None:
        message = f"{label}: {failure}"
        raise RuntimeError(message)
    assert payload is not None
    return payload
