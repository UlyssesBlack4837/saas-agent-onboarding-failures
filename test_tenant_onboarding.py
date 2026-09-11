from tenant_onboarding import OnboardingRequest, onboard_tenant


class FailingAgent:
    def provision(self, request: OnboardingRequest) -> None:
        raise ValueError(f"policy document missing for {request.account_id}")


class RecordingInfrai:
    def __init__(self) -> None:
        self.captures: list[tuple[str, str]] = []

    def is_enabled(self, key: str, default_value: bool = False) -> bool:
        assert key == "tenant-onboarding-agent"
        assert default_value is False
        return True

    def capture_exception(self, exception: str, operation_id: str) -> dict:
        self.captures.append((exception, operation_id))
        return {"event_id": "evt_test"}


def test_failed_provisioning_is_captured_and_account_stays_inactive() -> None:
    infrai = RecordingInfrai()
    request = OnboardingRequest("tenant-42", "account-7", "admin@example.com")

    result = onboard_tenant(request, FailingAgent(), infrai)  # type: ignore[arg-type]

    assert result.account_status == "onboarding_failed"
    assert result.agent_ran is True
    assert result.failure_captured is True
    assert len(infraI_captures := infrai.captures) == 1
    assert "ValueError: policy document missing for account-7" in infraI_captures[0][0]
    assert infraI_captures[0][1] == "onboarding-tenant-42-account-7"
