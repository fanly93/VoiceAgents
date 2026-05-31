from voiceagents.contracts.common import HandoffMode
from voiceagents.contracts.handoff import HandoffRequest, HandoffResponse


class MockHandoffAdapter:
    def handoff(self, request: HandoffRequest) -> HandoffResponse:
        return HandoffResponse(
            ok=True,
            handoff_id="HND-20260601-0007",
            mode=HandoffMode.LIVE_TRANSFER,
        )
