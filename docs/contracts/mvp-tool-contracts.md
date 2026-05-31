# MVP Tool Contracts

These contracts define the minimum tool boundary for the VoiceAgents phone-channel MVP. They are implementation contracts, not final production APIs.

## `lookup_order`

Input:

```json
{
  "merchant_id": "merchant_demo",
  "order_id": "ORD-20260601-1842"
}
```

Output:

```json
{
  "ok": true,
  "order_exists": true,
  "status": "paid",
  "user_summary": "Order ORD-20260601-1842 has been paid.",
  "safe_fields": {
    "order_status": "paid"
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
  "order_id": "ORD-20260601-1842"
}
```

Output:

```json
{
  "ok": true,
  "status": "in_transit",
  "latest_event": "Package departed the Shanghai Hongqiao sorting center.",
  "estimated_delivery": "2026-06-02",
  "carrier": "YTO Express",
  "user_summary": "Your package is in transit with YTO Express and is estimated to arrive on 2026-06-02."
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
  "locale": "zh-CN",
  "query": "LunaCare 假发护理套装应该怎么清洗假发？"
}
```

Output:

```json
{
  "ok": true,
  "short_answer": "Use cool water and a small amount of wig-safe shampoo. Do not twist the hair. Let it air dry on a stand.",
  "citations": ["faq:lunacare-wig-washing"],
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
  "call_id": "CALL-20260601-0901",
  "merchant_id": "merchant_demo",
  "intent_primary": "logistics_tracking",
  "order_id_candidate": "ORD-20260601-1842",
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
