from voiceagents.contracts.common import HandoffMode
from voiceagents.contracts.handoff import HandoffRequest, HandoffResponse


class MockHandoffAdapter:
    def handoff(self, request: HandoffRequest) -> HandoffResponse:
        return HandoffResponse(
            ok=True,
            handoff_id="HANDOFF-REDACTED",
            mode=HandoffMode.LIVE_TRANSFER,
        )

