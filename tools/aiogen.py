"""Purpose: check the four door faces emitted by doorfaces from marked bodies.

Guarantees: worker-owned methods remain in aio/_worker.py, and every ordinary
mirror uses the common signature, overload, docstring and call emitter
[tested: test_the_async_mirror_is_generated_from_the_sync_surface;
commit=WORKTREE].
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
sys.path[:0] = [str(TOOLS), str(ROOT / 'extensions/python')]

from doorfaces import (  # noqa: E402 -- tool imports follow the checkout search path
    asynchronous,
    synchronous,
)
from doorgen import all_rows  # noqa: E402 -- tool imports follow the checkout search path

# tool imports follow the checkout search path
from rootgen import projections as root_projections  # noqa: E402


def projections() -> dict[Path, str]:
    """Derive the four faces and the root's declarations in dependency order."""
    rows = all_rows()
    return {**synchronous(rows, ROOT), **asynchronous(rows, ROOT), **root_projections(rows)}


def main(argv: list[str] | None = None) -> int:
    """Check the derived files, or write the declared forms."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    stale = []
    for path, wanted in projections().items():
        if path.is_file() and path.read_text(encoding='utf-8') == wanted:
            continue
        if args.write:
            path.write_text(wanted, encoding='utf-8')
        else:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        print('aio-mirror: stale projections: ' + ', '.join(stale))
        return 1
    print('aio-mirror: all four faces agree with their declarations')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
