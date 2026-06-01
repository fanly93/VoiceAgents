# OpenAI Realtime 真实语音接入 MVP 交接文档

更新时间：2026-06-01

## 当前任务

VoiceAgents OpenAI Realtime 真实语音接入 MVP 已通过 PR #4 合并到 `main`。
本文档现在作为 post-merge archive handoff，记录已落地范围、验收证据、豁免项和后续跟进项。

目标是在现有文本智能客服和 browser/local realtime plumbing 基础上，提供一个研发测试可用的真实语音 MVP：

- 浏览器麦克风输入。
- OpenAI Realtime WebRTC 真实语音会话。
- 浏览器播放模型语音输出。
- 使用现有 `tool_call_token` / tool relay 执行订单、物流、商品知识、转人工工具。
- 保存结构化事件 JSONL 和脱敏 transcript JSONL。
- 不接电话供应商，不接真实电话，不保存 raw audio，不接 SaaS 商家配置、知识库后台或客服后台。

## 当前 Git 状态

已合并基线：

```bash
main / origin/main
```

合并记录：

```text
PR #4: https://github.com/fanly93/VoiceAgents/pull/4
Merge commit: 35f16a9 OpenAI Realtime voice MVP
Merged at: 2026-06-01
```

当前归档 checkpoint 分支：

```bash
docs/post-merge-realtime-archive
```

checkpoint 开始前工作区状态：

```bash
git status --short --branch
# ## main...origin/main
```

最近关键提交：

```bash
35f16a9 OpenAI Realtime voice MVP
6bc1b56 Merge pull request #3 from fanly93/docs/gstack-review-before-merge
cc4f1e4 docs: clarify gstack review timing
383d24b test: use realistic realtime validation fixtures
237de6c docs: refresh realtime voice MVP handoff
4710473 feat: add realtime browser adapter and controls
c22b06d feat: wire realtime provider event ingest and logs
59f7414 docs: align realtime MVP validation checklists
8238903 chore: add checkpoint workflow guardrails
e89f632 feat: add realtime event contracts
```

本阶段已经从文档阶段推进到合并归档阶段。自动化测试和 mock smoke 已通过；真实 OpenAI 语音手动验收的核心路径已经完成。订单/物流真实模式重测按用户确认改为 scoped waiver，浏览器 failure-mode 异常路径已在 PR #6 中补充自动化模拟覆盖。

## 重要项目规范

本项目使用项目级 gstack，规则在 `AGENTS.md`。

关键点：

- 使用 `.agents/skills/` 下的项目级 gstack。
- 优先使用 `$gstack-office-hours`、`$gstack-browse`、`$gstack-qa`、`$gstack-review`、`$gstack-autoplan`。
- 不要调用根 `$gstack`。
- 每个新需求必须从干净 `main` 新建 feature branch。
- `$gstack-review` 要在 feature branch 合并前运行。
- Python 开发和验证必须使用隔离环境，例如 `.venv` 或 conda，不使用系统 Python。
- 每完成一个可以独立验证的小功能、修复或文档更新，先测试并 checkpoint commit，再进入下一项。
- 探索性测试、浏览器自动化探针、合成音频、日志样本等默认放入已忽略目录，例如 `test-artifacts/` 或 `.voiceagents/`，不得混入正式提交。

手动运行 gstack 命令时使用项目级环境：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

## 已完成内容

### 1. Spec、tasks、review 与 checklist

已更新：

```text
docs/specs/voiceagents-openai-realtime-voice-mvp.md
docs/specs/voiceagents-openai-realtime-voice-mvp-tasks.md
docs/specs/openai-realtime-phase4-browser-checklist.md
docs/specs/voiceagents-openai-realtime-voice-mvp-manual-checklist.md
README.md
```

当前文档明确：

- OpenAI Realtime 是本阶段第一个真实 provider。
- 业务层保持 provider-neutral。
- 真实 provider dev endpoint 默认关闭，需要 `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true`。
- 所有日志禁止保存 raw audio、audio bytes、SDP、OpenAI API key、client secret、tool token、Authorization header、未脱敏 transcript、未脱敏 tool arguments。
- `VOICEAGENTS_TRANSCRIPT_LOGGING=off|structured|transcript`。
- 真实 OpenAI 3 分钟会话是手动验收，不进入自动化测试依赖。

### 2. 后端 Realtime provider、event ingest 与安全日志

已实现：

- `OpenAIRealtimeProvider` 真实 OpenAI client secret HTTP boundary。
- OpenAI 默认模型与语音：
  - `VOICEAGENTS_OPENAI_REALTIME_MODEL=gpt-realtime-2`
  - `VOICEAGENTS_OPENAI_REALTIME_VOICE=marin`
- `output_modalities` 根据 `response_mode=text|voice` 初始化。
- `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS` gate。
- localhost / same-origin dev origin 校验。
- client-secret 基础 rate limit。
- `/v1/realtime/event`。
- `/v1/realtime/tool-call` 绑定 `session_id`、`call_id`、`merchant_id`、`provider`。
- `tool_call_token` 不以明文持久化。
- blocked event key 拦截：`raw_audio`、`audio`、`audio_bytes`、`client_secret`、`tool_call_token`、`authorization`、`sdp`。
- 结构化 event JSONL 和 transcript JSONL repository。
- 写入前脱敏 transcript 和 safe summary。

主要文件：

```text
voiceagents/api/app.py
voiceagents/realtime/contracts.py
voiceagents/realtime/event_log.py
voiceagents/realtime/providers.py
voiceagents/realtime/session_store.py
voiceagents/realtime/tool_router.py
```

### 3. 浏览器 Realtime test page、OpenAI adapter 与工具桥接

已实现：

- `/realtime-test` WebRTC 测试页。
- 浏览器 `getUserMedia({ audio: true })`。
- 本地音轨加入 `RTCPeerConnection`。
- remote audio 元素用于播放模型语音。
- 用 ephemeral client secret 调 OpenAI `/v1/realtime/calls`。
- 独立 OpenAI browser adapter：

```text
voiceagents/api/static/realtime-openai-adapter.js
```

- OpenAI provider events 归一化为内部 normalized events。
- normalized events relay 到 `/v1/realtime/event`。
- OpenAI tool call relay 到 `/v1/realtime/tool-call`。
- tool result 回传 OpenAI function call output。
- tool result 后排队 `response.create`，避免 active response race。
- Text / Voice runtime 切换通过 `session.update` 更新 `output_modalities`。
- data channel open 后会重新应用当前 response mode。
- Mute 切换本地音轨 `track.enabled`，并更新 UI 状态。
- Stop / failure cleanup 会关闭 data channel、peer connection、local tracks、remote audio，并清理 secret-bearing state。

主要文件：

```text
voiceagents/api/static/realtime-test.html
voiceagents/api/static/realtime-openai-adapter.js
tests/fixtures/openai_realtime_events.json
```

### 4. 自动化测试

已通过全量测试：

```bash
./.venv/bin/python -m pytest
# 163 passed, 1 warning
```

重点测试覆盖：

- provider-neutral contracts
- OpenAI client secret request/response
- real provider dev gate
- `/v1/realtime/event`
- `/v1/realtime/tool-call`
- blocked key rejection
- transcript JSONL redaction
- structured JSONL redaction
- session token/provider/call/merchant binding
- browser adapter event mapping
- realtime test page controls and cleanup paths
- realtime failure-mode browser JS simulation:
  - client-secret failure
  - microphone permission denial
  - SDP exchange failure cleanup
  - data channel close/error
  - reconnect after failure

合并后补充 smoke 验证：

```bash
NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
./.venv/bin/python scripts/smoke_api.py --base-url http://127.0.0.1:8001
# health ok; customer-requests-human, logistics-tracking, low-asr-confidence,
# order-status, product-usage scenarios passed

NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
./.venv/bin/python scripts/smoke_realtime_api.py --base-url http://127.0.0.1:8001
# health ok; mock client-secret; lookup_order, lookup_logistics,
# query_product_knowledge, handoff_to_human passed; auth/tool rejection passed
```

## 合并后状态与延期项

状态：

- 已完成：真实 OpenAI Realtime 超过 3 分钟连续语音会话，页面未刷新，后端未崩溃。
- 已完成：Text 模式仅文字输出，切到 Voice 后有语音输出。
- 已完成：Mute/Unmute 切换后 Provider Events 显示 `mute_state=muted|unmuted`，会话不断开。
- 已完成：`query_product_knowledge` 命中真实感商品知识。
- 已完成：`query_product_knowledge` 低置信结果触发 `handoff_to_human`。
- 已完成：当前 real-mode session 的 JSONL 日志安全抽查，未发现 `client_secret`、`tool_call_token`、Authorization、SDP、raw audio 或未脱敏 transcript。
- Scoped waiver：用户确认不再继续手测 `lookup_order` 和 `lookup_logistics` 真实模式重测；这两条路径由 mock/API/pytest 覆盖，并已替换为真实感合成订单号 `ORD-20260601-1842`。
- 已完成：`$gstack-review` merge 前审查、review findings 修复、push、PR、merge。
- 已完成：PR #6 补齐浏览器 failure-mode 自动化模拟覆盖：
  - microphone permission denied
  - client-secret failure
  - SDP exchange failure cleanup
  - data channel close/error
  - reconnect after failure
- 可选跟进：真实浏览器手动复测上述 failure-mode，但不再作为当前 MVP 阻塞项。

## 2026-06-01 Real-Mode 手动验收记录

环境：

- URL：`http://127.0.0.1:8000/realtime-test`
- Provider：`openai_realtime`
- Model：`gpt-realtime-2`
- Browser：用户本机 Chrome
- 麦克风：真实浏览器麦克风，由用户朗读完成
- Transcript logging：`structured`

结果：

| 验收项 | 状态 | 证据/备注 |
|---|---|---|
| 真实 OpenAI session 建立 | PASS | 页面 Session State 进入 connected/ended，Provider Events 显示 `provider=openai_realtime`、`data_channel=open` |
| 3 分钟连续语音会话 | PASS | 用户确认测试时长超过 3 分钟，多轮对话持续完成 |
| Text 模式 | PASS | Text 模式下无语音，仅 Assistant Response/Transcript 文本更新 |
| Voice 模式 | PASS | 切到 Voice 后有模型语音输出 |
| Mute/Unmute | PASS | Provider Events 连续显示 `mute_state=muted` / `mute_state=unmuted`，本地音轨切换不结束会话 |
| `query_product_knowledge` 命中 | PASS | LunaCare 假发清洗问题返回知识库答案 |
| `query_product_knowledge` 低置信转人工 | PASS | 知识库无足够信息时触发 `handoff_to_human` |
| `handoff_to_human` | PASS | Handoff 面板进入转人工原因，例如 `order_id_unconfirmed` 或低置信相关 handoff |
| `lookup_order` real-mode 重测 | WAIVED | 用户确认不再继续手测；mock/API/pytest 覆盖，真实感订单号为 `ORD-20260601-1842` |
| `lookup_logistics` real-mode 重测 | WAIVED | 用户确认不再继续手测；mock/API/pytest 覆盖，真实感物流数据为 YTO Express / Shanghai Hongqiao sorting center |
| JSONL 日志安全抽查 | PASS | 当前 `.voiceagents/events/realtime-events.jsonl` 抽查未发现 secrets、SDP、raw audio、未脱敏 transcript |
| Failure-mode 验证 | PASS | Stop cleanup、Mute 已手动覆盖；permission denied、client-secret failure、SDP failure、data channel close/error、failure 后 reconnect 已由 `tests/test_realtime_test_page_failure_modes.py` 自动化模拟覆盖 |

Latency 面板说明：当前 UI 的 Latency 表示最近一次 client-secret/start 或 tool relay/event relay 的局部耗时，不是端到端语音响应延迟。

## 已知测试经验与注意事项

浏览器自动化 fake microphone 路线存在误判风险：

- in-app browser 无法可靠注入 fake mic。
- Chrome 带 `--use-fake-device-for-media-stream` 时可能得到静音假设备。
- 去掉该参数时可能回到真实系统麦克风，不能证明 WAV 文件进入 Realtime。
- 因此当前真实语音验收优先使用真实浏览器麦克风，由用户朗读或用手机播放测试音频。

本地生成的临时音频和探针在 `test-artifacts/`，已被 `.gitignore` 忽略，不纳入提交。

历史生成的短音频位于：

```text
test-artifacts/realtime-audio/order_lookup_zh.wav
test-artifacts/realtime-audio/logistics_lookup_zh.wav
test-artifacts/realtime-audio/knowledge_query_zh.wav
test-artifacts/realtime-audio/handoff_request_zh.wav
```

这些音频属于 `test-artifacts/` 临时产物，若要继续使用手机播放，建议先按当前测试句子重新生成，避免播放旧占位词。当前更推荐直接朗读这些句子：

```text
请查询订单 ORD-20260601-1842 的订单状态。
请查询订单 ORD-20260601-1842 的物流信息。
请查询商品知识库：LunaCare 假发护理套装应该怎么清洗假发？
我要转人工客服。
```

## Real-Mode 验证准备

启动命令必须在隔离 `.venv` 环境中运行：

```bash
set -a
source .env
set +a
VOICEAGENTS_REALTIME_PROVIDER=openai_realtime \
VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true \
VOICEAGENTS_TRANSCRIPT_LOGGING=structured \
./.venv/bin/python -m uvicorn voiceagents.api.main:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/realtime-test
```

验收顺序：

1. 确认 `.env` 已包含有效 `OPENAI_API_KEY`。
2. Start，授权浏览器麦克风。
3. 完成 3 分钟真实语音会话。
4. 依次触发当前需要手测的工具；订单/物流 real-mode 重测已按用户确认 scoped waiver，由 mock/API/pytest 覆盖。
5. 确认 Transcript、Assistant Response、Tool Calls、Handoff、Provider Events 面板符合预期。
6. 检查 `.voiceagents/events/realtime-events.jsonl` 不含 secrets、SDP、raw audio、未脱敏 transcript。
7. 如需更高信心，可选做真实浏览器 failure-mode 复测；当前自动化模拟已覆盖 MVP 阻塞项。

## 下一步建议

当前最优下一步：

1. 提交本次 PR #6 post-merge archive 文档归档 checkpoint。
2. 若开启新需求，从干净 `main` 新建 feature branch，并继续小步 checkpoint。
3. 可选补充真实浏览器 failure-mode 手动复测记录；这不是当前 MVP 阻塞项。

## 推荐新会话开局命令

```bash
git status --short --branch
git log --oneline -8
sed -n '1,220p' AGENTS.md
sed -n '1,260p' OPENAI_REALTIME_VOICE_MVP_HANDOFF.md
sed -n '1,260p' docs/specs/voiceagents-openai-realtime-voice-mvp-tasks.md
```
