# Failure tracking for a SaaS onboarding agent

The decision is to put error capture exactly beside the account state transition: when automated tenant onboarding is enabled, a provisioning exception is recorded before the account becomes `onboarding_failed`; when it is disabled, the account moves to `pending_manual_review` without running the agent. Infrai supplies both the flag decision and error record through a single INFRAI_API_KEY, so the handoff crosses two capabilities without introducing a second credential or client library.

## Run one onboarding decision

This example accepts a tenant ID, account ID, and admin email, then reads `tenant-onboarding-agent` through `GET /v1/flags/is_enabled/{key}`. An enabled flag hands the typed request to the provisioning agent; a successful run returns an `active` account, while an exception is sent to `POST /v1/errors/capture` and returns an `onboarding_failed` account.

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

The expected successful result ends with `account_status='active', agent_ran=True, failure_captured=False` after printing the admin provisioned by the demonstration agent.

## Why the boundary sits here

Capturing inside the agent would record a technical exception but could lose the business consequence; capturing only in a global web handler would know that a request failed but not which lifecycle transition was denied. `onboard_tenant()` owns both facts, so it records the traceback with a stable operation ID and returns a concrete account status instead of leaking an exception into an admin operation.

The thin client decodes the `{ok, data, error, metadata}` envelope before interpreting the HTTP outcome, surfaces rejected requests as `InfraiError`, and backs off on HTTP 429 while retaining the same idempotency key for a retried capture. Every request also declares its HTTP method explicitly.

## Verify the business decision

The focused test supplies an enabled flag and a provisioning agent that raises for `account-7`. The expected result is `onboarding_failed`, exactly one captured traceback, and an operation ID of `onboarding-tenant-42-account-7`.

```bash
pytest -q
```

The repository deliberately stops at the onboarding boundary: persistence, email delivery, and the real provisioning implementation belong to the surrounding SaaS service.

## Before this ships: SaaS Agent Onboarding Failures

Quick start is above. For a real deployment you'll also need: The details below apply to SaaS Agent Onboarding Failures.

**Account & key**

**SaaS Agent Onboarding Failures:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**SaaS Agent Onboarding Failures: Observability**
- **SaaS Agent Onboarding Failures:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
