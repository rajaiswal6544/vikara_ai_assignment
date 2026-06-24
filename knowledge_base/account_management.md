# CloudDash — Account and Access Management Guide

<!-- KB-024 -->
## Role-Based Access Control (RBAC) Configuration

**Article ID:** KB-024 | **Category:** account | **Tags:** rbac, roles, permissions, access-control, users | **Plans:** All | **Updated:** 2026-04-25

### Built-In Roles

| Permission | Viewer | Editor | Admin | Owner |
|-----------|--------|--------|-------|-------|
| View dashboards | ✓ | ✓ | ✓ | ✓ |
| Create / edit dashboards | ✗ | ✓ | ✓ | ✓ |
| Create / edit alerts | ✗ | ✓ | ✓ | ✓ |
| Manage notification channels | ✗ | ✗ | ✓ | ✓ |
| Manage integrations | ✗ | ✗ | ✓ | ✓ |
| Invite / remove users | ✗ | ✗ | ✓ | ✓ |
| Configure SSO | ✗ | ✗ | ✓ | ✓ |
| View / manage billing | ✗ | ✗ | ✗ | ✓ |
| Transfer ownership | ✗ | ✗ | ✗ | ✓ |
| Delete organisation | ✗ | ✗ | ✗ | ✓ |

### Assigning and Changing Roles

1. Navigate to **Settings > Team**.
2. Click the role badge next to any team member.
3. Select the new role from the dropdown.
4. The change takes effect immediately.

**Notes:**
- Only the Owner can assign or remove the Admin role.
- You cannot demote the Owner — transfer ownership first (see KB-025).
- There is exactly one Owner per organisation.

### Team-Level Access (Pro / Enterprise)

Pro and Enterprise plans support **Teams** for finer-grained access:
1. Create a team: **Settings > Teams > New Team**.
2. Add members to the team.
3. Assign dashboards, alert groups, or environments to the team.
4. Members only see resources assigned to their teams.

This is useful for large organisations with multiple product or geographic teams.

---

<!-- KB-025 -->
## Transferring Account Ownership

**Article ID:** KB-025 | **Category:** account | **Tags:** ownership, transfer, admin, account-management | **Plans:** All | **Updated:** 2026-03-20

Each CloudDash organisation has exactly one Owner who has billing access and can delete the organisation. Ownership can be transferred to any existing Admin.

### Steps to Transfer Ownership

1. Go to **Settings > Organisation > Transfer Ownership**.
2. Select the Admin user who will become the new Owner.
3. Enter your current account password to confirm.
4. Click **Transfer**.

The transfer is **immediate and irreversible** without the cooperation of the new Owner. The previous Owner is downgraded to Admin automatically.

### Before Transferring

- Ensure the target user has successfully logged in and set up their account.
- If SSO is enforced, ensure the new Owner can authenticate via SSO.
- Inform your billing team — the new Owner will receive all billing notifications.

---

<!-- KB-026 -->
## SSO Setup — Full Configuration Guide

**Article ID:** KB-026 | **Category:** account | **Tags:** sso, saml, okta, azure-ad, google-workspace, onelogin | **Plans:** Pro, Enterprise | **Updated:** 2026-05-01

CloudDash supports SAML 2.0 with any compliant Identity Provider (IdP), including Okta, Azure Active Directory (Microsoft Entra ID), Google Workspace, and OneLogin.

### Step-by-Step SSO Setup

**Step 1: Download CloudDash SP Metadata**
1. Go to **Settings > Security > Single Sign-On**.
2. Click **Download SP Metadata XML** — this file contains the Entity ID, ACS URL, and certificate.

**Step 2: Configure Your IdP**

*Okta:*
- Create a new SAML 2.0 app in Okta.
- Single Sign-On URL (ACS): `https://app.clouddash.io/auth/saml/callback`
- Audience URI (Entity ID): `https://app.clouddash.io/auth/saml`
- Attribute statements: `email` → `user.email`, `firstName` → `user.firstName`, `lastName` → `user.lastName`
- Optional role mapping: `role` → `user.role` (values: `viewer`, `editor`, `admin`)

*Azure AD / Microsoft Entra ID:*
- Create Enterprise Application > SAML.
- Reply URL: `https://app.clouddash.io/auth/saml/callback`
- Identifier: `https://app.clouddash.io/auth/saml`
- Attribute claims: `user.mail`, `user.givenname`, `user.surname`

*Google Workspace:*
- Admin Console > Apps > Web and Mobile Apps > Add Custom SAML App.
- ACS URL: `https://app.clouddash.io/auth/saml/callback`
- Entity ID: `https://app.clouddash.io/auth/saml`
- Attribute mappings: `Primary Email` → `email`

**Step 3: Upload IdP Metadata to CloudDash**
1. Download the IdP metadata XML from your IdP.
2. Upload it in CloudDash under **Settings > Security > SSO > Upload IdP Metadata**.
3. Click **Test SSO** — a new tab opens to run a test login flow.
4. If the test succeeds, toggle **Enable SSO**.

**Step 4 (Optional): Enforce SSO**
- Enabling **Enforce SSO** disables password-based login for all users.
- All users must authenticate via your IdP.
- **Warning:** Ensure at least two Admins can authenticate via SSO before enforcing. If you get locked out, contact support@clouddash.io.

### Just-In-Time (JIT) Provisioning

When SSO is enabled, users who authenticate via your IdP are automatically provisioned in CloudDash if they don't already have an account. Their role defaults to **Viewer** unless a `role` attribute is mapped in your IdP.

For SSO troubleshooting, see **KB-012**.

---

<!-- KB-027 -->
## Audit Logs — Access and Interpretation

**Article ID:** KB-027 | **Category:** account | **Tags:** audit-logs, compliance, security, access-history | **Plans:** Starter, Pro, Enterprise | **Updated:** 2026-04-12

### What Is Logged

CloudDash captures all administrative actions in the Audit Log:

| Action Category | Logged Events |
|----------------|--------------|
| User management | Invite sent, user joined, role changed, user removed |
| Authentication | Successful login, failed login attempt, SSO login, API key used |
| Integrations | Integration added, updated, deleted, verification failed |
| Dashboards | Dashboard created, cloned, deleted, shared publicly |
| Alerts | Alert created, threshold changed, muted, deleted |
| Billing | Plan changed, payment method updated, invoice downloaded |
| Security | SSO configured, SSO enforced, API key created/revoked |

### Accessing Audit Logs

1. Navigate to **Settings > Organisation > Audit Log**.
2. Use the date range filter to narrow down events.
3. Filter by user, action type, or resource.
4. Export to CSV for compliance reporting.

### Retention Periods

| Plan | Audit Log Retention |
|------|-------------------|
| Free | Not available |
| Starter | 30 days |
| Pro | 90 days |
| Enterprise | 365 days |

### Audit Log Format (API)

```
GET /api/v2/audit/events?from=2026-04-01&to=2026-04-30
```

```json
{
  "events": [
    {
      "id": "evt_abc123",
      "timestamp": "2026-04-15T10:22:31Z",
      "actor": {
        "user_id": "usr_xyz",
        "email": "admin@example.com",
        "name": "Jane Smith"
      },
      "action": "integration.updated",
      "resource": {"type": "integration", "id": "int_aws_prod"},
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0 ...",
      "details": {"field": "aws_region", "old": "us-east-1", "new": "us-east-1,eu-west-1"}
    }
  ],
  "total": 1,
  "page": 1
}
```

---

<!-- KB-028 -->
## Managing and Exporting Your Data

**Article ID:** KB-028 | **Category:** account | **Tags:** data-export, gdpr, data-management, retention, deletion | **Plans:** All | **Updated:** 2026-04-20

### Exporting Metrics and Dashboard Data

1. Go to **Settings > Data Export**.
2. Select the data type: **Metrics**, **Alert Events**, or **Audit Logs**.
3. Set a date range (limited to your plan's retention window).
4. Choose format: **CSV**, **JSON**, or **Parquet** (Enterprise only).
5. Click **Generate Export** — you'll receive a download link via email within 15 minutes.

**Continuous export to S3 (Pro / Enterprise):**
1. Go to **Settings > Data Export > Continuous Export**.
2. Provide an S3 bucket ARN and a CloudDash-assume-able IAM role.
3. Choose export frequency: hourly or daily.
4. Data is delivered as gzip-compressed JSON.

### Data Deletion

CloudDash automatically purges data beyond your plan's retention window on a daily basis.

**Immediate deletion of specific data:**
- You cannot selectively delete individual metric time series via the UI.
- Enterprise customers can request bulk deletion via their CSM.

**Account-level deletion:**
1. Go to **Settings > Organisation > Danger Zone > Delete Organisation**.
2. Type your organisation name to confirm.
3. All data is permanently deleted within 30 days.
4. This action is irreversible.

### GDPR / Data Privacy Requests

For GDPR data subject access requests or right-to-erasure requests:
- Email privacy@clouddash.io with the subject line "Data Subject Request".
- Include your account email and the specific data request.
- We respond within 30 days as required by GDPR.
