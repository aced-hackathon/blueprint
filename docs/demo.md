# Demo v2：30–60 秒实机录屏

演示前运行 `python app.py`，打开本机页面。最好在后端设置 `OPENAI_API_KEY`，并确认首页显示 **OpenAI API**；否则必须如实保留 **Scripted fallback** 标识。使用顶部客户选择器；每个场景开始先点击 **Reset scenario**。请勿输入真实客户信息或个人秘密。

| 时间 | 操作与画面 | 英文口播 |
| --- | --- | --- |
| 0:00–0:07 | 选择 Noah，点击 **Reset scenario**，停在首页建议卡 | “NextStep turns customer signals into a practical next step.” |
| 0:07–0:20 | 指向骑车通勤建议的 `15.36 kg CO₂e`，点击 **Compare two practical changes** | “The code calculates two illustrative behavior changes: bike commuting and a shorter grocery trip.” |
| 0:20–0:30 | 展示两项方案与公式，返回首页 | “Distances and current travel modes are explicit demo assumptions, not observed customer facts.” |
| 0:30–0:43 | 指向 **Facts → Signals → LLM interpretation → Possible why → Action** 链路和模式标识 | “The model interprets sanitized evidence and uncertainty. It never calculates the numbers or executes an action.” |
| 0:43–0:53 | **仅在 OpenAI API 已启用时**提问 “Why might the bike commute fit?”；否则跳到 Sofia | “Customers can ask why, while the concrete suggestion stays front and center.” |
| 0:53–1:00 | 切换 Sofia，点击 **Reset scenario**，展示押金建议 | “The same system also proposes a concrete deposit plan, with customer confirmation before any bank workflow.” |

如果只录 30 秒，保留 0:00–0:30 的 Noah 路径和最后一句 “Code computes; the model interprets; the customer decides.” 录屏前将浏览器缩放到能同时看清卡片和数值，关掉个人通知。可剪掉页面加载等待，但不要剪接成未发生的模型回复。

## 较长的完整路径（可选）

| 时间 | 点击与展示 | 讲述要点 |
| --- | --- | --- |
| 0:00–0:35 | Noah → Reset；看首页两张建议卡和五段链路 | “Code computes 15.36 kg from a fictional commute scenario. Model interpretation offers possible reasons, not facts. Action stays optional.” |
| 0:35–0:55 | Compare two practical changes → Save this idea | 展示骑车通勤和附近买菜的公式、路线未核验与食品产地限制；保存的是想法，不会预订行程。 |
| 0:55–1:15 | 返回首页，问 “Why could a bike commute help?” | 有密钥时为真正的 OpenAI 回答；无密钥时明确显示 Scripted fallback，不能称作实时 AI。 |
| 1:15–1:45 | Sofia → Reset；看第一屏押金数额和预估余额；确认目标 → 修改租金 | “The useful change appears first. Confirmation is required before entering the mock bank task.” 金额由代码计算。 |
| 1:45–2:05 | Privacy & evidence → 关闭 Spending trends | 实际模型输入立刻删除家居趋势；模型提案与后端动作决定分开展示。 |
| 2:05–2:25 | Thomas → Reset → 确认 → Remind me in 7 days → +7 days | 先没有站内提醒，推进时间后仅显示通用文案。 |
| 2:25–2:40 | Emma → Reset → I’m researching for a friend | 撤回搬家假设，停止该主题建议。 |
| 2:40–2:55 | Private space → 预览固定分享句子 | **明确说这里没有本地 LLM，只是隔离的 synthetic sandbox。** |

## 演示时的准确表述

- 银行端已实现真正的 OpenAI Responses API 调用，使用 `OPENAI_API_KEY`；现场若未设置或失败，必须展示 UI 上的 **Scripted fallback** 标识。没有密钥时，不可声称现场运行了模型。
- 数额和碳排变化是程序计算的；OpenAI 只负责解释、竞争假设、可能的动机与追问回答。动机只是假设。没有真实路线或可用商店查询。
- 私密区展示浏览器隔离和最小分享流程；没有真实本地 AI 推理，不能说已证明“无人能看见秘密”。
- 测试展示特定路径上的证据，不是全面安全认证。
- 顶部客户切换是评委合成数据工具，不是客户登录。
- 如需缩短至一分钟：展示 Noah 的两种已计算选择、五段链路与回答来源，再展示 Sofia 的押金建议。不要把不可用的私密模式说成已完成。

## 后续优先级

1. 在明确硬件、操作系统、设备所有权后，用不超过 15 分钟验证本地推理与运行时遥测；失败则保留不可用状态。
2. 配置测试用 `OPENAI_API_KEY` 后，人工验证一次真实模型返回的结构、质量、耗时与计费；现有模拟请求测试不能代替这一步。
3. 再考虑正式身份认证和真实银行接口的导师确认。当前没有已确认的官方 API 或比赛提交规范。
