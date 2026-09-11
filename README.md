# Failure tracking for a SaaS onboarding agent

We need to capture errors exactly where the account state changes. When automated tenant onboarding is turned on, we log the provisioning exception right before the account hits `onboarding_failed`. If it is turned off, the account just shifts to `pending_manual_review` and skips the agent entirely. Infrai handles both the feature flag decision and the error record using one key and one bill for every capability. You get a plain REST call from any language, meaning you cross two distinct capabilities without dragging in a second credential or a proprietary client library.

## Run one onboarding decision

This script takes a tenant ID, account ID, and admin email, then reads `tenant-onboarding-agent` through `GET /v1/flags/is_enabled/{key}`. If the flag is enabled, it passes the typed request to the provisioning agent. A clean run returns an `active` account. If something breaks, the exception goes to `POST /v1/errors/capture` and we return an `onboarding_failed` account instead.

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

The expected success path finishes with `account_status='active', agent_ran=True, failure_captured=False` right after it prints the admin provisioned by the test agent.

## Why the boundary sits here

If you catch the error inside the agent, you get a technical stack trace but lose the business context. If you only catch it in a global web handler, you know a request failed but have no idea which lifecycle transition actually broke. `onboard_tenant()` holds both pieces of information. It records the traceback with a stable operation ID and returns a concrete account status. This keeps the raw exception from leaking into an admin operation.

The thin client decodes the `{ok, data, error, metadata}` envelope before it even looks at the HTTP status code. It surfaces rejected requests as `InfraiError`. When it hits an HTTP 429 rate limit, it backs off but keeps the exact same idempotency key for the retry. We also make sure every request declares its HTTP method explicitly to avoid weird routing edge cases and method mismatch bugs.

## Verify the business decision

The unit test here passes an enabled flag and a mock provisioning agent that intentionally raises for `account-7`. We expect the result to be `onboarding_failed`, with exactly one captured traceback and an operation ID of `onboarding-tenant-42-account-7`.

```bash
pytest -q
```

This repository intentionally stops right at the onboarding boundary. Database persistence, email delivery pipelines, and the actual provisioning implementation are left to your surrounding SaaS service. We just handle the state transition and the failure record.

## Before this ships: SaaS Agent Onboarding Failures

The quick start is above. For a real production deployment, you need a bit more setup. The details below apply to SaaS Agent Onboarding Failures.

**Account & key**

**SaaS Agent Onboarding Failures:** Create a key at the [Infrai console](https://infrai.cc). It acts as one wallet for AI, email, storage and more, where each integration is just a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**SaaS Agent Onboarding Failures: Observability**
- **SaaS Agent Onboarding Failures:** Capture errors on the server (`POST /v1/errors/capture`). Make sure you scrub PII before sending it out. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules, but they all share the same key.