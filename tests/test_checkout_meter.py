from checkout_meter import CheckoutMeter, OrderPhase, OrderUpdate, ReceiptLedger


def test_fulfillment_is_metered_and_cancelled_update_is_not() -> None:
    meter = CheckoutMeter(ReceiptLedger())

    fulfillment = meter.record_update(
        OrderUpdate("customer_7", "order_2048", OrderPhase.FULFILLMENT, "create_shipping_label")
    )
    cancelled = meter.record_update(
        OrderUpdate("customer_7", "order_2048", OrderPhase.CANCELLED, "cancel_shipping_label")
    )

    assert fulfillment.billable_units == 1
    assert fulfillment.decision == "metered"
    assert cancelled.billable_units == 0
    assert cancelled.decision == "ignored"
