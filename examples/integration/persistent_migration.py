"""Purpose: migrate a persistent space's schema through the public factory.

The rename applies once while the old journal is opened. The migrated journal
then reopens with only its new schema, so ``rename`` is a migration request and
not a permanent alias.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from _common import check, done

from metta import S, space


with TemporaryDirectory(prefix="metta-persistent-example-") as directory:
    journal = Path(directory) / "facts.db"
    with space(backing={"old": 1}, journal=journal, sync="close") as original:
        original.add(S.old(S.value))

    with space(
        backing={"new": 1},
        journal=journal,
        sync="close",
        rename={"old": "new"},
    ) as migrated:
        check(
            "migration renames the stored head",
            list(migrated.atoms()),
            [S.new(S.value)],
        )

    with space(
        backing={"new": 1}, journal=journal, sync="close"
    ) as reopened:
        check(
            "the new schema reopens without an alias",
            list(reopened.atoms()),
            [S.new(S.value)],
        )

done("persistent_migration")
