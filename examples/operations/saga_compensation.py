"""Purpose: recover committed external-style steps through saga receipts.

An ordinary transaction cannot undo an effect that already committed. A saga
records one ``(did ...)`` receipt per committed step, then runs declared
compensations in reverse order if its scope exits exceptionally.
Owns resources: the MeTTa context closes the engine; the two anonymous spaces
are dropped after the checked recovery.
"""

from _common import check, done

from metta import MeTTa, S, V


class CancelOrderError(Exception):
    """The example's application-level reason to recover its committed step."""


with MeTTa() as context:
    orders = context.space()
    receipts = context.space()

    orders.run(
        "(= (undo-add (did add-atom ($space $atom) $result)) "
        "(remove-atom $space $atom))"
    )
    orders.compensates("add-atom", "undo-add")

    try:
        with orders.saga(receipts) as saga:
            check(
                "a committed step answers normally",
                saga.run(S.add_atom(orders, S.booked(S.Ada))),
                [True],
            )
            check(
                "the committed step leaves a queryable receipt",
                len(receipts.match(S.did(V.operation, V.arguments, V.result))),
                1,
            )
            raise CancelOrderError  # noqa: TRY301 -- exceptional scope exit is the behavior being demonstrated
    except CancelOrderError:
        pass

    check("exceptional exit ran the compensation", orders.match(S.booked(V.who)), [])
    check("successful recovery retired the receipt", receipts.atoms(), [])
    receipts.drop()
    orders.drop()

done("saga_compensation")
