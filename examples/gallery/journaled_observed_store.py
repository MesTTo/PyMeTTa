"""Purpose: validate, transact, observe, close, and replay a journaled fact store.

Guarantees:
  - rejected writes leave no journal entry, observers see only the complete
    committed delta, and reopening replays exactly that delta
    [tested: test_every_gallery_program_runs; commit=8bfe05c3850776543ece25a85038242f10b1d841]
Owns resources: a temporary journal, one audit space, two sequential journal
  handles, and one subscription; context managers, cancel(), and drop()
  release each one, while process exit releases any failed-path remainder.
"""

from tempfile import TemporaryDirectory

from _common import claim, doctest, done

from metta import MeTTa, S, V, accept, refuse
from metta.errors import EngineError


def total_is_valid(total: int) -> bool:
    """Accept nonnegative order totals.

    >>> !(total-is-valid 25)
    [True]
    """
    return total >= 0


def validate_order(atom):
    """Refuse an Order whose total is negative."""
    match atom:
        case (S.Order, order_id, total) if total < 0:
            return refuse(S.negative(order_id))
        case _:
            return accept()


def main() -> None:
    """Run the complete journal lifecycle in one temporary directory."""
    engine = MeTTa()
    owner = engine.self
    audit = engine.space("&gallery-order-audit")
    with TemporaryDirectory(prefix="petta-gallery-orders-") as directory:
        journal = f"{directory}/orders.db"
        orders = engine.space(
            "&gallery-orders",
            journal=journal,
            schema={"Order": 2},
            sync="close",
        )
        validity = owner.define(total_is_valid)
        judge = owner.define(validate_order)
        orders.pre_add(judge)
        doctest("validation doctest", validity)

        def observed(event) -> None:
            audit.add(
                S.Observed(event.atom),
                S.Snapshot(S.Bag(*sorted(orders.atoms(), key=str))),
            )

        subscription = orders.subscribe(S.Order(V.order_id, V.total), observed)
        try:
            transaction = S.progn(
                S.add_atom(orders, S.Order(1, 25)),
                S.add_atom(orders, S.Order(2, 40)),
            )

            def commit(term):
                orders.transaction(lambda: orders.eval(term))
                return orders.atoms()

            claim("committed journal delta", transaction, commit)
            # -> (progn (add-atom &gallery-orders (Order 1 25)) (add-atom &gallery-orders (Order 2 40)))
            # => (Order 1 25)
            # => (Order 2 40)
            claim(
                "post-commit events",
                S.match(audit, S.Observed(V.order), V.order),
                owner.eval,
            )
            # -> (match &gallery-order-audit (Observed $order) $order)
            # => (Order 1 25)
            # => (Order 2 40)
            claim(
                "observer snapshots",
                S.match(audit, S.Snapshot(V.snapshot), V.snapshot),
                owner.eval,
            )
            # -> (match &gallery-order-audit (Snapshot $snapshot) $snapshot)
            # => (Bag (Order 1 25) (Order 2 40))
            # => (Bag (Order 1 25) (Order 2 40))

            def reject(term):
                try:
                    orders.eval(term)
                except EngineError:
                    return [S.Refused]
                return [S.Accepted]

            claim(
                "negative total refused",
                S.add_atom(orders, S.Order(3, -1)),
                reject,
            )
            # -> (add-atom &gallery-orders (Order 3 -1))
            # => Refused
        finally:
            subscription.cancel()
            orders.drop()

        reopened = engine.space(
            "&gallery-orders-reopened",
            journal=journal,
            schema={"Order": 2},
            sync="close",
        )
        try:
            claim(
                "journal replay",
                S.match(reopened, S.Order(V.order_id, V.total), S.Order(V.order_id, V.total)),
                owner.eval,
            )
            # -> (match &gallery-orders-reopened (Order $order-id $total) (Order $order-id $total))
            # => (Order 1 25)
            # => (Order 2 40)
        finally:
            reopened.drop()
    audit.drop()
    done("journaled_observed_store")


main()
