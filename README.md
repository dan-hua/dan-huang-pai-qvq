# dan-huang-pai-qvq

## 拾途 · 求职搜索工作台

面向刚毕业的应届生、正在求职或待业的人、希望换工作的职场人，以及所有想寻找工作机会的人。拾途帮助用户从公开职位开始探索；当前只收录 Remotive 的公开远程岗位，并不覆盖所有地区、行业或线下工作。

先运行本机服务，再访问 `http://127.0.0.1:8765/`：

```bash
python app_server.py
```

在网页中输入目标职位、地区和技能即可搜索公开远程招聘信息。服务只绑定 `127.0.0.1`，其他设备无法连接；需要本机 Python 和访问 Remotive 的网络连接。

### 在线发布

- `render.yaml` 用于在 Render 创建 Python API；需要在 Render 登录并授权访问此 GitHub 仓库后，创建 Blueprint 服务。Render 免费实例空闲后可能休眠，首次访问会有冷启动延迟，不保证持续在线。
- GitHub Pages 工作流会从 `main` 构建前端。API 部署完成后，在仓库 **Settings → Secrets and variables → Actions → Variables** 添加 `SHITU_API_BASE_URL`，值填 Render 提供的 HTTPS 服务地址（例如 `https://your-api.onrender.com`），再运行 `Deploy Shitu to GitHub Pages` 工作流。
- Render 服务的 `ALLOWED_ORIGINS` 需包含 `https://dan-hua.github.io`；仓库提供的 `render.yaml` 已设定该值。前后端分离后 API 只允许此站点来源的浏览器跨域请求，开发机的回环地址仍可使用。
- 前端网址为 `https://dan-hua.github.io/dan-huang-pai-qvq/`。首次部署还需将 GitHub Pages 的发布源从当前分支/目录切换为 **GitHub Actions**。公开部署使用免费 Render 实例时可能休眠；Remotive 或 MyMemory 的限额和网络可用性也仍由第三方决定。
- Render 等托管商可能按其平台政策处理服务访问日志；本应用不记录客户端 IP、搜索词、翻译内容或请求参数。

### 能力与边界

- 点击搜索后会平滑滚动到结果区，加载中显示原创小猫跑步动画；数据返回后按职位、技能、地区与发布时间计算可解释的匹配分数，并支持排序、会话收藏和岗位详情。
- 每张岗位卡片只显示岗位介绍摘要；点“查看完整介绍”可在详情窗中阅读来源原文（最多展示 12,000 个字符），并可跳转到原始招聘页查看完整职位。详情中另有雇主官网搜索入口。匹配分数只是公开字段的条件相似度，不是录用概率。
- 可用右上角按钮切换中英文界面，所有网站自带介绍和状态文案一并切换。招聘标题、描述、地区、类别、岗位类型与标签默认显示来源原文；只有用户主动点某条岗位的“翻译”按钮时，这些公开岗位文字才会发送给 MyMemory 翻译 API，并可在原文/译文间切换。译文只保存在当前页面会话中。
- 结果区的“刷新结果”会重新执行当前条件匹配；为遵循岗位来源的访问频率建议，12 小时缓存有效期内继续使用缓存，不会强制重复访问岗位源。
- 搜索会读取来源的公开岗位列表；职位、技能与地区偏好都仅在当前浏览器中匹配。浏览器向同源本机 API 或部署后的固定 API 发送不带参数的 `GET /api/jobs`，服务端请求固定的 Remotive HTTPS 地址，不接受用户提供的 URL、搜索词或代理参数。
- 本地缓存 12 小时，避免频繁请求；来源说明岗位数据可能延迟约 24 小时。每条记录通过标题、公司、HTTPS 来源域名、链接和发布时间等基本检查，但这不等于雇主已确认岗位仍开放。申请前请到原始招聘页和公司官网复核。
- 浏览器 CSP 仅允许同源及指定 Render API 域名的数据请求；服务端再把外连固定为 Remotive 与 MyMemory HTTPS API，不接受任意代理地址。默认本机服务只绑定回环网卡；在线部署时由 Render 提供公网 HTTPS 入口，CORS 仅允许本站页面来源。服务仅提供白名单静态文件和限定 API；响应附带 CSP、`no-referrer`、`nosniff`、防嵌入和权限策略。没有第三方字体、CDN、分析器或广告脚本。
- 不收集、不上传或持久化简历、技能或地区偏好；收藏与译文仅保留在当前页面会话。浏览器缓存仅含公开岗位数据及抓取时间。API 到 Remotive 与 MyMemory 均使用经过证书校验的 HTTPS。只有用户主动点击外部链接时，所需职位词（Remotive）、公司/职位名（Google）或所选公开岗位文字（MyMemory）才会发送给相应网站；链接请求不带来源页面 Referrer。
- 应用不再另设每日翻译字符上限；但 MyMemory 匿名免费额度约为 5,000 字符/天，由服务商管理，应用无法取消。翻译功能仍可能因服务商配额、限流或网络故障暂不可用。每个翻译片段最多 450 字节，长文会拆分请求；详情页提供原文切换。若需更高可用或更严格的数据协议，应配置自有授权的付费翻译服务。
- 本机运行时服务只绑定 `127.0.0.1`；在线部署应通过 Render 等 HTTPS 托管服务，不要把本地开发服务自行改绑到 `0.0.0.0` 并暴露到互联网。此项目仍是 MVP，不能替代专业生产环境的可用性、隐私或安全审计。
- 这是一款透明的关键词/字段匹配 MVP，不包含大语言模型、全网搜索或对私人文件的访问；不会伪造“AI 已确认”的招聘事实。

### 三轮版本优化

1. **搜索与匹配**：从静态作品展示改为可检索的公开远程职位工作台，按条件给出可解释分数。
2. **证据与核验**：增加原始来源、发布时间、字段检查、雇主官网复核入口，并明确单一来源不能构成多方证实。
3. **隐私与可靠性**：技能/地区只在本地处理；增加回环地址服务、固定上游 HTTPS、同源 CSP、安全响应头、12 小时缓存、去重、错误状态、会话收藏和自动化测试。

### 使用与验证

```bash
python -m unittest discover -q
node tests/test_job_finder.js
```

前端不需构建。JavaScript 单测需 Node.js；Python 服务和服务端测试使用标准库。若岗位来源或网络不可用，页面会显示错误和 Remotive 直接搜索入口，不会用示例数据冒充真实职位。

## 局内行为监测原型

仓库包含一个可运行的 Python 遥测检测 MVP，可处理一局的 JSONL 事件并生成结构化风险报告。它使用透明规则与轻量评分给出 `observe`、`review` 或 `kick` 建议；可识别重复的服务器确认隔墙命中、不可见目标准星对齐和极端瞄准变化。**它不执行踢人、不读取屏幕/鼠标、不扫描进程，也不连接或修改 ACE**。

运行仓库内的演示遥测：

```powershell
python -m game_monitor --input examples\game_telemetry.jsonl
```

也可将游戏服务端导出的 JSONL 通过标准输入提供：

```powershell
Get-Content -Encoding utf8 match.jsonl | python -m game_monitor
```

每行必须是一个 JSON 对象，结构为 `{"timestamp_ms": 1000, "kind": "shot", "data": {...}}`。`aim` 事件需要 `angular_delta_deg`、`reaction_ms`、`target_visible`，可选 `occluded_target_alignment`；`shot` 事件需要 `hit`、`target_visible`、`line_of_sight_blocked`。事件时间戳必须按顺序递增或相等；最多处理 10,000 条事件，单行上限 16 KiB。报告打印到标准输出，格式错误会写到标准错误并以状态码 2 退出。

```python
from game_monitor import GameMonitor, TelemetryEvent

events = [
    TelemetryEvent(1000, "aim", {
        "angular_delta_deg": 8.0,
        "reaction_ms": 240,
        "target_visible": True,
    }),
    TelemetryEvent(1100, "shot", {
        "hit": True,
        "target_visible": True,
        "line_of_sight_blocked": False,
    }),
]
result = GameMonitor().evaluate(events, ace_status="unavailable")
print(result.to_dict())
```

事件字段必须由游戏服务器根据权威对局状态生成，不能直接信任客户端上报。只有在获得 ACE 厂商正式授权的集成后，才可把经认证的完整性状态传入 `ace_status`；默认 `unavailable` 不会影响风险分。当前评分是可解释的规则基线，不是已经训练或验证过的 AI 模型；命中被服务器确认穿过遮挡时，重复达到阈值才建议踢出，其他信号最多建议复核。上线前应使用真实对局数据校准阈值、评估误报，并由游戏服务端决定最终处置。

验证监测器与命令行：

```powershell
python -m unittest tests.test_game_monitor tests.test_game_monitor_cli -v
```

### 通用反作弊信号接入与融合

新增 `VendorAntiCheatAdapter` / `AntiCheatIngestor` 接口，可在游戏方提供正式 SDK 后接入完整性告警。厂商 SDK bridge 必须先验证事件来源、签名/授权和时效，再返回 `VerifiedSdkEvent`；未经认证的客户端 JSON 不能直接包装成“已验证”事件。适配器会校验厂商、会话、事件编号与严重级别，拒绝重复告警；接入器将规范化信号持久化到本地 SQLite。**目前没有 ACE 官方 SDK，因此本仓库没有 ACE bridge，也不应把模拟 bridge 当作真实 ACE 接入。**

```python
from game_monitor import (
    AntiCheatIngestor,
    EvidenceFusion,
    IntegritySignalStore,
    VendorAntiCheatAdapter,
)

# OfficialAceSdkBridge is supplied by the game/anti-cheat vendor.
signals_db = IntegritySignalStore("monitor-evidence.sqlite3")
adapter = VendorAntiCheatAdapter(
    OfficialAceSdkBridge(...),
    expected_vendor="authorized-vendor",
)
ingestor = AntiCheatIngestor(adapter, signals_db)
ingestor.ingest(official_sdk_callback_event)

signals = signals_db.list_signals(session_id="pseudonymous-match-id")
combined = EvidenceFusion().evaluate(
    session_id="pseudonymous-match-id",
    telemetry=server_telemetry_result,
    frame_evidence=frame_evidence_rows,
    integrity_signals=signals,
)
print(combined.to_dict())
signals_db.close()
```

融合报告会保留各来源评分与原因：服务端遥测、逐帧画面证据、反作弊完整性告警。单一最高分作为基线，多个独立来源同时超过复核阈值时增加有限佐证分；默认总分 40 建议复核，90 建议踢出。该结果只是服务端的处置建议，不会执行踢出或封禁；实际策略须由游戏运营方决定并基于授权数据校准。SQLite 可用 `IntegritySignalStore` 和 `LocalEvidenceStore` 查询；`--retention-days` 目前清理视频证据库，部署方还应对完整性信号设置适当留存策略。

### 逐帧画面监测接口

可在本机对自己有权处理的游戏录像逐帧运行演示系统。先安装视频解码依赖，再运行：

```powershell
python -m pip install -r requirements-game-monitor.txt
python -m game_monitor --video D:\Videos\match.mp4 --db D:\GameMonitor\evidence.sqlite3
```

可指定不含真实身份信息的对局 ID、画面变化阈值及证据保留时长：

```powershell
python -m game_monitor --video D:\Videos\match.mp4 --session-id match-demo --motion-threshold 0.22 --retention-days 7
```

命令逐帧解码整段录像，转为 320×180 灰度帧后进行轻量视觉变化分析；输出 JSON 汇总帧数、处理速度、最高风险与复核建议。可疑帧元数据立即写入本地 SQLite；默认每次启动清除超过 7 天的旧证据。证据库只保存局次伪名、帧号、时间戳、模型评分和原因代码，**不保存画面像素，也不上传到网络**。录像仅在本机解码处理。

此独立演示使用“画面变化”基线，突变也可能是正常转身、爆炸或切镜，因此结果只是复核线索，**并非训练好的反作弊 AI，也不能单凭画面证明外挂**。真实反作弊应将经验证的视觉模型输出与服务器权威事件融合。要开发授权的实时版本，捕获端可调用下方的 `LiveFrameMonitor` 接口：每帧同步分析，低置信度、可疑标签或高风险帧立即提交本地 SQLite。输入帧最大 4 MiB，帧号需递增。

```python
from game_monitor import (
    FrameAssessment,
    GameFrame,
    LiveFrameMonitor,
    LocalEvidenceStore,
)

class LocalVisionModel:
    def analyze(self, frame):
        prediction = your_local_model.predict(frame.image)
        return FrameAssessment(
            model_id="your-local-model-version",
            risk_score=prediction.risk * 100,
            confidence=prediction.confidence * 100,
            label=prediction.label,  # normal / suspicious / uncertain
            reasons=tuple(prediction.reason_codes),
        )

store = LocalEvidenceStore("monitor-evidence.sqlite3")
monitor = LiveFrameMonitor(LocalVisionModel(), store)
decision = monitor.process(GameFrame(
    session_id="pseudonymous-match-id",
    frame_index=1,
    captured_at_ms=16,
    width=1920,
    height=1080,
    image=game_only_frame_bytes,
))
print(decision.to_dict())
print(store.list_evidence(session_id="pseudonymous-match-id"))
store.close()
```

`your_local_model` 和 `game_only_frame_bytes` 是授权实时接入点，不包含在独立演示中。`inference_ms` 可用于测量单帧推理耗时；不保证特定帧率，需在目标设备测试。置信不足只记录证据供分析，不会自动处罚；部署前应设计权限控制、证据生命周期和游戏服务端处置。

逐帧管线测试：

```powershell
python -m unittest tests.test_game_monitor_frames -v
python -m unittest tests.test_game_monitor_video -v
python -m unittest tests.test_game_monitor_anticheat -v
```

## Python 论文写作 Agent

仓库还保留一个 Python 研究型论文写作 Agent，支持多源文献检索、研究计划、论文草稿、批判式自评和质量评估。

```bash
python -m paper_agent.cli "AI agents for research and software engineering" --output paper_output.md --json
```

```python
from paper_agent.core import ResearchPaperAgent

agent = ResearchPaperAgent("AI agents for research and software engineering")
bundle = agent.generate_paper_bundle()
print(bundle["title"])
print(bundle["evaluation"]["overall"])
```

论文 Agent 使用 Python 标准库，可在本地运行。验证命令：`python -m unittest discover -q`。

## GitHub Copilot agent

This repository includes the **Office and Development Partner** custom agent in `.github/agents/office-development.agent.md`. In a Copilot experience that supports repository custom agents, open the agent picker and select **Office and Development Partner**. If it is not listed, confirm the repository is available to that Copilot experience and that custom agents are supported there.

Use it for office-oriented writing and information work as well as software development grounded in this repository.

The agent can only work with files and tools available in the current Copilot session. It does not by itself connect to Word, Excel, Outlook, calendars, or other external services. Sending messages, changing shared documents, and creating events require an available integration and appropriate authorization; otherwise it can prepare copyable drafts or structured content.
