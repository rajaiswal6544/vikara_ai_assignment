# CloudDash — Technical Troubleshooting Guide

<!-- KB-007 -->
## Alerts Not Firing After AWS Integration Credential Update

**Article ID:** KB-007 | **Category:** troubleshooting | **Tags:** alerts, aws, credentials, integration, not-firing | **Plans:** Starter, Pro, Enterprise | **Updated:** 2026-04-20

When you rotate AWS IAM credentials used by CloudDash, alerts that depend on CloudWatch metrics may stop firing because the integration loses its data feed. Follow these steps to restore alert functionality.

### Step 1 — Verify the AWS Integration Status

1. Navigate to **Integrations > AWS**.
2. Locate your AWS account entry. If the status shows **Authentication Error** or **No Data**, the credentials need updating.
3. Click **Edit** on the integration.

### Step 2 — Update IAM Credentials

If you use an **IAM User with access keys:**
1. In AWS IAM, create a new access key for the CloudDash IAM user.
2. In CloudDash, enter the new **Access Key ID** and **Secret Access Key**.
3. Click **Verify & Save**.

If you use an **IAM Role (recommended):**
1. Confirm the cross-account role ARN is still valid in AWS IAM.
2. Check that the `sts:AssumeRole` trust policy still includes the CloudDash principal.
3. In CloudDash, click **Re-verify Role** — this re-tests the `AssumeRole` call.

### Step 3 — Confirm Metrics Are Flowing

1. Go to **Metrics > Browse** and filter by `aws.*`.
2. If metrics appear within 5 minutes, the integration is healthy.
3. If no metrics appear after 10 minutes, check:
   - IAM policy includes `cloudwatch:GetMetricData`, `cloudwatch:ListMetrics`, `ec2:DescribeInstances`.
   - No SCPs (Service Control Policies) in AWS Organizations block these actions.

### Step 4 — Re-evaluate Alert State

After metrics resume flowing, alerts that were in **"No Data"** state will automatically re-evaluate on their next evaluation window. You do not need to recreate alerts. If an alert remains in "No Data" after 15 minutes of metrics flowing, click **Re-evaluate Now** on the alert detail page.

### Verification Checklist
- [ ] Integration status shows "Active" (green)
- [ ] Metrics visible in Metrics Browser
- [ ] Alert transitions out of "No Data" state
- [ ] Test notification received on at least one channel

---

<!-- KB-008 -->
## Dashboard Loading Slowly or Showing Query Timeout

**Article ID:** KB-008 | **Category:** troubleshooting | **Tags:** dashboard, performance, timeout, slow-loading | **Plans:** All | **Updated:** 2026-04-25

### Common Causes

1. **Time range too wide:** Querying 30+ days of unaggregated data is expensive.
2. **Too many panels:** Dashboards with 20+ panels run many queries simultaneously.
3. **Missing variable filters:** If `$host` or `$region` variables are not set, the query scans all data.
4. **Data rollups disabled:** Without rollups, long time ranges query raw data.

### Step-by-Step Resolution

**Reduce time range first:**
- Change the time picker to **Last 1 Hour** or **Last 6 Hours** and observe if loading improves.
- If it does, the issue is query scope, not connectivity.

**Enable Data Rollups (Pro/Enterprise):**
1. Go to **Settings > Data Management > Rollups**.
2. Enable **1-hour rollups** for retention beyond 7 days.
3. Enable **1-day rollups** for retention beyond 30 days.
4. Rollups are applied retroactively overnight and immediately for new data.

**Add variable filters:**
1. Open **Dashboard Settings > Variables**.
2. Ensure `$host`, `$region`, and `$service` variables have sensible defaults.
3. Use the **Include All** option with caution — it disables filtering.

**Reduce panel count:**
1. Archive infrequently used panels: right-click > **Move to archive**.
2. Split large dashboards into focused sub-dashboards linked via the navigation bar.

**Optimize individual panels:**
- Click the panel kebab menu > **Inspect > Query** to see raw query execution time.
- Add `by: host` or `by: service` grouping to avoid full-dataset scans.

---

<!-- KB-009 -->
## AWS CloudWatch Integration Failing to Connect

**Article ID:** KB-009 | **Category:** troubleshooting | **Tags:** aws, cloudwatch, integration, authentication, iam | **Plans:** Starter, Pro, Enterprise | **Updated:** 2026-05-05

### Symptom

Integrations > AWS shows status: **"Connection Failed"** or **"Insufficient Permissions"**.

### Diagnosis

**Error: `AccessDenied` on `sts:AssumeRole`**
The CloudDash principal is not allowed to assume your IAM role.

Fix:
1. In AWS IAM, open the role > **Trust relationships**.
2. Add the CloudDash principal:
```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::123456789012:root"
  },
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {
      "sts:ExternalId": "YOUR_CLOUDDASH_EXTERNAL_ID"
    }
  }
}
```
Find your ExternalId in CloudDash under **Integrations > AWS > Setup Guide**.

**Error: `cloudwatch:GetMetricData` denied**
The role lacks sufficient CloudWatch permissions.

Attach the AWS managed policy `CloudWatchReadOnlyAccess`, or add:
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudwatch:GetMetricData",
    "cloudwatch:ListMetrics",
    "cloudwatch:GetMetricStatistics",
    "ec2:DescribeInstances",
    "ec2:DescribeRegions",
    "tag:GetResources"
  ],
  "Resource": "*"
}
```

**Error: Region not enabled**
Ensure the regions you selected in CloudDash are enabled in your AWS account under **Account Settings > Regions**.

### Verification

After fixing, click **Re-verify** in CloudDash. A green "Active" status confirms the integration works. Metrics begin flowing within 5 minutes.

---

<!-- KB-010 -->
## CloudDash Alerts Not Firing — General Troubleshooting

**Article ID:** KB-010 | **Category:** troubleshooting | **Tags:** alerts, not-firing, notification, configuration | **Plans:** All | **Updated:** 2026-04-18

### Step 1 — Check Alert Status

Navigate to **Alerts > Alert List**. Each alert shows one of:
- **OK** — metric is within threshold (alert correctly not firing).
- **Alerting** — threshold crossed (notification should be sending).
- **No Data** — no metric data received for the evaluation window.
- **Error** — query is invalid or metric name is wrong.

### Step 2 — "No Data" state

See **KB-007** if this follows an AWS credential change.

Otherwise:
1. Verify the agent is running: `sudo systemctl status clouddash-agent`.
2. Check `/var/log/clouddash/agent.log` for connectivity errors.
3. Confirm `ingest.clouddash.io:443` is reachable: `curl -v https://ingest.clouddash.io/ping`.

### Step 3 — "Alerting" but no notification received

1. Go to **Settings > Notification Channels** and click **Test** on each channel.
2. Verify the channel is attached to the alert: open alert > **Notification Channels** tab.
3. Check spam/junk folders for email channels.
4. For Slack: ensure the webhook is still valid (Slack webhooks expire if the app is removed).
5. For PagerDuty: verify the Integration Key matches the correct PagerDuty service.

### Step 4 — Alert evaluation window

Alerts evaluate on a fixed schedule, not instantly. If the threshold is breached for less than one full evaluation window, the alert does not fire.

- Change evaluation window from 1-minute to 5-minute for bursty metrics to reduce noise.
- Use **Multi-condition alerts** to require the threshold to be breached for N consecutive windows.

---

<!-- KB-011 -->
## Dashboard Shows "No Data Available"

**Article ID:** KB-011 | **Category:** troubleshooting | **Tags:** dashboard, no-data, empty, panels | **Plans:** All | **Updated:** 2026-03-30

### Causes and Fixes

**Cause 1: Time range contains no data**
- The selected time range predates your first agent check-in, or is in the future.
- Fix: Change the time range to **Last 1 Hour**.

**Cause 2: Agent is not reporting**
- Go to **Status > Infrastructure**. If no hosts appear, the agent is not sending data.
- Fix: Restart the agent: `sudo systemctl restart clouddash-agent`.
- Check logs: `sudo journalctl -u clouddash-agent -n 50`.

**Cause 3: Dashboard variables not set**
- Variables like `$host` or `$environment` filter all panels. If unset or set to a value with no data, all panels show empty.
- Fix: Click the variable dropdowns at the top of the dashboard and select valid values.

**Cause 4: Cloned dashboard with stale variable defaults**
- Cloned dashboards inherit variable defaults from the original.
- Fix: Go to **Dashboard Settings > Variables** and update defaults to match your environment.

**Cause 5: Metric name mismatch after agent version upgrade**
- Agent 3.x renamed some metrics (e.g., `system.cpu.percent` → `system.cpu.usage`).
- Fix: Use **Metrics > Browse** to find the current metric name and update panel queries.

---

<!-- KB-012 -->
## SSO SAML Integration Troubleshooting

**Article ID:** KB-012 | **Category:** troubleshooting | **Tags:** sso, saml, okta, azure-ad, login, authentication | **Plans:** Pro, Enterprise | **Updated:** 2026-05-01

### Common SSO Errors and Fixes

| Error | Cause | Resolution |
|-------|-------|-----------|
| `invalid_signature` | IdP certificate mismatch | Re-download SP metadata from CloudDash; reconfigure IdP with fresh metadata |
| `user_not_provisioned` | User not assigned to the SAML app in IdP | Add user to the CloudDash SAML application in your IdP |
| `attribute_missing: email` | Email attribute not mapped in IdP | Add `email` attribute mapping in IdP SAML app configuration |
| `sso_not_enabled` | SSO configured but toggle is off | Go to **Settings > Security > SSO** and enable the toggle |
| `session_expired` | SAML assertion lifetime too short | Set `SessionNotOnOrAfter` to at least 8 hours in your IdP |
| `audience_restriction_mismatch` | Audience URI doesn't match | Set Audience URI to the Entity ID shown in CloudDash SP metadata |

### Okta-Specific Setup

1. In Okta: **Applications > Create App Integration > SAML 2.0**.
2. Single Sign-On URL: `https://app.clouddash.io/auth/saml/callback`
3. Audience URI: `https://app.clouddash.io/auth/saml`
4. Attribute statements: `email` → `user.email`, `firstName` → `user.firstName`, `lastName` → `user.lastName`
5. Download Okta IdP metadata XML and upload to CloudDash.

### Azure AD (Microsoft Entra ID) Specific Setup

1. In Azure AD: **Enterprise Applications > New Application > Create your own application > Integrate with SAML**.
2. Reply URL: `https://app.clouddash.io/auth/saml/callback`
3. Identifier: `https://app.clouddash.io/auth/saml`
4. Add user attributes: `user.mail`, `user.givenname`, `user.surname`.
5. Download Federation Metadata XML and upload to CloudDash.

### Testing SSO Before Enforcing

Always click **Test SSO** in CloudDash before enabling **Enforce SSO**. If the test succeeds, a confirmation banner appears. If you accidentally get locked out, contact support@clouddash.io with your organisation name and Owner email — manual unlock takes up to 2 business hours.

---

<!-- KB-013 -->
## CloudDash Agent Reporting Offline

**Article ID:** KB-013 | **Category:** troubleshooting | **Tags:** agent, offline, connectivity, firewall | **Plans:** All | **Updated:** 2026-04-08

### Diagnostic Steps

**Step 1: Check agent process**
```bash
sudo systemctl status clouddash-agent
# Should show: Active (running)
```

If stopped: `sudo systemctl start clouddash-agent`

**Step 2: Check agent version**
```bash
clouddash-agent --version
```
Agent versions below 2.8 are end-of-life and will report as offline. Upgrade:
```bash
curl -sSL https://install.clouddash.io/upgrade | bash
```

**Step 3: Verify API key**
```bash
clouddash-agent check --api-key YOUR_API_KEY
```
A `key_valid: true` response confirms the key is active.

**Step 4: Check network connectivity**
```bash
# DNS resolution
nslookup ingest.clouddash.io

# TLS connectivity
curl -v https://ingest.clouddash.io/ping
# Expected: {"status":"ok"}
```

If `curl` fails:
- Ensure port 443 outbound is open.
- Check if a proxy is required: set `HTTP_PROXY` and `HTTPS_PROXY` in `/etc/clouddash/agent.conf`.
- Check if mTLS inspection is stripping the certificate — add CloudDash CA cert to your trust store.

**Step 5: Review agent logs**
```bash
sudo journalctl -u clouddash-agent -n 100 --no-pager
# Or:
sudo tail -100 /var/log/clouddash/agent.log
```
Look for: `connection refused`, `certificate verify failed`, `api_key_invalid`.
