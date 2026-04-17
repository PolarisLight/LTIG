# research-knowledge-base-builder

一个面向 Codex 的可复用技能，用来在 Obsidian 知识库中自动构建和维护某个研究领域的论文知识库。

这个技能不是“再记一篇论文”的小工具，而是一套可迁移的方法：先从网页检索候选论文，再下载可达 PDF，随后搭建分层知识库骨架、维护标准化论文笔记，并从 PDF 中裁剪关键方法图和主实验结果表。

## 适用场景

- 从零开始建立一个新领域的论文知识库
- 把当前项目中的论文管理方法迁移到别的方向
- 把一堆扁平的 PDF / 笔记整理成结构化的 Obsidian 知识库
- 持续维护某个研究方向的候选论文池、待处理队列和成熟笔记

## 核心能力

- 从 `arXiv`、`DBLP`、`Crossref` 等来源抓取候选论文
- 根据标题 / DOI 去重，并与当前 vault 进行比对
- 默认将可直达的 PDF 下载到待处理目录
- 自动生成主索引、子任务页、待处理清单、不相关条目、审计页和浏览器页
- 使用统一模板维护成熟论文笔记
- 从 PDF 中裁剪紧致的关键方法图和主结果表，避免整页截图

## 仓库结构

- `SKILL.md`
  技能主入口与完整 workflow
- `agents/openai.yaml`
  Codex 展示名与默认触发描述
- `references/`
  方法说明、模板、网页抓取说明、PDF 图表裁剪规则
- `scripts/`
  抓取、脚手架搭建、关键区域截图提取脚本

## 在 Codex 中调用

直接这样触发：

```text
Use $research-knowledge-base-builder to harvest candidate papers from the web and scaffold or maintain a domain knowledge base in my Obsidian vault.
```

你也可以直接用自然语言说：

- 用 `research-knowledge-base-builder` 给我建一个某某领域知识库
- 先从网页自动检索某个方向的论文，再搭建知识库
- 维护我现有的论文知识库，并补齐 PDF、截图和标准化笔记

## 常用命令

### 1. 从网页抓取候选论文

```bash
python scripts/harvest_topic_papers.py \
  --topic "long-tailed visual recognition" \
  --query "long-tailed visual recognition" \
  --query "long tail recognition" \
  --query "class imbalance recognition" \
  --vault "/path/to/vault" \
  --prefix "ltvr"
```

说明：

- 提供 `--vault` 时，脚本会默认尝试下载可达 PDF
- 如果你只想抓元数据，不想下载 PDF，可以显式加上 `--skip-pdf-download`

### 2. 搭建知识库骨架

```bash
python scripts/scaffold_research_kb.py \
  --vault "/path/to/vault" \
  --prefix "mmmissing" \
  --title "Missing Modality Learning" \
  --track "core|Core Line" \
  --track "bridge|Bridge Questions"
```

### 3. 提取关键方法图和主结果表

```bash
python scripts/extract_paper_key_regions.py \
  --pdf "/path/to/paper.pdf" \
  --out-dir "/path/to/assets/paper_figures/已入库"
```

## 工作流摘要

1. 先从网页 harvest 候选论文，而不是先等本地 PDF 准备好。
2. 自动下载可达 PDF，进入待处理目录。
3. 根据研究问题拆分子任务，而不是按年份或会议机械分组。
4. 搭建主索引、子任务页、待处理清单、浏览器和审计页。
5. 用统一模板维护成熟笔记。
6. 从 PDF 中提取关键方法图和主结果表。
7. 持续维护 `core / bridge / pending / excluded` 的状态边界。

## 注意事项

- 网页抓取是“可重复的覆盖性搜索”，不是对整个领域的绝对完备保证。
- 有些来源只提供元数据，不提供可直接下载的 PDF。
- 图表裁剪是启发式流程；如果自动裁剪置信度低，建议切换到手工 bbox。
- 这个 workflow 明显偏向 Obsidian + 研究型论文知识库管理场景。
