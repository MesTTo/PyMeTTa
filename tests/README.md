<!--
Purpose: say where a Python test belongs and why the packages are named after
book chapters rather than after modules of the library.
-->

# Where a Python test goes

The suite is organised by the same 22-chapter spine `examples/` uses, so the
two trees teach one order rather than two. A package name is the chapter's own
name in Python's casing: `ch04_spaces_and_matching`, not `ch04-spaces-and-matching`.
The number is in the path, which is the point: browsing the directory listing is
reading the order.

Two packages are not chapters, because their subject is not the language:

- `conformance/` holds the arbiters and oracles that decide what MeTTa MEANS.
  LeaTTa, the CeTTa fork, the presented-core oracle, the critical-pair
  enumerator, the differential against the CLI. A finding here says this engine
  disagrees with an authority, which is a different claim from a broken feature.
- `repository/` holds the tests whose subject is this repository: the README's
  executed blocks, the generated reference pages, the example corpus and its
  parity lane, the twins lane, the notebook, the tree partition, absolute paths
  in tracked files.

`fixtures/` holds inputs rather than tests: two MeTTa files a fixture loads and
the remote server one test starts as a subprocess. `twins/` is the Python twin
corpus, one file per example, addressed by transforming the example's own path,
which is why its directories keep the examples' hyphenated spelling.

Chapters 2 and 22 have no package. They are the book's project chapters, and
what they teach is a whole program, which `examples/ch02-programming-a-family-tree/`
and `examples/ch22-a-reasoner-you-can-serve/` carry end to end.

## Two things to know when adding one

`conftest.py` stays at the suite root and every package inherits its fixtures,
so a new test needs no conftest of its own.

A module one directory down counts one more parent. `Path(__file__).resolve().parents[4]`
is the repository root from inside a chapter package; it was `parents[3]` while
the suite was flat, and the 58 chains that counted parents were all rewritten
when the packages were made. A path derived from something that did NOT move,
such as `EXAMPLES_ROOT.parents[2]`, keeps its own count.
