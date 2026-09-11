"""Track the failure boundary of a tenant onboarding agent."""

from __future__ import annotations

import argparse
import traceback
import uuid
from dataclasses import dataclass
from typing import Protocol

from infrai_client import InfraiClient


@dataclass(frozen=True)
class OnboardingRequest:
    tenant_id: str
    account_id: str
    admin_email: str


@dataclass(frozen=True)
class OnboardingResult:
    tenant_id: str
    account_status: str
    agent_ran: bool
    failure_captured: bool


class Agent(Protocol):
    def provision(self, request: OnboardingRequest) -> None:
        """Provision the tenant resources represented by the request."""


class DemoProvisioningAgent:
    def provision(self, request: OnboardingRequest) -> None:
        print(f"Provisioned admin access for {request.admin_email}")


def onboard_tenant(
    request: OnboardingRequest,
    agent: Agent,
    infrai: InfraiClient,
) -> OnboardingResult:
    """Run provisioning when enabled and capture a failed account transition."""
    enabled = infrai.is_enabled("tenant-onboarding-agent", default_value=False)
    if not enabled:
        return OnboardingResult(request.tenant_id, "pending_manual_review", False, False)

    try:
        agent.provision(request)
    except Exception:
        operation_id = f"onboarding-{request.tenant_id}-{request.account_id}"
        infrai.capture_exception(traceback.format_exc(), operation_id)
        return OnboardingResult(request.tenant_id, "onboarding_failed", True, True)

    return OnboardingResult(request.tenant_id, "active", True, False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one tenant onboarding decision")
    parser.add_argument("--tenant-id", default=lambda: str(uuid.uuid4()))
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--admin-email", required=True)
    args = parser.parse_args()
    tenant_id = args.tenant_id() if callable(args.tenant_id) else args.tenant_id
    result = onboard_tenant(
        OnboardingRequest(tenant_id, args.account_id, args.admin_email),
        DemoProvisioningAgent(),
        InfraiClient.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
