# Autoplan Review: OpenAI Realtime 真实语音接入 MVP

Status: REVIEWED_WITH_PLAN_FIXES
Date: 2026-05-30
Branch: `feat/openai-realtime-voice-mvp`

Reviewed artifacts:

- `docs/specs/voiceagents-openai-realtime-voice-mvp.md`
- `docs/specs/voiceagents-openai-realtime-voice-mvp-tasks.md`

## Summary

本轮 autoplan/review 结论：产品范围合理，可以继续推进为内部研发测试阶段的真实语音 MVP，但实现前必须把安全边界、日志脱敏边界、浏览器失败路径和 provider adapter 可测试性写进 spec/tasks。

已按 review 结论直接修订 spec/tasks。当前仍不进入实现，下一步应由用户批准修订后的 spec/tasks/review，再进入逐 task 开发。

## Scope Verdict

IN SCOPE:

- 浏览器麦克风 + OpenAI Realtime WebRTC。
- 真实 OpenAI Realtime provider。
- 继续使用现有 `tool_call_token` / tool relay。
- 结构化事件 JSONL 与脱敏 transcript JSONL。
- 研发测试面板 `/realtime-test`。
- 订单、物流、商品知识、转人工工具调用链路。

OUT OF SCOPE:

- telephony、Twilio、SIP、真实电话接入。
- raw audio 存储。
- 未脱敏 transcript 存储。
- SaaS 商家配置、知识库后台、客服后台接入。
- DashScope、火山云等其他真实 provider 实现。
- provider 选择 UI、provider fallback、成本对比。

## Review Findings

| Severity | Finding | Decision | Plan Fix |
|---|---|---|---|
| Blocking | `/v1/realtime/client-secret` 会返回付费 provider ephemeral secret，缺少 MVP 访问门禁。 | 必须修 | spec 增加 `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS`、same-origin/localhost、限流、403 不创建 session；tasks 增加 Task 2.0。 |
| Blocking | 原始 transcript 可能通过 structured event JSONL 泄漏。 | 必须修 | spec 要求 `text` 仅作为 ingest 输入，持久化前转为 `text_redacted`；tasks 增加 Task 3.6。 |
| High | tool-call arguments 可能包含 PII，未纳入日志/DOM 脱敏规则。 | 必须修 | spec/tasks 要求 `tool_call.requested` 只保存 tool name、call id、状态、延迟、脱敏 safe summary。 |
| High | Phase 4 对 WebRTC 的验证偏静态，覆盖不了权限、SDP、清理、重连。 | 必须修 | tasks 增加 Task 4.8 和 Task 5.7，手动或 fake media 覆盖失败路径。 |
| High | OpenAI browser adapter 放在 HTML 内会削弱 provider-neutral 架构。 | 必须修 | spec 改为独立静态 JS module；tasks Task 4.4 输出 `realtime-openai-adapter.js`。 |
| Medium | `/v1/realtime/event` token 与 session/call/merchant/provider 绑定不够明确。 | 必须修 | spec/tasks 增加 mismatch 返回 403 的验收与测试要求。 |
| Medium | OpenAI GA event correctness 只在 spec 中提示，没有独立任务。 | 必须修 | tasks 增加 Task 4.0，要求官方 event fixture 和检索日期。 |

## Second-Pass Review

第二次独立 review 结论：No blocking findings found。

已继续修复的 high/medium 项：

- `RealtimeEventIngestRequest` 增加 tool event 的安全字段入口：`tool_name`、`provider_call_id`、`tool_status`、`safe_summary`，并明确 raw arguments 不进入 event ingest contract。
- Task 4.7 改为更新 `voiceagents/api/static/realtime-openai-adapter.js`，`realtime-test.html` 只做 wiring。
- 移除 task 文档中的 `.gstack` restore 注释，避免把本地工具状态写入 spec package。
- Task 5.6 real-mode manual verification 输入补充 `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true`。

## CEO Review

需求聚焦在“先证明真实语音模型可用，并保留业务工具调用闭环”。不接电话供应商、不接 SaaS 配置、不存 raw audio 是正确的阶段边界，因为当前最大未知数是浏览器语音体验、Realtime tool call、转写审计与兜底能力。

关键商业风险不是 scope 太小，而是内部 demo 如果误暴露会产生模型费用和 PII 泄漏风险。因此 MVP 必须明确“研发测试开关”，不能把真实 provider endpoint 当成未来生产鉴权。

## Design Review

UI 范围是研发测试面板，不要求商家可用的产品体验。设计重点应是操作可恢复和状态可观察：

- Start/Stop/Mute 状态明确。
- 麦克风权限失败、client-secret 失败、SDP 失败、data channel close/error 都必须可见。
- 页面不能显示 `client_secret`、`tool_call_token`、Authorization header、OpenAI API key、未脱敏 transcript 或原始 tool arguments。

## Engineering Review

架构方向成立：后端 provider adapter 只负责 credential creation；浏览器 WebRTC adapter 负责 provider event normalization 和 provider-specific result submission；业务工具仍走现有 `RealtimeToolRouter`。

修订后的关键工程约束：

- OpenAI 是本阶段第一个 provider，不是核心业务模型。
- normalized event contract 在 `voiceagents/realtime/contracts.py`。
- OpenAI browser adapter 独立为静态 JS module，HTML 只做 wiring。
- event ingest 必须先 sanitize/redact 再写任何 JSONL。
- token 必须绑定 session/call/merchant/provider。

## DX Review

实现阶段必须保留 mock 自动化路径，真实 OpenAI 只作为手动验收：

- 自动化测试不需要真实 `OPENAI_API_KEY`。
- smoke 仍以 mock provider 为主。
- README 必须分别说明 mock 运行、real provider 开关、server-only key、manual checklist。
- Task 5.6/5.7 的手动证据写到 PR notes。

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|---|---|---|---|---|---|
| 1 | CEO | 保持 telephony/raw audio/SaaS backend out-of-scope | Mechanical | Pragmatic | 本阶段目标是验证真实浏览器语音 + tool loop，不扩大到电话供应商。 | 同时接 telephony。 |
| 2 | Security | 为 real provider client-secret 增加 dev gate | Mechanical | Completeness | 否则任何可达调用方都能消耗 OpenAI 分钟数。 | 只依赖网络隔离或 README 提醒。 |
| 3 | Security | 禁止 raw text 和 raw tool arguments 进入所有 JSONL/DOM | Mechanical | Explicit over clever | transcript 与工具参数都可能包含 PII，必须统一红线。 | 只保护 transcript repository。 |
| 4 | Engineering | browser provider adapter 拆成独立静态 JS module | Mechanical | DRY | 后续 DashScope/火山云扩展需要可测试 adapter，不应散落在 HTML。 | 把 OpenAI mapping 直接写在 HTML 中。 |
| 5 | DX | 增加浏览器失败路径验证 | Mechanical | Completeness | 静态 HTML 测试无法证明 WebRTC 权限、SDP、清理、重连行为。 | 仅保留静态页面断言。 |

## Final Gate

Recommendation: APPROVE AFTER USER CONFIRMATION.

理由：blocking/high findings 已经转化为 spec/tasks 的明确实现任务和验收项；当前没有发现需要改变产品方向的 blocker。进入实现前，需要用户确认修订后的 spec、tasks 和本 review artifact。
