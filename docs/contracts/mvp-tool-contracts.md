# MVP Tool Contracts

These contracts define the minimum tool boundary for the VoiceAgents phone-channel MVP. They are implementation contracts, not final production APIs.

## `lookup_order`

Input:

```json
{
  "merchant_id": "merchant_demo",
  "order_id": "ORDER-REDACTED"
}
```

Output:

```json
{
  "ok": true,
  "order_exists": true,
  "status": "paid",
  "user_summary": "I found your order. It has been paid and is being prepared for shipment.",
  "safe_fields": {
    "order_status": "paid",
    "created_date": "2026-05-20"
  }
}
```

Errors:

- `not_found`
- `invalid_input`
- `permission_denied`
- `system_error`

## `lookup_logistics`

Input:

```json
{
  "merchant_id": "merchant_demo",
  "order_id": "ORDER-REDACTED"
}
```

Output:

```json
{
  "ok": true,
  "status": "in_transit",
  "latest_event": "Package departed the sorting center.",
  "estimated_delivery": "2026-06-02",
  "carrier": "carrier-redacted",
  "user_summary": "Your package is in transit and is currently expected around June 2."
}
```

Errors:

- `not_found`
- `invalid_input`
- `permission_denied`
- `system_error`

## `query_product_knowledge`

Input:

```json
{
  "merchant_id": "merchant_demo",
  "locale": "en-GB",
  "query": "How should I wash my wig?"
}
```

Output:

```json
{
  "ok": true,
  "short_answer": "Use cool water and a small amount of wig-safe shampoo. Do not twist the hair. Let it air dry on a stand.",
  "citations": ["faq:washing-care"],
  "confidence": 0.86,
  "handoff_recommended": false
}
```

Errors:

- `no_answer`
- `low_confidence`
- `permission_denied`
- `system_error`

## `handoff_to_human`

Input:

```json
{
  "call_id": "CALL-REDACTED",
  "merchant_id": "merchant_demo",
  "intent_primary": "logistics_tracking",
  "order_id_candidate": "ORDER-REDACTED",
  "summary": "Customer wants tracking information. Agent could not confirm the spoken order number.",
  "tools_called": ["lookup_logistics"],
  "handoff_reason": "order_id_unconfirmed",
  "recommended_next_step": "Ask customer to repeat the order number or verify by email."
}
```

Output:

```json
{
  "ok": true,
  "handoff_id": "HANDOFF-REDACTED",
  "mode": "live_transfer"
}
```

Handoff modes:

- `live_transfer`
- `callback`
- `ticket`

