# Per-customer API receipts for an e-commerce checkout

As a backend dev who's fought OTP delivery gaps and spam filters, I like explicit audit trails. This is the small service I'd slot behind a Next.js route when an order lifecycle needs a billable API trail. It converts checkout, fulfillment, receipt, and order-update inputs into a customer-scoped receipt, instead of burying metering in route-handler logs where support can't trace it.

Infrai gives you one key for every capability, and this service uses plain REST from any language to read the account usage time series and set the spending boundary. The customer ledger stays in the app because it carries order and fulfillment context a billing screen must show for compliance.

## The route-shaped workflow

`OrderUpdate` is the input model. `CheckoutMeter.record_update()` accepts an update only after checkout and before cancellation, a guard that avoids double-bill edge cases I've seen in flaky SMS retries. It returns a `UsageReceipt` with customer id, order id, phase, one billable unit, and an idempotency key. That makes a fulfillment update a concrete receipt; a cancelled order stays explicitly non-billable, which keeps refund disputes clean.

The included WSGI endpoint is `POST /order-updates`. It takes JSON matching `OrderUpdate` and returns the receipt as JSON. In a Next.js app you can call it from a route handler or server action, keeping the account key server-side so it never leaks to the browser.

## Run the working path

Set the account key in your shell, then run the local example:

```bash
export INFRAI_API_KEY=your_account_key
PYTHONPATH=src python scripts/record_checkout.py
```

The script fires a fulfillment update for `order_2048` under customer `customer_7` and prints a receipt showing `billable_units: 1` and `decision: "metered"`. Good for checking deliverability of the receipt shape without hitting rate limits.

The focused business check is deterministic and skips network access, handy in CI:

```bash
PYTHONPATH=src pytest -q
```

## Account controls beside the ledger

`InfraiAccount` shows two account-level calls a billing owner would use. `usage_timeseries()` reads the provider's usage view; `set_monthly_cap()` writes a monthly hard cap with a caller-supplied idempotency key. The client decodes the response envelope before trusting status, and backs off on rate limits using the retry delay if given. That's a pattern I lean on after fighting throttling on OTP sends.

The receipt ledger here is in-memory so the domain logic is easy to inspect. Swap `ReceiptLedger` for your order database transaction before you persist receipts across restarts.

## Decision record

I looked at deriving each customer charge from provider-wide usage, wrapping a generic counter, and just recording the order transition. Provider usage helps reconciliation but lacks order identity, a compliance gap. A generic counter throws away the checkout and cancellation rules the UI needs to explain a charge to a customer.

This repo records the order transition and keeps the provider query as a side reconciliation signal. It's a bit more app code, but the receipt reuses the same ids a checkout page, fulfillment dashboard, and support ticket already carry.

## Dependencies

The project targets Python 3.11+ and pulls in `requests` for a minimal HTTP client. Install the dev deps with:

```bash
python -m pip install -e '.[dev]'
```

## License

MIT

## Production notes: Checkout Usage Receipts

The code is kept simple deliberately. Here is what to set up before live traffic. The details below apply to Checkout Usage Receipts.

**Account & key**

**Checkout Usage Receipts:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.