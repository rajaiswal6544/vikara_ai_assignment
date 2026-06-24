# CloudDash — Billing Policy and Pricing Guide

<!-- KB-014 -->
## Plan Tiers, Pricing, and Features

**Article ID:** KB-014 | **Category:** billing | **Tags:** plans, pricing, tiers, comparison, cost | **Plans:** All | **Updated:** 2026-05-01

### Pricing Overview

| Plan | Monthly | Annual (20% off) | Hosts | Data Retention | Key Differentiators |
|------|---------|-----------------|-------|---------------|---------------------|
| **Free** | $0 | $0 | 5 | 7 days | Basic dashboards, 3 alerts, 1 notification channel |
| **Starter** | $49 | $470/yr (~$39/mo) | 25 | 30 days | 50 alerts, 5 notification channels, email support |
| **Pro** | $299 | $2,870/yr (~$239/mo) | 200 | 90 days | Unlimited alerts, SSO, API access, all integrations, chat support |
| **Enterprise** | Custom | Custom | Unlimited | Up to 365 days | Dedicated CSM, SLA 99.99%, custom retention, PO billing |

All prices are in USD. Applicable taxes are added at checkout based on your billing country.

### Add-On Pricing (Pro and Enterprise)

| Add-On | Price |
|--------|-------|
| Additional host block (25 hosts) | $35/month |
| Extended retention (per 30 days beyond plan) | $15/month |
| Dedicated on-call support | $199/month |

---

<!-- KB-015 -->
## Plan Upgrades and Downgrades

**Article ID:** KB-015 | **Category:** billing | **Tags:** upgrade, downgrade, plan-change, proration | **Plans:** All | **Updated:** 2026-04-20

### Upgrading Your Plan

Upgrades take effect **immediately**.

**Prorated billing:** You are charged the difference between plans for the remaining days in your current billing cycle.

**Example:**
- Current plan: Starter ($49/month), 10 days remaining in cycle.
- Upgrading to Pro ($299/month).
- Proration charge: ($299 − $49) × (10/30) = **$83.33** charged today.
- From next billing cycle: full Pro price of $299/month.

**How to upgrade:**
1. Go to **Settings > Billing > Change Plan**.
2. Select the new plan.
3. Review the prorated charge shown.
4. Click **Confirm Upgrade**.

New features (additional hosts, longer retention, SSO) are available immediately after upgrade.

### Downgrading Your Plan

Downgrades take effect at the **end of the current billing period**.

- No prorated refund or credit is issued for downgrades.
- Your current plan features remain active until the billing period ends.
- Data exceeding the lower plan's retention or host limits is **not immediately deleted** — you have a **7-day grace period** to export data.
- After the grace period, data outside the new plan's limits is purged.

**How to downgrade:**
1. Go to **Settings > Billing > Change Plan**.
2. Select the lower plan.
3. Confirm. A banner confirms the downgrade date.

---

<!-- KB-016 -->
## Refund Policy

**Article ID:** KB-016 | **Category:** billing | **Tags:** refund, cancellation, money-back, policy | **Plans:** All | **Updated:** 2026-04-15

### When Refunds Are Granted

**1. New customer 14-day money-back guarantee**
If you are a new CloudDash customer and cancel within 14 days of your **first paid invoice**, you are entitled to a full refund. No questions asked. Contact support@clouddash.io with your account email and invoice number.

**2. Extended service outage**
If CloudDash experiences a verified service outage exceeding **4 consecutive hours** in a calendar month, affected customers receive a prorated service credit for the outage duration. Credits are applied automatically within 10 business days and appear on the next invoice.

**3. Billing error caused by CloudDash**
If our systems charge an incorrect amount due to a platform bug or processing error, a full refund or billing correction is issued within **5 business days**.

**4. Double charge dispute**
If you believe you have been charged twice for the same billing period, contact billing@clouddash.io immediately with your invoice numbers. We will investigate within 2 business days. If a duplicate charge is confirmed, a full refund of the duplicate amount is processed within 5 business days.

### When Refunds Are NOT Granted

- Forgetting to cancel before an automatic renewal.
- Unused features or services within an active subscription.
- Downgrades (no credit for remaining days on a higher plan).
- Disputes filed more than 90 days after the charge.
- Accounts suspended for Terms of Service violations.

### How to Request a Refund

Email billing@clouddash.io with:
- Account email address
- Invoice ID (found in **Settings > Billing > Invoice History**)
- Reason for refund request

Refunds to credit cards typically clear within **5–10 business days** depending on your card issuer.

---

<!-- KB-017 -->
## Understanding Your Invoice

**Article ID:** KB-017 | **Category:** billing | **Tags:** invoice, charges, line-items, explanation | **Plans:** All | **Updated:** 2026-04-01

### Invoice Structure

Each CloudDash invoice contains:

1. **Subscription charge** — your base plan fee for the billing period.
2. **Prorated charges** — if you upgraded mid-cycle, the difference is shown here.
3. **Add-on charges** — additional hosts, extended retention, or support add-ons.
4. **Taxes / VAT** — calculated based on your billing country and tax registration.
5. **Credits applied** — any service credits from outages or promotions.
6. **Total due** — the net amount charged to your payment method.

### Viewing Invoices

All invoices are available at **Settings > Billing > Invoice History**. Each invoice can be:
- Downloaded as a PDF.
- Sent to an additional email address (set under **Settings > Billing > Billing Contacts**).

### Adding a VAT or Tax ID

1. Go to **Settings > Billing > Tax Information**.
2. Enter your VAT registration number or GST ID.
3. Save — this appears on all future invoices. Past invoices cannot be retroactively updated.

### Invoice Disputes

If a line item on your invoice looks incorrect:
1. Gather the invoice ID and a description of the issue.
2. Email billing@clouddash.io or use the **Dispute This Charge** link on the invoice PDF.
3. We respond within 2 business days with a resolution or request for additional information.

---

<!-- KB-018 -->
## Payment Failure Resolution

**Article ID:** KB-018 | **Category:** billing | **Tags:** payment-failure, card-declined, billing, recovery | **Plans:** All | **Updated:** 2026-04-28

### What Happens When a Payment Fails

CloudDash uses a **3-attempt retry schedule:**

| Attempt | Timing | Action |
|---------|--------|--------|
| 1st | Day 0 | Automatic charge at billing date |
| 2nd | Day 3 | Automatic retry |
| 3rd | Day 7 | Automatic retry |
| Downgrade | Day 10 | Account downgraded to Free plan |

You receive an email notification after each failed attempt. After the third failure, your account is downgraded to the Free plan but **all data and settings are preserved for 30 days**.

### How to Recover Access

**Step 1: Update your payment method**
1. Go to **Settings > Billing > Payment Methods**.
2. Click **+ Add Payment Method**.
3. Enter new card details. The new card becomes the default.

**Step 2: Retry the failed charge**
1. Go to **Settings > Billing > Outstanding Balance**.
2. Click **Pay Now**. This immediately attempts the charge on your new payment method.

**Step 3: Restore your plan**
If your account was downgraded:
1. After a successful payment, go to **Settings > Billing > Change Plan**.
2. Reselect your previous plan. Data and settings are restored instantly.

### Common Causes of Payment Failure

- Card expired — update with a new card before expiry.
- Insufficient funds — contact your bank or use a different card.
- Card blocked for international transactions — CloudDash bills from Ireland; ask your bank to allow international charges.
- 3D Secure verification required — your bank requires additional authorization; complete it via the verification link in the payment failure email.

---

<!-- KB-019 -->
## Cancelling Your Subscription

**Article ID:** KB-019 | **Category:** billing | **Tags:** cancellation, cancel, subscription, off-boarding | **Plans:** All | **Updated:** 2026-03-15

### How to Cancel

1. Navigate to **Settings > Billing > Subscription**.
2. Click **Cancel Subscription**.
3. Select a cancellation reason (optional but appreciated for feedback).
4. Confirm cancellation.

**Cancellation takes effect at the end of your current billing period.** Your account remains fully functional until then.

### What Happens After Cancellation

- Your account is downgraded to the Free plan (5 hosts, 7-day retention, 3 alerts).
- Data exceeding Free plan limits is retained for **30 days**, then permanently deleted.
- Export your data before cancellation: **Settings > Data Export**.

### Cancellation Does Not Provide a Refund

Cancelling mid-cycle does not entitle you to a refund for unused days unless you are within the 14-day new customer guarantee window (see **KB-016**).

### Reactivating After Cancellation

You can reactivate a cancelled account at any time before your data is deleted:
1. Log in to your account.
2. Go to **Settings > Billing > Reactivate**.
3. Select a plan and complete payment.

All dashboards, alerts, integrations, and data (within your previous retention window) are restored.
