from checkout_meter import CheckoutMeter, OrderPhase, OrderUpdate, ReceiptLedger


def main() -> None:
    meter = CheckoutMeter(ReceiptLedger())
    receipt = meter.record_update(
        OrderUpdate(
            customer_id="customer_7",
            order_id="order_2048",
            phase=OrderPhase.FULFILLMENT,
            api_operation="create_shipping_label",
        )
    )
    print(receipt.as_dict())


if __name__ == "__main__":
    main()
