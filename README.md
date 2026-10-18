# dan-huang-pai-qvq

## 拾途 · 求职搜索工作台

面向刚毕业的应届生、正在求职或待业的人、希望换工作的职场人，以及所有想寻找工作机会的人。拾途帮助用户从公开职位开始探索；当前只收录 Remotive 的公开远程岗位，并不覆盖所有地区、行业或线下工作。

先运行本机服务，再访问 `http://127.0.0.1:8765/`：

```bash
python app_server.py
```

在网页中输入目标职位、地区和技能即可搜索公开远程招聘信息。服务只绑定 `127.0.0.1`，其他设备无法连接；需要本机 Python 和访问 Remotive 的网络连接。

### 能力与边界

- 点击搜索后会平滑滚动到结果区，加载中显示原创小猫跑步动画；数据返回后按职位、技能、地区与发布时间计算可解释的匹配分数，并支持排序、会话收藏和岗位详情。
- 每张岗位卡片只显示岗位介绍摘要；点“查看完整介绍”可在详情窗中阅读来源原文（最多展示 12,000 个字符），并可跳转到原始招聘页查看完整职位。详情中另有雇主官网搜索入口。匹配分数只是公开字段的条件相似度，不是录用概率。
- 可用右上角按钮切换中英文界面，所有网站自带介绍和状态文案一并切换。招聘标题、描述、地区、类别、岗位类型与标签默认显示来源原文；只有用户主动点某条岗位的“翻译”按钮时，这些公开岗位文字才会发送给 MyMemory 翻译 API，并可在原文/译文间切换。译文只保存在当前页面会话中。
- 结果区的“刷新结果”会重新执行当前条件匹配；为遵循岗位来源的访问频率建议，12 小时缓存有效期内继续使用缓存，不会强制重复访问岗位源。
- 搜索会读取来源的公开岗位列表；职位、技能与地区偏好都仅在当前浏览器中匹配。浏览器只向本机发送不带参数的 `GET /api/jobs`，服务端请求固定的 Remotive HTTPS 地址，不接受用户提供的 URL、搜索词或代理参数。
- 本地缓存 12 小时，避免频繁请求；来源说明岗位数据可能延迟约 24 小时。每条记录通过标题、公司、HTTPS 来源域名、链接和发布时间等基本检查，但这不等于雇主已确认岗位仍开放。申请前请到原始招聘页和公司官网复核。
- 浏览器 CSP 仅允许本机同源数据请求；服务端再把外连固定为 Remotive HTTPS API，不接受任意代理地址。服务绑定回环网卡，且仅提供白名单静态文件与只读 API；响应附带 CSP、`no-referrer`、`nosniff`、防嵌入和权限策略。没有第三方字体、CDN、分析器或广告脚本。
- 不收集、不上传或持久化简历、技能或地区偏好；收藏与译文仅保留在当前页面会话。浏览器缓存仅含公开岗位数据及抓取时间。API 到 Remotive 与 MyMemory 均使用经过证书校验的 HTTPS。只有用户主动点击外部链接时，所需职位词（Remotive）、公司/职位名（Google）或所选公开岗位文字（MyMemory）才会发送给相应网站；链接请求不带来源页面 Referrer。
- 应用不再另设每日翻译字符上限；但 MyMemory 匿名免费额度约为 5,000 字符/天，由服务商管理，应用无法取消。翻译功能仍可能因服务商配额、限流或网络故障暂不可用。每个翻译片段最多 450 字节，长文会拆分请求；详情页提供原文切换。若需更高可用或更严格的数据协议，应配置自有授权的付费翻译服务。
- 这是本机求职 MVP 的应用层网络隔离，不会替用户修改操作系统/路由器防火墙，也不是面向公网的生产服务。不要把本服务改绑到 `0.0.0.0` 或直接暴露到互联网。
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
