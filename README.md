# dan-huang-pai-qvq

## AURA 光感实验室

一个无需安装依赖的单页创意工作室网站。直接在浏览器中打开 `index.html` 即可预览；移动端自适应，背景粒子会缓慢漂浮，点击时形成柔和涟漪。作品图片来自 Unsplash，需要联网加载。

## GitHub Copilot agent

This repository includes the **Office and Development Partner** custom agent in `.github/agents/office-development.agent.md`. In a Copilot experience that supports repository custom agents, open the agent picker and select **Office and Development Partner**. If it is not listed, confirm the repository is available to that Copilot experience and that custom agents are supported there.

Use it for office-oriented writing and information work (such as drafting or polishing documents, organizing notes, analyzing supplied tables, and preparing email or meeting drafts) as well as software development grounded in this repository (understanding code, making focused changes, testing, and reviewing).

The agent can only work with files and tools available in the current Copilot session. It does not by itself connect to Word, Excel, Outlook, calendars, or other external services. Sending messages, changing shared documents, and creating events require an available integration and appropriate authorization; otherwise it can prepare copyable drafts or structured content.

## Python 论文写作 Agent

这个仓库还包含一个可运行的 Python 版本“研究型论文写作 Agent”。它面向研究者、学生和工程师，已升级到第三版，具备以下能力：

- 主题分析、研究问题与研究空白（gap）识别
- arXiv + Crossref 多源文献检索（网络可用时），并保留本地兜底参考
- 研究计划生成：问题、动机、假设、方法、评估指标、风险、贡献
- 论文结构设计：摘要、引言、研究空白、相关工作、方法、评测、讨论、结论
- 论文草稿生成、批判式自评与修订
- CLI 可直接输出 Markdown 文件，并支持 JSON 研究分析输出

### 使用方式

```bash
python -m paper_agent.cli "AI agents for research and software engineering" --output paper_output.md --json
```

也可以在 Python 中直接调用：

```python
from paper_agent.core import ResearchPaperAgent

agent = ResearchPaperAgent("AI agents for research and software engineering")
bundle = agent.generate_paper_bundle()
print(bundle["title"])
print(bundle["evaluation"]["overall"])
```

### 设计特点

- 参考真实学术工作流：问题定义 → 文献检索 → 空白分析 → 研究计划 → 论文草稿 → 批判修订 → 质量评估
- 面向三类读者：研究者关注创新与严谨性，学生关注理解路径和可解释性，工程师关注工程落地与评估方法
- 代码基于标准库实现，避免强依赖，可在本地直接运行
- 支持更接近真实科研写作的“研究缺口分析”和“同行评审式修订”

### 验证

```bash
python -m unittest discover -q
```
