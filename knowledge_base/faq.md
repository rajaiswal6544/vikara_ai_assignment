# CloudDash — Frequently Asked Questions

<!-- KB-001 -->
## How Do I Reset My API Key?

**Article ID:** KB-001 | **Category:** faq | **Tags:** api-key, reset, authentication | **Plans:** All | **Updated:** 2026-04-10

If your API key has been compromised or you simply need a fresh key:

1. Log in to your CloudDash account and navigate to **Settings > API Keys**.
2. Locate the key you want to rotate and click the **…** (more) menu.
3. Select **Revoke Key** — this immediately invalidates the old key.
4. Click **+ New API Key**, give it a descriptive name, and choose a scope (Read-Only or Read-Write).
5. Copy the key immediately — it will not be shown again.
6. Update all services, agents, and scripts that used the old key.

**Note:** Revoking an API key is instant and permanent. Any service still using the revoked key will receive `401 Unauthorized` responses until updated.

---

<!-- KB-002 -->
## What Cloud Providers Does CloudDash Support?

**Article ID:** KB-002 | **Category:** faq | **Tags:** cloud-providers, aws, gcp, azure, integrations | **Plans:** All | **Updated:** 2026-03-20

CloudDash currently supports monitoring across three major cloud providers:

**Amazon Web Services (AWS)**
- Compute: EC2, Lambda, ECS, EKS, Fargate
- Storage: S3, EBS, EFS
- Databases: RDS, DynamoDB, ElastiCache, Redshift
- Networking: CloudFront, ALB, NLB, API Gateway
- Serverless: Lambda, Step Functions

**Google Cloud Platform (GCP)**
- Compute: Compute Engine, Cloud Run, GKE, App Engine
- Storage: Cloud Storage, Persistent Disk
- Databases: Cloud SQL, BigQuery, Firestore, Cloud Spanner
- Networking: Cloud Load Balancing, Cloud CDN

**Microsoft Azure**
- Compute: Virtual Machines, AKS, Azure Functions, Container Instances
- Storage: Blob Storage, Azure Files, Managed Disks
- Databases: Azure SQL, Cosmos DB, Cache for Redis
- Networking: Application Gateway, Azure CDN, Traffic Manager

Multi-cloud unified dashboards allow side-by-side comparison across all three providers. Does CloudDash support integration with Datadog for cross-platform alerting? Currently, CloudDash does not have a native Datadog integration. Cross-platform alerting between CloudDash and Datadog is not supported as a built-in feature. If you need this capability, please submit a feature request via **Settings > Feedback** or ask our support team to escalate to the product team on your behalf.

---

<!-- KB-003 -->
## How Do I Invite Team Members?

**Article ID:** KB-003 | **Category:** faq | **Tags:** team, invite, users, collaboration | **Plans:** All | **Updated:** 2026-04-01

**To invite a new team member:**

1. Navigate to **Settings > Team > Invite Member**.
2. Enter the member's email address.
3. Select their role:
   - **Viewer** — can view dashboards and alerts (read-only).
   - **Editor** — can create and edit dashboards and alerts.
   - **Admin** — full access except billing.
4. Optionally restrict access to specific teams or environments (Pro/Enterprise only).
5. Click **Send Invitation**.

The invitee receives an email with a sign-up link valid for **7 days**. If the link expires, you can resend from **Settings > Team > Pending Invitations**.

**Seat limits by plan:**
| Plan | Max Users |
|------|-----------|
| Free | 3 |
| Starter | 10 |
| Pro | 50 |
| Enterprise | Unlimited |

---

<!-- KB-004 -->
## What Are the CloudDash Plan Tiers?

**Article ID:** KB-004 | **Category:** faq | **Tags:** plans, pricing, tiers, features | **Plans:** All | **Updated:** 2026-05-01

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Monthly price | $0 | $49 | $299 | Custom |
| Annual price | $0 | $470 | $2,870 | Custom |
| Monitored hosts | 5 | 25 | 200 | Unlimited |
| Data retention | 7 days | 30 days | 90 days | Up to 365 days |
| Alerts | 3 | 50 | Unlimited | Unlimited |
| Notification channels | 1 | 5 | Unlimited | Unlimited |
| API access | ✗ | Read-only | Full | Full |
| SSO / SAML | ✗ | ✗ | ✓ | ✓ |
| Audit logs | ✗ | 30 days | 90 days | 365 days |
| SLA | ✗ | ✗ | 99.9% | 99.99% + dedicated |

Annual billing saves 20% on Starter and Pro plans. Enterprise pricing is based on host count, retention, and support tier — contact sales@clouddash.io.

---

<!-- KB-005 -->
## How Do I Install the CloudDash Agent?

**Article ID:** KB-005 | **Category:** faq | **Tags:** agent, installation, setup, onboarding | **Plans:** All | **Updated:** 2026-04-15

**Linux (Debian / Ubuntu):**
```bash
curl -sSL https://install.clouddash.io | bash -s -- --api-key YOUR_API_KEY
```

**Linux (RHEL / CentOS / Amazon Linux):**
```bash
curl -sSL https://install.clouddash.io | bash -s -- --api-key YOUR_API_KEY --pkg-manager yum
```

**Docker Compose:**
```yaml
services:
  clouddash-agent:
    image: clouddash/agent:latest
    environment:
      - CLOUDDASH_API_KEY=YOUR_API_KEY
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
```

**Windows (PowerShell, run as Administrator):**
```powershell
Invoke-WebRequest -Uri https://install.clouddash.io/windows -OutFile install.ps1
.\install.ps1 -ApiKey YOUR_API_KEY
```

After installation, the agent appears in **Status > Infrastructure** within 2 minutes. The agent reports metrics every 15 seconds by default.

---

<!-- KB-006 -->
## Does CloudDash Support Datadog Integration for Cross-Platform Alerting?

**Article ID:** KB-006 | **Category:** faq | **Tags:** datadog, integration, third-party, feature-request | **Plans:** Pro, Enterprise | **Updated:** 2026-05-10

CloudDash does **not** currently support a native integration with Datadog for cross-platform alerting. This means:

- You cannot forward CloudDash alerts directly into Datadog.
- You cannot pull Datadog metrics into CloudDash dashboards.
- There is no shared alert correlation between the two platforms.

**Alternatives available today:**
1. **PagerDuty or OpsGenie:** Both CloudDash and Datadog can route alerts to a shared on-call platform, achieving functional cross-platform alerting through a common sink.
2. **Webhooks:** CloudDash can send alert payloads to a custom webhook endpoint. You can build a lightweight relay that forwards these to Datadog's Events API.
3. **Feature Request:** If this integration is important to you, submit a feature request via **Settings > Feedback**. Requests with high customer votes are prioritized for our integration roadmap. Our support team can also escalate your request directly to the product team.
