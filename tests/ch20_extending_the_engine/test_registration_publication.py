"""Purpose: restore registry and completed observers after publication failure."""

from contextlib import nullcontext

import pytest

from metta import seam
from metta._declare import operations


@pytest.mark.parametrize("failed", [0, 1, 2])
@pytest.mark.parametrize("operation", ["insert", "replace", "remove"])
def test_registration_failure_restores_all_required_views(monkeypatch, failed, operation):
    """Each listener failure restores both the registry and completed views."""
    monkeypatch.setattr(seam, "_LISTENERS", [])
    point = seam.point("audit-publication", "declaration", fields=("value",), doc="publication")
    try:
        if operation != "insert":
            point.register("held", value="before")
        before = tuple(seam._ROWS[point.name])
        views = [before, before, before]

        def observer(index):
            def publish(_point, _name, _undo):
                if index == failed:
                    msg = f"listener {index} failure"
                    raise ValueError(msg)
                prior = views[index]
                views[index] = tuple(seam._ROWS[point.name])

                def restore():
                    views[index] = prior
                return restore
            return publish

        monkeypatch.setattr(seam, "_LISTENERS", [observer(index) for index in range(3)])
        with pytest.raises(ValueError, match=f"listener {failed} failure"):
            if operation == "remove":
                point.unregister("held")
            else:
                point.register("held", value="after")
        assert tuple(seam._ROWS[point.name]) == before
        assert views == [before, before, before]
    finally:
        seam.withdraw(point.name)


def test_validated_points_refuse_external_storage():
    """Validation's declared ownership rule rejects a split store before use."""
    calls = []

    def refuse(_row, _standing):
        msg = "invalid row"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="a validated point owns its rows"):
        seam.point("audit-validation", "declaration", fields=("value",),
                   doc="validation", validator=refuse, adder=calls.append)
    assert calls == []
    assert "audit-validation" not in seam._POINTS


def test_registration_reconciles_stateless_observers_after_failure(monkeypatch):
    """A projection without a receipt rereads the restored registry."""
    point = seam.point("audit-reconcile", "declaration", fields=("value",), doc="reconcile")
    snapshots = []

    def reconcile(_point, _name, _undo):
        snapshots.append(tuple(seam._ROWS[point.name]))

    def fail(_point, _name, _undo):
        msg = "publication failed"
        raise ValueError(msg)

    try:
        monkeypatch.setattr(seam, "_LISTENERS", [reconcile, fail])
        with pytest.raises(ValueError, match="publication failed"):
            point.register("held", value=1)
        assert len(snapshots[0]) == 1
        assert snapshots[-1] == ()
        assert seam._ROWS[point.name] == []
    finally:
        seam.withdraw(point.name)


def test_registration_inverse_retries_only_failed_actions(monkeypatch):
    """Independent failures survive, and completed inverses are never repeated."""
    external = []
    view = []
    attempts = []
    saved = []
    body = ValueError("publisher failed")
    store_failure = RuntimeError("store rollback failed")
    view_failure = KeyboardInterrupt("view rollback interrupted")

    def add(row):
        external.append(row)

        def undo():
            attempts.append("store")
            if attempts.count("store") == 1:
                raise store_failure
            external.remove(row)
        return undo

    def publish(_point, _name, undo):
        saved.append(undo)
        view.append("published")

        def restore():
            attempts.append("view")
            if attempts.count("view") == 1:
                raise view_failure
            view.pop()
        return restore

    def fail(_point, _name, _undo):
        raise body

    point = seam.point("audit-retry-inverse", "declaration", fields=("value",),
                       doc="retry inverses", adder=add)
    try:
        monkeypatch.setattr(seam, "_LISTENERS", [publish, fail])
        with pytest.raises(BaseExceptionGroup) as failure:
            point.register("held", value=1)

        def leaves(error):
            if isinstance(error, BaseExceptionGroup):
                return [leaf for child in error.exceptions for leaf in leaves(child)]
            return [error]

        assert leaves(failure.value) == [body, store_failure, view_failure]
        assert seam._ROWS[point.name] == []
        assert attempts == ["store", "view"]
        saved[0]()
        assert external == view == []
        assert attempts == ["store", "view", "store", "view"]
        saved[0]()
        assert attempts == ["store", "view", "store", "view"]
    finally:
        seam.withdraw(point.name)


def test_registration_compensates_observers_in_reverse_order(monkeypatch):
    """A later projection is undone before the projection it depended on."""
    point = seam.point("audit-observer-order", "declaration", fields=("value",), doc="order")
    order = []
    saved = []

    def observer(number):
        def publish(_point, _name, undo):
            saved.append(undo)
            return lambda: order.append(number)
        return publish

    try:
        monkeypatch.setattr(seam, "_LISTENERS", [observer(0), observer(1), observer(2)])
        point.register("held", value=1)
        saved[0]()
        assert order == [2, 1, 0]
        assert seam._ROWS[point.name] == []
        saved[1]()
        assert order == [2, 1, 0]
    finally:
        seam.withdraw(point.name)


@pytest.mark.parametrize("nested", [False, True])
def test_registration_retry_inside_a_caught_failure_retains_its_inverse(monkeypatch, nested):
    """A spent publication receipt cannot suppress a later valid inverse."""
    point = seam.point("audit-caught-retry", "declaration", fields=("value",), doc="retry")
    refuse = True

    def observer(_point, _name, _undo):
        if refuse:
            msg = "publication failed"
            raise ValueError(msg)

    try:
        monkeypatch.setattr(seam, "_LISTENERS", [operations._record_seam_undo, observer])
        with pytest.raises(RuntimeError, match="outer rollback"), operations.registry_undo():
            with operations.registry_undo() if nested else nullcontext():
                with pytest.raises(ValueError, match="publication failed"):
                    point.register("held", value="first")
                assert seam._ROWS[point.name] == []
                refuse = False
                point.register("held", value="second")
            msg = "outer rollback"
            raise RuntimeError(msg)
        assert seam._ROWS[point.name] == []
    finally:
        seam.withdraw(point.name)


@pytest.mark.parametrize("nested", [False, True])
def test_transaction_rollback_replays_each_seam_mutation(monkeypatch, nested):
    """Replacement, removal and reinsertion preserve the original ordered rows."""
    monkeypatch.setattr(seam, "_LISTENERS", [operations._record_seam_undo])
    point = seam.point("audit-sequential-undo", "declaration", fields=("value",), doc="sequence")
    try:
        before = [point.register("held", value="original"), point.register("next", value=0)]
        with pytest.raises(RuntimeError, match="rollback"), operations.registry_undo():
            with operations.registry_undo() if nested else nullcontext():
                point.register("held", value="replaced")
                point.unregister("held")
                point.register("held", value="reinserted")
                point.register("other", value=1)
            msg = "rollback"
            raise RuntimeError(msg)
        assert seam._ROWS[point.name] == before
    finally:
        seam.withdraw(point.name)
