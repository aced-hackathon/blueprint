# KBC Private NextStep — Demo v2

一个可运行的本地 hackathon 原型：**先给出具体建议，再让客户追问原因与假设。** 程序计算交易趋势、行为信号、押金现金流和低碳出行对比；接着把最小化的结构化上下文交给 OpenAI 模型解释情况、竞争解释、可能动机与不确定性。动作仍由后端政策决定。界面为英文；数据全部合成。此项目是独立概念演示，不连接 KBC，也不代表其官方产品或能力。

## 在 VS Code 运行

需要 Python 3.10+；本机验证使用 Python 3.14.3。应用只依赖 Python 标准库，不需要 pip install。没有密钥时，界面会明确标注 **Scripted fallback**。要启用**真实 OpenAI 解释与追问**，在启动后端的同一个终端设置环境变量：

```powershell
$env:OPENAI_API_KEY = '<your key>'
$env:OPENAI_MODEL = 'gpt-6-luna'  # 可省略；默认 GPT-6 Luna
python app.py --port 8001
```

打开 <http://127.0.0.1:8001> 查看启用密钥的实例。`8001` 用来避开当前可能仍运行在 `8000` 的离线实例；这两个服务的状态数据库相同，避免同时对同一客户演示写操作。密钥只由后端读取，不会发给浏览器或写入 SQLite。不要把密钥提交到 Git，也不要在聊天里发送密钥。该调用使用 [OpenAI Responses API 的严格 JSON Schema 输出](https://developers.openai.com/api/docs/guides/structured-outputs)，请求设置 `store: false`；这不代表零保留或个人设备本地推理。此工作环境没有 `OPENAI_API_KEY`，所以本次**没有实测真实账号的 API 回答**；请求格式和解析路径由隔离的 HTTP 模拟测试验证。

若只想运行离线回退：

```powershell
cd C:\Users\Eric\Documents\ChatGPT\hacka
python app.py
```

打开 <http://127.0.0.1:8000>。停止：在启动它的终端按 `Ctrl+C`。端口被占用时可用 `python app.py --port 8001`。

VS Code 也可以从 **Terminal → Run Task → Run Private NextStep** 启动。安装 Python/Debugger 扩展后，`F5` 可使用项目的调试配置。

## 已实现

- **Noah：低碳行为选择。** 两次路线预览和三次指南浏览是可能兴趣，不等于确认的气候目标。程序基于明示的**虚构出行假设**算出骑车通勤两天约 `15.36 kg CO₂e/四周` 和改为短途骑车买菜约 `5.63 kg CO₂e/四周` 的**汽车直接排放**变化。可比较公式、风险、来源并保存一个想法；不会声称真实路线或商店已查证。
- **Sofia：具体搬家建议。** 第一屏直接展示估算押金、下一月现金流和适用条件。六个月汇总趋势与指南浏览只构成假设；客户确认后才能进入押金准备。租金、押金月数、搬家费可编辑；后端用整数分计算。三个准备步骤完成后记录模拟结果。
- **Thomas：选择稍后。** 确认后延后七天，保存进度；顶部 `+7 days` 推进会话里的演示时钟，显示不含财务细节的站内提醒预览。
- **Emma：纠正误判。** “I’m researching for a friend” 撤回搬家假设，抑制后续建议。
- **事实 → 信号 → LLM 解释 → 可能动机 → 行动。** 首页可见整条链路。客户可以在建议下追问；有密钥时使用 OpenAI Responses API，无密钥或失败时明确标注脚本回退。模型不做金额或碳排计算，也不能凭建议直接执行动作。
- **Privacy & evidence。** 开关控制进入模型上下文的汇总字段；页面显示结构化请求、校验后的提案和后端政策决定。
- **Private space。** 独立的浏览器沙盒演示；明确显示 **Private mode unavailable**。对话保留在沙盒页面内存，回复为固定脚本。只有用户勾选确认后，才能导出预览过的固定搬家语句。
- **可重复演示。** 固定随机种子、2026-09-30 起始日期、每个客户单独重置、SQLite 保存银行流程进度。

## 必须如实说明的边界

**银行建议已接入真实 OpenAI API 路径；私密区仍不是 LLM。** 银行侧结构化汇总和客户主动输入的追问，在配置密钥时会发给 OpenAI。不要在追问里输入秘密。私密区无经验证的个人设备本地推理，始终保持脚本沙盒；不会静默切到 OpenAI。

低碳系数 `160 g/km`、两条距离和当前出行模式都是演示假设，不是从银行卡推断或从地图验证。这里只比较被替换的汽车行程的直接排放；自行车生命周期、食物生产、商品价格和供应状况都未计算。**本地食物不必然更低碳**；参见 [食物影响背景](https://ourworldindata.org/faqs-environmental-impacts-food) 和 [英国政府转换因子目录](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025)。

顶部客户选择器是**高权限合成数据演示工具**；并非生产登录、授权或多租户安全证明。普通客户 API 从会话确定客户，拒绝调用方传入的客户标识，但任何访问本地演示的人都能使用该选择器。

本地 HTTP 服务只绑定 `127.0.0.1`，用于开发展示。银行侧 SQLite 数据持久保存，未做静态加密或自动保留期删除；所有同一客户的演示会话共享该客户状态。私密文本不发送给服务端、不存入浏览器存储；操作系统、管理员、浏览器扩展或屏幕录制不在已实现保护范围内。

## 验证

```powershell
python -m unittest discover -s tests -v
```

可选浏览器验证需要 Playwright 和浏览器，仅用于开发验收，不是应用运行依赖：

```powershell
# 在已配置 Playwright 的开发环境运行
node tests/browser.cjs
# 如果未安装 Playwright 自带浏览器，可设置 BROWSER_EXECUTABLE 指向 Chromium/Edge
```

浏览器脚本操作正在运行的本地 demo 并重置四个合成场景；请勿对正在演示或有需保留进度的实例执行。可使用 `DEMO_URL` 指向专门测试实例。单元测试会屏蔽环境中的真实密钥，绝不会为测试发起真实付费调用。

验证说明、复现步骤和局限见 [docs/validation.md](docs/validation.md)；30–60 秒实机录屏脚本见 [docs/demo.md](docs/demo.md)。

## 文件结构

```text
app.py                   本地 HTTP、会话、CSRF、路由与 CSP
nextstep/store.py        SQLite 表、固定种子合成数据
nextstep/engine.py       汇总、信号、字段白名单、校验、策略与任务
nextstep/impact.py       用合成出行参数确定性计算可比较选项
nextstep/llm.py          OpenAI Responses API 结构化输出与短期内存缓存
static/                  英文响应式界面、独立私密沙盒
tests/test_demo.py       数据、策略、会话与隐私边界测试
tests/browser.cjs        真实浏览器流程、canary 与请求观察
.vscode/                 运行任务和 Python 调试配置
docs/                    架构、演示和验证说明
data/                    运行时 SQLite（不纳入 Git）
artifacts/               本地验收截图和报告（不纳入 Git）
```

工程设计见 [docs/architecture.md](docs/architecture.md)。真实 OpenAI 接口已用于银行建议流程；私密模式没有远程后备。

## English pitch

**Private NextStep turns permitted evidence into a concrete, explainable suggestion.** Code calculates the facts and possible changes. An OpenAI model, when configured, interprets the context, offers competing explanations and answers follow-up questions; backend rules retain control of actions. The demo compares a moving deposit plan and two illustrative lower-carbon travel changes while respecting “later,” corrections and sharing boundaries. All data is synthetic; personal-device private AI remains future work.
