# CloudDash — API Documentation

<!-- KB-020 -->
## Authentication and API Keys

**Article ID:** KB-020 | **Category:** api | **Tags:** api, authentication, api-key, bearer-token, security | **Plans:** Starter (read-only), Pro, Enterprise | **Updated:** 2026-05-01

### Overview

The CloudDash REST API uses **Bearer token authentication**. All requests must include your API key in the `Authorization` header.

```
Authorization: Bearer YOUR_API_KEY
```

### Generating an API Key

1. Navigate to **Settings > API Keys**.
2. Click **+ New API Key**.
3. Enter a descriptive name (e.g., `terraform-production`, `grafana-integration`).
4. Choose scope:
   - **Read-Only** — can query metrics, dashboards, alerts. Cannot modify.
   - **Read-Write** — full access to create, update, delete resources.
5. Set an optional expiry date for automated rotation compliance.
6. Copy the key immediately — it is shown only once.

### Key Scopes

| Scope | Allowed Operations |
|-------|-------------------|
| `metrics:read` | Query metrics and time series data |
| `dashboards:read` | List and retrieve dashboard configs |
| `dashboards:write` | Create, update, delete dashboards |
| `alerts:read` | List alert states and configurations |
| `alerts:write` | Create, mute, delete alerts |
| `integrations:read` | View integration status |
| `integrations:write` | Create and update integrations |

Read-Only keys have `metrics:read`, `dashboards:read`, `alerts:read`, and `integrations:read` by default.

### Security Best Practices

- Use one key per service — never share keys between applications.
- Rotate keys every 90 days: create new key → update services → revoke old key.
- Never commit API keys to source control. Use environment variables or a secrets manager.
- Immediately revoke a key if you suspect it has been exposed: **Settings > API Keys > Revoke**.

---

<!-- KB-021 -->
## API Rate Limits

**Article ID:** KB-021 | **Category:** api | **Tags:** api, rate-limits, throttling, 429, requests | **Plans:** All | **Updated:** 2026-04-10

### Rate Limit Tiers

| Plan | Requests/minute | Burst limit | Daily limit |
|------|----------------|-------------|-------------|
| Free | 60 | 100 | 5,000 |
| Starter | 300 | 500 | 50,000 |
| Pro | 1,000 | 2,000 | 500,000 |
| Enterprise | Custom | Custom | Unlimited |

Rate limits are applied per API key, not per account.

### Rate Limit Headers

Every API response includes:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1719100860
```
- `X-RateLimit-Reset` is a Unix timestamp indicating when the limit resets.

### Handling 429 Too Many Requests

When rate-limited, the API returns:
```json
HTTP 429 Too Many Requests
{
  "error": "rate_limit_exceeded",
  "retry_after": 42,
  "message": "You have exceeded your rate limit. Retry after 42 seconds."
}
```

**Recommended retry pattern (exponential backoff):**
```python
import time, requests

def api_call_with_retry(url, headers, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
            time.sleep(retry_after)
            continue
        return response
    raise Exception("Max retries exceeded")
```

### Increasing Rate Limits

- Upgrade to a higher plan.
- Enterprise customers can request custom limits via their Customer Success Manager.
- If you regularly hit limits on the Pro plan, contact support@clouddash.io to discuss your use case.

---

<!-- KB-022 -->
## Webhook Configuration

**Article ID:** KB-022 | **Category:** api | **Tags:** webhook, notifications, alerts, http, integration | **Plans:** Pro, Enterprise | **Updated:** 2026-04-30

### What Webhooks Do

CloudDash can send HTTP POST requests to your endpoint whenever an alert state changes (OK → Alerting → No Data). Use webhooks to:
- Trigger automated remediation workflows.
- Post to custom Slack workspaces or Microsoft Teams.
- Log alert events to your own systems.
- Relay alerts to platforms not natively supported (e.g., custom ticketing systems).

### Setting Up a Webhook

1. Navigate to **Settings > Notification Channels > New Channel**.
2. Select **Webhook**.
3. Enter your HTTPS endpoint URL.
4. Optionally add custom headers (e.g., `Authorization: Bearer your-internal-token`).
5. Select the alert severity levels to trigger the webhook (Warning, Critical, or both).
6. Click **Test** — CloudDash sends a sample payload to verify your endpoint responds with `2xx`.

### Webhook Payload Format

```json
{
  "alert_id": "alert_abc123",
  "alert_name": "High CPU on prod-server-01",
  "state": "alerting",
  "previous_state": "ok",
  "severity": "critical",
  "triggered_at": "2026-05-01T14:22:00Z",
  "metric": "system.cpu.usage",
  "current_value": 94.7,
  "threshold": 90.0,
  "host": "prod-server-01",
  "tags": {"env": "production", "region": "us-east-1"},
  "dashboard_url": "https://app.clouddash.io/dashboards/xyz",
  "runbook_url": "https://wiki.example.com/runbooks/high-cpu"
}
```

### Webhook Retry Behaviour

If your endpoint returns a non-2xx response or times out (>10 seconds), CloudDash retries:
- Retry 1: after 1 minute
- Retry 2: after 5 minutes
- Retry 3: after 30 minutes

After 3 failures, the alert event is marked as "delivery failed" and logged in **Settings > Notification Channels > Delivery Log**.

### Securing Your Webhook

CloudDash signs every webhook request with an HMAC-SHA256 signature:
```
X-CloudDash-Signature: sha256=<hex_digest>
```

Verify the signature in your handler:
```python
import hmac, hashlib

def verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

---

<!-- KB-023 -->
## Metrics Query API

**Article ID:** KB-023 | **Category:** api | **Tags:** api, metrics, query, time-series, aggregation | **Plans:** Starter (read-only), Pro, Enterprise | **Updated:** 2026-05-02

### Endpoint

```
GET /api/v2/metrics/query
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metric` | string | Yes | Metric name, e.g. `system.cpu.usage` |
| `from` | ISO-8601 or Unix | Yes | Start of time range |
| `to` | ISO-8601 or Unix | Yes | End of time range |
| `resolution` | string | No | `raw`, `1m`, `5m`, `1h`, `1d` (default: auto) |
| `filter` | string | No | Tag filter, e.g. `env:production,region:us-east-1` |
| `group_by` | string | No | Group results by tag, e.g. `host` |

### Example Request

```bash
curl -X GET "https://api.clouddash.io/api/v2/metrics/query" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -G \
  --data-urlencode "metric=system.cpu.usage" \
  --data-urlencode "from=2026-05-01T00:00:00Z" \
  --data-urlencode "to=2026-05-01T01:00:00Z" \
  --data-urlencode "filter=env:production" \
  --data-urlencode "group_by=host"
```

### Example Response

```json
{
  "metric": "system.cpu.usage",
  "unit": "percent",
  "series": [
    {
      "tags": {"host": "prod-server-01"},
      "points": [
        [1746057600, 42.3],
        [1746057660, 44.1],
        [1746057720, 89.7]
      ]
    }
  ]
}
```

### Common API Error Codes

| Code | Error | Cause | Fix |
|------|-------|-------|-----|
| 400 | `invalid_metric` | Metric name not found | Use `/api/v2/metrics/list` to find valid names |
| 401 | `unauthorized` | Missing or invalid API key | Check key in Settings > API Keys |
| 403 | `forbidden` | Key lacks required scope | Use a Read-Write key or adjust scope |
| 429 | `rate_limit_exceeded` | Too many requests | See KB-021 for retry guidance |
| 503 | `service_unavailable` | CloudDash outage | Check status.clouddash.io |
