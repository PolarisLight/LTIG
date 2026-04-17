# research-knowledge-base-builder

Reusable Codex skill for building and maintaining a domain research knowledge base in an Obsidian vault.

This skill packages a layered workflow that starts from web discovery instead of requiring a pre-existing local PDF pile. It includes:

- web harvesting from sources such as arXiv, DBLP, and Crossref
- vault scaffolding for index pages, track pages, pending queue, exclusion list, audit page, and browser view
- canonical paper-note templates
- tight method-figure and results-table extraction from PDFs

## What Is In This Repo

- `SKILL.md`: the skill entrypoint and workflow
- `agents/openai.yaml`: display metadata for Codex
- `references/`: method notes, templates, web-harvest guide, and figure-cropping guide
- `scripts/`: scaffolding, harvesting, and PDF region extraction utilities

## Example Trigger

Use the skill in Codex with:

```text
Use $research-knowledge-base-builder to harvest candidate papers from the web and scaffold or maintain a domain knowledge base in my Obsidian vault.
```

## Example Commands

Harvest candidate papers from the web:

```bash
python scripts/harvest_topic_papers.py \
  --topic "long-tailed visual recognition" \
  --query "long-tailed visual recognition" \
  --query "long tail recognition" \
  --query "class imbalance recognition" \
  --vault "/path/to/vault" \
  --prefix "ltvr" \
  --download-pdfs
```

Scaffold a new layered vault structure:

```bash
python scripts/scaffold_research_kb.py \
  --vault "/path/to/vault" \
  --prefix "mmmissing" \
  --title "Missing Modality Learning" \
  --track "core|Core Line" \
  --track "bridge|Bridge Questions"
```

Extract the main method figure and results table from a paper PDF:

```bash
python scripts/extract_paper_key_regions.py \
  --pdf "/path/to/paper.pdf" \
  --out-dir "/path/to/assets/paper_figures/已入库"
```

## Notes

- The workflow is opinionated around Obsidian-based literature management.
- The harvesting step is designed as a repeatable coverage pass, not as a guarantee of literal completeness.
- PDF figure/table extraction uses heuristics and supports manual bounding-box overrides when automatic crops are low confidence.
