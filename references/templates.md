# Templates

## Canonical Paper Note

```markdown
---
tags:
  - paper-note
  - <domain-tag>
  - <year>
  - task-<task-slug>
  - category-<core-or-related>
  - method-<method-slug>
title: "<paper title>"
year: <year>
venue: <venue>
tier: <tier>
subtype: <task subtype>
category: <category>
official_url: <url-or-N/A>
doi: <doi-or-N/A>
---

# <paper title>

[[<prefix>-索引|返回总索引]]

## 基本信息

- 作者：待补
- 年份：<year>
- 来源：<venue>
- 质量层级：<tier>
- 分类位置：<core / related / mainlist>
- 任务子类：<subtype>
- 方法标签：<method tags>
- 官方页面：<url>
- PDF：![[assets/paper_pdfs/已入库/<paper>.pdf]]
- 关键图片：![[assets/paper_figures/已入库/<paper>_figure_main.png]]
- 图片说明：<why this image matters>
- 主要实验结果图表（可选）：![[assets/paper_figures/已入库/<paper>_table_main_1.png]]

## 背景

<what broader problem this paper sits in>

## 动机

<what exact gap the authors think prior work misses>

## 方法总览

<compress the full method into one or two paragraphs>

## 方法家族定位

<which method family or route this belongs to>

## 方法拆解

1. <step/module 1>
2. <step/module 2>
3. <step/module 3>

## 关键增益点

- <gain 1>
- <gain 2>

## 与经典方法的区别

- <difference 1>
- <difference 2>

## 核心公式

<only the formulas worth remembering>

## 公式如何理解

- <reading hint 1>
- <reading hint 2>

## 实验与结果

<main datasets, main metrics, strongest evidence>

### 主要实验结果图表（可选）

![[assets/paper_figures/已入库/<paper>_table_main_1.png]]

## 结论

<what the paper is worth remembering for>

## 与当前项目的相关性

<why this belongs in the current knowledge base>

## 证据边界与后续补强

- <what was verified from full text>
- <what still needs deeper reading>
```

## Track Page Template

```markdown
---
tags:
  - index
  - <prefix>
  - <track-slug>
---

# <title> 子任务清单 [[<prefix>-索引|返回总索引]]

> 纯索引页，只保留该子任务的分组、入口和待补清单。

## 快速入口

- 代表论文：待补
- 桥接 / 强相关：待补

## 推荐阅读路径

1. 待补

## 核心主线

- 待补

## 桥接 / 强相关

- 待补

## 待补条目

- 待补
```

## Quality Checklist

写完一篇成熟笔记后，至少检查下面几项：

- 所有占位文字都被替换掉
- 作者、来源、层级、任务子类都已填写
- PDF 和关键图至少补齐其一，最好两者都有
- 如果保留了结果表截图，裁剪区域不能接近整页；接近整页时改用手工 bbox 重做
- 章节顺序保持稳定，不要随意改名
- `与当前项目的相关性` 不是空话
- `证据边界与后续补强` 明确说明目前掌握到什么程度
