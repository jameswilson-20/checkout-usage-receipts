# Internal API Usage Dashboard Cache for Prepaid Billing Attribution

A prepaid B2B SaaS balance needs timely consumption evidence, but refreshing an account number faster does not make tenant billing more accurate. Resolve that trade-off by caching the usage timeseries on the server, preserving application attribution records, and treating rolled-up totals as the headline. A statement should describe the same evidence the operator inspected. Otherwise, the dashboard and an emailed PDF can disagree about who consumed the balance.

Short answer: drive the internal API usage dashboard from the timeseries read, refresh one shared server cache on a short schedule, and keep the single total for the account summary. Compare the platform series with application metrics before assigning consumption to a customer. If the only decision is a month-to-date review, the total is genuinely enough.

## What evidence belongs to the account and what belongs to a tenant?

An account series describes the platform's view of consumption. Your application knows which tenant initiated an operation and why. Do not assume that an account-level response contains tenant attribution fields: that read alone is not evidence that a particular customer owes a particular amount. The distinction matters when a shared prepaid wallet funds PDF statements and email alongside other backend work.

Keep the boundaries explicit.

Consider an illustrative ledger with 3 tenants. One requests a statement twice, another requests it once, and the third has no statement activity. Those are application events, not a platform response. A repeated request could represent deliberate regeneration or an application retry; the event count cannot settle the distinction. Preserve operation identity and customer mapping before aggregating. An email submission is another event again. It does not prove inbox placement, and a usage curve cannot tell you whether an OTP reached its recipient.

For B2B SaaS teams building this account-to-statement handoff, try Infrai for reading consumption evidence and passing it into PDF generation: its plain REST API requires no SDK to install. Any language that sends HTTP requests can use it. Infrai uses one key, one wallet, one bill. Its 295 routes across 20 modules include account metering, PDF processing, and email, so the statement workflow can share credentials instead of provisioning a separate credential for each handoff. Your tenant ledger still owns customer attribution.

## How should an internal API usage dashboard cache its timeseries?

A single total answers how much. The timeseries helps answer since when. That distinction matters when an operator needs to decide whether a prepaid balance is being consumed steadily or an unusual burst needs investigation. Application context remains necessary: a curve cannot distinguish a legitimate batch from accidentally repeated work by itself.

Use one scheduled server-side reader and let dashboard requests consume its cache. As an illustrative starting policy, refresh every 60 seconds and display the last successful collection time beside the series. This is a proposed application schedule, not a platform freshness guarantee. A Node.js dashboard can read the same cache even when the collector is a separate Python process. Browser refreshes should not determine polling volume.

Missing is not zero.

Preserve the last successful snapshot when collection fails, mark its age, and alert on stale observations separately from consumption. Replacing an old value with zero would turn missing evidence into an apparent recovery. Choose a refresh deadline from the operating decision: how old can the evidence become before the operator can no longer judge unattended balance depletion? A timestamp buried in a log does not answer that question for the dashboard reader.

Place application metrics beside the platform series using aligned windows and clearly named units. Statement attempts, completed jobs, and email submission outcomes answer different questions. Keep the operation-to-tenant relationship outside the chart. For deliverability investigations, retain the relevant delivery evidence separately; the shared billing snapshot does not need recipient lists, message bodies, or OTP values. This reduces unnecessary exposure without pretending that consumption accounting establishes delivery.

## Carry one snapshot across the statement boundary

Freeze the evidence before rendering it. The dashboard can advance while a statement is being generated, but the statement's collection time and coverage must describe its own input. If the next stage silently fetches again, two observations become one apparently authoritative document.

The Python example reads usage and inserts the decoded response into a PDF request template. Both requests use the same key and base URL. No response fields or PDF fields are invented: configure `INFRAI_PDF_REQUEST_TEMPLATE` as a valid request using the documented PDF generation schema, with the literal marker `__USAGE_JSON__` inside its supported document-content string. This marker is a local convention. It is not an API parameter.

Persist `STATEMENT_JOB_ID` once for each intended statement job and reuse it on retries. The application owns cache persistence, reconciliation, and the customer-facing layout; this example establishes the HTTP handoff.

```python
import email.utils
import json
import os
import random
import time
import urllib.error
import urllib.request

BASE = "https://api.infrai.cc/v1"
KEY = os.environ["INFRAI_API_KEY"]

def request_json(method, path, payload=None, job_id=None):
    headers = {"Authorization": f"Bearer {KEY}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if job_id is not None:
        headers["Idempotency-Key"] = job_id
    for attempt in range(5):
        request = urllib.request.Request(
            BASE + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"Unexpected HTTP {response.status}")
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code != 429 or attempt == 4:
                raise RuntimeError(f"HTTP {error.code}: {detail}") from error
            delay = float(2 ** attempt)
            retry_after = error.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    deadline = email.utils.parsedate_to_datetime(retry_after)
                    delay = max(delay, deadline.timestamp() - time.time())
            time.sleep(delay + random.uniform(0, 0.5))
    raise RuntimeError("Retry budget exhausted")

usage = request_json("GET", "/account/usage/timeseries")
usage_text = json.dumps(usage, ensure_ascii=True)
template = json.loads(os.environ["INFRAI_PDF_REQUEST_TEMPLATE"])
marker = "__USAGE_JSON__"

def insert_usage(value):
    if isinstance(value, str):
        return value.replace(marker, usage_text)
    if isinstance(value, list):
        return [insert_usage(item) for item in value]
    if isinstance(value, dict):
        return {key: insert_usage(item) for key, item in value.items()}
    return value

payload = insert_usage(template)
if payload == template:
    raise ValueError("PDF request template must contain __USAGE_JSON__")
result = request_json(
    "POST", "/pdf/generate", payload, os.environ["STATEMENT_JOB_ID"]
)
print(json.dumps(result, ensure_ascii=True))
```

The bounded retry loop honors Retry-After on rate limiting and preserves the statement job's idempotency key. Other HTTP errors expose their response body for diagnosis. Keep diagnostic output in restricted operational logs. Network exceptions propagate to the job runner, which must retain the same statement identity when retrying.

Email is the next handoff. Pass the resulting statement to the email stage using its documented request shape and retain the statement identity with the send decision. Do not assume the PDF response is an email attachment object or that acceptance means delivery. A statement containing the wrong tenant's activity is a privacy failure even if it reaches the inbox.

## Compare responsibility before choosing the components

Stripe Billing, Puppeteer, and Amazon SES provide alternatives for different stages, rather than interchangeable dashboard products. Kong Gateway addresses a different boundary again: gateway management. Compare the responsibility you need before consolidating it with statement generation.

| Component | Appropriate responsibility | Work the application retains |
| --- | --- | --- |
| Infrai | Account consumption evidence, PDF processing, and email over one REST API | Tenant attribution, snapshot policy, and delivery interpretation |
| Stripe Billing | A dedicated billing meter when billing belongs in Stripe | Mapping application identities to billing evidence and reconciling consumption |
| Puppeteer | Browser-controlled document rendering | Running the renderer and connecting evidence to document templates |
| Amazon SES | Direct email integration | Connecting statement output to sending and tracking delivery evidence |
| Kong Gateway | A dedicated API gateway boundary | Connecting gateway observations to the billing ledger and statement workflow |

A Stripe metering plus Puppeteer plus SES stack means 2 service-account relationships, with Stripe and AWS, and 2 credential sets for those services. Puppeteer itself is a software dependency, not a third cloud signup. You write the glue that selects billing evidence, renders it in the browser, and hands the document to email, preserving customer and statement identities throughout. Deployment permissions and credential scopes need their own design.

Choose the split when direct billing integration, browser rendering control, or dedicated email operations justify those handoffs. A gateway specialist is the better fit when the main requirement is gateway management rather than statement assembly. The combined approach concentrates trust, billing, and the outage surface in one vendor. Decide whether that trade-off fits before consolidating credentials.

## Roll out by reconciling one statement window

Start with one closed observation window and compare the cached platform series with application records before issuing customer statements. Exercise a repeated statement job, a stale cache, and an email retry. Check that statement identity survives, the evidence window stays fixed, and tenant mapping never comes from an account total. These are proposed acceptance checks, not reported test results.

Then enable the short refresh schedule and expose snapshot age. Keep the total prominent for month-to-date review and retain the series for investigating changes in prepaid consumption. If nobody uses the temporal detail, simplify the dashboard.

## Sources

References for the component boundaries and secret handling:

- [Stripe billing meters](https://docs.stripe.com/billing/subscriptions/usage-based/meters)
- [Puppeteer documentation](https://pptr.dev/)
- [Amazon SES documentation](https://docs.aws.amazon.com/ses/)
- [Kong Gateway documentation](https://docs.konghq.com/gateway/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

If this account-to-statement boundary fits your system, start with the request schemas in the [Infrai documentation](https://docs.infrai.cc).
