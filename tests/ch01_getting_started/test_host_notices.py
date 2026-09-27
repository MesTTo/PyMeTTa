"""Purpose: hold the booted engine to naming, through SWI-Prolog's license/0, the components the host's notices name.

Every native host loads the engine through metta_qlf_boot:qlf_load_engine,
whose first half loads engine/host_notices.pl after the host check. That
module answers license:licensed/2 from the THIRD-PARTY-NOTICES in the SWI
home, reading the file each time it is asked, so a notices text planted ahead
of the home on the swi search path is answered by the engine already running,
and no real home is touched.
Guarantees:
  - with notices first on the swi search path, license:licensed/2 answers,
    beyond SWI's own registrations, exactly each block's SWI-Prolog-License
    and Component, and answers as before once they are gone
    [tested 2026-09-27T17:11:46+10:00: test_license_answers_the_components_of_the_home_notices]
"""

import metta
from metta._binding.runtime import bridge

_RULE, _THIN = "=" * 78, "-" * 78


def _notices(blocks):
    """A notices text in tools/host-notices/notices.py's format, one block per (Component, id)."""
    lines = ["Third-party notices", "", "Files:", "  libswipl.so"]
    for component, identifier in blocks:
        lines += ["", _RULE, f"Component: {component}", "License: planted",
                  f"SWI-Prolog-License: {identifier}", "Source: this test", "Files: libswipl.so",
                  _THIN, "Copyright (c) 2026 Nobody", "", "the licence text"]
    return "\n".join(lines) + "\n"


def _answered(janus):
    """Each Id<TAB>Component license:licensed/2 answers beyond SWI's own facts."""
    row = janus.query_once(
        "findall(_L, (license:licensed(_I, _C), \\+ clause(license:licensed(_I, _C), true), "
        "format(string(_L), '~w\\t~w', [_I, _C])), _Ls), atomic_list_concat(_Ls, '\\n', Text)")
    return set(filter(None, str(row["Text"]).split("\n")))


def test_license_answers_the_components_of_the_home_notices(tmp_path):
    """Plant two blocks ahead of the home; license:licensed/2 answers exactly them, then as before."""
    metta.space().run("!(+ 1 1)")
    janus = bridge()
    before = _answered(janus)
    blocks = [("planted zlib 1.3.2", "zlib"), ("planted isub 2011", "lgplv2+")]
    (tmp_path / "THIRD-PARTY-NOTICES").write_text(_notices(blocks), encoding="utf-8")
    janus.query_once("asserta(user:file_search_path(swi, Dir))", {"Dir": str(tmp_path)})
    try:
        assert _answered(janus) == {f"{identifier}\t{component}" for component, identifier in blocks}
    finally:
        janus.query_once("retract(user:file_search_path(swi, Dir))", {"Dir": str(tmp_path)})
    assert _answered(janus) == before
