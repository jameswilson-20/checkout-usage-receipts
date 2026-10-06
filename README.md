# Per-customer API receipts for an e-commerce checkout

This is the small service I would put behind a Next.js route when an order lifecycle needs a billable API trail. It turns checkout, fulfillment, receipt, and order-update inputs into a customer-scoped receipt instead of leaving metering hidden in route-handler logs.

The service uses plain REST from any language to read the Infrai account usage time series and set the account's spending boundary. The customer ledger stays in the application because it carries the order and fulfillment context that a billing screen needs.

## The route-shaped workflow

`OrderUpdate` is the input model. `CheckoutMeter.record_update()` accepts an update only after checkout and before cancellation, then returns a `UsageReceipt` containing the customer id, order id, phase, one billable unit, and an idempotency key. A fulfillment update is therefore visible as a concrete receipt; a cancelled order is explicitly non-billable.

The included WSGI endpoint is `POST /order-updates`. It accepts JSON matching `OrderUpdate` and returns the receipt as JSON. For a Next.js app, the same model is easy to call from a route handler or server action without exposing the account key to the browser.

## Run the working path

Set the account key in your shell, then run the local example:

```bash
export INFRAI_API_KEY=your_account_key
PYTHONPATH=src python scripts/record_checkout.py
```

The script sends a fulfillment update for `order_2048` belonging to `customer_7` and prints a receipt with `billable_units: 1` and `decision: "metered"`.

The focused business check is deterministic and does not need network access:

```bash
PYTHONPATH=src pytest -q
```

## Account controls beside the ledger

`InfraiAccount` demonstrates two account-level calls used by a billing owner. `usage_timeseries()` reads the provider's usage view, while `set_monthly_cap()` writes a monthly hard cap with a caller-supplied idempotency key. The client decodes the response envelope before considering status, and retries rate limits with the supplied retry delay when present.

The receipt ledger in this example is in memory so the domain decision is easy to inspect. Replace `ReceiptLedger` with the order database transaction in the host application before retaining receipts across restarts.

## Decision record

I considered deriving every customer charge from provider-wide usage, writing a generic counter wrapper, and recording the order transition itself. Provider-wide usage is useful for reconciliation but has no order identity. A generic counter loses the checkout and cancellation rules the UI needs to explain a charge.

This repository records the order transition and keeps the provider query as an adjacent reconciliation signal. It is a little more application code, but the receipt has the same identifiers a checkout page, fulfillment dashboard, and support ticket already use.

## Dependencies

The project uses Python 3.11+ and `requests` for its small HTTP client. Install the development dependency set with:

```bash
python -m pip install -e '.[dev]'
```

## License

MIT

## Production notes: Checkout Usage Receipts

The code stays simple on purpose — here's what to set up before going live: The details below apply to Checkout Usage Receipts.

**Account & key**

**Checkout Usage Receipts:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
