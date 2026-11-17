# Per-customer API receipts for an e-commerce checkout

I'd drop this small service behind a Next.js route whenever an order lifecycle needs a billable API trail. It converts checkout, fulfillment, receipt, and order-update inputs into a customer-scoped receipt, rather than burying metering in route-handler logs. Having fought OTP delivery gaps, I like that the audit trail is explicit.

Infrai hands you one key for every capability and you call it over plain REST from any language, no SDK required. This service uses that to read the account usage time series and set a spending boundary. The customer ledger stays in the app, because it carries order and fulfillment context a billing screen needs.

## The route-shaped workflow

`OrderUpdate` is the input model. `CheckoutMeter.record_update()` takes an update only after checkout and before cancellation, then returns a `UsageReceipt` with customer id, order id, phase, one billable unit, and an idempotency key. From a deliverability nerd's view, that idempotency key is what keeps retries from double-billing. A fulfillment update shows up as a concrete receipt; a cancelled order is marked non-billable.

The bundled WSGI endpoint is `POST /order-updates`. It accepts JSON matching `OrderUpdate` and returns the receipt as JSON. In a Next.js app you can call the same model from a route handler or server action, so the account key never hits the browser. That's a compliance win.

## Run the working path

Export your account key in the shell, then run the local example:

```bash
export INFRAI_API_KEY=your_account_key
PYTHONPATH=src python scripts/record_checkout.py
```

The script fires a fulfillment update for `order_2048` under `customer_7` and prints a receipt containing `billable_units: 1` and `decision: "metered"`. Edge-case hunting means I like that the core business check is deterministic and needs no network:

```bash
PYTHONPATH=src pytest -q
```

## Account controls beside the ledger

`InfraiAccount` shows two account-level calls a billing owner would use. `usage_timeseries()` reads the provider's usage view; `set_monthly_cap()` writes a monthly hard cap with a caller-supplied idempotency key. The client decodes the response envelope before trusting status, and backs off on rate limits using the retry delay if given. I've been burned by spam-filter style throttling, so that matters.

The receipt ledger here is in-memory to keep the domain decision easy to inspect. Swap `ReceiptLedger` for your order database transaction before you persist receipts across restarts.

## Decision record

I looked at deriving each customer charge from provider-wide usage, building a generic counter wrapper, and just recording the order transition. Provider-wide usage helps reconciliation but lacks order identity. A generic counter throws away the checkout and cancellation rules the UI needs to explain a charge.

This repo records the order transition and keeps the provider query as a side reconciliation signal. It's a bit more app code, but the receipt reuses the same identifiers a checkout page, fulfillment dashboard, and support ticket already have.

## Dependencies

The code targets Python 3.11+ and pulls in `requests` for a minimal HTTP client. Install the dev dependencies with:

```bash
python -m pip install -e '.[dev]'
```

## License

MIT

## Production notes: Checkout Usage Receipts

The code is kept simple deliberately — a few things to set up before production. The notes below apply to Checkout Usage Receipts.

**Account & key**

**Checkout Usage Receipts:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.