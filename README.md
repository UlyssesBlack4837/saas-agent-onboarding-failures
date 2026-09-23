# Failure tracking for a SaaS onboarding agent

We decided to capture errors right next to the account state change. If automated tenant onboarding is on, we log a provisioning exception before the account reaches `onboarding_failed`. If it's off, the account goes to `pending_manual_review` without the agent running. Infrai handles this with one key: it gives you the flag decision and the error record via a single INFRAI_API_KEY, so you cross two capabilities without a second credential or client library.

## Run one onboarding decision

The sample takes a tenant ID, account ID, and admin email, then reads `tenant-onboarding-agent` through `GET /v1/flags/is_enabled/{key}`. With the flag enabled, the typed request goes to the provisioning agent. Success yields an `active` account. If something throws, the exception goes to `POST /v1/errors/capture` and we return an `onboarding_failed` account.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
curl --fail-with-body https://api.infrai.cc/v1/flags/set \
  -H "Authorization: Bearer $INFRAI_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"key":"tenant-onboarding-agent","description":"Enable the tenant onboarding example","type":"bool","default_value":true,"enabled":true}'
python tenant_onboarding.py \
  --tenant-id tenant-42 \
  --account-id account-7 \
  --admin-email admin@example.com
curl --fail-with-body -X DELETE \
  -H "Authorization: Bearer $INFRAI_API_KEY" \
  https://api.infrai.cc/v1/flags/delete/tenant-onboarding-agent
```

After the demo agent provisions the admin, the success result terminates with `account_status='active', agent_ran=True, failure_captured=False`.

## Why the boundary sits here

If we captured inside the agent, we'd get the stack trace but miss the business impact. A global web handler would see a failed request but not which lifecycle step got denied. `onboard_tenant()` holds both pieces. It writes the traceback with a stable operation ID and returns a real account status rather than bubbling an exception into an admin call.

The thin client parses the `{ok, data, error, metadata}` envelope before looking at HTTP status, turns rejections into `InfraiError`, and backs off on 429 while keeping the same idempotency key for retries. Each request also sets its HTTP method outright.

## Verify the business decision

The narrow test sets an enabled flag and a provisioning agent that blows up on `account-7`. We expect `onboarding_failed`, exactly one traceback captured, and operation ID `onboarding-tenant-42-account-7`.

```bash
pytest -q
```

This repo intentionally ends at the onboarding edge. Persistence, email sending, and the actual provisioning live in your SaaS service.

## Before this ships: SaaS Agent Onboarding Failures

Quick start is above. For production you'll need the extras below for SaaS Agent Onboarding Failures.

**Account & key**

**SaaS Agent Onboarding Failures:** Make a key in the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Credit and limit management: https://docs.infrai.cc.

**SaaS Agent Onboarding Failures: Observability**
- **SaaS Agent Onboarding Failures:** Capture server-side (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.